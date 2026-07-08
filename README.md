# Live Sales Bot

An AI-powered live-streaming sales bot based on the DeepSeek large language model. Supports text interaction and speech synthesis broadcasting, with TikTok live room real-time comments integration, enabling fully automated unattended live-streaming sales.

## Features

- **Dual-mode operation**: When no one is asking questions, auto-hype sales pitches (random topic selection + interval control); when a question comes in, immediately switch to Q&A mode to reply to comments
- **DeepSeek API driven**: All natural language generation is handled by the DeepSeek LLM, supporting both Chinese and English output
- **RAG knowledge base retrieval**: Based on LangChain + Chroma vector database + HuggingFace Embeddings, retrieves relevant context from local product documentation to improve response accuracy
- **Local dialect synthesis (TTS)**: Converts text to speech via the CosyVoice local API (port 50000), supporting zero-shot voice cloning (requires a reference audio file `my_voice.wav`)
- **Chinese-English translation pipeline**: Chinese content is automatically translated to English via Google Translator, then fed into CosyVoice for English speech synthesis
- **TikTok live room integration**: Monitors comments in a specified TikTok live room in real time via the `TikTokLive` library; automatically extracts and passes comments to the bot for processing
- **Microphone voice input**: Supports converting spoken questions from viewers into text via microphone + Google Speech Recognition (`deepseek ai.py`)
- **Anti-repetition mechanism**: Uses `SequenceMatcher` to detect similarity in recent sales pitches; triggers a rewrite when the repetition rate exceeds the threshold
- **Smart text truncation**: Chinese output is automatically truncated at punctuation to a specified character count, ensuring speech playback is not cut off mid-sentence (default: 70 characters)
- **CTA (Call-to-Action) injection**: Automatically inserts fan-group traffic-driving copy every N sentences (configurable interval); CTA text reserves space to avoid truncation
- **Comment noise filtering**: Filters meaningless comments (pure numbers, single characters, spam duplicates), with a deduplication window
- **Quick reply matching**: Preset responses for common questions (price, waterproofing, material, movement, shipping, after-sales), answered instantly without going through the LLM
- **Interrupt mechanism**: Upon detecting a new comment, immediately stops current audio playback, clears the pending playback queue, and prioritizes answering the question

## Requirements

- Python 3.9+
- CosyVoice local TTS service (running at `127.0.0.1:50000`; must be deployed separately)
- Reference audio file `my_voice.wav` (for CosyVoice voice cloning)
- DeepSeek API Key
- (Optional) TikTok target live room username
- (Optional) PyAudio dependencies for microphone input

### Dependencies

Core dependencies:
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

Optional dependencies (install as needed):
```
TikTokLive          # TikTok comment monitoring
SpeechRecognition   # Microphone voice input
pyaudio             # Microphone audio capture
```

## Installation

```bash
git clone https://github.com/doaneruby970-hub/live-sales-bot.git
cd live-sales-bot
pip install openai langchain langchain-community langchain-openai langchain-chroma langchain-huggingface langchain-text-splitters chromadb sentence-transformers pygame requests deep-translator

# For TikTok integration
pip install TikTokLive

# For microphone input
pip install SpeechRecognition pyaudio
```

## Configuration

1. Copy and edit the environment variable file:
```bash
cp .env.example .env
```

2. Edit `.env` and fill in your configuration:
```
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
CUSTOM_BASE_URL=https://api.deepseek.com
CUSTOM_MODEL=deepseek-chat
```

3. (TikTok mode) Set the target live room:
```bash
# Windows PowerShell
setx TIKTOK_TARGET_USERNAME "@target_username"
```

4. Prepare the product knowledge base files. The project references two filenames; create one or both as needed:
   - `my_watch_data.txt` — used by `auto_live_bot.py`, `auto_live_voice.py`, `yumagpt.py`, `gpt111.py`, `rag_sales_bot.py`
   - `knowledge_base.txt` — used by `auto_live_english.py`, `V6.0ultimateversion..py`, `tiktok000111.py`

   If the file does not exist, the RAG versions will auto-create it with default content.

5. Prepare the CosyVoice reference audio:
   - Provide `my_voice.wav` as the reference audio for voice cloning
   - Also configure the `REF_TEXT` variable in the code so that it matches the actual content of the reference audio
   - Default reference text: "人总是要死的，但死的意义有不同。中国古时候有个文学家叫做司马迁的说过：人固有一死，或重于泰山，或轻于鸿毛"

