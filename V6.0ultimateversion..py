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

# 1. DeepSeek Key
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
os.environ["OPENAI_API_KEY"] = DEEPSEEK_API_KEY
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# 2. CosyVoice 本地地址
LOCAL_API_URL = "http://127.0.0.1:50000/inference_zero_shot"

# 3. 参考音频
REF_AUDIO_PATH = "my_voice.wav"
REF_TEXT = "人总是要死的，但死的意义有不同。中国古时候有个文学家叫做司马迁的说过：人固有一死，或重于泰山，或轻于鸿毛"

# 4. 资料文件
DATA_FILE = "knowledge_base.txt"

# ================= 🛡️ 核心人设 (V7.7 实在靠谱·接地气版) =================
SYSTEM_PROMPT = """
你是一个**实在、靠谱**的手表源头工厂代表。
你的目标是：用**正常、接地气、专业**的商务话介绍产品，建立信任，引导进【粉丝群】。

【🔒 核心底线 (必须死记硬背)】
1. **全场统一价**：**$179 USD (美元)**。
   - ❌ 严禁说： "几百到几千"、"看配置定价"、"价格不一"。
   - ✅ 必须说： "我们要么不做，做就做顶配，全场统一 179 美元"。
2. **货币单位**：默认报 **美元 (USD)**。
3. **渠道**：源头工厂直销，没有中间商。

【🚫 语言禁忌 (拒绝忽悠)】
1. **严禁夸张**：不要说 "皇家级"、"艺术品"、"手术刀"、"千百次" 这种虚词。
   - 要说： "扎实"、"耐用"、"做工精细"、"工业级标准"。
2. **严禁品牌名/WhatsApp**：只准提 "粉丝群"。
3. **严禁废话**：不要堆砌辞藻，直接说这表好在哪，服务好在哪。

【🗣️ 说话风格 (实在感)】
1. **重事实**：多讲 "904L实心钢"、"日本机芯"、"出厂质检" 这些看得见摸得着的。
2. **重承诺**：强调 "发货拍视频"、"不满意能退"，让客户觉得咱们做事规矩。

【参考资料 (Context)】:
{context}
"""

# ================= ⚙️ 全局变量 =================
input_queue = queue.Queue()
translator = GoogleTranslator(source='zh-CN', target='en')
pygame.mixer.init()


# ================= 🛠️ 工具函数 =================

def clean_text_for_tts(text):
    text = text.replace("*", "").replace("#", "").replace("- ", "")
    text = re.sub(r'\[.*?\]', '', text)
    return text.strip()


def translate_cn_to_en(text_cn):
    try:
        print(f"🇨🇳 [中文原文]: {text_cn}")
        text_en = translator.translate(text_cn)
        print(f"🇺🇸 [英文译文]: {text_en}")
        return text_en
    except Exception as e:
        print(f"❌ 翻译失败: {e}")
        return text_cn


def generate_audio(text_en):
    if not text_en: return None
    filename = f"temp_{uuid.uuid4().hex}.wav"
    payload = {'tts_text': text_en, 'prompt_text': REF_TEXT}
    try:
        with open(REF_AUDIO_PATH, 'rb') as audio_file:
            files = [('prompt_wav', ('prompt_wav', audio_file, 'application/octet-stream'))]
            response = requests.request("GET", LOCAL_API_URL, data=payload, files=files)
            if response.status_code == 200:
                with wave.open(filename, 'wb') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(22050)
                    wav_file.writeframes(response.content)
                return filename
    except Exception as e:
        print(f"❌ 语音合成失败: {e}")
    return None


def play_audio_blocking(filename):
    if not filename or not os.path.exists(filename): return
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

def setup_rag_brain():
    print("正在连接 DeepSeek...")
    llm = ChatOpenAI(
        model="deepseek-chat",
        openai_api_base=DEEPSEEK_BASE_URL,
        temperature=1.0,  # V7.0 灵活性设定
        max_tokens=300
    )

    print("正在加载 Embedding 模型...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            f.write("临时资料：源头工厂手表，售价179美元。")

    loader = TextLoader(DATA_FILE, encoding="utf-8")
    docs = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
    splits = text_splitter.split_documents(docs)

    print("正在构建知识库索引...")
    vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{input}"),
    ])

    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
    return rag_chain


def input_listener():
    while True:
        try:
            u_in = input()
            if u_in.strip(): input_queue.put(u_in)
        except:
            pass


