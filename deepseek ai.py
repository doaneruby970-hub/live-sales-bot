import os
import sys
import time

# 尝试导入必要的库
try:
    from openai import OpenAI
    import speech_recognition as sr  # 导入语音识别库
except ImportError as e:
    print("【缺少零件】请在终端运行安装命令：")
    print("pip install openai SpeechRecognition pyaudio")
    print(f"具体报错: {e}")
    sys.exit(1)

# ==========================================
# 1. 配置区域
# ==========================================
MY_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")  # 从环境变量读取
DEEPSEEK_URL = "https://api.deepseek.com"

# ==========================================
# 2. 定义销售大脑
# ==========================================
SYSTEM_PROMPT = """
你是一位顶级名表直播间主播。你的风格是：
1. 热情、语速快、有感染力。
2. 极其专业，对劳力士、欧米茄等参数倒背如流。
3. 回复要简短有力（口语化），不要长篇大论。

请根据观众说的话进行回复。
"""


# ==========================================
# 3. 核心功能：让电脑“听” (语音转文字)
# ==========================================
def listen_to_microphone():
    r = sr.Recognizer()

    # 调整麦克风灵敏度
    r.energy_threshold = 3000
    r.dynamic_energy_threshold = True

    try:
        with sr.Microphone() as source:
            print("\n🎤 正在听你说话 (请对着麦克风说)...")
            # 自动调整环境噪音
            r.adjust_for_ambient_noise(source, duration=0.5)
            # 开始录音，5秒内没声音就超时
            audio = r.listen(source, timeout=10, phrase_time_limit=10)

            print("Creating text... (正在识别...)")
            # 调用谷歌的免费识别服务 (需要联网)
            text = r.recognize_google(audio, language='zh-CN')
            print(f"👂 听到你说: 【{text}】")
            return text

    except sr.WaitTimeoutError:
        print("... (没听到声音，继续监听)")
        return None
    except sr.UnknownValueError:
        print("... (声音太小或没听清，请重说)")
        return None
    except sr.RequestError:
        print("❌ 网络连接谷歌语音服务失败，请检查网络 (或需要科学上网)")
        return None
    except Exception as e:
        print(f"❌ 麦克风出错: {e}")
        return None


# ==========================================
# 4. 主程序
# ==========================================
def run_voice_agent():
    if "在这里填入" in MY_API_KEY:
        print("【错误】：请先在代码第 18 行填入你的 API Key！")
        return

    client = OpenAI(api_key=MY_API_KEY, base_url=DEEPSEEK_URL)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    print("\n" + "=" * 50)
    print("🎙️ 语音版·名表直播智能体已启动！")
    print("请确保麦克风已连接，并调大音量。")
    print("=" * 50)
    print("主播：哈喽大家！欢迎来到直播间！今天想看什么表？直接喊出来！")

    while True:
        # 1. 获取语音输入
        user_text = listen_to_microphone()

        # 如果没听到声音，就跳过这次循环，重新听
        if not user_text:
            continue

        # 退出指令
        if "退出" in user_text or "再见" in user_text:
            print("主播：好的老板，下次再来！")
            break

        # 2. 把听到的字发给 DeepSeek
        messages.append({"role": "user", "content": user_text})
        print("...主播思考中...")

        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=1.2,
                stream=False
            )
            ai_reply = response.choices[0].message.content

            # 3. 显示回复
            messages.append({"role": "assistant", "content": ai_reply})
            print(f"💎 主播回复: {ai_reply}\n")
            print("-" * 30)

        except Exception as e:
            print(f"❌ API 调用错误: {e}")


if __name__ == "__main__":
    run_voice_agent()