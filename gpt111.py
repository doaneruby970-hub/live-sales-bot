import os
import sys
import time
import threading
import queue
import random
import requests
import wave
import uuid
import re
import pygame
from deep_translator import GoogleTranslator
from collections import deque
from difflib import SequenceMatcher

# ================= 🛡️ 兼容性导入修复 =================
try:
    from langchain_openai import ChatOpenAI
except ImportError:
    from langchain_community.chat_models import ChatOpenAI

try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain_community.document_loaders import TextLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain


# ================= 🔴 配置区域 =================

# DeepSeek Base URL
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# CosyVoice 本地地址（按你要求：不改 GET）
LOCAL_API_URL = "http://127.0.0.1:50000/inference_zero_shot"

# 参考音频
REF_AUDIO_PATH = "my_voice.wav"
REF_TEXT = "人总是要死的，但死的意义有不同。中国古时候有个文学家叫做司马迁的说过：人固有一死，或重于泰山，或轻于鸿毛"

# 资料文件
DATA_FILE = "knowledge_base.txt"

# 中文输出硬限制
MAX_CN_LEN = 70

# 最近话术记忆（防复读）
recent_lines = deque(maxlen=10)

# ✅ CTA 改短：保证永远不截断 + 更像口语
CTA_SHORT = "想看发货视频和细节图，进粉丝群我发你"

# ✅ stop_event：线程正常退出，避免 Ctrl+C 的 stdin 锁报错
stop_event = threading.Event()

# ✅ Key 配置（推荐用环境变量；也可以填 KEY_HARDCODE）
# Windows PowerShell: setx DEEPSEEK_API_KEY "sk-你的完整key"
KEY_HARDCODE = os.getenv("DEEPSEEK_API_KEY", "")  # 从环境变量读取，不要硬编码密钥


# ================= 🛡️ 核心人设（含反复读规则） =================
SYSTEM_PROMPT = """
你是一个实在、靠谱的手表源头工厂代表。

【核心底线】
1) 全场统一价：$179 USD
   必须用这句表达：我们要么不做，做就做顶配，全场统一179美元
2) 默认货币：美元（USD）
3) 源头工厂直销，没有中间商

【禁忌】
- 不要夸张词（皇家级/艺术品/千百次等），改用：扎实、耐用、做工细、工业级标准
- 禁止品牌名/WhatsApp；除非用户指令明确要求“提粉丝群”，否则不要提“粉丝群”
- 简短、说人话，别堆辞藻

【反复读规则（关键）】
最近说过的话术（只用于避重复）：
{recent}
要求：
- 不要复用以上内容的整句/固定短语
- 同一卖点换说法，并补充一个新细节（材质/机芯/质检/发货/售后之一）

【输出限制】
- 输出必须是中文
- 输出必须≤70个汉字（含标点）

【参考资料（Context）】:
{context}
"""


# ================= ⚙️ 全局变量 =================
input_queue = queue.Queue()
translator = GoogleTranslator(source="zh-CN", target="en")
pygame.mixer.init()


# ================= 🛠️ 工具函数 =================
def validate_api_key(key: str) -> str:
    """
    防止 httpx Headers ascii 编码炸：
    - strip 去掉空格/换行
    - 必须 ascii
    - 必须 sk- 开头
    """
    k = (key or "").strip()
    if not k:
        raise ValueError("DEEPSEEK_API_KEY 为空：请设置环境变量或在代码里 KEY_HARDCODE 填入真实 key。")
    try:
        k.encode("ascii")
    except UnicodeEncodeError:
        raise ValueError("DEEPSEEK_API_KEY 含中文/特殊字符：只保留 sk- 开头的英文数字串（不要带空格/换行/中文）。")
    if not k.startswith("sk-"):
        raise ValueError("DEEPSEEK_API_KEY 格式不对：必须以 sk- 开头。")
    return k


def clean_text_for_tts(text: str) -> str:
    text = text.replace("*", "").replace("#", "").replace("- ", "")
    text = re.sub(r"\[.*?\]", "", text)
    return text.strip()


def smart_truncate_cn(text: str, max_len: int = MAX_CN_LEN) -> str:
    """
    中文≤max_len：尽量在标点处截断，避免半句。
    """
    t = (text or "").strip()
    if len(t) <= max_len:
        return t

    cut = t[:max_len]
    puncts = "。！？；，、"
    best = -1
    for p in puncts:
        pos = cut.rfind(p)
        if pos > best:
            best = pos

    if best >= max(12, max_len - 18):
        cut = cut[:best + 1]
    return cut.strip()


def sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a or "", b or "").ratio()


def is_too_similar(text: str, history, threshold: float = 0.88) -> bool:
    """
    和最近几条太像，就算重复
    """
    hlist = list(history)[-4:]
    for h in hlist:
        if sim(text, h) >= threshold:
            return True
    return False


