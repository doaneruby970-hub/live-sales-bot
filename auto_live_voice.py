import os
import sys
import time
import threading
import queue
import random
import requests
import wave
import uuid
import pygame

# 检查库安装
try:
    from openai import OpenAI
except ImportError:
    print("❌ 缺少库，请运行: pip install openai pygame requests")
    sys.exit(1)

# ================= 🔴 配置区域 (请修改这里) =================

# 1. DeepSeek Key
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# 2. CosyVoice 本地地址 (端口 50000)
LOCAL_API_URL = "http://127.0.0.1:50000/inference_zero_shot"

# 3. 参考音频文件 (你的声音样本)
REF_AUDIO_PATH = "my_voice.wav"

# 4. 参考音频对应的文字 (必须要和录音内容一致)
REF_TEXT = "人总是要死的，但死的意义有不同。"

# 5. 产品资料库文件
DATA_FILE = "my_watch_data.txt"

# ================= ⚙️ 全局队列与状态 =================

# 存放用户输入的弹幕
input_queue = queue.Queue()

# 存放待合成的文字 (Text -> Audio)
tts_queue = queue.Queue()

# 存放待播放的音频文件 (WAV -> Speaker)
play_queue = queue.Queue()

# 控制打断的标志位
is_interrupted = False

# 初始化播放器
try:
    pygame.mixer.init()
except Exception as e:
    print(f"❌ 音频设备初始化失败: {e}")


# ================= 🧠 功能函数 =================

def load_knowledge_base():
    """读取手表资料"""
    if not os.path.exists(DATA_FILE):
        return "（未找到资料文件，请自由发挥）"
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return f.read()


def call_deepseek(client, messages, temperature=1.0):
    """调用 DeepSeek 生成文本"""
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=temperature,
            stream=False
        )
        return response.choices[0].message.content
    except Exception:
        return "网络有点卡，大家稍等。"


def generate_cosyvoice_audio(text, filename):
    """调用 CosyVoice API 合成语音"""
    payload = {
        'tts_text': text,
        'prompt_text': REF_TEXT
    }
    try:
        if not os.path.exists(REF_AUDIO_PATH):
            print(f"❌ 找不到参考音频: {REF_AUDIO_PATH}")
            return False

        with open(REF_AUDIO_PATH, 'rb') as audio_file:
            files = [('prompt_wav', ('prompt_wav', audio_file, 'application/octet-stream'))]
            # 发送请求
            response = requests.request("GET", LOCAL_API_URL, data=payload, files=files, stream=True)

            if response.status_code == 200:
                raw_data = b""
                for chunk in response.iter_content(chunk_size=4096):
                    raw_data += chunk

                # 保存为 wav
                with wave.open(filename, 'wb') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(22050)
                    wav_file.writeframes(raw_data)
                return True
            else:
                print(f"❌ TTS生成失败: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ TTS请求错误: {e}")
        return False


# ================= 🧵 线程定义 =================

def input_listener_thread():
    """👂 耳朵线程：监听键盘输入 (模拟弹幕)"""
    while True:
        try:
            user_text = input()  # 阻塞等待输入
            if user_text.strip():
                input_queue.put(user_text)
        except:
            pass


def tts_worker_thread():
    """🏭 工厂线程：从 tts_queue 拿文字 -> 合成音频 -> 放入 play_queue"""
    global is_interrupted
    while True:
        try:
            # 获取文字
            text = tts_queue.get()
            if text is None: break

            # 如果处于打断状态，抛弃旧的生成任务
            if is_interrupted:
                tts_queue.task_done()
                continue

            print(f"⚙️ [正在合成]: {text[:15]}...")
            filename = f"temp_{uuid.uuid4().hex}.wav"

            success = generate_cosyvoice_audio(text, filename)

            if success:
                play_queue.put(filename)

            tts_queue.task_done()
        except Exception as e:
            print(f"TTS线程错误: {e}")


def player_worker_thread():
    """👄 嘴巴线程：从 play_queue 拿文件 -> 播放"""
    global is_interrupted
    while True:
        try:
            filename = play_queue.get()
            if filename is None: break

            # 播放前检查文件是否存在
            if os.path.exists(filename):
                pygame.mixer.music.load(filename)
                pygame.mixer.music.play()

                print("🔊 [正在播放]...")

                # 等待播放结束，同时检测是否被打断
                while pygame.mixer.music.get_busy():
                    if is_interrupted:
                        pygame.mixer.music.stop()
                        print("🛑 [播放被打断]")
                        break
                    time.sleep(0.1)

                pygame.mixer.music.unload()

                # 播完删除文件，清理垃圾
                try:
                    os.remove(filename)
                except:
                    pass

            play_queue.task_done()

            # 恢复打断标志 (只有当队列空了或者被打断处理完)
            if is_interrupted and play_queue.empty():
                pass

        except Exception as e:
            print(f"播放器错误: {e}")