# ================= 🚀 主程序逻辑 (V7.7 修复版) =================
def main():
    if "xxxx" in DEEPSEEK_API_KEY:
        print("请填写 Key！")
        return

    # 1. 初始化大脑 (这里会自动读取上面定义的 SYSTEM_PROMPT)
    rag_chain = setup_rag_brain()
    print("\n⌚️ 智能体已就绪 (V7.7 实在靠谱·接地气版)！")

    # 2. 启动耳朵
    t = threading.Thread(target=input_listener, daemon=True)
    t.start()

    print("👉 可以在下方输入弹幕...")

    # 👇 定义计数器
    speech_count = 0
    next_ad_threshold = random.randint(3, 5)

    while True:
        # A. 检查是否有弹幕
        has_question = not input_queue.empty()
        query_text = ""

        # B. 分流处理
        if has_question:
            # --- 分支1: 有人提问 ---
            user_msg = input_queue.get()
            if user_msg in ["exit", "退出", "quit"]: break

            print(f"\n💬 [收到弹幕]: {user_msg}")
            # 回答问题：要实在，别整虚的
            query_text = f"用户问：'{user_msg}'。请用实在、靠谱的语气回答。不要提品牌名。回答完后，告诉他'粉丝群里有实拍视频'，让他自己去看。"

        else:
            # --- 分支2: 没人提问 (自动吆喝 - V7.7 实在话术篇) ---
            topics = [
                # 1. 针对“材质做工” (实心钢)
                "请介绍手表的'材质'。强调全是'实心钢'，拿在手里很沉、很有分量，表带打磨得很光滑，不夹汗毛，戴着舒服。",

                # 2. 针对“机芯稳定性” (日本机芯)
                "请介绍'机芯'。强调我们用的是'日本进口机芯'，走时很准，出厂前都测过摇表仪，不会戴两天就停，很省心。",

                # 3. 针对“信任服务” (发货检查)
                "请介绍我们的'发货流程'。告诉大家：每块表发货前，我们都会仔细检查外观和走时，还会拍个发货视频给你确认，没问题再发货。",

                # 4. 针对“售后保障” (维修退换)
                "请介绍'售后服务'。强调我们做长久生意的，有保修，哪里坏了随时找我们，不像有些地方卖完就不理人了。",

                # 5. 针对“日常佩戴” (防水防刮)
                "请介绍'耐用性'。强调是蓝宝石镜面，平时磕磕碰碰不容易花；防水也做得好，洗手淋雨完全没问题。",

                # 6. 针对“源头价格” (179)
                "请解释为什么卖'$179'。直接说因为是源头工厂，少赚点，走个量。同样的品质，你去专柜得多花十几倍的冤枉钱。"
            ]

            topic_instruction = random.choice(topics)

            # 👇 核心逻辑：判断是不是该打广告了？
            speech_count += 1

            if speech_count >= next_ad_threshold:
                # 👉 触发引流：给个实在的理由
                print(f"🔔 [触发引流] 第 {speech_count} 句，插入粉丝群广告")
                suffix = "注意：最后一句要自然地说：'欢迎新人进入直播间，想看发货视频或者细节图的，直接进粉丝群，我发给你看'。"
                speech_count = 0
                next_ad_threshold = random.randint(3, 5)
            else:
                # 👉 平时：只聊产品
                print(f"📢 [纯干货] 第 {speech_count} 句，不打广告")
                suffix = "注意：**严禁提及粉丝群**，只专注讲产品哪里好，哪里实在。"

            # 组合最终指令 (强调说人话)
            query_text = f"现在没人说话，{topic_instruction}。请用诚恳、做生意的口吻陈述，不要用夸张形容词。注意：1.绝不提品牌名和WhatsApp。2.多用'扎实'、'靠谱'这种词。3.{suffix} 字数70字左右。"

        # --- C. 公共执行流程 ---
        try:
            print("🧠 思考中...")
            result = rag_chain.invoke({"input": query_text})
            cn_text = result['answer']

            # 1. 清洗 & 翻译
            clean_cn = clean_text_for_tts(cn_text)
            en_text = translate_cn_to_en(clean_cn)

            # 2. 合成 & 播放
            audio_file = generate_audio(en_text)
            if audio_file:
                play_audio_blocking(audio_file)

            # 3. 休息
            print("⏳ (说完休息1秒...)\n")
            time.sleep(1)

        except Exception as e:
            print(f"❌ 流程出错: {e}")
            time.sleep(1)


if __name__ == "__main__":
    main()