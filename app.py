import os
import re
import uuid
import shutil
from pathlib import Path
from typing import Optional

import requests
import yt_dlp
import edge_tts

from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from faster_whisper import WhisperModel
from argostranslate import translate as argos_translate


# =========================================================
# BASIC PATHS
# =========================================================

BASE = Path(__file__).resolve().parent

WORK = BASE / "work"
WORK.mkdir(exist_ok=True)

STATIC_DIR = BASE / "Static"
TEMPLATES_DIR = BASE / "Templates"

STATIC_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)


# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(title="RecapMaster")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Static files
app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static",
)


# =========================================================
# SETTINGS
# =========================================================

WHISPER_MODEL = os.getenv(
    "WHISPER_MODEL",
    "small"
)

TRANSLATE_URL = os.getenv(
    "TRANSLATE_URL",
    "https://translate.argosopentech.com/translate"
)

_model = None


# =========================================================
# WHISPER MODEL
# =========================================================

def get_model():
    global _model

    if _model is None:
        _model = WhisperModel(
            WHISPER_MODEL,
            device="cpu",
            compute_type="int8"
        )

    return _model


# =========================================================
# JOB FOLDER
# =========================================================

def safe_job():
    job = WORK / uuid.uuid4().hex
    job.mkdir(parents=True, exist_ok=True)
    return job


# =========================================================
# DOWNLOAD VIDEO / AUDIO
# =========================================================

def download_media(url: str, out: Path):

    if not re.match(r"^https?://", url, re.I):
        raise ValueError("Invalid URL")

    out.mkdir(
        parents=True,
        exist_ok=True
    )

    template = str(
        out / "source.%(ext)s"
    )

    opts = {
        "outtmpl": template,
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
    }

    with yt_dlp.YoutubeDL(opts) as y:

        info = y.extract_info(
            url,
            download=True
        )

        path = Path(
            y.prepare_filename(info)
        )

        if path.exists():
            return path

        candidates = list(
            out.glob("source.*")
        )

        if not candidates:
            raise RuntimeError(
                "Downloaded media file not found"
            )

        return candidates[0]


# =========================================================
# TRANSCRIPTION
# =========================================================

def transcribe(
    path: Path,
    lang: Optional[str]
):

    model = get_model()

    kwargs = {
        "beam_size": 5,
        "vad_filter": True
    }

    if lang and lang != "auto":
        kwargs["language"] = lang

    segments, info = model.transcribe(
        str(path),
        **kwargs
    )

    rows = []

    for s in segments:

        rows.append(
            {
                "start": float(s.start),
                "end": float(s.end),
                "text": s.text.strip()
            }
        )

    return rows, info.language


# =========================================================
# ARGOS TRANSLATION
# =========================================================

def argos_translate_text(
    text,
    source,
    target
):

    langs = (
        argos_translate
        .get_installed_languages()
    )

    src = next(
        (
            x for x in langs
            if x.code == source
        ),
        None
    )

    dst = next(
        (
            x for x in langs
            if x.code == target
        ),
        None
    )

    if not src or not dst:
        return None

    try:

        tr = src.get_translation(dst)

        return tr.translate(text)

    except Exception:

        return None


# =========================================================
# REMOTE TRANSLATION
# =========================================================

def remote_translate(
    text,
    source,
    target
):

    r = requests.post(
        TRANSLATE_URL,
        json={
            "q": text,
            "source": source,
            "target": target,
            "format": "text"
        },
        timeout=120,
    )

    r.raise_for_status()

    data = r.json()

    return (
        data.get("translatedText")
        or data.get("translation")
    )


# =========================================================
# TRANSLATE SEGMENTS
# =========================================================

def translate_segments(
    segments,
    source,
    target
):

    if source == target:

        return [
            dict(
                x,
                translated=x["text"]
            )
            for x in segments
        ]

    out = []

    for x in segments:

        text = x["text"]

        translated = argos_translate_text(
            text,
            source,
            target
        )

        if not translated:

            try:

                translated = remote_translate(
                    text,
                    source,
                    target
                )

            except Exception:

                translated = text

        out.append(
            dict(
                x,
                translated=translated
            )
        )

    return out


# =========================================================
# SRT TIME
# =========================================================