def reserve_and_append_cta(body_cn: str, cta: str = CTA_SHORT, max_len: int = MAX_CN_LEN) -> str:
    """
    ✅ 关键：CTA 永远完整不被截断
    - 先给 CTA 预留空间
    - 正文截断后再拼接
    """
    cta = (cta or "").strip()
    if not cta:
        return smart_truncate_cn(body_cn, max_len)

    reserve = len(cta) + 1  # 预留一个标点
    if reserve >= max_len:
        # CTA 太长就直接截短 CTA（但我们 CTA 已经很短，基本不会走这里）
        return smart_truncate_cn(cta, max_len)

    body = smart_truncate_cn(body_cn, max_len - reserve)
    body = body.rstrip("，。；！？、")
    return f"{body}，{cta}".strip()


def translate_cn_to_en(text_cn: str) -> str:
    try:
        print(f"🇨🇳 [中文原文]: {text_cn}")
        text_en = translator.translate(text_cn)
        print(f"🇺🇸 [英文译文]: {text_en}")
        return text_en
    except Exception as e:
        print(f"❌ 翻译失败: {e}")
        return text_cn


def generate_audio(text_en: str):
    """
    按你要求：GET + data + files 不改
    """
    if not text_en:
        return None
    filename = f"temp_{uuid.uuid4().hex}.wav"
    payload = {"tts_text": text_en, "prompt_text": REF_TEXT}

    try:
        with open(REF_AUDIO_PATH, "rb") as audio_file:
            files = [("prompt_wav", ("prompt_wav", audio_file, "application/octet-stream"))]
            response = requests.request("GET", LOCAL_API_URL, data=payload, files=files)

            if response.status_code == 200:
                with wave.open(filename, "wb") as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(22050)
                    wav_file.writeframes(response.content)
                return filename
            else:
                print(f"❌ TTS接口返回码: {response.status_code}")

    except Exception as e:
        print(f"❌ 语音合成失败: {e}")

    return None


def play_audio_blocking(filename: str):
    if not filename or not os.path.exists(filename):
        return
    try:
        print("🔊 正在播放...")
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        pygame.mixer.music.unload()
        os.remove(filename)
    except Exception as e:
        print(f"❌ 播放出错: {e}")


# ================= 🧠 大脑初始化 =================
def build_llm(base_url: str):
    """
    修复你之前报错：top_p/frequency_penalty/presence_penalty 必须显式传参
    兼容不同版本：base_url 或 openai_api_base
    """
    kwargs = dict(
        model="deepseek-chat",
        temperature=0.9,
        max_tokens=260,
        top_p=0.9,
        frequency_penalty=0.7,
        presence_penalty=0.5,
    )

    try:
        return ChatOpenAI(base_url=base_url, **kwargs)
    except TypeError:
        return ChatOpenAI(openai_api_base=base_url, **kwargs)


def setup_rag_brain():
    print("正在连接 DeepSeek...")
    llm = build_llm(DEEPSEEK_BASE_URL)

    print("正在加载 Embedding 模型...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            f.write(
                "资料：源头工厂直销手表，全场统一179美元。\n"
                "材质：实心钢，拿手里有分量，表带打磨顺滑不夹毛。\n"
                "机芯：日本机芯，走时稳定，出厂校时测试。\n"
                "镜面：蓝宝石镜面，日常耐刮。\n"
                "防水：洗手淋雨没问题，日常佩戴省心。\n"
                "质检：出厂检查外观与走时。\n"
                "发货：发货前拍视频确认再发。\n"
                "售后：不满意可退换，支持保修。\n"
            )

    loader = TextLoader(DATA_FILE, encoding="utf-8")
    docs = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=60)
    splits = text_splitter.split_documents(docs)

    print("正在构建知识库索引...")
    vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings)

    # ✅ MMR：减少每次检索到相同内容
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 4, "fetch_k": 12, "lambda_mult": 0.7},
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{input}"),
    ])

    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
    return rag_chain


def input_listener():
    """
    非 daemon：通过 stop_event 正常退出，避免 Ctrl+C stdin 锁报错
    """
    while not stop_event.is_set():
        try:
            u_in = input()
            if u_in.strip():
                input_queue.put(u_in)
        except (EOFError, KeyboardInterrupt):
            stop_event.set()
            return
        except:
            pass