6. Start the CosyVoice local TTS service, ensuring it runs at `http://127.0.0.1:50000/inference_zero_shot`

## Usage

The project includes multiple versions, evolving from simple to full-featured. Choose as needed:

### Text-mode live bot (pure CLI, no voice)

```bash
python rag_sales_bot.py          # RAG knowledge base Q&A version
python deepseek spell ai.py      # Luxury watch sales pitch version (with full sales strategy prompt)
python auto_live_bot.py          # Fully automated sales version (auto hype + reply to comments)
```

After running the above scripts, type a comment in the terminal and press Enter to send. Type `exit` or `quit` to stop.

### Voice-mode live bot (TTS broadcast)

```bash
python auto_live_voice.py        # Multi-threaded TTS version, supports interrupt and queue clearing
python yumagpt.py                # Chinese generation → English translation → English TTS, compatible with older CosyVoice API
python gpt111.py                 # Same as above, simplified version; rests 5 seconds after each sentence
python auto_live_english.py      # Full version with RAG + anti-repetition + CTA control
python V6.0ultimateversion..py   # Version with RAG + anti-repetition + CTA + TikTok (stdin mode)
```

Ensure the CosyVoice service is running and `my_voice.wav` is in place before running.

### Microphone voice input version

```bash
python deepseek ai.py            # Microphone → Google STT → DeepSeek → text output
```

Speak into the microphone; the program automatically recognizes speech and calls DeepSeek for a reply.

### TikTok live room integration version

```bash
python tiktok000111.py           # Monitors TikTok live room comments + RAG + TTS full pipeline
```

Requires setting the `TIKTOK_TARGET_USERNAME` environment variable first. The script automatically connects to the specified live room and retrieves real-time comments. Even if the live room is offline or the connection drops, the bot continues to deliver content automatically based on its topic list.

### Audio test tool

```bash
python listen.py                 # Plays my_voice.wav to test whether audio is working
```

## Architecture

Core differences between scripts:

| Script | RAG | TTS | TikTok | Anti-repetition | CTA Control | Input Method |
|------|-----|-----|--------|--------|---------|----------|
| `auto_live_bot.py` | No | No | No | No | No | stdin |
| `rag_sales_bot.py` | No | No | No | No | No | stdin |
| `deepseek spell ai.py` | No | No | No | No | No | stdin |
| `deepseek ai.py` | No | No | No | No | No | Mic |
| `auto_live_voice.py` | No | CosyVoice CN | No | No | No | stdin |
| `yumagpt.py` | No | CosyVoice EN | No | No | No | stdin |
| `gpt111.py` | No | CosyVoice EN | No | No | No | stdin |
| `auto_live_english.py` | Chroma | CosyVoice EN | No | Yes | Yes | stdin |
| `V6.0ultimateversion..py` | Chroma | CosyVoice EN | No | No | Yes | stdin |
| `tiktok000111.py` | Chroma | CosyVoice EN | Yes | Yes | Yes | TikTok + stdin (optional) |

All RAG scripts use the same tech stack: LangChain + Chroma vector store + `sentence-transformers/all-MiniLM-L6-v2` embedding model + MMR retrieval strategy.

## Notes

1. **API Key security**: Never hardcode `DEEPSEEK_API_KEY` in source code; always manage it via environment variables or `.env` file
2. **CosyVoice dependency**: Voice-mode scripts depend on a locally running CosyVoice TTS service; ensure the service is running and port 50000 is accessible
3. **Reference audio matching**: The `REF_TEXT` variable must exactly match the actual recorded content of `my_voice.wav`, otherwise synthesis quality will be abnormal
4. **Proxy configuration**: If an HTTP proxy is configured on the machine, be sure to set `no_proxy=localhost,127.0.0.1,::1` so that local CosyVoice requests bypass the proxy
5. **TikTok limitations**: The `TikTokLive` library can only retrieve comments from public live rooms; the target account must be currently live streaming, otherwise the connection fails (the script will continue running in offline mode)
6. **Google Translate**: `deep_translator` relies on the Google Translate service, which may require a proxy in some network environments
7. **Python version**: Python 3.9+ recommended; `langchain` library version compatibility is fairly sensitive — if you encounter import errors, refer to the compatibility import fallback logic in the code
8. **First run**: LangChain RAG scripts download the `all-MiniLM-L6-v2` model (~90MB) on first launch; please be patient
9. **Product positioning**: The preset prompts and sales pitches in each script are written for the watch sales scenario (replica watches / factory-source watches). For other product categories, modify `SYSTEM_PROMPT` and topic lists accordingly