# ================= 🚀 主程序逻辑 =================

def run_main_logic():
    global is_interrupted

    if "xxxx" in DEEPSEEK_API_KEY:
        print("❌ 错误：请先填写 DeepSeek API Key")
        return

    # 1. 启动线程
    threading.Thread(target=input_listener_thread, daemon=True).start()
    threading.Thread(target=tts_worker_thread, daemon=True).start()
    threading.Thread(target=player_worker_thread, daemon=True).start()

    # 2. 准备大脑
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    knowledge = load_knowledge_base()

    # 3. 提示词设置
    # --- 闲聊模式 (无人说话时) ---
    idle_prompt = f"""
    你是一个卖100-200元复刻表的带货主播。
    当前直播间没人说话，你需要主动吆喝，暖场。
    【店铺资料】：{knowledge}
    【要求】：
    1. 口语化，情绪高昂，像喊麦一样。
    2. 每次只说一两句，控制在30字以内。
    3. 随机介绍一款表，或催单，或欢迎新人。
    """

    # --- 回复模式 (有人说话时) ---
    reply_prompt = f"""
    你是一个卖100-200元复刻表的主播。
    用户发了弹幕，请根据【店铺资料】回复。
    资料：{knowledge}
    要求：
    1. 优先解决用户顾虑，然后引导下单。
    2. 语气热情，接地气，叫“兄弟”、“老铁”。
    3. 简短有力，不要长篇大论。
    """

    print("\n" + "=" * 50)
    print("🎙️ AI 语音带货主播已上线 (CosyVoice版)")
    print("👉 你不说话，他会一直吆喝。")
    print("👉 你输入弹幕，他会立刻停下嘴巴，思考3秒后回复你。")
    print("=" * 50 + "\n")

    last_speak_time = time.time()

    while True:
        current_time = time.time()

        # [情形A]：检测到有新弹幕
        if not input_queue.empty():
            user_msg = input_queue.get()

            if user_msg in ["exit", "退出"]:
                print("主播下播了！")
                break

            print(f"\n💬 [收到弹幕]: {user_msg}")

            # --- 1. 触发打断机制 ---
            is_interrupted = True  # 告诉播放线程：别播了！

            # 清空待播放队列（防止回复前还念叨旧的广告）
            with play_queue.mutex:
                play_queue.queue.clear()
            with tts_queue.mutex:
                tts_queue.queue.clear()

            # --- 2. 模拟思考停顿 (3秒) ---
            time.sleep(0.5)  # 给一点时间让播放器停下来
            is_interrupted = False  # 重置标志，准备接收新语音

            print("⏳ (主播正在看弹幕...停顿3秒)")
            time.sleep(2.5)  # 剩下的等待时间

            # --- 3. 生成回复 ---
            messages = [
                {"role": "system", "content": reply_prompt},
                {"role": "user", "content": user_msg}
            ]
            reply_text = call_deepseek(client, messages)
            print(f"📝 [生成回复]: {reply_text}")

            # 发送到 TTS 队列
            tts_queue.put(reply_text)

            # 重置闲聊计时器
            last_speak_time = time.time()

        # [情形B]：没人说话，自动吆喝
        # 逻辑：距离上次说话超过 5-8秒，且当前没有正在播放的内容，且没有被打断
        elif (current_time - last_speak_time > random.randint(5, 8)) and not is_interrupted:

            # 如果队列里还有没播完的，就先别生成新的，防止堆积
            if play_queue.qsize() == 0 and tts_queue.qsize() == 0:
                topics = ["催单", "介绍绿水鬼", "介绍蓝气球", "强调售后", "欢迎新人"]
                chosen_topic = random.choice(topics)

                msg = [
                    {"role": "system", "content": idle_prompt},
                    {"role": "user", "content": f"现在冷场了，请以{chosen_topic}为主题吆喝一句。"}
                ]

                # print("...准备吆喝...")
                ad_text = call_deepseek(client, msg, temperature=1.1)
                print(f"📢 [自动吆喝]: {ad_text}")

                tts_queue.put(ad_text)
                last_speak_time = time.time()

        time.sleep(0.1)


if __name__ == "__main__":
    run_main_logic()