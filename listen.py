import winsound
import os
import time

# ================= 配置 =================
# 这里填你想听的那个文件名
FILENAME = "my_voice.wav"


# =======================================

def play_audio():
    print(f"🔍 正在寻找文件: {FILENAME} ...")

    # 1. 检查文件在不在
    if not os.path.exists(FILENAME):
        print("❌ 找不到文件！请确认文件名写对了吗？")
        print("💡 提示：文件必须和代码在同一个文件夹里。")
        return

    print("✅ 文件找到了！")
    print("------------------------------------------------")
    print(f"🔊 正在播放... (请仔细听最后停在哪个字)")
    print("------------------------------------------------")

    try:
        # 方法 A: 纯代码播放 (播完才会停)
        winsound.PlaySound(FILENAME, winsound.SND_FILENAME)

        # 方法 B: 如果你想调出系统播放器(能暂停/进度条)，把上面那行删掉，取消下面这行的注释
        # os.startfile(FILENAME)

        print("\n✅ 播放结束！")
        print("👉 现在去修改 Final_50000.py 的第 19 行吧！")

    except Exception as e:
        print(f"❌ 播放出错: {e}")


if __name__ == "__main__":
    play_audio()