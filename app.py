# ─────────────────────────────────────────────────────────────────────────────
#  MOTION TRANSFER STUDIO  v2  ·  Kling AI + RunwayML Act-One
#  Frame-accurate chunking · Comprehensive cost calculation
#  Deploy to Streamlit Cloud · Set secrets in app Settings → Secrets
# ─────────────────────────────────────────────────────────────────────────────
#
#  PIPELINE
#  Guide Video (5 min) ──► frame-accurate split into N × 10-sec chunks
#  Static Image ─────────────────────────────────────┐
#                                                     ▼
#  Chunk 1 ──► API (Kling / Runway) ──► Output Clip 1  ┐
#  Chunk 2 ──► API (Kling / Runway) ──► Output Clip 2  ├─► ZIP for NLE
#  ...                                                 │
#  Chunk N ──► API (Kling / Runway) ──► Output Clip N  ┘
#
#  CHUNK SIZE RATIONALE
#  Both Kling AI and Runway Act-One max out at 10 seconds per generation.
#  10 s is therefore the longest possible chunk — minimising seam count.
#  A 5-minute guide = 30 chunks of 10 s each.
#
#  ENDPOINT NOTES
#  Kling AI :  POST https://api.klingai.com/v1/videos/image2video
#              field: motion_video  (base64 data URI of segment)
#              Verify: https://docs.klingai.com/video-generation/motion-reference
#
#  RunwayML :  POST https://api.dev.runwayml.com/v1/image_to_video
#              model: "gen3a_turbo"  |  field: promptVideo (base64 data URI)
#              Verify: https://docs.dev.runwayml.com/
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import requests
import time
import json
import base64
import math
import os
import io
import zipfile
import tempfile
import subprocess
from fractions import Fraction

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Motion Transfer Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;600;700&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #080810; color: #ddd8f0; }

