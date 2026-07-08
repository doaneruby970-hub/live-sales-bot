import os
import sys

# 检查库
try:
    from openai import OpenAI
except ImportError:
    print("请先安装库：pip install openai")
    sys.exit(1)

# ================= 配置区 =================
# 1. 填入你的 DeepSeek Key
MY_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")  # 从环境变量读取

# 2. 你的知识库文件名
DATA_FILE = "my_watch_data.txt"


# ================= 核心代码 =================

def load_knowledge_base():
    """读取你的文本文件内容"""
    if not os.path.exists(DATA_FILE):
        print(f"❌ 错误：找不到文件 【{DATA_FILE}】")
        print("请在代码的同一个文件夹里新建这个txt文件，并填入你的手表资料。")
        return None

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return f.read()


def run_rag_bot():
    # 0. 检查 Key
    if "在这里填入" in MY_API_KEY:
        print("❌ 请先在代码第 13 行填入你的 DeepSeek API Key！")
        return

    # 1. 读取知识库
    print("正在加载你的库存和话术文档...")
    knowledge = load_knowledge_base()
    if not knowledge:
        return  # 文件没找到，停止运行

    client = OpenAI(api_key=MY_API_KEY, base_url="https://api.deepseek.com")

    # 2. 构建“最强场控”提示词
    # 这里的 Prompt 专门针对 100-200元 复刻表市场进行了优化
    system_prompt = f"""
    你是一个反应极快、说话接地气的直播间销售助手。
    你卖的是【高性价比复刻表/款式表】，价格在100-200元之间。

    【核心原则】：
    1. **绝不欺骗**：不要说这是正品，要说是“工厂货”、“平替”、“款式表”。
    2. **强调性价比**：突出“戴着玩”、“坏了不心疼”、“搭配衣服”。
    3. **依据文档回答**：你的回答必须基于下方的【店铺资料】。如果用户问了文档里没有的表，就说“那款目前没货，看看刚介绍的这几款？”。

    【店铺资料】：
    {knowledge}

    【回复风格】：
    简短、口语化（用“老铁”、“兄弟”、“集美”）、热情。
    不要长篇大论，直接切中痛点。
    """

    messages = [{"role": "system", "content": system_prompt}]

    print("\n" + "=" * 50)
    print("✅ 智能体已加载文档：my_watch_data.txt")
    print("🚀 直播间助手已就位！(输入 'exit' 退出)")
    print("=" * 50)
    print("主播：来来来，刚进直播间的兄弟们，想看什么表打在公屏上！")

    while True:
        try:
            # 获取打字输入
            user_input = input("\n👤 弹幕: ")

            if not user_input.strip(): continue
            if user_input.lower() in ["exit", "退出"]: break

            messages.append({"role": "user", "content": user_input})

            # 调用 DeepSeek
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=1.0,  # 稍微灵活一点
                stream=False
            )

            ai_reply = response.choices[0].message.content
            messages.append({"role": "assistant", "content": ai_reply})

            print(f"🎙️ 主播: {ai_reply}")

        except Exception as e:
            print(f"❌ 出错了: {e}")


if __name__ == "__main__":
    run_rag_bot()