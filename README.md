# RecapMaster — API-keyless backend

ဒီ version က Blogger-only မဟုတ်ပါ။ Backend တစ်ခုလိုပါတယ်။ Blogger မှာ UI/link ချိတ်နိုင်ပြီး backend က YouTube/media → Whisper transcription → translation → SRT → recap → Edge TTS လုပ်ပေးပါတယ်။

## Run locally

လိုအပ်ချက်:
- Python 3.11
- FFmpeg
- Internet (YouTube download, Edge TTS, optional translation)
- ပထမ run မှာ faster-whisper model download လုပ်ပါမယ်

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

Browser:
http://127.0.0.1:8000

## Flow

YouTube URL → yt-dlp → faster-whisper → translation → SRT → extractive recap → Edge TTS MP3.

## Important

- API key မလိုတဲ့ components ကို ဦးစားပေးထားပါတယ်။
- Translation အတွက် Argos Translate local package ရှိရင် local သုံးပြီး မရှိရင် configured public LibreTranslate-compatible endpoint ကို fallback သုံးပါတယ်။ Public service availability/limits မအာမခံနိုင်ပါ။
- Burmese translation model availability varies. Quality may be lower than a commercial LLM.
- Recap generator က local extractive summarizer ဖြစ်ပါတယ်; ChatGPT/Gemini လို generative movie recap quality မဟုတ်ပါ။
- YouTube/media ကို အသုံးပြုခွင့်ရှိတဲ့ content နဲ့ပဲ သုံးပါ။