.hero {
  background: linear-gradient(140deg,#0c0c1e 0%,#120820 40%,#0a160c 100%);
  border: 1px solid #1e1a32;
  border-radius: 18px; padding: 2.4rem 2rem 2rem; margin-bottom: 1.8rem;
  text-align: center;
}
.hero h1 {
  font-family: 'DM Sans', sans-serif; font-weight: 700; font-size: 2.6rem;
  background: linear-gradient(90deg,#a78bfa,#60a5fa,#34d399);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  margin:0; letter-spacing:-0.5px;
}
.hero sub {
  color:#7c6f9a; font-size:1rem; font-family:'Space Mono',monospace;
  display:block; margin-top:0.45rem;
}

.api-badge {
  display:inline-block; padding:0.25rem 0.75rem; border-radius:6px;
  font-family:'Space Mono',monospace; font-size:0.75rem; font-weight:700;
  letter-spacing:0.08em; margin-right:0.4rem;
}
.badge-kling { background:#1a0f30; color:#a78bfa; border:1px solid #4c1d95; }
.badge-runway { background:#0d1f12; color:#34d399; border:1px solid #065f46; }

/* cost table */
.cost-tbl { width:100%; border-collapse:collapse; font-family:'Space Mono',monospace; font-size:0.78rem; }
.cost-tbl th {
  color:#6b7280; text-align:left; padding:0.4rem 0.7rem;
  border-bottom:1px solid #1e1a32; white-space:nowrap;
}
.cost-tbl td { color:#c4bdd8; padding:0.32rem 0.7rem; }
.cost-tbl tr:nth-child(even) td { background:#0d0d18; }
.cost-tbl .hl { color:#a78bfa; font-weight:700; }
.cost-tbl .hl-g { color:#34d399; font-weight:700; }
.cost-tbl .section-hdr td {
  background:#0f0f20; color:#7c6f9a; font-size:0.7rem;
  letter-spacing:0.12em; text-transform:uppercase; padding:0.5rem 0.7rem;
}

/* chunk tracker */
.chunk-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:8px; margin-top:0.5rem; }
.chunk-card {
  background:#0d0d1a; border:1px solid #1e1a32; border-radius:9px;
  padding:0.6rem 0.8rem; font-family:'Space Mono',monospace; font-size:0.72rem;
  display:flex; flex-direction:column; gap:4px;
}
.chunk-card .chunk-id { color:#6b7280; }
.chunk-card .chunk-tc { color:#9d8fbe; }
.chunk-card .chunk-status { font-weight:700; }
.s-wait { color:#4b5563; }
.s-run  { color:#a78bfa; }
.s-done { color:#34d399; }
.s-fail { color:#f87171; }
.s-skip { color:#d97706; }

div[data-testid="metric-container"] {
  background:#0d0d1a; border:1px solid #1e1a32; border-radius:10px; padding:0.7rem;
}
[data-testid="stMetricLabel"] { color:#6b7280 !important; font-size:0.75rem !important; }
[data-testid="stMetricValue"] { color:#a78bfa !important; font-weight:700 !important; }

[data-testid="stSidebar"] { background:#060610 !important; }

.stButton>button {
  background:linear-gradient(135deg,#7c3aed,#2563eb) !important;
  border:none !important; border-radius:10px !important; color:#fff !important;
  font-family:'DM Sans',sans-serif !important; font-weight:700 !important;
  font-size:0.96rem !important; letter-spacing:0.02em !important;
}
.stButton>button:hover { opacity:0.85 !important; }
.stButton>button:disabled { opacity:0.35 !important; }

.stProgress > div > div { background:linear-gradient(90deg,#7c3aed,#34d399) !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# Maximum clip length each API can generate in one call.
# This is the longest possible chunk — use it to minimise seam count.
API_MAX_SECONDS = {
    "Kling AI":   10,   # Kling supports 5 s or 10 s
    "RunwayML":   10,   # Runway Act-One supports 5 s or 10 s
}

# ── Kling AI Pricing (USD per generated clip, as of mid-2025) ────────────────
# Source: https://klingai.com/pricing  — verify before billing clients
KLING_PRICING = {
    "Standard (720p)":      {5: 0.045, 10: 0.070},
    "Professional (1080p)": {5: 0.090, 10: 0.140},
}

# ── RunwayML Act-One Pricing (estimated USD per generated clip, mid-2025) ────
# Runway uses a credit system. Estimates based on public pricing tiers.
# Source: https://runwayml.com/pricing  — verify before billing clients
# Gen-3 Alpha Turbo ≈ 50 credits / 5 s clip
# Gen-3 Alpha       ≈ 90 credits / 5 s clip
# Basic plan        ≈ $0.024/credit (125 credits = $3)
RUNWAY_PRICING = {
    "Gen-3 Alpha Turbo": {5: 0.50, 10: 1.00},
    "Gen-3 Alpha":       {5: 0.90, 10: 1.80},
}

# Minimum chunk duration sent to the API (shorter tail chunks are padded or skipped)
MIN_CHUNK_SEC = 4  # seconds


# ─────────────────────────────────────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
_defaults = {
    "result_urls":   [],
    "chunk_meta":    [],
    "processing":    False,
    "log":           [],
    "zip_bytes":     None,
    "manifest_csv":  "",
    "total_cost":    0.0,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def append_log(msg: str):
    ts = time.strftime("%H:%M:%S")
    st.session_state.log.append(f"[{ts}]  {msg}")


# ─────────────────────────────────────────────────────────────────────────────
#  SECRETS
# ─────────────────────────────────────────────────────────────────────────────
def secret(key: str) -> str | None:
    try:
        return st.secrets[key]
    except Exception:
        return None

STORED_KLING  = secret("KLING_API_KEY")
STORED_RUNWAY = secret("RUNWAY_API_KEY")


# ─────────────────────────────────────────────────────────────────────────────
#  UTILITY
# ─────────────────────────────────────────────────────────────────────────────
def to_b64(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")

def sec_to_tc(s: float) -> str:
    """Seconds → HH:MM:SS:FF (at 25 fps for display)."""
    h  = int(s) // 3600
    m  = (int(s) % 3600) // 60
    sc = int(s) % 60
    fr = int((s % 1) * 25)
    return f"{h:02d}:{m:02d}:{sc:02d}:{fr:02d}"

def fmt_usd(v: float) -> str:
    return f"${v:.2f}"


# ─────────────────────────────────────────────────────────────────────────────
#  COST CALCULATOR
# ─────────────────────────────────────────────────────────────────────────────
def compute_cost(total_sec: float, chunk_sec: int, api: str, model: str) -> dict:
    n_full  = int(total_sec // chunk_sec)
    tail    = total_sec % chunk_sec
    n_tail  = 1 if tail >= MIN_CHUNK_SEC else 0
    n_skip  = 1 if tail > 0 and tail < MIN_CHUNK_SEC else 0
    n_total = n_full + n_tail

    if api == "Kling AI":
        per_clip = KLING_PRICING[model][chunk_sec]
    else:
        per_clip = RUNWAY_PRICING[model][chunk_sec]

    tail_cost = per_clip * n_tail  # full-price even for shorter tail (API minimum billing)
    total_cost = n_full * per_clip + tail_cost

    return {
        "n_full":    n_full,
        "n_tail":    n_tail,
        "n_skip":    n_skip,
        "n_total":   n_total,
        "tail_sec":  tail,
        "per_clip":  per_clip,
        "total":     total_cost,
    }


def render_cost_table(total_sec: float, chunk_sec: int):
    """Render full side-by-side cost comparison table as HTML."""
    rows = ""

    # Kling AI block
    rows += '<tr class="section-hdr"><td colspan="5">KLING AI</td></tr>'
    for model, prices in KLING_PRICING.items():
        for dur in [5, 10]:
            c = compute_cost(total_sec, dur, "Kling AI", model)
            selected = "hl" if dur == chunk_sec else ""
            rows += (
                f"<tr>"
                f"<td>{model}</td>"
                f"<td>{dur}s</td>"
                f"<td>{c['n_total']}</td>"
                f"<td>{fmt_usd(c['per_clip'])}</td>"
                f"<td class='{selected}'>{fmt_usd(c['total'])}</td>"
                f"</tr>"
            )

    # RunwayML block
    rows += '<tr class="section-hdr"><td colspan="5">RUNWAYML ACT-ONE</td></tr>'
    for model, prices in RUNWAY_PRICING.items():
        for dur in [5, 10]:
            c = compute_cost(total_sec, dur, "RunwayML", model)
            selected = "hl-g" if dur == chunk_sec else ""
            rows += (
                f"<tr>"
                f"<td>{model}</td>"
                f"<td>{dur}s</td>"
                f"<td>{c['n_total']}</td>"
                f"<td>{fmt_usd(c['per_clip'])}</td>"
                f"<td class='{selected}'>{fmt_usd(c['total'])}</td>"
                f"</tr>"
            )

    return f"""
<table class="cost-tbl">
  <thead>
    <tr>
      <th>Model</th><th>Chunk</th><th>Clips</th>
      <th>$/Clip</th><th>Total</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
</table>
<p style="font-size:0.68rem;color:#4b5563;margin-top:0.4rem;">
  ★ Highlighted row = current settings.&nbsp;
  Kling prices from klingai.com/pricing.&nbsp;
  Runway prices estimated from runwayml.com/pricing credit tiers — verify before use.
</p>"""


# ─────────────────────────────────────────────────────────────────────────────
#  FFMPEG — FRAME-ACCURATE CHUNK SPLITTER
# ─────────────────────────────────────────────────────────────────────────────
def ffmpeg_ok() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def probe_video(path: str) -> dict:
    """
    Return dict with duration, fps (float), total_frames, width, height.
    Uses ffprobe JSON output — most reliable approach.
    """
    r = subprocess.run(
        ["ffprobe", "-v", "quiet",
         "-select_streams", "v:0",
         "-show_entries", "stream=r_frame_rate,nb_frames,width,height",
         "-show_entries", "format=duration",
         "-print_format", "json", path],
        capture_output=True, text=True, check=True
    )
    data   = json.loads(r.stdout)
    stream = data["streams"][0]
    fmt    = data["format"]

    duration = float(fmt["duration"])
    fps      = float(Fraction(stream["r_frame_rate"]))  # e.g. "30000/1001" → 29.97

    # nb_frames may be absent in some containers — derive from duration + fps
    if "nb_frames" in stream and stream["nb_frames"] != "N/A":
        total_frames = int(stream["nb_frames"])
    else:
        total_frames = int(duration * fps)

    return {
        "duration":     duration,
        "fps":          fps,
        "total_frames": total_frames,
        "width":        int(stream.get("width",  0)),
        "height":       int(stream.get("height", 0)),
    }


def split_video_frame_accurate(
    video_bytes: bytes,
    chunk_sec: int,
    status_fn=None
) -> tuple[list[dict], dict]:
    """
    Split video into frame-accurate chunks.

    Strategy:
    1. Write input to temp file.
    2. Probe: get exact fps, frame count, duration.
    3. Calculate chunk boundaries in FRAME numbers (not seconds) to avoid
       drift from floating-point timestamp rounding.
    4. For each chunk, decode precisely with:
         ffmpeg -ss <start_pts> -i input -t <dur> -c:v libx264 ...
       Using -ss AFTER -i ensures frame-accurate decode (not fast keyframe seek).
    5. Each chunk gets a forced keyframe at frame 0 so NLE can cut cleanly.

    Returns: (list of chunk dicts, probe info dict)
    """
    chunks = []

    with tempfile.TemporaryDirectory() as tmp:
        inp = os.path.join(tmp, "input.mp4")
        with open(inp, "wb") as f:
            f.write(video_bytes)

        info  = probe_video(inp)
        fps   = info["fps"]
        total = info["total_frames"]
        dur   = info["duration"]

        chunk_frames = int(round(chunk_sec * fps))
        n_chunks     = math.ceil(total / chunk_frames)

        if status_fn:
            status_fn(f"Video: {dur:.2f}s · {fps:.3f} fps · {total} frames · {n_chunks} chunks")

        for i in range(n_chunks):
            start_frame = i * chunk_frames
            end_frame   = min((i + 1) * chunk_frames, total)
            n_frames    = end_frame - start_frame

            # Use precise float timestamps derived from frame numbers
            start_ts   = start_frame / fps
            chunk_dur  = n_frames / fps

            out = os.path.join(tmp, f"chunk_{i:04d}.mp4")

            # Frame-accurate split:
            # -ss AFTER -i  → slow but frame-exact decode
            # -t             → output exactly chunk_dur seconds
            # -force_key_frames 0 → I-frame at the very first output frame
            # -an            → strip audio (motion reference only)
            # -avoid_negative_ts make_zero → clean timeline for each chunk
            result = subprocess.run(
                ["ffmpeg", "-y",
                 "-i", inp,
                 "-ss", f"{start_ts:.9f}",
                 "-t",  f"{chunk_dur:.9f}",
                 "-c:v", "libx264",
                 "-preset", "fast",
                 "-crf", "18",
                 "-pix_fmt", "yuv420p",
                 "-x264opts", "keyint=1:min-keyint=1",  # every frame is a keyframe (safest for NLE)
                 "-an",
                 "-avoid_negative_ts", "make_zero",
                 "-movflags", "+faststart",
                 out],
                capture_output=True
            )

            file_ok   = os.path.exists(out) and os.path.getsize(out) > 2048
            is_tail   = (i == n_chunks - 1) and (chunk_dur < chunk_sec - 0.1)
            too_short = chunk_dur < MIN_CHUNK_SEC

            chunk_bytes = b""
            if file_ok:
                with open(out, "rb") as f:
                    chunk_bytes = f.read()

            fname = (
                f"chunk_{i+1:04d}"
                f"_TC_{sec_to_tc(start_ts).replace(':','-')}"
                f"_to_{sec_to_tc(start_ts+chunk_dur).replace(':','-')}"
                f".mp4"
            )

            chunks.append({
                "index":        i,
                "bytes":        chunk_bytes,
                "start_ts":     start_ts,
                "end_ts":       start_ts + chunk_dur,
                "duration":     chunk_dur,
                "start_frame":  start_frame,
                "end_frame":    end_frame,
                "n_frames":     n_frames,
                "fps":          fps,
                "is_tail":      is_tail,
                "too_short":    too_short,
                "file_ok":      file_ok,
                "filename":     fname,
                "status":       "skip" if too_short else "wait",
                "output_url":   None,
            })

            if status_fn:
                status_fn(
                    f"  chunk {i+1}/{n_chunks}: "
                    f"frame {start_frame}–{end_frame} "
                    f"({chunk_dur:.3f}s) "
                    f"{'[TAIL]' if is_tail else ''}"
                    f"{'[TOO SHORT → SKIP]' if too_short else ''}"
                )

    return chunks, info


# ─────────────────────────────────────────────────────────────────────────────
#  KLING AI API
# ─────────────────────────────────────────────────────────────────────────────
KLING_BASE = "https://api.klingai.com"

def kling_headers(key: str) -> dict:
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

def kling_submit(key: str, image_b64: str, video_b64: str, duration: int, model: str, prompt: str) -> str:
    """
    POST /v1/videos/image2video  with motion_video field (motion-reference feature).
    Returns task_id.
    Endpoint docs: https://docs.klingai.com/video-generation/motion-reference
    """
    # Detect image MIME
    mime = "image/png" if image_b64.startswith("iVBORw0") else "image/jpeg"

    payload = {
        "model_name":        "kling-v1-5",
        "image":             f"data:{mime};base64,{image_b64}",
        "motion_video":      f"data:video/mp4;base64,{video_b64}",
        "duration":          str(duration),
        "mode":              "professional" if "1080" in model else "standard",
        "cfg_scale":         0.5,
        "prompt":            prompt or "smooth motion, high quality, cinematic",
        "negative_prompt":   "blur, artifacts, distortion, watermark, low quality",
    }
    r = requests.post(f"{KLING_BASE}/v1/videos/image2video",
                      headers=kling_headers(key), json=payload, timeout=90)
    if not r.ok:
        raise requests.HTTPError(f"Kling {r.status_code}: {r.text}", response=r)
    data    = r.json()
    task_id = data.get("data", {}).get("task_id", "")
    if not task_id:
        raise ValueError(f"No task_id in Kling response: {data}")
    return task_id


def kling_poll(key: str, task_id: str, max_wait: int = 600) -> str:
    """Poll until done. Returns output video URL."""
    start = time.time()
    while True:
        if time.time() - start > max_wait:
            raise TimeoutError(f"Kling task {task_id} timed out after {max_wait}s")
        r = requests.get(f"{KLING_BASE}/v1/videos/image2video/{task_id}",
                         headers=kling_headers(key), timeout=30)
        r.raise_for_status()
        d      = r.json().get("data", {})
        status = d.get("task_status", "processing")
        if status == "succeed":
            try:
                return d["task_result"]["videos"][0]["url"]
            except (KeyError, IndexError):
                raise ValueError(f"No video URL in result: {d}")
        if status in ("failed", "error"):
            raise RuntimeError(f"Kling task failed: {d.get('task_status_msg','unknown')}")
        time.sleep(6)


# ─────────────────────────────────────────────────────────────────────────────
#  RUNWAYML ACT-ONE API
# ─────────────────────────────────────────────────────────────────────────────
RUNWAY_BASE = "https://api.dev.runwayml.com/v1"

def runway_headers(key: str) -> dict:
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
        "X-Runway-Version": "2024-11-06",   # API version header required by Runway
    }

def runway_submit(key: str, image_b64: str, video_b64: str, duration: int, model: str, prompt: str) -> str:
    """
    POST /image_to_video  with promptVideo (Act-One motion driver).
    Returns task_id.
    Docs: https://docs.dev.runwayml.com/

    Act-One uses the uploaded video as the performance driver and the
    promptImage as the character/subject to animate.
    """
    mime   = "image/png" if image_b64.startswith("iVBORw0") else "image/jpeg"
    m_slug = "gen3a_turbo" if "Turbo" in model else "gen3a"

    payload = {
        "model":        m_slug,
        "promptImage":  f"data:{mime};base64,{image_b64}",
        "promptVideo":  f"data:video/mp4;base64,{video_b64}",  # Act-One driver
        "duration":     duration,
        "ratio":        "1280:720" if duration <= 5 else "1280:720",
        "watermark":    False,
        "promptText":   prompt or "smooth motion, high quality, cinematic",
        "seed":         42,   # reproducible across chunks
    }
    r = requests.post(f"{RUNWAY_BASE}/image_to_video",
                      headers=runway_headers(key), json=payload, timeout=90)
    if not r.ok:
        raise requests.HTTPError(f"Runway {r.status_code}: {r.text}", response=r)
    data    = r.json()
    task_id = data.get("id", "")
    if not task_id:
        raise ValueError(f"No task id in Runway response: {data}")
    return task_id


def runway_poll(key: str, task_id: str, max_wait: int = 600) -> str:
    """Poll GET /tasks/{id} until SUCCEEDED. Returns output video URL."""
    start = time.time()
    while True:
        if time.time() - start > max_wait:
            raise TimeoutError(f"Runway task {task_id} timed out after {max_wait}s")
        r = requests.get(f"{RUNWAY_BASE}/tasks/{task_id}",
                         headers=runway_headers(key), timeout=30)
        r.raise_for_status()
        d      = r.json()
        status = d.get("status", "PENDING")
        if status == "SUCCEEDED":
            output = d.get("output", [])
            if output:
                return output[0]
            raise ValueError(f"No output URL in Runway result: {d}")
        if status in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"Runway task {task_id} failed: {d.get('failure','unknown')}")
        time.sleep(6)


# ─────────────────────────────────────────────────────────────────────────────
#  ZIP PACKAGER
# ─────────────────────────────────────────────────────────────────────────────
def build_zip(chunks: list[dict]) -> tuple[bytes, str]:
    """
    Download all output clips and pack into a ZIP.
    Also generates a CSV manifest with timecodes for NLE import.
    Returns (zip_bytes, manifest_csv_string).
    """
    buf     = io.BytesIO()
    manifest_lines = [
        "chunk_number,filename,start_tc,end_tc,start_sec,end_sec,duration_sec,output_url"
    ]

    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        for ch in chunks:
            if ch["status"] != "done" or not ch["output_url"]:
                continue

            fname = ch["filename"]

            # Download the output clip
            r = requests.get(ch["output_url"], timeout=120)
            r.raise_for_status()
            zf.writestr(fname, r.content)

            manifest_lines.append(
                f"{ch['index']+1},{fname},"
                f"{sec_to_tc(ch['start_ts'])},{sec_to_tc(ch['end_ts'])},"
                f"{ch['start_ts']:.3f},{ch['end_ts']:.3f},{ch['duration']:.3f},"
                f"{ch['output_url']}"
            )

        manifest_csv = "\n".join(manifest_lines)
        zf.writestr("MANIFEST.csv", manifest_csv)
        zf.writestr(
            "README_NLE_IMPORT.txt",
            "MOTION TRANSFER STUDIO — Output Package\n"
            "========================================\n\n"
            "Each file is one chunk of the animated output, in order.\n"
            "Import all MP4 files into your NLE (Avid / Premiere / DaVinci) and\n"
            "place them on a timeline in sequence — they will align perfectly.\n\n"
            "MANIFEST.csv lists each chunk with:\n"
            "  - SMPTE timecode (HH:MM:SS:FF at 25 fps display)\n"
            "  - Precise start/end in seconds\n"
            "  - Original Kling/Runway output URL\n\n"
            "Chunks are named:\n"
            "  chunk_NNNN_TC_HH-MM-SS-FF_to_HH-MM-SS-FF.mp4\n\n"
            "All clips are H.264 MP4, no audio, suitable for AMA linking in Avid.\n"
        )

    return buf.getvalue(), manifest_csv


# ─────────────────────────────────────────────────────────────────────────────
#  CHUNK STATUS RENDERER
# ─────────────────────────────────────────────────────────────────────────────
def render_chunk_grid(chunks: list[dict]) -> str:
    cards = ""
    for ch in chunks:
        s  = ch["status"]
        sc = {"wait":"s-wait","run":"s-run","done":"s-done","fail":"s-fail","skip":"s-skip"}.get(s,"s-wait")
        label = {"wait":"QUEUED","run":"RUNNING","done":"DONE","fail":"FAILED","skip":"SKIP (too short)"}.get(s, s.upper())
        tail_tag = " [TAIL]" if ch["is_tail"] else ""
        cards += f"""
        <div class="chunk-card">
          <span class="chunk-id">Chunk {ch['index']+1:04d}{tail_tag}</span>
          <span class="chunk-tc">{sec_to_tc(ch['start_ts'])} → {sec_to_tc(ch['end_ts'])}</span>
          <span class="chunk-tc">{ch['duration']:.3f}s · {ch['n_frames']} frames</span>
          <span class="chunk-status {sc}">{label}</span>
        </div>"""
    return f'<div class="chunk-grid">{cards}</div>'


# ─────────────────────────────────────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎛️ Settings")

    # API selector
    st.markdown("### 🔌 Motion Transfer API")
    chosen_api = st.radio(
        "API Engine",
        ["Kling AI", "RunwayML"],
        horizontal=True,
        label_visibility="collapsed"
    )

    if chosen_api == "Kling AI":
        st.markdown('<span class="api-badge badge-kling">KLING AI</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="api-badge badge-runway">RUNWAYML ACT-ONE</span>', unsafe_allow_html=True)

    st.markdown("---")

    # API Keys
    st.markdown("### 🔑 API Keys")

    if chosen_api == "Kling AI":
        if STORED_KLING:
            st.success("Kling key loaded from Secrets ✓")
            active_key = STORED_KLING
        else:
            k = st.text_input("Kling AI API Key", type="password",
                              help="klingai.com → Developer → API Keys")
            active_key = k or None
            if not active_key:
                st.caption("Or add `KLING_API_KEY = \"...\"` to Streamlit Secrets.")
    else:
        if STORED_RUNWAY:
            st.success("Runway key loaded from Secrets ✓")
            active_key = STORED_RUNWAY
        else:
            k = st.text_input("RunwayML API Key", type="password",
                              help="app.runwayml.com → Account → API")
            active_key = k or None
            if not active_key:
                st.caption("Or add `RUNWAY_API_KEY = \"...\"` to Streamlit Secrets.")

    st.markdown("---")

    # Model & quality
    st.markdown("### 🎥 Model & Quality")

    if chosen_api == "Kling AI":
        model = st.selectbox("Quality", list(KLING_PRICING.keys()), index=1)
    else:
        model = st.selectbox("Model", list(RUNWAY_PRICING.keys()), index=0)

    # Chunk length — always show 10 s as default (and explain why)
    chunk_sec = st.select_slider(
        "Chunk Length",
        options=[5, 10],
        value=10,
        format_func=lambda x: f"{x} seconds (MAX)" if x == API_MAX_SECONDS[chosen_api] else f"{x} seconds"
    )
    st.caption(
        f"10 s is the **maximum** {chosen_api} can generate per call — "
        "always choose this to minimise the number of seams in the final edit."
    )

    prompt_txt = st.text_area(
        "Style Prompt (optional)",
        placeholder="cinematic, sharp detail, studio lighting…",
        height=60
    )

    st.markdown("---")

    # Inline log
    if st.session_state.log:
        with st.expander("📋 Processing Log", expanded=False):
            st.code("\n".join(st.session_state.log[-60:]), language=None)


# ─────────────────────────────────────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>🎬 Motion Transfer Studio</h1>
  <sub>Frame-accurate chunking · Kling AI + RunwayML Act-One · ZIP export for Avid / Premiere / DaVinci</sub>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  STEP 1 — UPLOAD
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("## 1 · Upload Files")
col_v, col_i = st.columns(2, gap="large")

with col_v:
    st.markdown("#### 🎥 Motion Guide Video")
    st.caption(
        "The movement blueprint. Any length — the app will split it into "
        f"frame-accurate {chunk_sec}-second chunks automatically. "
        "Single person, full body visible, good contrast."
    )
    guide_file = st.file_uploader(
        "Guide video", type=["mp4", "mov", "webm", "avi"],
        key="guide", label_visibility="collapsed"
    )
    if guide_file:
        st.video(guide_file)
        st.caption(f"`{guide_file.name}` · {guide_file.size/1_048_576:.1f} MB")

with col_i:
    st.markdown("#### 🖼️ Static Subject Image")
    st.caption(
        "The figure that will come to life. Single person, any pose, "
        "full body preferred. PNG or JPEG, min 512×512 px."
    )
    image_file = st.file_uploader(
        "Subject image", type=["jpg","jpeg","png","webp"],
        key="subject", label_visibility="collapsed"
    )
    if image_file:
        st.image(image_file, use_container_width=True)
        st.caption(f"`{image_file.name}`")


# ─────────────────────────────────────────────────────────────────────────────
#  STEP 2 — COST & CHUNK PREVIEW
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("## 2 · Cost & Chunk Preview")

if guide_file:
    # Rough duration estimate from file size (1.5 Mbit/s web video average)
    est_sec = min(guide_file.size / (1.5 * 1_048_576 / 8), 600)
    est_sec = max(est_sec, 5.0)

    c_now = compute_cost(est_sec, chunk_sec, chosen_api, model)

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("Est. Duration",  f"{est_sec:.0f}s")
    col_m2.metric("Chunks",         c_now["n_total"])
    col_m3.metric("Cost / Chunk",   fmt_usd(c_now["per_clip"]))
    col_m4.metric("Total Est. Cost",fmt_usd(c_now["total"]))

    if c_now["n_skip"] > 0:
        st.caption(
            f"ℹ️ The last {c_now['tail_sec']:.1f}s tail is shorter than "
            f"{MIN_CHUNK_SEC}s and will be skipped (too short for API minimum)."
        )

    st.markdown("**Full pricing comparison — all modes:**")
    st.markdown(render_cost_table(est_sec, chunk_sec), unsafe_allow_html=True)

else:
    st.markdown("**Showing 5-minute (300s) reference costs:**")
    st.markdown(render_cost_table(300, chunk_sec), unsafe_allow_html=True)
    st.caption("Upload your guide video above to see costs based on its actual duration.")


# ─────────────────────────────────────────────────────────────────────────────
#  STEP 3 — GENERATE
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("## 3 · Generate")

ffmpeg_ready = ffmpeg_ok()
if not ffmpeg_ready:
    st.error(
        "**ffmpeg not found.** Add `ffmpeg` to `packages.txt` in your repo root "
        "and redeploy to Streamlit Cloud."
    )

if not active_key:
    st.warning(f"⚠️ Enter your {chosen_api} API key in the sidebar.")
elif not guide_file or not image_file:
    st.info("📂 Upload both files to unlock generation.")
elif not ffmpeg_ready:
    pass  # error shown above
else:
    c_preview = compute_cost(
        min(guide_file.size / (1.5*1_048_576/8), 600),
        chunk_sec, chosen_api, model
    )
    st.markdown(
        f"**{chosen_api} · {model} · {chunk_sec}s chunks · "
        f"~{c_preview['n_total']} clips · Est. {fmt_usd(c_preview['total'])}**"
    )
    go_btn = st.button(
        f"▶️  Start Motion Transfer  ({chosen_api})",
        type="primary",
        disabled=st.session_state.processing
    )

    if go_btn:
        # ── Reset state ────────────────────────────────────────────────────
        st.session_state.update({
            "result_urls": [], "chunk_meta": [], "log": [],
            "zip_bytes": None, "manifest_csv": "", "total_cost": 0.0,
            "processing": True,
        })

        st.markdown("---")
        st.markdown("## ⚙️ Processing")

        prog         = st.progress(0, text="Reading files…")
        status_ph    = st.empty()
        grid_ph      = st.empty()
        cost_live_ph = st.empty()

        try:
            image_bytes = image_file.read()
            video_bytes = guide_file.read()
            image_b64   = to_b64(image_bytes)
            append_log("Files read into memory.")

            # ── Split video ────────────────────────────────────────────────
            status_ph.info("✂️ Splitting guide video with frame-accurate ffmpeg pass…")
            append_log("Starting ffmpeg frame-accurate split.")

            def log_split(msg):
                append_log(msg)

            chunks, vid_info = split_video_frame_accurate(
                video_bytes, chunk_sec, log_split
            )
            st.session_state.chunk_meta = chunks

            n_processable = sum(1 for c in chunks if c["status"] == "wait")
            n_skip        = sum(1 for c in chunks if c["status"] == "skip")

            status_ph.info(
                f"📹 Video split: **{len(chunks)} chunks** "
                f"({vid_info['duration']:.2f}s · {vid_info['fps']:.3f} fps) · "
                f"{n_processable} to process · {n_skip} skipped (tail too short)"
            )
            grid_ph.markdown(render_chunk_grid(chunks), unsafe_allow_html=True)
            append_log(f"Split complete: {len(chunks)} chunks, {n_processable} processable.")

            # ── Process each chunk ─────────────────────────────────────────
            cost_so_far  = 0.0
            done_count   = 0
            per_clip_cost = (
                KLING_PRICING[model][chunk_sec]
                if chosen_api == "Kling AI"
                else RUNWAY_PRICING[model][chunk_sec]
            )

            for i, ch in enumerate(chunks):
                if ch["status"] == "skip":
                    append_log(f"Chunk {i+1}: SKIPPED (too short: {ch['duration']:.2f}s)")
                    continue

                pct = int(10 + (done_count / n_processable) * 85)
                prog.progress(pct, text=f"Chunk {i+1}/{len(chunks)}  ·  {sec_to_tc(ch['start_ts'])} → {sec_to_tc(ch['end_ts'])}")

                ch["status"] = "run"
                grid_ph.markdown(render_chunk_grid(chunks), unsafe_allow_html=True)

                try:
                    if not ch["file_ok"]:
                        raise RuntimeError("ffmpeg failed to produce this chunk file")

                    seg_b64 = to_b64(ch["bytes"])
                    append_log(f"Chunk {i+1}: submitting to {chosen_api}…")

                    if chosen_api == "Kling AI":
                        task_id = kling_submit(
                            active_key, image_b64, seg_b64,
                            chunk_sec, model, prompt_txt
                        )
                        append_log(f"Chunk {i+1}: task_id={task_id}")
                        out_url = kling_poll(active_key, task_id)
                    else:
                        task_id = runway_submit(
                            active_key, image_b64, seg_b64,
                            chunk_sec, model, prompt_txt
                        )
                        append_log(f"Chunk {i+1}: task_id={task_id}")
                        out_url = runway_poll(active_key, task_id)

                    ch["output_url"] = out_url
                    ch["status"]     = "done"
                    cost_so_far     += per_clip_cost
                    done_count      += 1
                    st.session_state.result_urls.append(out_url)
                    st.session_state.total_cost = cost_so_far
                    append_log(f"Chunk {i+1}: DONE → {out_url[:70]}…")

                except Exception as e:
                    ch["status"] = "fail"
                    append_log(f"Chunk {i+1}: FAILED — {e}")
                    st.warning(f"⚠️ Chunk {i+1} failed: {e}")

                grid_ph.markdown(render_chunk_grid(chunks), unsafe_allow_html=True)
                cost_live_ph.info(
                    f"💳 Cost so far: **{fmt_usd(cost_so_far)}** "
                    f"({done_count} clips done)"
                )

            # ── Build ZIP ──────────────────────────────────────────────────
            done_chunks = [c for c in chunks if c["status"] == "done"]
            if done_chunks:
                prog.progress(97, text="Packaging ZIP…")
                status_ph.info("📦 Downloading output clips and building ZIP…")
                append_log(f"Building ZIP for {len(done_chunks)} clips.")
                try:
                    zip_bytes, manifest = build_zip(chunks)
                    st.session_state.zip_bytes    = zip_bytes
                    st.session_state.manifest_csv = manifest
                    append_log("ZIP built successfully.")
                except Exception as ze:
                    st.warning(f"ZIP packaging failed: {ze}")

            prog.progress(100, text="Complete ✓")
            status_ph.success(
                f"✅ Done! {len(done_chunks)}/{n_processable} chunks rendered · "
                f"Total cost: **{fmt_usd(cost_so_far)}**"
            )
            st.session_state.total_cost = cost_so_far

        except Exception as e:
            status_ph.error(f"❌ {e}")
            append_log(f"Fatal error: {e}")
        finally:
            st.session_state.processing = False


# ─────────────────────────────────────────────────────────────────────────────
#  STEP 4 — RESULTS
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.result_urls or st.session_state.chunk_meta:
    st.markdown("---")
    st.markdown("## 4 · Results")

    done_chunks = [c for c in st.session_state.chunk_meta if c["status"] == "done"]
    fail_chunks = [c for c in st.session_state.chunk_meta if c["status"] == "fail"]

    col_r1, col_r2, col_r3 = st.columns(3)
    col_r1.metric("Clips Rendered",  len(done_chunks))
    col_r2.metric("Failed",          len(fail_chunks))
    col_r3.metric("Total Cost",      fmt_usd(st.session_state.total_cost))

    # ZIP download
    if st.session_state.zip_bytes:
        st.markdown("### 📦 Download Package (All Clips + Manifest)")
        st.download_button(
            "⬇️  Download ZIP for NLE import",
            data=st.session_state.zip_bytes,
            file_name="motion_transfer_output.zip",
            mime="application/zip",
            type="primary",
            use_container_width=False
        )
        st.caption(
            "ZIP contains all output MP4 chunks named with timecodes, "
            "plus `MANIFEST.csv` and `README_NLE_IMPORT.txt`. "
            "Import all files into Avid / Premiere / DaVinci and place "
            "them in sequence on a timeline — no further alignment needed."
        )

        if st.session_state.manifest_csv:
            with st.expander("📄 View MANIFEST.csv"):
                st.code(st.session_state.manifest_csv, language="csv")

    # Individual clip viewer
    if done_chunks:
        with st.expander(f"▶️  Preview {len(done_chunks)} individual clips"):
            for ch in done_chunks:
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.markdown(
                        f"**Chunk {ch['index']+1}** · "
                        f"{sec_to_tc(ch['start_ts'])} → {sec_to_tc(ch['end_ts'])} · "
                        f"{ch['duration']:.3f}s · {ch['n_frames']} frames"
                    )
                    st.video(ch["output_url"])
                with col_b:
                    st.markdown(f"[↗ Direct URL]({ch['output_url']})")


# ─────────────────────────────────────────────────────────────────────────────
#  EXPLAINER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("ℹ️  How it works — technical details"):
    st.markdown(f"""
**Why chunks?**
Both Kling AI and RunwayML can generate a maximum of **10 seconds** of video per
API call. A 5-minute guide therefore requires **30 separate calls**, each
producing a 10-second clip. These clips are exported as a ZIP that you import
directly into your NLE and place in sequence — the timing matches exactly
because the input was split with the same precision.

**Frame-accurate splitting (how it's done)**
```
1. ffprobe  →  exact FPS (e.g. 29.97 = 30000/1001), total frame count, duration
2. Chunk boundaries are calculated in FRAME NUMBERS (not seconds)
   to eliminate floating-point drift across 30 chunks.
3. ffmpeg decode: -ss AFTER -i ensures frame-exact decode (not keyframe seek).
4. -x264opts keyint=1:min-keyint=1 makes every frame an I-frame — NLE can
   cut at any point without artefacts.
5. -avoid_negative_ts make_zero resets the timeline of each chunk to 0.
```

**Chunk naming convention**
```
chunk_0001_TC_00-00-00-00_to_00-00-10-00.mp4
chunk_0002_TC_00-00-10-00_to_00-00-20-00.mp4
...
chunk_0030_TC_00-04-50-00_to_00-05-00-00.mp4
```
Timecode is HH:MM:SS:FF (25 fps display). Import in numeric order.

**5-minute video cost breakdown**

| API | Model | Chunk | Clips | Cost |
|-----|-------|-------|-------|------|
| Kling AI | Standard 720p | 5s | 60 | **$2.70** |
| Kling AI | Standard 720p | 10s | 30 | **$2.10** |
| Kling AI | Professional 1080p | 5s | 60 | **$5.40** |
| Kling AI | Professional 1080p | 10s | 30 | **$4.20** |
| RunwayML | Gen-3 Alpha Turbo | 5s | 60 | **$30.00** *(est.)* |
| RunwayML | Gen-3 Alpha Turbo | 10s | 30 | **$30.00** *(est.)* |
| RunwayML | Gen-3 Alpha | 5s | 60 | **$54.00** *(est.)* |
| RunwayML | Gen-3 Alpha | 10s | 30 | **$54.00** *(est.)* |

*Runway prices are estimates based on public credit-tier pricing. Always verify
at [runwayml.com/pricing](https://runwayml.com/pricing) before use.*

**Tips for best results**
- Full-body shots with clear silhouette against a neutral background work best.
- For dance/performance, use Professional (Kling) or Gen-3 Alpha (Runway).
- Keep the same background and lighting in the subject image as the guide video
  for the most coherent output across all 30 chunks.
- Use 10s chunks always — they give the model more temporal context and
  produce smoother motion than 5s chunks.
    """)

# Footer
st.markdown("---")
st.caption(
    "Motion Transfer Studio v2 · "
    "[Kling AI docs](https://docs.klingai.com) · "
    "[RunwayML docs](https://docs.dev.runwayml.com) · "
    "Built with Streamlit"
)
