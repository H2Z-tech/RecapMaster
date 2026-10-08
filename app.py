from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse

app = FastAPI()

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
