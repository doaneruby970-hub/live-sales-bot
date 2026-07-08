import os
import sys
import time
import threading
import queue
import random

# 检查库
try:
    from openai import OpenAI
except ImportError:
    print("请先安装库：pip install openai")
    sys.exit(1)

# ================= 配置区 =================
MY_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")  # 从环境变量读取，不要硬编码密钥
DATA_FILE = "my_watch_data.txt"

# 这是一个队列，用来存放“耳朵”听到的弹幕
input_queue = queue.Queue()


# ================= 核心功能函数 =================

def load_knowledge_base():
    """读取知识库"""
    if not os.path.exists(DATA_FILE):
        return "（未找到数据文件，请确保my_watch_data.txt存在）"
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return f.read()


def get_deepseek_response(client, messages, temperature=1.0):
    """封装DeepSeek调用，方便复用"""
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=temperature,
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"（网络卡顿中...）"


def listen_for_input():
    """这是【耳朵】线程：专门在后台等用户打字"""
    while True:
        # 这里的 input 会阻塞，但因为是在独立线程里，所以不会影响主播说话
        user_text = input()
        if user_text.strip():
            input_queue.put(user_text)


# ================= 主程序 =================

def run_auto_live_agent():
    if "在这里填入" in MY_API_KEY:
        print("❌ 请先配置 API Key！")
        return

    # 1. 准备工作
    knowledge = load_knowledge_base()
    client = OpenAI(api_key=MY_API_KEY, base_url="https://api.deepseek.com")

    # 2. 启动【耳朵】线程
    # daemon=True 表示如果主程序结束，这个线程也会自动结束
    listener_thread = threading.Thread(target=listen_for_input, daemon=True)
    listener_thread.start()

    print("\n" + "=" * 50)
    print("🔥 全自动带货主播已上线！(输入 'exit' 退出)")
    print("💡 说明：")
    print("   1. 你不说话，它会自己根据文档吆喝。")
    print("   2. 你在下方输入弹幕，它会停下来回复你。")
    print("=" * 50 + "\n")

    # 3. 初始化上下文
    # 专门用于“闲聊”的 Prompt
    idle_system_prompt = f"""
    你是一个卖100-200元复刻表的直播主播。
    你的任务是：在没人提问时，主动根据【店铺资料】进行推销、欢迎新人、或者制造紧迫感。

    【店铺资料】：
    {knowledge}

    【要求】：
    1. 每次只说一句话，简短有力（20-40字）。
    2. 风格接地气，多用“兄弟们”、“炸街”、“福利”。
    3. 随机介绍一款表，或者强调发货快/售后好。
    """

    # 专门用于“回复弹幕”的 Prompt
    reply_system_prompt = f"""
    你是一个卖100-200元复刻表的主播。
    用户正在提问，请根据【店铺资料】回复。
    资料：{knowledge}
    要求：态度热情，直接解决疑虑，最后要引导下单。
    """

    # 记录上一次说话的时间
    last_speak_time = time.time()

    # 4. 进入直播循环
    while True:
        current_time = time.time()

        # --- A. 检查有没有新弹幕 ---
        if not input_queue.empty():
            # 拿到弹幕
            user_msg = input_queue.get()

            if user_msg.lower() in ["exit", "退出"]:
                print("主播：好勒，那今天先下播，兄弟们明天见！")
                break

            # 模拟“看到弹幕后的反应时间” (停顿3秒)
            # print("\n(主播正在看弹幕...)\n")
            time.sleep(3)

            # 调用 DeepSeek 回复
            messages = [
                {"role": "system", "content": reply_system_prompt},
                {"role": "user", "content": user_msg}
            ]
            print(f"\n💬 收到弹幕：{user_msg}")
            reply = get_deepseek_response(client, messages)
            print(f"🎙️ 主播回复: {reply}\n")

            # 回复完重置计时器，避免刚回复完马上又闲聊
            last_speak_time = time.time()

        # --- B. 如果没人说话，且时间到了，就自己吆喝 ---
        # 设定间隔：5秒 到 8秒 之间随机，这样更自然
        elif current_time - last_speak_time > random.randint(5, 8):

            # 随机生成一个指令，让 DeepSeek 自由发挥
            random_topics = [
                "介绍一款店里的爆款表",
                "欢迎新进来的观众点关注",
                "强调一下售后服务",
                "强调一下现在的价格优势",
                "催促一下大家下单"
            ]
            topic = random.choice(random_topics)

            messages = [
                {"role": "system", "content": idle_system_prompt},
                {"role": "user", "content": f"现在没人说话，请{topic}，说一句吆喝的话。"}
            ]

            # print("...(主播正在组织语言)...") # 调试用，可注释掉
            auto_talk = get_deepseek_response(client, messages, temperature=1.1)
            print(f"📢 主播吆喝: {auto_talk}")

            # 重置计时器
            last_speak_time = time.time()

        # --- C. 防止CPU空转，稍微睡一小会儿 ---
        time.sleep(0.1)


if __name__ == "__main__":
    run_auto_live_agent()