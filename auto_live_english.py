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
from deep_translator import GoogleTranslator  # 引入翻译库

# 检查库安装
try:
    from openai import OpenAI
except ImportError:
    print("❌ 缺少库，请运行: pip install openai pygame requests deep-translator")
    sys.exit(1)

# ================= 🔴 配置区域 =================

# 1. DeepSeek Key
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# 2. CosyVoice 本地地址
LOCAL_API_URL = "http://127.0.0.1:50000/inference_zero_shot"

# 3. 参考音频 (你的声音样本)
REF_AUDIO_PATH = "my_voice.wav"

# 4. 参考音频对应的文字 (必须精准)
REF_TEXT = "人总是要死的，但死的意义有不同。中国古时候有个文学家叫做司马迁的说过：人固有一死，或重于泰山，或轻于鸿毛"

# 5. 产品资料
DATA_FILE = "my_watch_data.txt"

# ================= ⚙️ 全局变量 =================

input_queue = queue.Queue()  # 存放弹幕
translator = GoogleTranslator(source='zh-CN', target='en')  # 翻译器初始化

# 初始化音频
try:
    pygame.mixer.init()
except:
    pass


# ================= 🛠️ 工具函数 =================

def load_knowledge_base():
    if not os.path.exists(DATA_FILE): return "暂无资料"
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return f.read()


def clean_text_for_tts(text):
    """
    🧹 清洗文本：去掉 ** # 这种Markdown符号和表情，防止TTS读乱码
    """
    # 去掉 markdown 符号
    text = text.replace("*", "").replace("#", "").replace("- ", "")
    # 去掉中括号里的内容 (比如 [思考中])
    text = re.sub(r'\[.*?\]', '', text)
    # 去掉多余空格
    text = text.strip()
    return text


def get_deepseek_content(client, messages, temperature=1.0):
    """获取 DeepSeek 的中文回复"""
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=temperature,
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ DeepSeek 报错: {e}")
        return None


def translate_cn_to_en(text_cn):
    """🇨🇳 -> 🇺🇸 翻译函数"""
    try:
        print(f"🇨🇳 [中文原文]: {text_cn}")
        # 翻译
        text_en = translator.translate(text_cn)
        print(f"🇺🇸 [英文译文]: {text_en}")
        return text_en
    except Exception as e:
        print(f"❌ 翻译失败: {e}")
        return text_cn  # 如果翻译挂了，就只能读中文了


def generate_audio(text_en):
    """调用 CosyVoice 生成音频"""
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
    """
    🎵 播放音频（阻塞模式）
    意思就是：不播完这个文件，程序绝对不往下走！
    这样保证了不会“话还没说完就被截断”
    """
    if not filename or not os.path.exists(filename): return

    try:
        print("🔊 正在播放...")
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()

        # 循环检查是否播完
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)

        pygame.mixer.music.unload()
        os.remove(filename)  # 播完删除
    except Exception as e:
        print(f"❌ 播放出错: {e}")


# ================= 👂 监听线程 =================
def input_listener():
    """只负责收听弹幕，收到了就放进队列，不干扰主程序"""
    while True:
        try:
            u_in = input()
            if u_in.strip(): input_queue.put(u_in)
        except:
            pass


# ================= 🚀 主程序逻辑 =================
def main():
    if "xxxx" in DEEPSEEK_API_KEY:
        print("请填写 Key！")
        return

    # 启动监听线程
    t = threading.Thread(target=input_listener, daemon=True)
    t.start()

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    knowledge = load_knowledge_base()

    # 提示词：强制中文思考，不要带表情
    system_prompt = f"""
    你是一个高情商的带货主播。
    【资料】：{knowledge}
    【规则】：
    1. 必须用**中文**生成内容（后面代码会自动翻译）。
    2. 不要使用任何表情符号（emoji）、星号（**）或特殊符号。
    3. 只要纯文本，句子要通顺，适合口语表达。
    4. 每次只说一两句话，不要长篇大论。
    """

    print("✅ 系统已启动：中文思考 -> 英文翻译 -> 英文语音")
    print("👉 可以在下方输入弹幕，主播说完当前这句后会回复你。")

    while True:
        # 1. 检查有没有弹幕要回
        # (如果没有弹幕，input_queue.empty() 就是 True)
        has_question = not input_queue.empty()

        messages = [{"role": "system", "content": system_prompt}]

        if has_question:
            # --- 有人提问 ---
            user_msg = input_queue.get()
            if user_msg in ["exit", "退出"]: break

            print(f"\n💬 [收到弹幕]: {user_msg}")
            messages.append({"role": "user", "content": f"用户问：{user_msg}。请用中文简短回答。"})
        else:
            # --- 没人提问 (自动吆喝) ---
            topics = ["介绍一款表", "催单", "强调价格", "强调售后"]
            topic = random.choice(topics)
            messages.append({"role": "user", "content": f"现在没人说话，请用中文吆喝一句，主题是{topic}。"})

        # 2. DeepSeek 生成中文
        cn_text = get_deepseek_content(client, messages)
        if not cn_text: continue

        # 3. 清洗文本 (去掉乱七八糟的符号)
        clean_cn = clean_text_for_tts(cn_text)

        # 4. 翻译成英文
        en_text = translate_cn_to_en(clean_cn)

        # 5. 合成语音
        audio_file = generate_audio(en_text)

        # 6. 播放 (必须播完才往下走)
        if audio_file:
            play_audio_blocking(audio_file)

        # 7. 关键点：每说完一句话，强制休息 5 秒
        # 这期间如果有人发弹幕，会存进队列，等睡醒了下一轮处理
        print("⏳ (说完休息5秒...)\n")
        time.sleep(5)


if __name__ == "__main__":
    main()