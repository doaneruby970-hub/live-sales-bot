# Live Sales Bot

基于 DeepSeek 大模型的 AI 直播带货机器人，支持文字互动和语音合成播报，可接入 TikTok 直播间实时弹幕，实现全自动无人值守直播带货。

## 功能特性

- **双模式运行**：无人提问时自动吆喝推销（随机选题 + 间隔控制），有人提问时立即切换为问答模式回复弹幕
- **DeepSeek API 驱动**：所有自然语言生成由 DeepSeek 大模型完成，支持中文和英文输出
- **RAG 知识库检索**：基于 LangChain + Chroma 向量数据库 + HuggingFace Embeddings，从本地产品资料文档中检索相关上下文，提升回复准确度
- **本地方言合成 (TTS)**：通过 CosyVoice 本地 API（端口 50000）将文字合成为语音，支持零样本音色克隆（需提供参考音频 `my_voice.wav`）
- **中英翻译流水线**：中文内容生成后自动通过 Google Translator 翻译为英文，再送入 CosyVoice 合成英文语音播报
- **TikTok 直播间接入**：通过 `TikTokLive` 库实时监听指定 TikTok 直播间的弹幕评论，自动提取后交由机器人处理
- **麦克风语音输入**：支持通过麦克风 + Google 语音识别将观众口头提问转为文字（`deepseek ai.py`）
- **防复读机制**：基于 `SequenceMatcher` 检测最近话术相似度，重复率超过阈值自动触发改写
- **智能文本截断**：中文输出自动在标点处截断至指定字数，确保语音播报不被打断（默认 70 字）
- **CTA 引流控制**：每隔 N 句自动插入粉丝群引流文案（可配置间隔），CTA 文案预留空间确保不被截断
- **弹幕降噪过滤**：过滤无意义弹幕（纯数字、单个字符、刷屏重复内容），支持去重窗口
- **快速回复匹配**：对常见问题（价格、防水、材质、机芯、发货、售后）预设话术，秒回不经过大模型
- **打断机制**：检测到新弹幕时立即停止当前语音播放，清空待播队列，优先回复提问

## 环境要求

- Python 3.9+
- CosyVoice 本地 TTS 服务（运行在 `127.0.0.1:50000`，需自行部署）
- 参考音频文件 `my_voice.wav`（用于 CosyVoice 音色克隆）
- DeepSeek API Key
- （可选）TikTok 目标直播间用户名
- （可选）用于麦克风输入的 PyAudio 依赖

### 依赖库

核心依赖：
```
openai>=1.0.0
langchain>=0.2.0
langchain-community
langchain-openai
langchain-chroma
langchain-huggingface
langchain-text-splitters
chromadb
sentence-transformers
pygame
requests
deep-translator
```

可选依赖（按需安装）：
```
TikTokLive          # TikTok 弹幕监听
SpeechRecognition   # 麦克风语音输入
pyaudio             # 麦克风音频采集
```

## 安装

```bash
git clone https://github.com/doaneruby970-hub/live-sales-bot.git
cd live-sales-bot
pip install openai langchain langchain-community langchain-openai langchain-chroma langchain-huggingface langchain-text-splitters chromadb sentence-transformers pygame requests deep-translator

# 如需 TikTok 接入
pip install TikTokLive

# 如需麦克风输入
pip install SpeechRecognition pyaudio
```

## 配置

1. 复制并编辑环境变量文件：
```bash
cp .env.example .env
```

2. 编辑 `.env`，填入你的配置：
```
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
CUSTOM_BASE_URL=https://api.deepseek.com
CUSTOM_MODEL=deepseek-chat
```

3. （TikTok 模式）设置目标直播间：
```bash
# Windows PowerShell
setx TIKTOK_TARGET_USERNAME "@目标用户名"
```

4. 准备产品知识库文件。项目中用到两个文件名，按实际需要创建其一或全部：
   - `my_watch_data.txt` — 供 `auto_live_bot.py`、`auto_live_voice.py`、`yumagpt.py`、`gpt111.py`、`rag_sales_bot.py` 使用
   - `knowledge_base.txt` — 供 `auto_live_english.py`、`V6.0ultimateversion..py`、`tiktok000111.py` 使用

   如果文件不存在，RAG 版本会自动创建包含默认内容的文件。

5. 准备 CosyVoice 参考音频：
   - 提供 `my_voice.wav` 文件作为音色克隆的参考音频
   - 同时需在代码中配置 `REF_TEXT` 变量，使其与参考音频的实际内容一致
   - 默认参考文本："人总是要死的，但死的意义有不同。中国古时候有个文学家叫做司马迁的说过：人固有一死，或重于泰山，或轻于鸿毛"

6. 启动 CosyVoice 本地 TTS 服务，确保其运行在 `http://127.0.0.1:50000/inference_zero_shot`