def srt_time(sec):

    ms = int(
        round(sec * 1000)
    )

    h, ms = divmod(
        ms,
        3600000
    )

    m, ms = divmod(
        ms,
        60000
    )

    s, ms = divmod(
        ms,
        1000
    )

    return (
        f"{h:02d}:"
        f"{m:02d}:"
        f"{s:02d},"
        f"{ms:03d}"
    )


# =========================================================
# CREATE SRT
# =========================================================

def make_srt(
    segments,
    field="translated"
):

    chunks = []

    for i, x in enumerate(
        segments,
        1
    ):

        text = (
            x.get(field)
            or x["text"]
        )

        chunks.append(
            f"{i}\n"
            f"{srt_time(x['start'])} --> "
            f"{srt_time(x['end'])}\n"
            f"{text}\n"
        )

    return "\n".join(chunks)


# =========================================================
# CREATE RECAP
# =========================================================

def make_recap(
    segments,
    max_sentences=18
):

    texts = [
        x["translated"]
        for x in segments
        if x.get("translated")
    ]

    sentences = []

    for t in texts:

        sentences += re.split(
            r"(?<=[.!?။！？])\s+|\n+",
            t
        )

    sentences = [
        s.strip()
        for s in sentences
        if len(s.strip()) > 25
    ]

    if len(sentences) <= max_sentences:

        return " ".join(
            sentences
        )

    words = []

    for s in sentences:

        words += re.findall(
            r"[\w\u1000-\u109F]+",
            s.lower()
        )

    freq = {}

    for w in words:

        if len(w) >= 2:

            freq[w] = (
                freq.get(w, 0) + 1
            )

    scored = []

    for idx, s in enumerate(
        sentences
    ):

        ws = re.findall(
            r"[\w\u1000-\u109F]+",
            s.lower()
        )

        score = (
            sum(
                freq.get(w, 0)
                for w in ws
            )
            / max(1, len(ws))
        )

        scored.append(
            (
                score,
                idx,
                s
            )
        )

    chosen = sorted(
        sorted(
            scored,
            reverse=True
        )[:max_sentences],
        key=lambda z: z[1]
    )

    return " ".join(
        x[2]
        for x in chosen
    )


# =========================================================
# TEXT TO SPEECH
# =========================================================

async def tts(
    text,
    voice,
    out
):

    communicate = edge_tts.Communicate(
        text,
        voice
    )

    await communicate.save(
        str(out)
    )


# =========================================================
# HOME PAGE
# =========================================================

@app.get(
    "/",
    response_class=HTMLResponse
)
def home():

    index_file = (
        TEMPLATES_DIR
        / "index.html"
    )

    if not index_file.exists():

        return HTMLResponse(
            """
            <html>
            <head>
                <title>RecapMaster</title>
            </head>
            <body>
                <h1>RecapMaster</h1>
                <p>
                    Templates/index.html
                    မတွေ့ပါ။
                </p>
            </body>
            </html>
            """,
            status_code=404
        )

    return index_file.read_text(
        encoding="utf-8"
    )


# =========================================================
# PROCESS URL
# =========================================================

@app.post("/api/process")
async def process(

    url: str = Form(...),

    source_lang: str = Form(
        "auto"
    ),

    target_lang: str = Form(
        "my"
    ),

    voice: str = Form(
        "my-MM-ThihaNeural"
    ),
):

    job = safe_job()

    try:

        # Download
        src = download_media(
            url,
            job
        )

        # Transcribe
        segments, detected = transcribe(
            src,
            None
            if source_lang == "auto"
            else source_lang
        )

        source = (
            detected
            if source_lang == "auto"
            else source_lang
        )

        # Translate
        translated = translate_segments(
            segments,
            source,
            target_lang
        )

        # Create files
        srt = make_srt(
            translated
        )

        transcript = "\n".join(
            x["text"]
            for x in translated
        )

        translation = "\n".join(
            x["translated"]
            for x in translated
        )

        recap = make_recap(
            translated
        )

        recap_file = (
            job / "recap.txt"
        )

        recap_file.write_text(
            recap,
            encoding="utf-8"
        )

        srt_file = (
            job / "subtitles.srt"
        )

        srt_file.write_text(
            srt,
            encoding="utf-8"
        )

        transcript_file = (
            job / "transcript.txt"
        )

        transcript_file.write_text(
            transcript,
            encoding="utf-8"
        )

        translation_file = (
            job / "translation.txt"
        )

        translation_file.write_text(
            translation,
            encoding="utf-8"
        )

        # TTS
        audio_file = (
            job / "narration.mp3"
        )

        try:

            await tts(
                recap,
                voice,
                audio_file
            )

        except Exception:

            audio_file = None

        return {
            "ok": True,
            "job": job.name,
            "detected_language": source,

            "transcript": transcript,

            "translation": translation,

            "recap": recap,

            "srt": srt,

            "audio":
                (
                    f"/api/download/"
                    f"{job.name}/"
                    f"narration.mp3"
                )
                if audio_file
                else None,

            "srt_url":
                f"/api/download/"
                f"{job.name}/"
                f"subtitles.srt",

            "translation_url":
                f"/api/download/"
                f"{job.name}/"
                f"translation.txt",

            "transcript_url":
                f"/api/download/"
                f"{job.name}/"
                f"transcript.txt",

            "recap_url":
                f"/api/download/"
                f"{job.name}/"
                f"recap.txt",
        }

    except Exception as e:

        return JSONResponse(
            {
                "ok": False,
                "error": str(e)
            },
            status_code=500
        )


