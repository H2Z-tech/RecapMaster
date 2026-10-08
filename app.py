from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

app = FastAPI()

# Blogger ကနေ လှမ်းခေါ်လို့ရအောင် CORS ချိတ်ဆက်ပေးခြင်း
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # လိုအပ်ပါက Blogger domain သီးသန့် ထည့်နိုင်ပါတယ်
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Project ရဲ့ Root နေရာကို သတ်မှတ်ခြင်း
BASE = Path(__file__).resolve().parent


@app.get("/", response_class=HTMLResponse)
def home():
  index_file = BASE / "index.html"
  if not index_file.exists():
    return HTMLResponse("<h1>index.html not found</h1>", status_code=404)
  return index_file.read_text(encoding="utf-8")


@app.get("/style.css")
def serve_css():
  return FileResponse(BASE / "style.css", media_type="text/css")


@app.get("/app.js")
def serve_js():
  return FileResponse(BASE / "app.js", media_type="application/javascript")


# --- Blogger မှ API လှမ်းခေါ်မည့် Endpoint ---
class RecapRequest(BaseModel):
  youtube_url: str


@app.post("/api/recap")
def generate_recap(data: RecapRequest):
  # ဒီနေရာမှာ YouTube download လုပ်တာ၊ Whisper နဲ့ စာထုတ်တာ၊ Recap လုပ်တာတွေ ဆက်လက်ထည့်သွင်းနိုင်ပါတယ်
  return {
      "status": "success",
      "message": "YouTube URL လက်ခံရရှိပါပြီ",
      "url": data.youtube_url,
  }