## 使用方式

项目包含多个版本，从简单到完整逐级演进，按需选择：

### 文字版直播机器人（纯 CLI，无语音）

```bash
python rag_sales_bot.py          # RAG 知识库问答版
python deepseek spell ai.py      # 名表销售话术版（有完整销售策略 prompt）
python auto_live_bot.py          # 全自动带货版（自动吆喝 + 回复弹幕）
```

以上脚本运行后在终端输入弹幕文字，按回车发送。输入 `exit` 或 `退出` 停止。

### 语音版直播机器人（TTS 播报）

```bash
python auto_live_voice.py        # 多线程 TTS 版，支持打断、清队列
python yumagpt.py                # 中文生成 -> 英文翻译 -> 英文 TTS，兼容旧版 CosyVoice API
python gpt111.py                 # 同上，简化版，每句说完休息 5 秒
python auto_live_english.py      # 带 RAG + 防复读 + CTA 控制的完整版
python V6.0ultimateversion..py   # 带 RAG + 防复读 + CTA + TikTok 版（stdin 模式）
```

运行前确保 CosyVoice 服务已启动，`my_voice.wav` 已就位。

### 麦克风语音输入版

```bash
python deepseek ai.py            # 麦克风 -> Google STT -> DeepSeek -> 文字输出
```

对着麦克风说话，程序自动识别并调用 DeepSeek 回复。

### TikTok 直播接入版

```bash
python tiktok000111.py           # 监听 TikTok 直播间弹幕 + RAG + TTS 全流程
```

需先设置环境变量 `TIKTOK_TARGET_USERNAME`。脚本自动连接指定直播间并获取实时弹幕。即使直播间不在线或连接断开，机器人会继续按照话题列表自动讲干货。

### 音频测试工具

```bash
python listen.py                 # 播放 my_voice.wav 测试音频是否正常
```

## 架构说明

各脚本的核心差异：

| 脚本 | RAG | TTS | TikTok | 防复读 | CTA控制 | 输入方式 |
|------|-----|-----|--------|--------|---------|----------|
| `auto_live_bot.py` | 无 | 无 | 无 | 无 | 无 | stdin |
| `rag_sales_bot.py` | 无 | 无 | 无 | 无 | 无 | stdin |
| `deepseek spell ai.py` | 无 | 无 | 无 | 无 | 无 | stdin |
| `deepseek ai.py` | 无 | 无 | 无 | 无 | 无 | 麦克风 |
| `auto_live_voice.py` | 无 | CosyVoice 中文 | 无 | 无 | 无 | stdin |
| `yumagpt.py` | 无 | CosyVoice 英文 | 无 | 无 | 无 | stdin |
| `gpt111.py` | 无 | CosyVoice 英文 | 无 | 无 | 无 | stdin |
| `auto_live_english.py` | Chroma | CosyVoice 英文 | 无 | 有 | 有 | stdin |
| `V6.0ultimateversion..py` | Chroma | CosyVoice 英文 | 无 | 无 | 有 | stdin |
| `tiktok000111.py` | Chroma | CosyVoice 英文 | 有 | 有 | 有 | TikTok + stdin(可选) |

所有 RAG 脚本使用相同的技术栈：LangChain + Chroma 向量存储 + `sentence-transformers/all-MiniLM-L6-v2` Embedding 模型 + MMR 检索策略。

## 注意事项

1. **API Key 安全**：不要在代码中硬编码 `DEEPSEEK_API_KEY`，务必通过环境变量或 `.env` 文件管理
2. **CosyVoice 依赖**：语音版脚本依赖本地运行的 CosyVoice TTS 服务，确保服务已启动且端口 50000 可访问
3. **参考音频匹配**：`REF_TEXT` 变量必须与 `my_voice.wav` 的实际录音内容完全一致，否则合成效果异常
4. **代理配置**：如果本机配置了 HTTP 代理，务必设置 `no_proxy=localhost,127.0.0.1,::1` 使 CosyVoice 本地请求绕过代理
5. **TikTok 限制**：`TikTokLive` 库仅能获取公开直播间的弹幕，目标账号必须正在直播，否则连接失败（脚本会继续以离线模式运行）
6. **Google 翻译**：`deep_translator` 依赖 Google 翻译服务，国内网络环境下可能需要代理
7. **Python 版本**：建议 Python 3.9+；`langchain` 系列库版本兼容性较为敏感，如遇导入错误请参考代码中的兼容性导入 fallback 逻辑
8. **首次运行**：LangChain RAG 脚本首次启动时会下载 `all-MiniLM-L6-v2` 模型（约 90MB），请耐心等待
9. **产品定位**：各脚本内预设的 prompt 和话术围绕手表销售场景编写（复刻表/工厂源头表），如需其他品类请自行修改 `SYSTEM_PROMPT` 和话题列表
