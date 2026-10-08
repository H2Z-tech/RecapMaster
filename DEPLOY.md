# Web deployment

Blogger က backend မဟုတ်တဲ့အတွက် full processing ကို Blogger HTML တစ်ခုတည်းထဲ မထည့်နိုင်ပါ။

Dockerfile ပါပြီးသားပါ။ Docker support ရှိတဲ့ server/container host တစ်ခုမှာ deploy လုပ်ပြီး public HTTPS URL ရလာတဲ့အခါ Blogger UI က အဲဒီ URL ကို fetch လုပ်နိုင်ပါတယ်။

Free hosting plans may sleep, have CPU/RAM/time/storage limits. Whisper transcription is CPU-heavy. The small model is a safer starting point.

For a public site, add:
- job queue
- authentication/rate limiting
- file size and duration limits
- automatic work-directory cleanup
- HTTPS
- CORS policy
- terms/copyright notice

Do not expose server credentials in Blogger JavaScript.
