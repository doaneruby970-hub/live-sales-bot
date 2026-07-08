import os
import sys

# 尝试导入 openai 库，如果没安装会提示
try:
    from openai import OpenAI
except ImportError:
    print("错误：你还没有安装 openai 库。")
    print("请在终端运行命令：pip install openai")
    sys.exit(1)

# ==========================================
# 1. 配置区域 (只需修改这里)
# ==========================================

# 请将下方的 "sk-xxxxxxxx" 替换为你自己在 DeepSeek 官网申请的 API Key
MY_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")  # 从环境变量读取

# DeepSeek 的官方接口地址 (通常不需要改)
DEEPSEEK_URL = "https://api.deepseek.com"

# ==========================================
# 2. 定义“销售大脑” (这是智能体的灵魂)
# ==========================================

# 这里定义了机器人的角色、性格和销售技巧
SYSTEM_PROMPT = """
你是一位拥有15年经验的顶级名表直播间主播，专门销售劳力士(Rolex)、欧米茄(Omega)等高端腕表。

【你的性格】：
1. 极其专业：对机芯参数、材质（如904L钢、陶瓷圈）如数家珍。
2. 优雅从容：不会像卖地摊货一样大喊大叫，而是像老朋友聊天。
3. 擅长逼单：会巧妙地制造稀缺感（库存紧张、行情上涨）。

【销售策略】：
1. 当用户嫌贵时：不要直接降价。要强调“保值属性”和“身份象征”，用“每天佩戴成本”来拆解价格。
2. 当用户担心真假时：强调“支持专柜验货”、“假一赔三”，并指出只有真表才有的打磨细节。
3. 当用户犹豫时：告诉他这款表现在的二级市场行情，强调“现在不买，明年涨价”。

【当前任务】：
你正在直播，请根据“观众弹幕”进行实时回复。回复要口语化，像在说话一样，长度控制在100字以内，干脆利落。
"""


# ==========================================
# 3. 核心功能代码 (不要修改)
# ==========================================

def run_sales_agent():
    # 检查 Key 是否填了
    if "在这里填入" in MY_API_KEY:
        print("【错误】：请先在代码第 17 行填入你的 DeepSeek API Key！")
        return

    # 初始化客户端
    client = OpenAI(api_key=MY_API_KEY, base_url=DEEPSEEK_URL)

    # 记录对话历史（让它记得上下文）
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    print("\n" + "=" * 50)
    print("⌚️ 名表直播销售智能体已启动！(输入 'exit' 退出)")
    print("=" * 50 + "\n")
    print("主播：欢迎来到直播间！今天给大家带来几款尖货，有什么问题尽管问！")

    while True:
        # 获取你的输入（模拟观众弹幕）
        user_input = input("\n👤 观众(你)说: ")

        # 如果输入 exit 就退出
        if user_input.lower() in ["exit", "quit", "退出"]:
            print("主播：感谢大家捧场，我们下场直播见！")
            break

        # 如果输入为空，跳过
        if not user_input.strip():
            continue

        # 把观众的话加入对话历史
        messages.append({"role": "user", "content": user_input})

        print("...主播正在思考话术...")

        try:
            # 向 DeepSeek 发送请求
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=1.2,  # 温度高一点，让话术更灵活、不僵硬
                stream=False
            )

            # 获取 AI 的回答
            ai_reply = response.choices[0].message.content

            # 把 AI 的回答也加入历史，这样它能记住自己说过的话
            messages.append({"role": "assistant", "content": ai_reply})

            # 打印回复
            print(f"🎙️ 主播回复: {ai_reply}")

        except Exception as e:
            print(f"❌ 发生错误: {e}")
            print("请检查你的 API Key 是否正确，或者网络是否通畅。")


# ==========================================
# 4. 程序入口
# ==========================================
if __name__ == "__main__":
    run_sales_agent()