# ================= 🚀 主程序逻辑 =================
def main():
    # 读取 key：环境变量优先，其次 KEY_HARDCODE
    key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not key:
        key = (KEY_HARDCODE or "").strip()

    try:
        key = validate_api_key(key)
    except Exception as e:
        print(f"❌ Key 配置错误：{e}")
        print("✅ 建议：Windows PowerShell 执行：setx DEEPSEEK_API_KEY \"sk-你的完整key\"，然后重启 VSCode/终端")
        return

    os.environ["OPENAI_API_KEY"] = key

    rag_chain = setup_rag_brain()
    print("\n⌚️ 智能体已就绪（反复读 + 70字硬限制 + 重复自动重写 + CTA不截断）！")

    t = threading.Thread(target=input_listener)
    t.start()

    print("👉 可以在下方输入弹幕...（输入 exit/退出/quit 结束）")

    speech_count = 0
    next_ad_threshold = random.randint(3, 5)

    topics = [
        "讲材质：实心钢，佩戴有分量，表带打磨顺滑不夹毛。",
        "讲机芯：日本机芯，走时稳定，出厂测过走时。",
        "讲发货：发前看外观和走时，拍视频确认再发。",
        "讲售后：不满意可退换，有问题支持保修。",
        "讲耐用：蓝宝石镜面更耐刮，洗手淋雨没问题。",
        "讲价格：源头工厂直销，全场统一179美元。"
    ]

    try:
        while not stop_event.is_set():
            has_question = not input_queue.empty()
            query_text = ""
            should_add_cta = False  # ✅ 由代码拼 CTA，模型正文禁止出现“粉丝群”

            if has_question:
                user_msg = input_queue.get()
                if user_msg in ["exit", "退出", "quit"]:
                    stop_event.set()
                    break

                print(f"\n💬 [收到弹幕]: {user_msg}")

                # 用户提问：回答正文不提粉丝群，最后由代码拼 CTA
                should_add_cta = True
                query_text = (
                    f"用户问：{user_msg}\n"
                    f"要求：实在、靠谱、说人话；不提品牌名/WhatsApp；默认美元。\n"
                    f"正文里禁止出现“粉丝群”三个字（我会在最后自动加引导）。\n"
                    f"必须≤{MAX_CN_LEN}个汉字（含标点）。"
                )

            else:
                topic_instruction = random.choice(topics)

                speech_count += 1
                if speech_count >= next_ad_threshold:
                    print(f"🔔 [触发引流] 第 {speech_count} 句，插入粉丝群广告")
                    should_add_cta = True
                    speech_count = 0
                    next_ad_threshold = random.randint(3, 5)
                else:
                    print(f"📢 [纯干货] 第 {speech_count} 句，不打广告")
                    should_add_cta = False

                if should_add_cta:
                    query_text = (
                        f"现在没人说话，请按这个点说：{topic_instruction}\n"
                        f"要求：别夸张、讲规矩、尽量换说法；必须≤{MAX_CN_LEN}个汉字。\n"
                        f"正文里禁止出现“粉丝群”三个字（我会在最后自动加引导）。"
                    )
                else:
                    query_text = (
                        f"现在没人说话，请按这个点说：{topic_instruction}\n"
                        f"要求：别夸张、讲规矩、尽量换说法；必须≤{MAX_CN_LEN}个汉字。\n"
                        f"禁止提粉丝群，只讲产品或服务。"
                    )

            # ========= 公共执行 =========
            print("🧠 思考中...")

            recent_text = "\n".join(recent_lines) if recent_lines else "（暂无）"
            result = rag_chain.invoke({"input": query_text, "recent": recent_text})

            cn_text = clean_text_for_tts(result.get("answer", "").strip())

            # 先做一次截断（正文）
            cn_text = smart_truncate_cn(cn_text, MAX_CN_LEN)

            # ✅ 重复检测：太像就自动重写一次
            if is_too_similar(cn_text, recent_lines, threshold=0.88):
                rewrite_prompt = (
                    "把下面这句话换一种完全不同的说法，意思不变。\n"
                    "要求：中文≤70字；不要用相同开头与句式；不要提品牌名/WhatsApp；正文里禁止出现“粉丝群”。\n"
                    f"原句：{cn_text}"
                )
                result2 = rag_chain.invoke({"input": rewrite_prompt, "recent": recent_text})
                cn_text2 = smart_truncate_cn(clean_text_for_tts(result2.get("answer", "").strip()), MAX_CN_LEN)
                if cn_text2 and (not is_too_similar(cn_text2, recent_lines, threshold=0.88)):
                    cn_text = cn_text2

            # ✅ 如果需要引流：由代码拼 CTA，保证 CTA 不被截断
            if should_add_cta:
                cn_text = reserve_and_append_cta(cn_text, CTA_SHORT, MAX_CN_LEN)
            else:
                cn_text = smart_truncate_cn(cn_text, MAX_CN_LEN)

            # 写入记忆（把 CTA 去掉再存，避免把模型卡死）
            mem = cn_text.replace(CTA_SHORT, "").strip().rstrip("，。；！？、")
            if mem:
                recent_lines.append(mem)

            # 翻译 -> TTS -> 播放
            en_text = translate_cn_to_en(cn_text)
            audio_file = generate_audio(en_text)
            if audio_file:
                play_audio_blocking(audio_file)

            print("⏳ (说完休息1秒...)\n")
            time.sleep(1)

    except KeyboardInterrupt:
        stop_event.set()

    finally:
        stop_event.set()
        try:
            t.join(timeout=1.0)
        except:
            pass


if __name__ == "__main__":
    main()
