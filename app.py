# ─────────────────────────────────────────────────────────────────────────────
#  MOTION TRANSFER STUDIO  v3
#  Kling AI (JWT auth) + RunwayML Act-One
#  Frame-accurate chunking · Comprehensive cost calculation · ZIP export
#
#  Streamlit Cloud secrets required:
#    KLING_ACCESS_KEY = "..."   ← Kling Access Key ID
#    KLING_SECRET_KEY = "..."   ← Kling Secret Key
#    RUNWAY_API_KEY   = "..."   ← RunwayML API Key
#
#  packages.txt must contain: ffmpeg
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import requests
import time
import json
import base64
import hmac
import hashlib
import math
import os
import io
import zipfile
import tempfile
import subprocess
from fractions import Fraction

# ─────────────────────────────────────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Motion Transfer Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────────────────────
#  CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #07070f; color: #ddd6f3; }

/* ── Hero ── */
.hero {
  background: linear-gradient(145deg,#0b0b1e 0%,#130b24 45%,#090f14 100%);
  border: 1px solid #1c1830; border-radius: 20px;
  padding: 2.5rem 2rem 2.2rem; margin-bottom: 2rem; text-align: center;
}
.hero h1 {
  font-weight: 800; font-size: 2.7rem;
  background: linear-gradient(95deg,#a78bfa 0%,#60a5fa 50%,#34d399 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  margin: 0; letter-spacing: -0.5px;
}
.hero .sub {
  color: #6b5f8a; font-size: 0.93rem;
  font-family: 'Space Mono', monospace; margin-top: 0.5rem;
}

/* ── API badges ── */
.badge {
  display: inline-block; padding: 0.22rem 0.7rem; border-radius: 6px;
  font-family: 'Space Mono', monospace; font-size: 0.72rem;
  font-weight: 700; letter-spacing: 0.08em;
}
.badge-kling  { background:#1a0f30; color:#a78bfa; border:1px solid #4c1d95; }
.badge-runway { background:#0c1e12; color:#34d399; border:1px solid #064e30; }

/* ── Section labels ── */
.section-label {
  font-size: 0.68rem; font-family: 'Space Mono', monospace;
  letter-spacing: 0.14em; text-transform: uppercase; color: #4b4570;
  margin-bottom: 0.3rem;
}

/* ── Cost table ── */
.cost-tbl { width:100%; border-collapse:collapse;
  font-family:'Space Mono',monospace; font-size:0.76rem; }
.cost-tbl th {
  color:#4b4570; text-align:left; padding:0.38rem 0.7rem;
  border-bottom:1px solid #181428; white-space:nowrap;
}
.cost-tbl td { color:#b8aed0; padding:0.3rem 0.7rem; }
.cost-tbl tr:nth-child(even) td { background:#0b0b17; }
.cost-tbl .sep td {
  background:#0f0f1e; color:#4b4570; font-size:0.66rem;
  letter-spacing:0.14em; text-transform:uppercase; padding:0.45rem 0.7rem;
}
.cost-tbl .active-k td { background:#130f22; }
.cost-tbl .active-r td { background:#0a160d; }
.cost-tbl .hl-k { color:#a78bfa; font-weight:700; }
.cost-tbl .hl-r { color:#34d399; font-weight:700; }

/* ── Chunk grid ── */
.chunk-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px,1fr));
  gap: 7px; margin-top: 0.6rem;
}
.chunk-card {
  background:#0c0c1a; border:1px solid #181428; border-radius:9px;
  padding:0.55rem 0.75rem; font-family:'Space Mono',monospace;
  font-size:0.7rem; display:flex; flex-direction:column; gap:3px;
}
.cc-id   { color:#3d3660; }
.cc-tc   { color:#6b5f8a; }
.cc-st   { font-weight:700; }
.s-wait  { color:#3d3660; }
.s-run   { color:#a78bfa; }
.s-done  { color:#34d399; }
.s-fail  { color:#f87171; }
.s-skip  { color:#d97706; }

/* ── Metrics ── */
div[data-testid="metric-container"] {
  background:#0c0c1a; border:1px solid #181428;
  border-radius:10px; padding:0.7rem;
}
[data-testid="stMetricLabel"]  { color:#4b4570 !important; font-size:0.73rem !important; }
[data-testid="stMetricValue"]  { color:#a78bfa !important; font-weight:800 !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] { background:#060610 !important; }

/* ── Buttons ── */
.stButton>button {
  background:linear-gradient(135deg,#7c3aed,#2563eb) !important;
  border:none !important; border-radius:10px !important;
  color:#fff !important; font-family:'DM Sans',sans-serif !important;
  font-weight:700 !important; font-size:0.96rem !important;
  letter-spacing:0.02em !important;
}
.stButton>button:hover   { opacity:0.84 !important; }
.stButton>button:disabled{ opacity:0.3  !important; }

/* ── Progress bar ── */
.stProgress>div>div { background:linear-gradient(90deg,#7c3aed,#34d399) !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# Maximum seconds a single API call can generate
API_MAX_SEC = {"Kling AI": 10, "RunwayML": 10}

# Kling AI pricing (USD per generated clip, klingai.com/pricing, mid-2025)
KLING_PRICE = {
    "Standard (720p)":      {5: 0.045, 10: 0.070},
    "Professional (1080p)": {5: 0.090, 10: 0.140},
}

# RunwayML pricing (estimated USD per clip from credit-tier pricing, mid-2025)
# Gen-3 Alpha Turbo ≈ 50 credits/5s · Gen-3 Alpha ≈ 90 credits/5s
# Basic plan ≈ $0.024/credit — verify at runwayml.com/pricing
RUNWAY_PRICE = {
    "Gen-3 Alpha Turbo": {5: 0.50, 10: 1.00},
    "Gen-3 Alpha":       {5: 0.90, 10: 1.80},
}

MIN_CHUNK_SEC = 4   # tail chunks shorter than this are skipped


# ─────────────────────────────────────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
_state_defaults = {
    "chunk_meta":   [],
    "result_urls":  [],
    "zip_bytes":    None,
    "manifest_csv": "",
    "total_cost":   0.0,
    "processing":   False,
    "log":          [],
}
for _k, _v in _state_defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ─────────────────────────────────────────────────────────────────────────────
#  UTILITY
# ─────────────────────────────────────────────────────────────────────────────
def to_b64(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")


def sec_to_tc(s: float, fps: float = 25.0) -> str:
    """Seconds → HH:MM:SS:FF timecode string."""
    s   = max(0.0, s)
    h   = int(s) // 3600
    m   = (int(s) % 3600) // 60
    sc  = int(s) % 60
    fr  = int(round((s % 1) * fps)) % int(fps)
    return f"{h:02d}:{m:02d}:{sc:02d}:{fr:02d}"


def tc_for_filename(s: float) -> str:
    return sec_to_tc(s).replace(":", "-")


def fmt_usd(v: float) -> str:
    return f"${v:.2f}"


def alog(msg: str):
    ts = time.strftime("%H:%M:%S")
    st.session_state.log.append(f"[{ts}]  {msg}")


def get_secret(key: str):
    try:
        return st.secrets[key]
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
#  KLING AI — JWT AUTHENTICATION
# ─────────────────────────────────────────────────────────────────────────────
#
#  Kling AI requires two credentials:
#    Access Key  (KLING_ACCESS_KEY) — the key ID, identifies who you are
#    Secret Key  (KLING_SECRET_KEY) — signs the JWT, proves authenticity
#
#  A JWT is generated per-request and expires in 30 minutes.
#  Docs: https://docs.klingai.com/overview/authentication
# ─────────────────────────────────────────────────────────────────────────────

def _b64url(data: bytes) -> str:
    """Base64-URL encode without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def kling_jwt(access_key: str, secret_key: str) -> str:
    """
    Build a signed HS256 JWT from Kling Access Key + Secret Key.
    Token is valid for 30 minutes from time of generation.
    """
    header_b64  = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())

    now         = int(time.time())
    payload     = {"iss": access_key, "exp": now + 1800, "nbf": now - 5}
    payload_b64 = _b64url(json.dumps(payload).encode())

    signing_input = f"{header_b64}.{payload_b64}"
    signature     = _b64url(
        hmac.new(
            secret_key.encode("utf-8"),
            signing_input.encode("utf-8"),
            hashlib.sha256
        ).digest()
    )
    return f"{signing_input}.{signature}"


def kling_headers(access_key: str, secret_key: str) -> dict:
    """Return HTTP headers with a freshly signed Kling JWT."""
    return {
        "Authorization": f"Bearer {kling_jwt(access_key, secret_key)}",
        "Content-Type":  "application/json",
    }


# ─────────────────────────────────────────────────────────────────────────────
#  KLING AI — API CALLS
# ─────────────────────────────────────────────────────────────────────────────
KLING_BASE = "https://api.klingai.com"


def kling_submit(
    access_key: str, secret_key: str,
    image_b64: str, video_b64: str,
    duration: int, model: str, prompt: str
) -> str:
    """
    Submit a motion-reference image-to-video task to Kling AI.
    Returns task_id string.

    Endpoint: POST /v1/videos/image2video
    Field 'motion_video' carries the base64 guide-video segment.
    Verify at: https://docs.klingai.com/video-generation/motion-reference
    """
    mime    = "image/png" if image_b64.startswith("iVBORw0") else "image/jpeg"
    mode    = "professional" if "1080" in model else "standard"

    payload = {
        "model_name":      "kling-v1-5",
        "image":           f"data:{mime};base64,{image_b64}",
        "motion_video":    f"data:video/mp4;base64,{video_b64}",
        "duration":        str(duration),
        "mode":            mode,
        "cfg_scale":       0.5,
        "prompt":          prompt or "smooth motion, high quality, cinematic",
        "negative_prompt": "blur, artifacts, distortion, watermark, low quality",
    }

    resp = requests.post(
        f"{KLING_BASE}/v1/videos/image2video",
        headers=kling_headers(access_key, secret_key),
        json=payload,
        timeout=90,
    )
    if not resp.ok:
        raise requests.HTTPError(
            f"Kling submit HTTP {resp.status_code}: {resp.text}", response=resp
        )

    data    = resp.json()
    task_id = data.get("data", {}).get("task_id", "")
    if not task_id:
        raise ValueError(f"Kling returned no task_id. Response: {data}")
    return task_id


def kling_poll(
    access_key: str, secret_key: str,
    task_id: str, max_wait: int = 600
) -> str:
    """
    Poll GET /v1/videos/image2video/{task_id} until task_status == 'succeed'.
    Returns the output video URL.
    A fresh JWT is generated for each poll request.
    """
    deadline = time.time() + max_wait
    while True:
        if time.time() > deadline:
            raise TimeoutError(f"Kling task {task_id} timed out after {max_wait}s")

        resp = requests.get(
            f"{KLING_BASE}/v1/videos/image2video/{task_id}",
            headers=kling_headers(access_key, secret_key),
            timeout=30,
        )
        resp.raise_for_status()

        data   = resp.json().get("data", {})
        status = data.get("task_status", "processing")

        if status == "succeed":
            try:
                url = data["task_result"]["videos"][0]["url"]
                return url
            except (KeyError, IndexError):
                raise ValueError(f"Kling task succeeded but no video URL: {data}")

        if status in ("failed", "error"):
            msg = data.get("task_status_msg", "unknown error")
            raise RuntimeError(f"Kling task {task_id} failed: {msg}")

        time.sleep(6)


# ─────────────────────────────────────────────────────────────────────────────
#  RUNWAYML — API CALLS
# ─────────────────────────────────────────────────────────────────────────────
RUNWAY_BASE = "https://api.dev.runwayml.com/v1"


def runway_headers(api_key: str) -> dict:
    return {
        "Authorization":    f"Bearer {api_key}",
        "Content-Type":     "application/json",
        "X-Runway-Version": "2024-11-06",
    }


def runway_submit(
    api_key: str,
    image_b64: str, video_b64: str,
    duration: int, model: str, prompt: str
) -> str:
    """
    Submit an Act-One motion-transfer task to RunwayML.
    Returns task_id string.

    Endpoint: POST /v1/image_to_video
    Field 'promptVideo' is the Act-One motion driver (guide video segment).
    Verify at: https://docs.dev.runwayml.com/
    """
    mime   = "image/png" if image_b64.startswith("iVBORw0") else "image/jpeg"
    slug   = "gen3a_turbo" if "Turbo" in model else "gen3a"

    payload = {
        "model":       slug,
        "promptImage": f"data:{mime};base64,{image_b64}",
        "promptVideo": f"data:video/mp4;base64,{video_b64}",
        "duration":    duration,
        "ratio":       "1280:720",
        "watermark":   False,
        "promptText":  prompt or "smooth motion, high quality, cinematic",
        "seed":        42,
    }

    resp = requests.post(
        f"{RUNWAY_BASE}/image_to_video",
        headers=runway_headers(api_key),
        json=payload,
        timeout=90,
    )
    if not resp.ok:
        raise requests.HTTPError(
            f"Runway submit HTTP {resp.status_code}: {resp.text}", response=resp
        )

    data    = resp.json()
    task_id = data.get("id", "")
    if not task_id:
        raise ValueError(f"Runway returned no task id. Response: {data}")
    return task_id


def runway_poll(api_key: str, task_id: str, max_wait: int = 600) -> str:
    """
    Poll GET /v1/tasks/{task_id} until status == 'SUCCEEDED'.
    Returns the output video URL.
    """
    deadline = time.time() + max_wait
    while True:
        if time.time() > deadline:
            raise TimeoutError(f"Runway task {task_id} timed out after {max_wait}s")

        resp = requests.get(
            f"{RUNWAY_BASE}/tasks/{task_id}",
            headers=runway_headers(api_key),
            timeout=30,
        )
        resp.raise_for_status()

        data   = resp.json()
        status = data.get("status", "PENDING")

        if status == "SUCCEEDED":
            output = data.get("output", [])
            if output:
                return output[0]
            raise ValueError(f"Runway task succeeded but no output URL: {data}")

        if status in ("FAILED", "CANCELLED"):
            failure = data.get("failure", "unknown")
            raise RuntimeError(f"Runway task {task_id} failed: {failure}")

        time.sleep(6)


# ─────────────────────────────────────────────────────────────────────────────
#  FFMPEG — FRAME-ACCURATE VIDEO SPLITTING
# ─────────────────────────────────────────────────────────────────────────────

def ffmpeg_available() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def probe_video(path: str) -> dict:
    """
    Return precise video metadata via ffprobe.
    FPS is parsed as an exact rational (e.g. 30000/1001 = 29.97…)
    to avoid floating-point accumulation across many chunks.
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
    fps      = float(Fraction(stream["r_frame_rate"]))  # exact rational → float

    if "nb_frames" in stream and stream["nb_frames"] not in ("N/A", ""):
        total_frames = int(stream["nb_frames"])
    else:
        total_frames = int(math.floor(duration * fps))

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
) -> tuple[list[dict], dict]:
    """
    Split video bytes into frame-accurate chunks using ffmpeg.

    Splitting strategy:
    ┌──────────────────────────────────────────────────────────────────────┐
    │ 1. ffprobe extracts exact FPS as a rational fraction — no drift.     │
    │ 2. Chunk boundaries are computed in FRAME NUMBERS, not seconds,      │
    │    so rounding errors cannot accumulate across 30+ chunks.           │
    │ 3. ffmpeg uses -ss AFTER -i (slow but frame-exact decode path).      │
    │ 4. keyint=1:min-keyint=1  → every frame is an I-frame, safe for      │
    │    any NLE to cut at any point (Avid AMA, Premiere, DaVinci).        │
    │ 5. -avoid_negative_ts make_zero resets each chunk timeline to 0.     │
    └──────────────────────────────────────────────────────────────────────┘

    Returns (chunks list, probe info dict).
    Each chunk dict contains bytes, timecodes, frame numbers, status.
    """
    chunks: list[dict] = []

    with tempfile.TemporaryDirectory() as tmp:
        inp = os.path.join(tmp, "input.mp4")
        with open(inp, "wb") as f:
            f.write(video_bytes)

        info         = probe_video(inp)
        fps          = info["fps"]
        total_frames = info["total_frames"]
        duration     = info["duration"]

        chunk_frames = int(round(chunk_sec * fps))
        n_chunks     = math.ceil(total_frames / chunk_frames)

        alog(
            f"Probe: {duration:.3f}s · {fps:.4f}fps · "
            f"{total_frames} frames · {n_chunks} chunks"
        )

        for i in range(n_chunks):
            start_frame  = i * chunk_frames
            end_frame    = min((i + 1) * chunk_frames, total_frames)
            n_frames     = end_frame - start_frame

            # Timestamps derived from frame numbers for maximum precision
            start_ts     = start_frame / fps
            chunk_dur    = n_frames / fps

            is_tail      = (i == n_chunks - 1) and (chunk_dur < chunk_sec - 0.05)
            too_short    = chunk_dur < MIN_CHUNK_SEC

            out = os.path.join(tmp, f"c_{i:05d}.mp4")

            subprocess.run(
                ["ffmpeg", "-y",
                 # -ss AFTER -i → frame-exact decode (not fast keyframe seek)
                 "-i",   inp,
                 "-ss",  f"{start_ts:.9f}",
                 "-t",   f"{chunk_dur:.9f}",
                 # H.264, every frame an I-frame → NLE-safe
                 "-c:v", "libx264",
                 "-preset", "fast",
                 "-crf", "18",
                 "-pix_fmt", "yuv420p",
                 "-x264opts", "keyint=1:min-keyint=1",
                 # Clean timeline per chunk
                 "-avoid_negative_ts", "make_zero",
                 "-movflags", "+faststart",
                 # No audio — motion reference only
                 "-an",
                 out],
                capture_output=True
            )

            file_ok     = os.path.exists(out) and os.path.getsize(out) > 2048
            chunk_bytes = b""
            if file_ok:
                with open(out, "rb") as f:
                    chunk_bytes = f.read()

            fname = (
                f"chunk_{i+1:04d}"
                f"_TC_{tc_for_filename(start_ts)}"
                f"_to_{tc_for_filename(start_ts + chunk_dur)}"
                f".mp4"
            )

            status = "skip" if too_short else "wait"

            chunks.append({
                "index":       i,
                "bytes":       chunk_bytes,
                "start_ts":    start_ts,
                "end_ts":      start_ts + chunk_dur,
                "duration":    chunk_dur,
                "start_frame": start_frame,
                "end_frame":   end_frame,
                "n_frames":    n_frames,
                "fps":         fps,
                "is_tail":     is_tail,
                "too_short":   too_short,
                "file_ok":     file_ok,
                "filename":    fname,
                "status":      status,
                "output_url":  None,
            })

            alog(
                f"  chunk {i+1:04d}: frames {start_frame}–{end_frame} "
                f"({chunk_dur:.3f}s)"
                + (" [TAIL]" if is_tail else "")
                + (" [SKIP — too short]" if too_short else "")
            )

    return chunks, info


# ─────────────────────────────────────────────────────────────────────────────
#  COST CALCULATOR
# ─────────────────────────────────────────────────────────────────────────────

def cost_breakdown(
    total_sec: float, chunk_sec: int,
    api: str, model: str
) -> dict:
    """Compute full cost breakdown for a given duration and API/model."""
    n_full   = int(total_sec // chunk_sec)
    tail     = total_sec % chunk_sec
    has_tail = tail >= MIN_CHUNK_SEC
    n_total  = n_full + (1 if has_tail else 0)

    per_clip = (
        KLING_PRICE[model][chunk_sec]
        if api == "Kling AI"
        else RUNWAY_PRICE[model][chunk_sec]
    )
    total = n_total * per_clip

    return {
        "n_full": n_full, "n_total": n_total,
        "tail_sec": tail, "has_tail": has_tail,
        "per_clip": per_clip, "total": total,
    }


def render_cost_table(
    total_sec: float,
    active_api: str,
    active_model: str,
    active_chunk: int,
) -> str:
    """Build complete HTML cost comparison table for all models and chunk sizes."""
    rows = ""

    def row(api, model, dur, active):
        c     = cost_breakdown(total_sec, dur, api, model)
        is_k  = api == "Kling AI"
        hl    = "hl-k" if is_k else "hl-r"
        tr_cl = ("active-k" if is_k else "active-r") if active else ""
        price_src = (
            "klingai.com/pricing"
            if is_k
            else "runwayml.com/pricing (est.)"
        )
        return (
            f'<tr class="{tr_cl}">'
            f'<td>{model}</td>'
            f'<td>{dur}s</td>'
            f'<td>{c["n_total"]}</td>'
            f'<td>{fmt_usd(c["per_clip"])}</td>'
            f'<td class="{hl if active else ""}">{fmt_usd(c["total"])}</td>'
            f'</tr>'
        )

    rows += '<tr class="sep"><td colspan="5">KLING AI — exact pricing</td></tr>'
    for m in KLING_PRICE:
        for d in [5, 10]:
            active = (active_api == "Kling AI" and active_model == m and active_chunk == d)
            rows  += row("Kling AI", m, d, active)

    rows += '<tr class="sep"><td colspan="5">RUNWAYML ACT-ONE — estimated pricing</td></tr>'
    for m in RUNWAY_PRICE:
        for d in [5, 10]:
            active = (active_api == "RunwayML" and active_model == m and active_chunk == d)
            rows  += row("RunwayML", m, d, active)

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
<div style="font-size:0.67rem;color:#3d3660;margin-top:0.35rem;">
  Highlighted = current selection.
  Kling prices: klingai.com/pricing.
  Runway prices: estimated from credit tiers at runwayml.com/pricing — verify before use.
</div>"""


# ─────────────────────────────────────────────────────────────────────────────
#  CHUNK GRID RENDERER
# ─────────────────────────────────────────────────────────────────────────────

def render_chunk_grid(chunks: list[dict]) -> str:
    STATUS_MAP = {
        "wait": ("s-wait", "QUEUED"),
        "run":  ("s-run",  "RUNNING"),
        "done": ("s-done", "DONE"),
        "fail": ("s-fail", "FAILED"),
        "skip": ("s-skip", "SKIP — tail too short"),
    }
    cards = ""
    for ch in chunks:
        cls, label = STATUS_MAP.get(ch["status"], ("s-wait", ch["status"].upper()))
        tail_tag   = " ·TAIL" if ch["is_tail"] else ""
        cards += f"""
<div class="chunk-card">
  <span class="cc-id">Chunk {ch['index']+1:04d}{tail_tag}</span>
  <span class="cc-tc">{sec_to_tc(ch['start_ts'])} → {sec_to_tc(ch['end_ts'])}</span>
  <span class="cc-tc">{ch['duration']:.3f}s · {ch['n_frames']} frames</span>
  <span class="cc-st {cls}">{label}</span>
</div>"""
    return f'<div class="chunk-grid">{cards}</div>'


# ─────────────────────────────────────────────────────────────────────────────
#  ZIP PACKAGER
# ─────────────────────────────────────────────────────────────────────────────

def build_zip(chunks: list[dict]) -> tuple[bytes, str]:
    """
    Download all done output clips and pack into a ZIP.
    Includes MANIFEST.csv and a README for NLE import.
    """
    buf  = io.BytesIO()
    done = [c for c in chunks if c["status"] == "done" and c["output_url"]]

    manifest_lines = [
        "chunk_number,filename,start_tc,end_tc,"
        "start_sec,end_sec,duration_sec,n_frames,output_url"
    ]

    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        for ch in done:
            r = requests.get(ch["output_url"], timeout=120)
            r.raise_for_status()
            zf.writestr(ch["filename"], r.content)

            manifest_lines.append(
                f"{ch['index']+1},{ch['filename']},"
                f"{sec_to_tc(ch['start_ts'])},{sec_to_tc(ch['end_ts'])},"
                f"{ch['start_ts']:.4f},{ch['end_ts']:.4f},"
                f"{ch['duration']:.4f},{ch['n_frames']},"
                f"{ch['output_url']}"
            )

        csv_content = "\n".join(manifest_lines)
        zf.writestr("MANIFEST.csv", csv_content)

        readme = (
            "MOTION TRANSFER STUDIO — Output Package\n"
            "=========================================\n\n"
            "IMPORT INSTRUCTIONS\n"
            "  1. Import all MP4 files into your NLE (Avid / Premiere / DaVinci).\n"
            "  2. Place them on the timeline in numeric order (chunk_0001 first).\n"
            "  3. No gap trimming needed — chunks are frame-contiguous.\n\n"
            "FILE NAMING\n"
            "  chunk_NNNN_TC_HH-MM-SS-FF_to_HH-MM-SS-FF.mp4\n"
            "  Timecode is at 25 fps display rate.\n\n"
            "MANIFEST.csv\n"
            "  Contains SMPTE timecode, precise seconds, frame count,\n"
            "  and original API output URL for every clip.\n\n"
            "CODEC\n"
            "  H.264 MP4 · no audio · every frame is an I-frame.\n"
            "  Compatible with Avid AMA linking, Premiere, DaVinci Resolve.\n"
        )
        zf.writestr("README_NLE_IMPORT.txt", readme)

    return buf.getvalue(), csv_content


# ─────────────────────────────────────────────────────────────────────────────
#  LOAD SECRETS
# ─────────────────────────────────────────────────────────────────────────────
STORED_KLING_ACCESS = get_secret("KLING_ACCESS_KEY")
STORED_KLING_SECRET = get_secret("KLING_SECRET_KEY")
STORED_RUNWAY       = get_secret("RUNWAY_API_KEY")


# ─────────────────────────────────────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎛️ Settings")

    # ── API selector ────────────────────────────────────────────────────────
    st.markdown("### 🔌 API Engine")
    chosen_api = st.radio(
        "engine", ["Kling AI", "RunwayML"],
        horizontal=True, label_visibility="collapsed"
    )

    badge_html = (
        '<span class="badge badge-kling">KLING AI</span>'
        if chosen_api == "Kling AI"
        else '<span class="badge badge-runway">RUNWAYML ACT-ONE</span>'
    )
    st.markdown(badge_html, unsafe_allow_html=True)

    st.markdown("---")

    # ── API keys ────────────────────────────────────────────────────────────
    st.markdown("### 🔑 API Keys")

    if chosen_api == "Kling AI":
        if STORED_KLING_ACCESS and STORED_KLING_SECRET:
            st.success("Kling Access Key + Secret Key loaded ✓")
            active_access = STORED_KLING_ACCESS
            active_secret = STORED_KLING_SECRET
        else:
            active_access = st.text_input(
                "Kling Access Key",
                type="password",
                help="From klingai.com → Developer → API Keys"
            )
            active_secret = st.text_input(
                "Kling Secret Key",
                type="password",
                help="From klingai.com → Developer → API Keys"
            )
            if not (active_access and active_secret):
                st.caption(
                    "Add `KLING_ACCESS_KEY` and `KLING_SECRET_KEY` "
                    "to Streamlit Secrets to avoid entering them here."
                )
        active_key  = None  # not used for Kling
        keys_ready  = bool(active_access and active_secret)

    else:
        active_access = None
        active_secret = None
        if STORED_RUNWAY:
            st.success("RunwayML API Key loaded ✓")
            active_key = STORED_RUNWAY
        else:
            active_key = st.text_input(
                "RunwayML API Key",
                type="password",
                help="From app.runwayml.com → Account → API"
            )
            if not active_key:
                st.caption(
                    "Add `RUNWAY_API_KEY` to Streamlit Secrets "
                    "to avoid entering it here."
                )
        keys_ready = bool(active_key)

    st.markdown("---")

    # ── Model & chunk ───────────────────────────────────────────────────────
    st.markdown("### 🎥 Model & Quality")

    if chosen_api == "Kling AI":
        model = st.selectbox("Quality", list(KLING_PRICE.keys()), index=1)
    else:
        model = st.selectbox("Model", list(RUNWAY_PRICE.keys()), index=0)

    chunk_sec = st.select_slider(
        "Chunk Length",
        options=[5, 10], value=10,
        format_func=lambda x: (
            f"{x}s  ← MAXIMUM (fewer seams)" if x == 10 else f"{x}s"
        )
    )
    st.caption(
        "10 seconds is the maximum both APIs can generate per call. "
        "Always use 10s to minimise the number of edit points."
    )

    prompt_txt = st.text_area(
        "Style Prompt (optional)",
        placeholder="cinematic, sharp detail, studio lighting…",
        height=58,
        label_visibility="visible"
    )

    st.markdown("---")

    # ── Log ────────────────────────────────────────────────────────────────
    if st.session_state.log:
        with st.expander("📋 Log", expanded=False):
            st.code("\n".join(st.session_state.log[-80:]), language=None)


# ─────────────────────────────────────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>🎬 Motion Transfer Studio</h1>
  <div class="sub">
    Frame-accurate chunking · Kling AI JWT auth · RunwayML Act-One ·
    ZIP export for Avid / Premiere / DaVinci
  </div>
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
        "The movement blueprint. Any length — split automatically into "
        f"{chunk_sec}-second frame-accurate chunks. "
        "Single person, full body, clear silhouette."
    )
    guide_file = st.file_uploader(
        "Guide video",
        type=["mp4", "mov", "webm", "avi"],
        key="guide",
        label_visibility="collapsed"
    )
    if guide_file:
        st.video(guide_file)
        st.caption(f"`{guide_file.name}` · {guide_file.size/1_048_576:.1f} MB")

with col_i:
    st.markdown("#### 🖼️ Static Subject Image")
    st.caption(
        "The figure that will come to life. "
        "Single person, full body preferred. PNG or JPEG, min 512×512 px."
    )
    image_file = st.file_uploader(
        "Subject image",
        type=["jpg", "jpeg", "png", "webp"],
        key="subject",
        label_visibility="collapsed"
    )
    if image_file:
        st.image(image_file, use_container_width=True)
        st.caption(f"`{image_file.name}`")


# ─────────────────────────────────────────────────────────────────────────────
#  STEP 2 — COST PREVIEW
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("## 2 · Cost & Chunk Preview")

# Estimate duration from file size (web video ≈ 1.5 Mbit/s average)
if guide_file:
    est_sec = min(max(guide_file.size / (1.5 * 131_072), 5.0), 3600.0)
else:
    est_sec = 300.0  # default 5-minute reference

c_now = cost_breakdown(est_sec, chunk_sec, chosen_api, model)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Est. Duration",   f"{est_sec:.0f}s")
m2.metric("Chunks",          c_now["n_total"])
m3.metric("Cost / Clip",     fmt_usd(c_now["per_clip"]))
m4.metric("Total Est. Cost", fmt_usd(c_now["total"]))

if not guide_file:
    st.caption("Showing 5-minute (300s) reference. Upload your guide video for actual estimate.")
elif c_now["has_tail"] is False and (est_sec % chunk_sec) > 0:
    tail = est_sec % chunk_sec
    st.caption(
        f"ℹ️  Last {tail:.1f}s tail is shorter than {MIN_CHUNK_SEC}s "
        "and will be skipped (below API minimum)."
    )

st.markdown("**Full pricing comparison — all models and chunk sizes:**")
st.markdown(
    render_cost_table(est_sec, chosen_api, model, chunk_sec),
    unsafe_allow_html=True
)


# ─────────────────────────────────────────────────────────────────────────────
#  STEP 3 — GENERATE
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("## 3 · Generate")

ffmpeg_ready = ffmpeg_available()

if not ffmpeg_ready:
    st.error(
        "**ffmpeg not found.** "
        "Add `ffmpeg` to `packages.txt` in your repository root "
        "and redeploy to Streamlit Cloud."
    )
elif not keys_ready:
    st.warning(
        f"⚠️  Enter your {chosen_api} API "
        f"{'keys (both Access Key and Secret Key)' if chosen_api == 'Kling AI' else 'key'} "
        "in the sidebar to continue."
    )
elif not guide_file or not image_file:
    st.info("📂 Upload both files above to unlock generation.")
else:
    go_btn = st.button(
        f"▶️  Start Motion Transfer  ({chosen_api} · {model} · {chunk_sec}s chunks · est. {fmt_usd(c_now['total'])})",
        type="primary",
        disabled=st.session_state.processing,
    )

    if go_btn:
        # Reset state
        for k, v in _state_defaults.items():
            st.session_state[k] = v
        st.session_state.processing = True

        st.markdown("---")
        st.markdown("## ⚙️ Processing")

        prog     = st.progress(0, text="Reading files…")
        status_p = st.empty()
        grid_p   = st.empty()
        cost_p   = st.empty()

        try:
            image_bytes = image_file.read()
            video_bytes = guide_file.read()
            image_b64   = to_b64(image_bytes)
            alog("Files loaded into memory.")

            # ── Split ──────────────────────────────────────────────────────
            status_p.info("✂️ Splitting guide video — frame-accurate ffmpeg pass…")
            prog.progress(4, text="Splitting video…")

            chunks, vid_info = split_video_frame_accurate(video_bytes, chunk_sec)
            st.session_state.chunk_meta = chunks

            n_proc = sum(1 for c in chunks if c["status"] == "wait")
            n_skip = sum(1 for c in chunks if c["status"] == "skip")

            status_p.info(
                f"📹 Split complete: **{len(chunks)} chunks** "
                f"({vid_info['duration']:.2f}s · {vid_info['fps']:.4f} fps) · "
                f"{n_proc} to process · {n_skip} skipped"
            )
            grid_p.markdown(render_chunk_grid(chunks), unsafe_allow_html=True)

            # ── API calls per chunk ────────────────────────────────────────
            per_clip_usd = (
                KLING_PRICE[model][chunk_sec]
                if chosen_api == "Kling AI"
                else RUNWAY_PRICE[model][chunk_sec]
            )
            cost_so_far = 0.0
            done_count  = 0

            for i, ch in enumerate(chunks):
                if ch["status"] == "skip":
                    continue

                pct = int(8 + (done_count / max(n_proc, 1)) * 87)
                prog.progress(
                    pct,
                    text=f"Chunk {i+1}/{len(chunks)} · {sec_to_tc(ch['start_ts'])} → {sec_to_tc(ch['end_ts'])}"
                )

                ch["status"] = "run"
                grid_p.markdown(render_chunk_grid(chunks), unsafe_allow_html=True)

                try:
                    if not ch["file_ok"]:
                        raise RuntimeError("ffmpeg produced no usable file for this chunk")

                    seg_b64 = to_b64(ch["bytes"])

                    if chosen_api == "Kling AI":
                        alog(f"Chunk {i+1}: submitting to Kling AI…")
                        task_id = kling_submit(
                            active_access, active_secret,
                            image_b64, seg_b64,
                            chunk_sec, model, prompt_txt
                        )
                        alog(f"Chunk {i+1}: task_id={task_id}")
                        out_url = kling_poll(active_access, active_secret, task_id)

                    else:
                        alog(f"Chunk {i+1}: submitting to RunwayML…")
                        task_id = runway_submit(
                            active_key,
                            image_b64, seg_b64,
                            chunk_sec, model, prompt_txt
                        )
                        alog(f"Chunk {i+1}: task_id={task_id}")
                        out_url = runway_poll(active_key, task_id)

                    ch["output_url"] = out_url
                    ch["status"]     = "done"
                    cost_so_far     += per_clip_usd
                    done_count      += 1
                    st.session_state.result_urls.append(out_url)
                    st.session_state.total_cost = cost_so_far
                    alog(f"Chunk {i+1}: DONE")

                except Exception as e:
                    ch["status"] = "fail"
                    alog(f"Chunk {i+1}: FAILED — {e}")
                    st.warning(f"⚠️ Chunk {i+1} failed: {e}")

                grid_p.markdown(render_chunk_grid(chunks), unsafe_allow_html=True)
                cost_p.info(
                    f"💳 Running cost: **{fmt_usd(cost_so_far)}** "
                    f"({done_count} clip{'s' if done_count != 1 else ''} done)"
                )

            # ── ZIP ────────────────────────────────────────────────────────
            done_chunks = [c for c in chunks if c["status"] == "done"]
            if done_chunks:
                prog.progress(97, text="Packaging ZIP…")
                status_p.info("📦 Downloading output clips and building ZIP…")
                alog(f"Building ZIP for {len(done_chunks)} clips.")
                try:
                    zip_bytes, manifest = build_zip(chunks)
                    st.session_state.zip_bytes    = zip_bytes
                    st.session_state.manifest_csv = manifest
                    alog("ZIP ready.")
                except Exception as ze:
                    st.warning(f"ZIP packaging failed: {ze}")
            else:
                st.error("All chunks failed. Check your API credentials and quota.")

            prog.progress(100, text="Complete ✓")
            status_p.success(
                f"✅ Done! {len(done_chunks)}/{n_proc} clips rendered · "
                f"Total cost: **{fmt_usd(cost_so_far)}**"
            )

        except requests.HTTPError as e:
            status_p.error(f"❌ API error: {e}")
            try:
                st.json(e.response.json())
            except Exception:
                pass
            alog(f"HTTPError: {e}")
        except TimeoutError as e:
            status_p.error(f"⏰ {e}")
            alog(f"Timeout: {e}")
        except Exception as e:
            status_p.error(f"❌ {e}")
            alog(f"Exception: {e}")
        finally:
            st.session_state.processing = False


# ─────────────────────────────────────────────────────────────────────────────
#  STEP 4 — RESULTS
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.result_urls or st.session_state.chunk_meta:
    st.markdown("---")
    st.markdown("## 4 · Results")

    done_ch  = [c for c in st.session_state.chunk_meta if c["status"] == "done"]
    fail_ch  = [c for c in st.session_state.chunk_meta if c["status"] == "fail"]
    skip_ch  = [c for c in st.session_state.chunk_meta if c["status"] == "skip"]

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Clips Rendered", len(done_ch))
    r2.metric("Failed",         len(fail_ch))
    r3.metric("Skipped",        len(skip_ch))
    r4.metric("Total Cost",     fmt_usd(st.session_state.total_cost))

    if st.session_state.zip_bytes:
        st.markdown("### 📦 Download Package")
        st.download_button(
            "⬇️  Download ZIP — all clips + MANIFEST.csv",
            data=st.session_state.zip_bytes,
            file_name="motion_transfer_output.zip",
            mime="application/zip",
            type="primary"
        )
        st.caption(
            "ZIP contains all output MP4 chunks with timecode filenames, "
            "MANIFEST.csv, and NLE import instructions. "
            "Import into Avid / Premiere / DaVinci and place in sequence "
            "— no further alignment needed."
        )
        if st.session_state.manifest_csv:
            with st.expander("📄 MANIFEST.csv"):
                st.code(st.session_state.manifest_csv, language="csv")

    if done_ch:
        with st.expander(f"▶️  Preview {len(done_ch)} individual clips"):
            for ch in done_ch:
                st.markdown(
                    f"**Chunk {ch['index']+1:04d}** · "
                    f"{sec_to_tc(ch['start_ts'])} → {sec_to_tc(ch['end_ts'])} · "
                    f"{ch['duration']:.3f}s · {ch['n_frames']} frames"
                )
                st.video(ch["output_url"])
                st.caption(f"[Direct URL ↗]({ch['output_url']})")
                st.markdown("---")


# ─────────────────────────────────────────────────────────────────────────────
#  EXPLAINER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("ℹ️  Technical details — auth, chunking, costs"):
    st.markdown("""
**Kling AI — two-key JWT authentication**

Kling uses an Access Key (who you are) and a Secret Key (signature proof).
A short-lived JWT is generated per request using HMAC-SHA256:
```
header  = base64url({ "alg": "HS256", "typ": "JWT" })
payload = base64url({ "iss": ACCESS_KEY, "exp": now+1800, "nbf": now-5 })
signature = HMAC-SHA256(SECRET_KEY, header + "." + payload)
JWT = header.payload.signature
```
The token expires after 30 minutes. A fresh JWT is generated for every
submit and every poll call so long-running jobs never hit an auth error.

**Frame-accurate splitting — why and how**

```
1. ffprobe reads FPS as an exact rational fraction (e.g. 30000/1001 = 29.97…)
2. Chunk boundaries are computed in FRAME NUMBERS — not seconds.
   This eliminates floating-point drift that would otherwise show up as
   a 1–2 frame slip at the edit point after 30+ chunks.
3. ffmpeg: -ss AFTER -i  →  slow but frame-exact decode (not keyframe seek).
4. keyint=1:min-keyint=1  →  every output frame is an I-frame.
   Any NLE (Avid, Premiere, DaVinci) can cut anywhere without artefacts.
5. -avoid_negative_ts make_zero  →  each chunk timeline starts at 0.
```

**Maximum chunk size**

Both Kling AI and RunwayML generate a maximum of **10 seconds per API call**.
10 seconds is always chosen as the default — it gives the model more temporal
context and produces fewer seams than 5-second chunks.

**5-minute video cost reference (300 seconds, 30 × 10s clips)**

| API | Model | Cost |
|-----|-------|------|
| Kling AI | Standard 720p | **$2.10** |
| Kling AI | Professional 1080p | **$4.20** |
| RunwayML | Gen-3 Alpha Turbo | **~$30.00** *(est.)* |
| RunwayML | Gen-3 Alpha | **~$54.00** *(est.)* |

Runway prices are estimates based on public credit tiers. Verify at
[runwayml.com/pricing](https://runwayml.com/pricing).

**Tips for best results**
- Full-body shots with clear silhouette against a plain background.
- Use Professional (Kling) or Gen-3 Alpha (Runway) for final delivery.
- Test a single chunk first before running the full 5-minute job.
- Consistent background/lighting across the subject image and guide
  video gives the most coherent output across all 30 chunks.
    """)


# ─────────────────────────────────────────────────────────────────────────────
#  FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "Motion Transfer Studio v3 · "
    "[Kling AI docs](https://docs.klingai.com) · "
    "[RunwayML docs](https://docs.dev.runwayml.com) · "
    "Built with Streamlit"
)