# =========================================================
# UPLOAD FILE
# =========================================================

@app.post("/api/upload")
async def upload(

    file: UploadFile = File(...),

    source_lang: str = Form(
        "auto"
    ),

    target_lang: str = Form(
        "my"
    ),

    voice: str = Form(
        "my-MM-ThihaNeural"
    ),
):

    job = safe_job()

    suffix = (
        Path(
            file.filename or "media"
        ).suffix
        or ".mp4"
    )

    path = (
        job
        / f"source{suffix}"
    )

    with path.open("wb") as f:

        shutil.copyfileobj(
            file.file,
            f
        )

    try:

        # Transcribe
        segments, detected = transcribe(
            path,
            None
            if source_lang == "auto"
            else source_lang
        )

        source = (
            detected
            if source_lang == "auto"
            else source_lang
        )

        # Translate
        translated = translate_segments(
            segments,
            source,
            target_lang
        )

        # Generate content
        srt = make_srt(
            translated
        )

        transcript = "\n".join(
            x["text"]
            for x in translated
        )

        translation = "\n".join(
            x["translated"]
            for x in translated
        )

        recap = make_recap(
            translated
        )

        # Save files
        (
            job / "subtitles.srt"
        ).write_text(
            srt,
            encoding="utf-8"
        )

        (
            job / "transcript.txt"
        ).write_text(
            transcript,
            encoding="utf-8"
        )

        (
            job / "translation.txt"
        ).write_text(
            translation,
            encoding="utf-8"
        )

        (
            job / "recap.txt"
        ).write_text(
            recap,
            encoding="utf-8"
        )

        # TTS
        audio = (
            job / "narration.mp3"
        )

        try:

            await tts(
                recap,
                voice,
                audio
            )

            audio_url = (
                f"/api/download/"
                f"{job.name}/"
                f"narration.mp3"
            )

        except Exception:

            audio_url = None

        return {
            "ok": True,

            "job": job.name,

            "detected_language":
                source,

            "transcript":
                transcript,

            "translation":
                translation,

            "recap":
                recap,

            "srt":
                srt,

            "audio":
                audio_url,

            "srt_url":
                f"/api/download/"
                f"{job.name}/"
                f"subtitles.srt",

            "translation_url":
                f"/api/download/"
                f"{job.name}/"
                f"translation.txt",

            "transcript_url":
                f"/api/download/"
                f"{job.name}/"
                f"transcript.txt",

            "recap_url":
                f"/api/download/"
                f"{job.name}/"
                f"recap.txt",
        }

    except Exception as e:

        return JSONResponse(
            {
                "ok": False,
                "error": str(e)
            },
            status_code=500
        )


# =========================================================
# DOWNLOAD GENERATED FILES
# =========================================================

@app.get(
    "/api/download/{job}/{name}"
)
def download(
    job: str,
    name: str
):

    # Prevent path traversal
    safe_name = Path(name).name
    safe_job_name = Path(job).name

    p = (
        WORK
        / safe_job_name
        / safe_name
    )

    if not p.exists():

        return JSONResponse(
            {
                "error":
                    "file not found"
            },
            status_code=404
        )

    return FileResponse(
        str(p),
        filename=p.name
    )