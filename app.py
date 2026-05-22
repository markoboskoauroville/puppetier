# ─────────────────────────────────────────────────────────────────────────────
#  MOTION TRANSFER STUDIO  v4
#  Kling AI (JWT) + RunwayML Act-One
#  Manual cut points · Auto scene detection · Crop tool · No audio
#
#  Streamlit Cloud Secrets:
#    KLING_ACCESS_KEY = "..."
#    KLING_SECRET_KEY = "..."
#    RUNWAY_API_KEY   = "..."
#
#  packages.txt: ffmpeg
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import requests
import time, json, base64, hmac, hashlib
import math, os, io, zipfile, tempfile, subprocess
from fractions import Fraction

# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Motion Transfer Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;600;700;800&display=swap');
html,body,[class*="css"]{ font-family:'DM Sans',sans-serif; }
.stApp{ background:#07070f; color:#ddd6f3; }

.hero{ background:linear-gradient(145deg,#0b0b1e,#130b24 45%,#090f14);
  border:1px solid #1c1830; border-radius:18px;
  padding:2.4rem 2rem 2rem; margin-bottom:1.8rem; text-align:center; }
.hero h1{ font-weight:800; font-size:2.6rem;
  background:linear-gradient(95deg,#a78bfa,#60a5fa,#34d399);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  margin:0; letter-spacing:-.5px; }
.hero .sub{ color:#6b5f8a; font-size:.9rem;
  font-family:'Space Mono',monospace; margin-top:.45rem; }

.badge{ display:inline-block; padding:.22rem .7rem; border-radius:6px;
  font-family:'Space Mono',monospace; font-size:.72rem; font-weight:700;
  letter-spacing:.08em; }
.bk{ background:#1a0f30; color:#a78bfa; border:1px solid #4c1d95; }
.br{ background:#0c1e12; color:#34d399; border:1px solid #064e30; }

.step-hdr{ font-size:.68rem; font-family:'Space Mono',monospace;
  letter-spacing:.14em; text-transform:uppercase; color:#4b4570; margin-bottom:.3rem; }

.tl-wrap{ position:relative; width:100%; height:56px;
  background:#0c0c1a; border:1px solid #181428; border-radius:8px;
  margin:.5rem 0; overflow:visible; }
.tl-seg{ position:absolute; top:6px; height:34px; border-radius:3px;
  border-right:1px solid #07070f; cursor:default;
  transition:filter .15s; }
.tl-seg:hover{ filter:brightness(1.4); }
.tl-cut{ position:absolute; top:0; width:2px; height:56px;
  background:#a78bfa; z-index:10; }
.tl-cut-lbl{ position:absolute; top:42px; font-size:8px;
  font-family:'Space Mono',monospace; color:#a78bfa;
  transform:translateX(-50%); white-space:nowrap; }
.tl-lbl-l{ position:absolute; bottom:2px; left:4px; font-size:8px;
  font-family:'Space Mono',monospace; color:#3d3660; }
.tl-lbl-r{ position:absolute; bottom:2px; right:4px; font-size:8px;
  font-family:'Space Mono',monospace; color:#3d3660; }

.cut-list{ display:flex; flex-wrap:wrap; gap:6px; margin:.4rem 0; }
.cut-pill{ background:#1a0f30; border:1px solid #4c1d95; border-radius:20px;
  padding:.18rem .7rem; font-family:'Space Mono',monospace;
  font-size:.73rem; color:#a78bfa; display:inline-flex; align-items:center; gap:6px; }

.cost-tbl{ width:100%; border-collapse:collapse;
  font-family:'Space Mono',monospace; font-size:.76rem; }
.cost-tbl th{ color:#4b4570; text-align:left; padding:.36rem .65rem;
  border-bottom:1px solid #181428; white-space:nowrap; }
.cost-tbl td{ color:#b8aed0; padding:.28rem .65rem; }
.cost-tbl tr:nth-child(even) td{ background:#0b0b17; }
.cost-tbl .sep td{ background:#0f0f1e; color:#4b4570; font-size:.66rem;
  letter-spacing:.14em; text-transform:uppercase; padding:.4rem .65rem; }
.cost-tbl .ak td{ background:#130f22; }
.cost-tbl .ar td{ background:#0a160d; }
.cost-tbl .hlk{ color:#a78bfa; font-weight:700; }
.cost-tbl .hlr{ color:#34d399; font-weight:700; }

.chunk-grid{ display:grid;
  grid-template-columns:repeat(auto-fill,minmax(200px,1fr));
  gap:6px; margin-top:.5rem; }
.chunk-card{ background:#0c0c1a; border:1px solid #181428;
  border-radius:8px; padding:.5rem .7rem;
  font-family:'Space Mono',monospace; font-size:.69rem;
  display:flex; flex-direction:column; gap:3px; }
.cc-id{ color:#3d3660; } .cc-tc{ color:#6b5f8a; } .cc-st{ font-weight:700; }
.sw{ color:#3d3660; } .sr{ color:#a78bfa; }
.sd{ color:#34d399; } .sf{ color:#f87171; } .ss{ color:#d97706; }

div[data-testid="metric-container"]{
  background:#0c0c1a; border:1px solid #181428; border-radius:9px; padding:.65rem; }
[data-testid="stMetricLabel"]{ color:#4b4570 !important; font-size:.72rem !important; }
[data-testid="stMetricValue"]{ color:#a78bfa !important; font-weight:800 !important; }
[data-testid="stSidebar"]{ background:#060610 !important; }
.stButton>button{ background:linear-gradient(135deg,#7c3aed,#2563eb) !important;
  border:none !important; border-radius:9px !important; color:#fff !important;
  font-family:'DM Sans',sans-serif !important; font-weight:700 !important;
  font-size:.94rem !important; letter-spacing:.02em !important; }
.stButton>button:hover{ opacity:.84 !important; }
.stButton>button:disabled{ opacity:.3 !important; }
.stProgress>div>div{ background:linear-gradient(90deg,#7c3aed,#34d399) !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
API_MAX_SEC  = 10   # maximum seconds both APIs can generate per call
MIN_CHUNK    = 3    # tail chunks shorter than this are skipped (seconds)

KLING_PRICE = {
    "Standard (720p)":      {5: 0.045, 10: 0.070},
    "Professional (1080p)": {5: 0.090, 10: 0.140},
}
RUNWAY_PRICE = {
    "Gen-3 Alpha Turbo": {5: 0.50, 10: 1.00},
    "Gen-3 Alpha":       {5: 0.90, 10: 1.80},
}
SEG_COLORS = [
    "#1e1a32","#1a2232","#221a32","#1a2218",
    "#22201a","#1a1e2a","#2a1a1a","#1a2a1a",
]


# ─────────────────────────────────────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
_defaults = dict(
    guide_bytes=None, guide_file_key="", probe_info=None,
    image_bytes=None, image_file_key="",
    cut_points=[],
    crop_applied=False,
    working_bytes=None,         # video bytes after crop applied
    working_probe=None,         # probe of working_bytes
    chunk_meta=[], result_urls=[],
    zip_bytes=None, manifest_csv="",
    total_cost=0.0, processing=False, log=[],
)
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────────────────────────────────────
#  UTILITY
# ─────────────────────────────────────────────────────────────────────────────
def to_b64(data: bytes) -> str:
    return base64.b64encode(data).decode()

def sec_to_tc(s: float, fps: float = 25.0) -> str:
    s  = max(0.0, s)
    h  = int(s) // 3600
    m  = (int(s) % 3600) // 60
    sc = int(s) % 60
    fr = int(round((s % 1) * fps)) % max(1, int(fps))
    return f"{h:02d}:{m:02d}:{sc:02d}:{fr:02d}"

def tc_fn(s: float) -> str:
    return sec_to_tc(s).replace(":", "-")

def fmt_usd(v: float) -> str:
    return f"${v:.2f}"

def alog(msg: str):
    st.session_state.log.append(f"[{time.strftime('%H:%M:%S')}]  {msg}")

def get_secret(k: str):
    try:    return st.secrets[k]
    except: return None

def parse_time(s: str) -> float:
    """Accept '83.5', '1:23.5', '00:01:23.5'."""
    s = s.strip()
    p = s.split(":")
    if   len(p) == 1: return float(p[0])
    elif len(p) == 2: return int(p[0]) * 60 + float(p[1])
    else:             return int(p[0]) * 3600 + int(p[1]) * 60 + float(p[2])


# ─────────────────────────────────────────────────────────────────────────────
#  KLING AI — JWT AUTHENTICATION
#  Two credentials required:
#    KLING_ACCESS_KEY  →  who you are (key ID)
#    KLING_SECRET_KEY  →  signs the token (proves authenticity)
#  A fresh JWT is generated for every API call (submit + every poll).
#  Token expires in 30 min; fresh generation avoids stale-token failures.
# ─────────────────────────────────────────────────────────────────────────────
def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

def kling_jwt(access_key: str, secret_key: str) -> str:
    hdr = _b64url(json.dumps({"alg":"HS256","typ":"JWT"}).encode())
    now = int(time.time())
    pay = _b64url(json.dumps({"iss":access_key,"exp":now+1800,"nbf":now-5}).encode())
    msg = f"{hdr}.{pay}"
    sig = _b64url(hmac.new(secret_key.encode(), msg.encode(), hashlib.sha256).digest())
    return f"{msg}.{sig}"

def kling_hdrs(ak: str, sk: str) -> dict:
    return {"Authorization": f"Bearer {kling_jwt(ak, sk)}", "Content-Type": "application/json"}

KLING_BASE = "https://api.klingai.com"

def kling_submit(ak: str, sk: str, img_b64: str, vid_b64: str,
                 dur: int, model: str, prompt: str) -> str:
    """
    POST /v1/videos/image2video  — motion-reference feature.
    Both image and video sent as RAW base64 (no data URI prefix).
    No audio field included — Kling ignores audio but we strip it upstream.
    """
    payload = {
        "model_name":      "kling-v1-5",
        "image":           img_b64,       # raw base64, no 'data:image/...' prefix
        "motion_video":    vid_b64,       # raw base64, no 'data:video/...' prefix
        "duration":        int(dur),
        "mode":            "professional" if "1080" in model else "standard",
        "cfg_scale":       0.5,
        "prompt":          prompt or "smooth motion, high quality, cinematic",
        "negative_prompt": "blur, artifacts, distortion, watermark, low quality",
    }
    r = requests.post(f"{KLING_BASE}/v1/videos/image2video",
                      headers=kling_hdrs(ak, sk), json=payload, timeout=90)
    if not r.ok:
        raise requests.HTTPError(f"Kling {r.status_code}: {r.text}", response=r)
    tid = r.json().get("data", {}).get("task_id", "")
    if not tid:
        raise ValueError(f"Kling: no task_id in response: {r.json()}")
    return tid

def kling_poll(ak: str, sk: str, task_id: str, max_wait: int = 600) -> str:
    deadline = time.time() + max_wait
    while True:
        if time.time() > deadline:
            raise TimeoutError(f"Kling task {task_id} timed out")
        r = requests.get(f"{KLING_BASE}/v1/videos/image2video/{task_id}",
                         headers=kling_hdrs(ak, sk), timeout=30)
        r.raise_for_status()
        d = r.json().get("data", {})
        s = d.get("task_status", "processing")
        if s == "succeed":
            try:    return d["task_result"]["videos"][0]["url"]
            except: raise ValueError(f"Kling: no video URL in result: {d}")
        if s in ("failed", "error"):
            raise RuntimeError(f"Kling task failed: {d.get('task_status_msg','?')}")
        time.sleep(6)


# ─────────────────────────────────────────────────────────────────────────────
#  RUNWAYML ACT-ONE
# ─────────────────────────────────────────────────────────────────────────────
RUNWAY_BASE = "https://api.dev.runwayml.com/v1"

def runway_hdrs(key: str) -> dict:
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
            "X-Runway-Version": "2024-11-06"}

def runway_submit(key: str, img_b64: str, vid_b64: str,
                  dur: int, model: str, prompt: str) -> str:
    mime = "image/png" if img_b64.startswith("iVBORw0") else "image/jpeg"
    payload = {
        "model":       "gen3a_turbo" if "Turbo" in model else "gen3a",
        "promptImage": f"data:{mime};base64,{img_b64}",
        "promptVideo": f"data:video/mp4;base64,{vid_b64}",
        "duration":    int(dur),
        "ratio":       "1280:720",
        "watermark":   False,
        "promptText":  prompt or "smooth motion, high quality, cinematic",
        "seed":        42,
    }
    r = requests.post(f"{RUNWAY_BASE}/image_to_video",
                      headers=runway_hdrs(key), json=payload, timeout=90)
    if not r.ok:
        raise requests.HTTPError(f"Runway {r.status_code}: {r.text}", response=r)
    tid = r.json().get("id", "")
    if not tid:
        raise ValueError(f"Runway: no task id: {r.json()}")
    return tid

def runway_poll(key: str, task_id: str, max_wait: int = 600) -> str:
    deadline = time.time() + max_wait
    while True:
        if time.time() > deadline:
            raise TimeoutError(f"Runway task {task_id} timed out")
        r = requests.get(f"{RUNWAY_BASE}/tasks/{task_id}",
                         headers=runway_hdrs(key), timeout=30)
        r.raise_for_status()
        d = r.json()
        s = d.get("status", "PENDING")
        if s == "SUCCEEDED":
            out = d.get("output", [])
            if out: return out[0]
            raise ValueError(f"Runway: no output URL: {d}")
        if s in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"Runway task failed: {d.get('failure','?')}")
        time.sleep(6)


# ─────────────────────────────────────────────────────────────────────────────
#  VIDEO PROCESSING  (ffmpeg)
# ─────────────────────────────────────────────────────────────────────────────
def ffmpeg_ok() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

def probe_video(path: str) -> dict:
    """Return duration, fps, total_frames, width, height."""
    r = subprocess.run(
        ["ffprobe", "-v", "quiet",
         "-select_streams", "v:0",
         "-show_entries", "stream=r_frame_rate,nb_frames,width,height",
         "-show_entries", "format=duration",
         "-print_format", "json", path],
        capture_output=True, text=True, check=True)
    d  = json.loads(r.stdout)
    st = d["streams"][0]
    fps = float(Fraction(st["r_frame_rate"]))
    dur = float(d["format"]["duration"])
    nf  = int(st["nb_frames"]) if st.get("nb_frames","N/A") != "N/A" else int(dur * fps)
    return {"duration": dur, "fps": fps, "total_frames": nf,
            "width": int(st.get("width", 0)), "height": int(st.get("height", 0))}

def apply_crop(video_bytes: bytes, x: int, y: int, w: int, h: int) -> bytes:
    """
    Crop video to isolate one person.
    Dimensions are rounded to even numbers (H.264 requirement).
    Audio is stripped (-an) — we never need audio for motion transfer.
    """
    x, y = x - x%2, y - y%2
    w, h = w - w%2, h - h%2
    with tempfile.TemporaryDirectory() as tmp:
        inp = os.path.join(tmp, "i.mp4")
        out = os.path.join(tmp, "o.mp4")
        with open(inp, "wb") as f: f.write(video_bytes)
        subprocess.run(
            ["ffmpeg", "-y", "-i", inp,
             "-vf", f"crop={w}:{h}:{x}:{y}",
             "-c:v", "libx264", "-preset", "fast", "-crf", "18",
             "-pix_fmt", "yuv420p", "-an", out],
            capture_output=True, check=True)
        with open(out, "rb") as f: return f.read()

def detect_scene_cuts(video_bytes: bytes, threshold: float = 0.35) -> list[float]:
    """
    Detect shot-change timestamps using ffmpeg scene-change detection.
    Returns sorted list of timestamps in seconds (excluding 0.0).
    Lower threshold = more sensitive (more cuts detected).
    """
    with tempfile.TemporaryDirectory() as tmp:
        inp = os.path.join(tmp, "i.mp4")
        with open(inp, "wb") as f: f.write(video_bytes)
        r = subprocess.run(
            ["ffmpeg", "-i", inp,
             "-vf", f"select='gt(scene,{threshold})',showinfo",
             "-vsync", "vfr", "-an", "-f", "null", "-"],
            capture_output=True, text=True, timeout=300)
        cuts = []
        for line in r.stderr.split("\n"):
            if "pts_time:" in line and "showinfo" in line:
                try:
                    t = float(line.split("pts_time:")[1].split()[0])
                    if t > 0.25:          # skip near-zero false positives
                        cuts.append(round(t, 3))
                except (ValueError, IndexError):
                    pass
        return sorted(set(cuts))

def extract_chunk_bytes(video_bytes: bytes, start: float, end: float,
                         fps: float) -> bytes:
    """
    Extract a precise time range from video bytes.

    Frame-accurate strategy:
    · Boundaries converted to frame numbers (eliminates float drift).
    · -ss AFTER -i  →  slow but frame-exact decode.
    · keyint=1      →  every output frame is an I-frame (NLE-safe).
    · -an           →  NO AUDIO — saves cost; Kling ignores it anyway.
    """
    sf   = int(round(start * fps))
    ef   = int(round(end   * fps))
    nf   = ef - sf
    s_ts = sf / fps
    dur  = nf / fps

    with tempfile.TemporaryDirectory() as tmp:
        inp = os.path.join(tmp, "i.mp4")
        out = os.path.join(tmp, "o.mp4")
        with open(inp, "wb") as f: f.write(video_bytes)
        result = subprocess.run(
            ["ffmpeg", "-y",
             "-i", inp,
             "-ss", f"{s_ts:.9f}",
             "-t",  f"{dur:.9f}",
             "-c:v", "libx264", "-preset", "fast", "-crf", "18",
             "-pix_fmt", "yuv420p",
             "-x264opts", "keyint=1:min-keyint=1",   # every frame an I-frame
             "-avoid_negative_ts", "make_zero",
             "-movflags", "+faststart",
             "-an",          # ← NO AUDIO, always
             out],
            capture_output=True)
        if not os.path.exists(out) or os.path.getsize(out) < 1024:
            raise RuntimeError(
                f"ffmpeg extraction failed for {start:.3f}–{end:.3f}s\n"
                f"stderr: {result.stderr[-500:]}")
        with open(out, "rb") as f: return f.read()


# ─────────────────────────────────────────────────────────────────────────────
#  CHUNK LOGIC
#  Cut points define shot boundaries.
#  Any shot longer than API_MAX_SEC is auto-subdivided.
#  Tail chunks shorter than MIN_CHUNK are skipped.
# ─────────────────────────────────────────────────────────────────────────────
def build_chunk_plan(total_dur: float, cut_points: list[float],
                     fps: float) -> list[dict]:
    """
    Convert cut points into a final ordered list of chunk dicts.
    Each dict: index, start, end, duration, n_frames, is_sub, status, filename, ...
    """
    cps   = sorted({cp for cp in cut_points if 0.1 < cp < total_dur - 0.1})
    bounds = [0.0] + list(cps) + [total_dur]

    segments: list[tuple[float, float, bool]] = []   # (start, end, is_subdivision)
    for i in range(len(bounds) - 1):
        s, e = bounds[i], bounds[i + 1]
        d = e - s
        if d < 0.1:
            continue
        if d <= API_MAX_SEC:
            segments.append((s, e, False))
        else:
            n   = math.ceil(d / API_MAX_SEC)
            sub = d / n
            for j in range(n):
                ss = s + j * sub
                se = min(s + (j + 1) * sub, e)
                segments.append((ss, se, True))

    chunks = []
    for i, (s, e, is_sub) in enumerate(segments):
        d  = e - s
        nf = int(round(d * fps))
        skip = d < MIN_CHUNK
        fname = (f"chunk_{i+1:04d}"
                 f"_TC_{tc_fn(s)}_to_{tc_fn(e)}.mp4")
        chunks.append({
            "index":      i,
            "start":      s,
            "end":        e,
            "duration":   d,
            "n_frames":   nf,
            "is_sub":     is_sub,
            "status":     "skip" if skip else "wait",
            "filename":   fname,
            "output_url": None,
            "bytes":      None,
        })
    return chunks


# ─────────────────────────────────────────────────────────────────────────────
#  RENDER HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def timeline_html(total_dur: float, cut_points: list[float],
                  chunks: list[dict]) -> str:
    if total_dur <= 0:
        return ""
    segs = ""
    for i, ch in enumerate(chunks):
        left  = ch["start"] / total_dur * 100
        width = ch["duration"] / total_dur * 100
        col   = SEG_COLORS[i % len(SEG_COLORS)]
        label = f"{ch['duration']:.1f}s" if width > 4 else ""
        tip   = (f"Chunk {i+1}: {sec_to_tc(ch['start'])} → {sec_to_tc(ch['end'])} "
                 f"({ch['duration']:.2f}s)")
        segs += (f'<div class="tl-seg" style="left:{left:.3f}%;'
                 f'width:{width:.3f}%;background:{col};" title="{tip}">'
                 f'<span style="font-size:8px;font-family:monospace;color:#4b4570;'
                 f'padding:2px 3px;">{label}</span></div>')
    cuts = ""
    for cp in cut_points:
        x = cp / total_dur * 100
        cuts += (f'<div class="tl-cut" style="left:{x:.3f}%;">'
                 f'<span class="tl-cut-lbl" style="left:{x:.3f}%;">'
                 f'{sec_to_tc(cp)}</span></div>')
    return (f'<div class="tl-wrap">{segs}{cuts}'
            f'<span class="tl-lbl-l">00:00:00:00</span>'
            f'<span class="tl-lbl-r">{sec_to_tc(total_dur)}</span></div>')

def chunk_grid_html(chunks: list[dict]) -> str:
    ST = {"wait":("sw","QUEUED"),"run":("sr","RUNNING"),
          "done":("sd","DONE"),"fail":("sf","FAILED"),"skip":("ss","SKIP")}
    cards = ""
    for ch in chunks:
        cl, lb = ST.get(ch["status"], ("sw", ch["status"].upper()))
        sub = " ·SUB" if ch["is_sub"] else ""
        cards += (f'<div class="chunk-card">'
                  f'<span class="cc-id">Chunk {ch["index"]+1:04d}{sub}</span>'
                  f'<span class="cc-tc">{sec_to_tc(ch["start"])} → {sec_to_tc(ch["end"])}</span>'
                  f'<span class="cc-tc">{ch["duration"]:.3f}s · {ch["n_frames"]} fr</span>'
                  f'<span class="cc-st {cl}">{lb}</span></div>')
    return f'<div class="chunk-grid">{cards}</div>'

def cost_table_html(chunk_count: int, active_api: str,
                    active_model: str, active_chunk: int) -> str:
    def row(api, model, dur, active):
        p  = (KLING_PRICE if api == "Kling AI" else RUNWAY_PRICE)[model][dur]
        t  = chunk_count * p
        hl = ("hlk" if api == "Kling AI" else "hlr") if active else ""
        rc = ("ak" if api == "Kling AI" else "ar") if active else ""
        return (f'<tr class="{rc}"><td>{model}</td><td>{dur}s</td>'
                f'<td>{chunk_count}</td><td>{fmt_usd(p)}</td>'
                f'<td class="{hl}">{fmt_usd(t)}</td></tr>')

    rows  = '<tr class="sep"><td colspan="5">KLING AI — exact pricing</td></tr>'
    for m in KLING_PRICE:
        for d in [5, 10]:
            rows += row("Kling AI", m, d,
                        active_api == "Kling AI" and active_model == m and active_chunk == d)
    rows += '<tr class="sep"><td colspan="5">RUNWAYML ACT-ONE — estimated pricing</td></tr>'
    for m in RUNWAY_PRICE:
        for d in [5, 10]:
            rows += row("RunwayML", m, d,
                        active_api == "RunwayML" and active_model == m and active_chunk == d)
    note = ("Highlighted = current selection. "
            "Kling: klingai.com/pricing. "
            "Runway: estimated from runwayml.com/pricing credit tiers.")
    return (f'<table class="cost-tbl"><thead><tr>'
            f'<th>Model</th><th>Clip</th><th>Clips</th>'
            f'<th>$/Clip</th><th>Total</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>'
            f'<div style="font-size:.66rem;color:#3d3660;margin-top:.3rem;">{note}</div>')


# ─────────────────────────────────────────────────────────────────────────────
#  ZIP BUILDER
# ─────────────────────────────────────────────────────────────────────────────
def build_zip(chunks: list[dict]) -> tuple[bytes, str]:
    buf   = io.BytesIO()
    done  = [c for c in chunks if c["status"] == "done" and c["output_url"]]
    lines = ["chunk_number,filename,start_tc,end_tc,start_sec,end_sec,duration_sec,n_frames,output_url"]
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
        for ch in done:
            r = requests.get(ch["output_url"], timeout=120)
            r.raise_for_status()
            zf.writestr(ch["filename"], r.content)
            lines.append(
                f"{ch['index']+1},{ch['filename']},"
                f"{sec_to_tc(ch['start'])},{sec_to_tc(ch['end'])},"
                f"{ch['start']:.4f},{ch['end']:.4f},{ch['duration']:.4f},"
                f"{ch['n_frames']},{ch['output_url']}")
        csv = "\n".join(lines)
        zf.writestr("MANIFEST.csv", csv)
        zf.writestr("README_NLE_IMPORT.txt",
            "MOTION TRANSFER STUDIO — Output Package\n"
            "=========================================\n\n"
            "1. Import all MP4 files into Avid / Premiere / DaVinci.\n"
            "2. Place on timeline in numeric chunk order.\n"
            "3. Chunks are frame-contiguous — no gap trimming needed.\n\n"
            "Codec: H.264, no audio, every frame is an I-frame.\n"
            "Filenames include SMPTE timecode (HH-MM-SS-FF at 25fps display).\n"
            "MANIFEST.csv has precise seconds, frame count and API URLs.\n")
    return buf.getvalue(), csv


# ─────────────────────────────────────────────────────────────────────────────
#  LOAD SECRETS
# ─────────────────────────────────────────────────────────────────────────────
S_KLING_AK = get_secret("KLING_ACCESS_KEY")
S_KLING_SK = get_secret("KLING_SECRET_KEY")
S_RUNWAY   = get_secret("RUNWAY_API_KEY")


# ─────────────────────────────────────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎛️ Settings")

    st.markdown("### 🔌 API Engine")
    chosen_api = st.radio("engine", ["Kling AI", "RunwayML"],
                          horizontal=True, label_visibility="collapsed")
    st.markdown(
        f'<span class="badge {"bk" if chosen_api=="Kling AI" else "br"}">'
        f'{"KLING AI" if chosen_api=="Kling AI" else "RUNWAYML ACT-ONE"}'
        f'</span>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🔑 API Keys")

    if chosen_api == "Kling AI":
        if S_KLING_AK and S_KLING_SK:
            st.success("Kling Access Key + Secret Key loaded ✓")
            active_ak, active_sk = S_KLING_AK, S_KLING_SK
        else:
            active_ak = st.text_input("Kling Access Key", type="password",
                                      help="klingai.com → Developer → API Keys")
            active_sk = st.text_input("Kling Secret Key", type="password",
                                      help="klingai.com → Developer → API Keys")
            if not (active_ak and active_sk):
                st.caption("Or add `KLING_ACCESS_KEY` and `KLING_SECRET_KEY` to Secrets.")
        active_rk  = None
        keys_ready = bool(active_ak and active_sk)
    else:
        active_ak = active_sk = None
        if S_RUNWAY:
            st.success("RunwayML API Key loaded ✓")
            active_rk = S_RUNWAY
        else:
            active_rk = st.text_input("RunwayML API Key", type="password",
                                      help="app.runwayml.com → Account → API")
            if not active_rk:
                st.caption("Or add `RUNWAY_API_KEY` to Secrets.")
        keys_ready = bool(active_rk)

    st.markdown("---")
    st.markdown("### 🎥 Model & Quality")
    model = st.selectbox(
        "Model",
        list(KLING_PRICE.keys()) if chosen_api == "Kling AI" else list(RUNWAY_PRICE.keys()),
        index=1 if chosen_api == "Kling AI" else 0,
    )
    st.markdown("**Chunk length:** 10 s (API maximum — always use this)")
    prompt_txt = st.text_area("Style Prompt (optional)",
                              placeholder="cinematic, sharp detail…", height=56)

    st.markdown("---")
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
    Manual cuts · Auto scene detection · Crop · No audio ·
    Kling AI JWT · RunwayML Act-One · ZIP for Avid/Premiere/DaVinci
  </div>
</div>
""", unsafe_allow_html=True)

if not ffmpeg_ok():
    st.error("**ffmpeg not found.** Add `ffmpeg` to `packages.txt` and redeploy.")
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
#  STEP 1 — UPLOAD
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("## 1 · Upload Files")
col_v, col_i = st.columns(2, gap="large")

with col_v:
    st.markdown("#### 🎥 Motion Guide Video")
    st.caption("The movement blueprint. Multiple shots, any length.")
    guide_file = st.file_uploader("Guide video",
                                  type=["mp4","mov","webm","avi"],
                                  key="guide", label_visibility="collapsed")
    if guide_file:
        st.video(guide_file)
        fk = f"{guide_file.name}_{guide_file.size}"
        if st.session_state.guide_file_key != fk:
            st.session_state.guide_bytes    = guide_file.read()
            st.session_state.guide_file_key = fk
            st.session_state.cut_points     = []
            st.session_state.working_bytes  = None
            st.session_state.working_probe  = None
            st.session_state.crop_applied   = False
            st.session_state.probe_info     = None
            # Auto-probe on upload
            with tempfile.TemporaryDirectory() as tmp:
                p = os.path.join(tmp, "i.mp4")
                with open(p, "wb") as f: f.write(st.session_state.guide_bytes)
                try:
                    st.session_state.probe_info = probe_video(p)
                except Exception as e:
                    st.warning(f"Probe failed: {e}")
        mb = guide_file.size / 1_048_576
        st.caption(f"`{guide_file.name}` · {mb:.1f} MB")

with col_i:
    st.markdown("#### 🖼️ Static Subject Image")
    st.caption("The figure that will come to life.")
    image_file = st.file_uploader("Subject image",
                                  type=["jpg","jpeg","png","webp"],
                                  key="subject", label_visibility="collapsed")
    if image_file:
        st.image(image_file, use_container_width=True)
        ik = f"{image_file.name}_{image_file.size}"
        if st.session_state.image_file_key != ik:
            st.session_state.image_bytes    = image_file.read()
            st.session_state.image_file_key = ik
        st.caption(f"`{image_file.name}`")


# ─────────────────────────────────────────────────────────────────────────────
#  STEP 2 — VIDEO SETUP  (crop + cuts)  — only shown when video is uploaded
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.guide_bytes and st.session_state.probe_info:
    st.markdown("---")
    st.markdown("## 2 · Video Setup")

    probe = st.session_state.probe_info
    dur   = probe["duration"]
    fps   = probe["fps"]
    vw    = probe["width"]
    vh    = probe["height"]

    # ── 2a. CROP ─────────────────────────────────────────────────────────────
    with st.expander("✂️  Crop — isolate one person from multi-person video", expanded=False):
        st.caption(
            "Watch the video above, note where the target person is, "
            "then set the crop region below. All values in pixels. "
            f"Original: **{vw} × {vh} px**"
        )
        c1, c2 = st.columns(2)
        cx = c1.number_input("Left edge  (x)", 0, max(vw-2, 0), 0, step=2, key="cx")
        cy = c2.number_input("Top edge   (y)", 0, max(vh-2, 0), 0, step=2, key="cy")
        cw = c1.number_input("Width",  2, vw, vw, step=2, key="cw",
                             help="Crop width. Set to full width to skip crop.")
        ch_v = c2.number_input("Height", 2, vh, vh, step=2, key="ch",
                               help="Crop height.")

        crop_is_noop = (cx == 0 and cy == 0 and cw == vw and ch_v == vh)
        if not crop_is_noop:
            st.info(f"Crop preview: x={cx} y={cy} w={cw} h={ch_v}  →  {cw}×{ch_v} px output")

        apply_crop_btn = st.button(
            "Apply Crop" if not crop_is_noop else "No Crop (full frame)",
            key="apply_crop_btn",
            disabled=crop_is_noop,
        )
        if apply_crop_btn and not crop_is_noop:
            with st.spinner("Applying crop with ffmpeg…"):
                try:
                    cropped = apply_crop(st.session_state.guide_bytes,
                                         int(cx), int(cy), int(cw), int(ch_v))
                    with tempfile.TemporaryDirectory() as tmp:
                        p = os.path.join(tmp, "c.mp4")
                        with open(p, "wb") as f: f.write(cropped)
                        new_probe = probe_video(p)
                    st.session_state.working_bytes = cropped
                    st.session_state.working_probe = new_probe
                    st.session_state.crop_applied  = True
                    st.session_state.probe_info    = new_probe  # update UI values
                    probe = new_probe
                    dur   = probe["duration"]
                    fps   = probe["fps"]
                    vw    = probe["width"]
                    vh    = probe["height"]
                    alog(f"Crop applied: {cw}×{ch_v} at ({cx},{cy})")
                    st.success(f"Crop applied ✓  →  {vw}×{vh} px · {dur:.2f}s")
                except Exception as e:
                    st.error(f"Crop failed: {e}")

        if st.session_state.crop_applied:
            st.success("✅ Crop active — processing will use cropped video")
            if st.button("Reset crop (use original video)", key="reset_crop"):
                st.session_state.working_bytes = None
                st.session_state.working_probe = None
                st.session_state.crop_applied  = False
                # Restore original probe
                with tempfile.TemporaryDirectory() as tmp:
                    p = os.path.join(tmp, "i.mp4")
                    with open(p, "wb") as f:
                        f.write(st.session_state.guide_bytes)
                    st.session_state.probe_info = probe_video(p)
                st.rerun()

    # Use working bytes if crop was applied
    active_video_bytes = (st.session_state.working_bytes
                          if st.session_state.crop_applied
                          else st.session_state.guide_bytes)
    active_probe       = (st.session_state.working_probe
                          if st.session_state.crop_applied
                          else st.session_state.probe_info)
    dur = active_probe["duration"]
    fps = active_probe["fps"]

    # ── 2b. CUT POINTS ───────────────────────────────────────────────────────
    st.markdown("### 🔪 Cut Points — Shot Boundaries")
    st.caption(
        "Each cut point marks where one shot ends and the next begins. "
        "Segments are sent to the API individually — shot-accurate, never mixed. "
        "Segments longer than 10 s are auto-subdivided."
    )

    # Auto scene detection
    col_det1, col_det2 = st.columns([2, 1])
    with col_det1:
        scene_thresh = st.slider(
            "Scene detection sensitivity",
            min_value=0.10, max_value=0.60, value=0.35, step=0.05,
            help="Lower = more sensitive (detects subtler cuts). 0.35 is a good default.",
            key="scene_thresh"
        )
    with col_det2:
        detect_btn = st.button("🔍 Auto-detect Cuts", key="detect_btn",
                               use_container_width=True)
    if detect_btn:
        with st.spinner("Running ffmpeg scene detection…"):
            found = detect_scene_cuts(active_video_bytes, scene_thresh)
            if found:
                existing = set(st.session_state.cut_points)
                new_cuts = sorted(existing | set(found))
                st.session_state.cut_points = new_cuts
                alog(f"Scene detection found {len(found)} cuts (thresh={scene_thresh})")
                st.success(f"Found {len(found)} scene cut(s). Added to cut list.")
            else:
                st.info("No scene cuts detected at this threshold. Try lowering it.")

    st.markdown("---")

    # Playhead slider for manual cuts
    st.markdown("**🎚️ Manual Cut — drag to shot change, then add:**")
    playhead_val = st.slider(
        "Playhead",
        min_value=0.0,
        max_value=float(dur),
        value=0.0,
        step=round(1.0 / fps, 4),     # one frame at a time
        format="%.3f",
        key="playhead",
        label_visibility="collapsed",
    )
    col_ph1, col_ph2, col_ph3 = st.columns([2, 1, 1])
    with col_ph1:
        st.markdown(
            f"**{sec_to_tc(playhead_val, fps)}** "
            f"<span style='color:#4b4570;font-size:.8rem;font-family:monospace;'>"
            f"({playhead_val:.3f}s)</span>",
            unsafe_allow_html=True
        )
    with col_ph2:
        if st.button(f"📍 Add cut here", key="add_ph", use_container_width=True):
            t = round(playhead_val, 3)
            if 0.5 < t < dur - 0.5 and t not in st.session_state.cut_points:
                st.session_state.cut_points.append(t)
                st.session_state.cut_points.sort()
                alog(f"Manual cut added: {sec_to_tc(t, fps)} ({t}s)")
                st.rerun()

    # Type-in time input
    with col_ph3:
        typed_time = st.text_input("Or type time", placeholder="1:23.5 or 83.5",
                                   key="typed_time", label_visibility="collapsed")
    if typed_time:
        try:
            t = round(parse_time(typed_time), 3)
            if st.button(f"Add {sec_to_tc(t, fps)}", key="add_typed"):
                if 0.1 < t < dur - 0.1 and t not in st.session_state.cut_points:
                    st.session_state.cut_points.append(t)
                    st.session_state.cut_points.sort()
                    alog(f"Typed cut added: {t}s")
                    st.rerun()
        except ValueError:
            st.caption("Invalid time format.")

    # Show current cut points as removable pills
    if st.session_state.cut_points:
        st.markdown(
            '<div class="step-hdr">Current cut points '
            f'({len(st.session_state.cut_points)})</div>',
            unsafe_allow_html=True
        )
        # Render in rows of 6
        pills_per_row = 6
        cps = st.session_state.cut_points
        for row_start in range(0, len(cps), pills_per_row):
            row_cps = cps[row_start:row_start + pills_per_row]
            cols    = st.columns(len(row_cps))
            for j, (col, cp) in enumerate(zip(cols, row_cps)):
                with col:
                    if st.button(f"✕ {sec_to_tc(cp, fps)}", key=f"rm_{cp}",
                                 use_container_width=True):
                        st.session_state.cut_points.remove(cp)
                        alog(f"Cut removed: {cp}s")
                        st.rerun()

        col_ca, _ = st.columns([1, 3])
        with col_ca:
            if st.button("🗑️ Clear all cuts", key="clear_cuts"):
                st.session_state.cut_points = []
                st.rerun()
    else:
        st.caption(
            "No cut points set. The whole video will be treated as one shot "
            "and auto-subdivided into 10-second API chunks."
        )

    # ── 2c. CHUNK PLAN PREVIEW ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📋 Chunk Plan Preview")

    chunk_plan = build_chunk_plan(dur, st.session_state.cut_points, fps)
    n_proc     = sum(1 for c in chunk_plan if c["status"] == "wait")
    n_skip     = sum(1 for c in chunk_plan if c["status"] == "skip")

    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Total Chunks", len(chunk_plan))
    p2.metric("To Process",   n_proc)
    p3.metric("Skipped",      n_skip,
              help=f"Tail segments shorter than {MIN_CHUNK}s are skipped (API minimum)")
    p4.metric("Est. Output",  f"{n_proc * API_MAX_SEC}s")

    st.markdown(timeline_html(dur, st.session_state.cut_points, chunk_plan),
                unsafe_allow_html=True)
    with st.expander(f"▾  View all {len(chunk_plan)} chunks", expanded=False):
        st.markdown(chunk_grid_html(chunk_plan), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  STEP 3 — COST PREVIEW
# ─────────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 3 · Cost Preview")

    per_clip = (KLING_PRICE if chosen_api == "Kling AI" else RUNWAY_PRICE)[model][API_MAX_SEC]
    est_cost = n_proc * per_clip

    cc1, cc2, cc3 = st.columns(3)
    cc1.metric("Clips to Generate",  n_proc)
    cc2.metric("Cost / Clip",        fmt_usd(per_clip))
    cc3.metric("Total Estimated",    fmt_usd(est_cost))

    st.markdown("**All options:**")
    st.markdown(cost_table_html(n_proc, chosen_api, model, API_MAX_SEC),
                unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  STEP 4 — GENERATE
# ─────────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 4 · Generate")

    if not keys_ready:
        st.warning(f"⚠️  Enter your {chosen_api} API keys in the sidebar.")
    elif not st.session_state.image_bytes:
        st.info("📂 Upload the subject image in Step 1.")
    elif n_proc == 0:
        st.warning("No processable chunks. Check cut points and video duration.")
    else:
        btn_label = (f"▶️  Generate {n_proc} clips  ·  {chosen_api}  ·  "
                     f"{model}  ·  est. {fmt_usd(est_cost)}")
        go_btn = st.button(btn_label, type="primary",
                           disabled=st.session_state.processing)

        if go_btn:
            # Reset output state
            st.session_state.chunk_meta  = []
            st.session_state.result_urls = []
            st.session_state.zip_bytes   = None
            st.session_state.manifest_csv= ""
            st.session_state.total_cost  = 0.0
            st.session_state.log         = []
            st.session_state.processing  = True

            st.markdown("---")
            st.markdown("## ⚙️ Processing")

            prog    = st.progress(0, text="Preparing…")
            stat_p  = st.empty()
            grid_p  = st.empty()
            cost_p  = st.empty()

            try:
                img_b64  = to_b64(st.session_state.image_bytes)
                vid_src  = (st.session_state.working_bytes
                            if st.session_state.crop_applied
                            else st.session_state.guide_bytes)
                v_probe  = (st.session_state.working_probe
                            if st.session_state.crop_applied
                            else st.session_state.probe_info)
                v_fps    = v_probe["fps"]
                v_dur    = v_probe["duration"]

                chunks   = build_chunk_plan(v_dur, st.session_state.cut_points, v_fps)
                st.session_state.chunk_meta = chunks
                n_proc_now = sum(1 for c in chunks if c["status"] == "wait")

                alog(f"Plan: {len(chunks)} chunks, {n_proc_now} to process")
                grid_p.markdown(chunk_grid_html(chunks), unsafe_allow_html=True)

                cost_so_far = 0.0
                done_count  = 0

                for i, ch in enumerate(chunks):
                    if ch["status"] == "skip":
                        alog(f"Chunk {i+1}: skipped ({ch['duration']:.2f}s < {MIN_CHUNK}s)")
                        continue

                    pct = int(5 + (done_count / max(n_proc_now, 1)) * 90)
                    prog.progress(pct, text=f"Chunk {i+1}/{len(chunks)} — "
                                            f"{sec_to_tc(ch['start'], v_fps)} → "
                                            f"{sec_to_tc(ch['end'], v_fps)}")
                    ch["status"] = "run"
                    grid_p.markdown(chunk_grid_html(chunks), unsafe_allow_html=True)

                    try:
                        # Extract this chunk from source video
                        stat_p.info(f"✂️  Extracting chunk {i+1} ({ch['duration']:.2f}s)…")
                        chunk_vid = extract_chunk_bytes(vid_src,
                                                        ch["start"], ch["end"], v_fps)
                        ch["bytes"] = chunk_vid
                        vid_b64 = to_b64(chunk_vid)
                        alog(f"Chunk {i+1}: extracted {len(chunk_vid)//1024}KB")

                        # Submit to API
                        stat_p.info(f"🚀  Submitting chunk {i+1} to {chosen_api}…")
                        if chosen_api == "Kling AI":
                            tid = kling_submit(active_ak, active_sk,
                                               img_b64, vid_b64,
                                               API_MAX_SEC, model, prompt_txt)
                            alog(f"Chunk {i+1}: Kling task_id={tid}")
                            stat_p.info(f"⏳  Polling Kling chunk {i+1} (task {tid[:10]}…)")
                            url = kling_poll(active_ak, active_sk, tid)
                        else:
                            tid = runway_submit(active_rk,
                                                img_b64, vid_b64,
                                                API_MAX_SEC, model, prompt_txt)
                            alog(f"Chunk {i+1}: Runway task_id={tid}")
                            stat_p.info(f"⏳  Polling Runway chunk {i+1} (task {tid[:10]}…)")
                            url = runway_poll(active_rk, tid)

                        ch["output_url"] = url
                        ch["status"]     = "done"
                        ch["bytes"]      = None    # free memory
                        cost_so_far     += per_clip
                        done_count      += 1
                        st.session_state.result_urls.append(url)
                        st.session_state.total_cost = cost_so_far
                        alog(f"Chunk {i+1}: DONE — {url[:60]}…")

                    except Exception as e:
                        ch["status"] = "fail"
                        ch["bytes"]  = None
                        alog(f"Chunk {i+1}: FAILED — {e}")
                        st.warning(f"⚠️  Chunk {i+1} failed: {e}")

                    grid_p.markdown(chunk_grid_html(chunks), unsafe_allow_html=True)
                    cost_p.info(f"💳  Running cost: **{fmt_usd(cost_so_far)}** "
                                f"({done_count} clip{'s' if done_count!=1 else ''} done)")

                # Build ZIP
                done_chunks = [c for c in chunks if c["status"] == "done"]
                if done_chunks:
                    prog.progress(97, text="Packaging ZIP…")
                    stat_p.info("📦  Building download package…")
                    try:
                        zb, mcsv = build_zip(chunks)
                        st.session_state.zip_bytes    = zb
                        st.session_state.manifest_csv = mcsv
                        alog("ZIP ready.")
                    except Exception as ze:
                        st.warning(f"ZIP failed: {ze}")

                prog.progress(100, text="Complete ✓")
                stat_p.success(
                    f"✅  Done!  {len(done_chunks)}/{n_proc_now} clips rendered  ·  "
                    f"Total: **{fmt_usd(cost_so_far)}**"
                )

            except requests.HTTPError as e:
                stat_p.error(f"❌  API error: {e}")
                try: st.json(e.response.json())
                except: pass
                alog(f"HTTPError: {e}")
            except TimeoutError as e:
                stat_p.error(f"⏰  {e}")
                alog(f"Timeout: {e}")
            except Exception as e:
                stat_p.error(f"❌  {e}")
                alog(f"Exception: {e}")
            finally:
                st.session_state.processing = False


# ─────────────────────────────────────────────────────────────────────────────
#  STEP 5 — RESULTS
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.result_urls or st.session_state.chunk_meta:
    st.markdown("---")
    st.markdown("## 5 · Results")

    done_ch = [c for c in st.session_state.chunk_meta if c["status"] == "done"]
    fail_ch = [c for c in st.session_state.chunk_meta if c["status"] == "fail"]
    skip_ch = [c for c in st.session_state.chunk_meta if c["status"] == "skip"]

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Rendered",  len(done_ch))
    r2.metric("Failed",    len(fail_ch))
    r3.metric("Skipped",   len(skip_ch))
    r4.metric("Total Cost",fmt_usd(st.session_state.total_cost))

    if st.session_state.zip_bytes:
        st.markdown("### 📦 Download Package")
        st.download_button(
            "⬇️  Download ZIP (all clips + MANIFEST.csv + NLE readme)",
            data=st.session_state.zip_bytes,
            file_name="motion_transfer_output.zip",
            mime="application/zip",
            type="primary",
        )
        st.caption(
            "Import all MP4s into Avid / Premiere / DaVinci and place in order. "
            "Chunks are frame-contiguous — no alignment needed."
        )
        if st.session_state.manifest_csv:
            with st.expander("📄 MANIFEST.csv"):
                st.code(st.session_state.manifest_csv, language="csv")

    if done_ch:
        with st.expander(f"▶️  Preview {len(done_ch)} clips"):
            for ch in done_ch:
                st.markdown(
                    f"**Chunk {ch['index']+1:04d}** · "
                    f"{sec_to_tc(ch['start'])} → {sec_to_tc(ch['end'])} · "
                    f"{ch['duration']:.3f}s")
                st.video(ch["output_url"])
                st.caption(f"[Direct URL ↗]({ch['output_url']})")
                st.markdown("---")


# ─────────────────────────────────────────────────────────────────────────────
#  EXPLAINER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("ℹ️  How it works — cuts, auth, audio, cost"):
    st.markdown(f"""
**Cut points and shot-accurate chunking**

Cut points define shot boundaries in the guide video. Each shot is sent to the
API as its own generation task so motion never bleeds across a hard cut.
Any shot longer than {API_MAX_SEC}s is automatically subdivided into equal
{API_MAX_SEC}s sub-chunks. The timeline visualisation above shows the final
chunk plan before you click Generate.

**Auto scene detection (ffmpeg)**

The `select='gt(scene,threshold)'` filter compares the histogram of adjacent
frames. A value above the threshold is flagged as a cut. Lower threshold = more
sensitive. Results are merged with your manual cut points.

**Frame-accurate extraction**

```
· Boundaries computed in frame numbers (not seconds) — no float drift
· -ss AFTER -i  →  frame-exact decode, not fast keyframe seek
· keyint=1      →  every output frame is an I-frame (NLE-safe)
· -avoid_negative_ts make_zero  →  each chunk timeline resets to 0
```

**No audio — always**

Every ffmpeg call includes `-an`. No audio is extracted, sent to the API,
or expected back. This saves bandwidth, speeds up uploads, and avoids any
Kling error about unsupported audio formats.

**Kling AI — JWT authentication**

Kling uses two credentials: an Access Key (identity) and a Secret Key
(signature). A fresh HS256 JWT is generated for every submit and every poll
call, so long jobs never hit a stale-token 401 error.

**Cost for a 5-minute video (30 × 10s clips)**

| API | Model | Total |
|-----|-------|-------|
| Kling AI | Standard 720p | **$2.10** |
| Kling AI | Professional 1080p | **$4.20** |
| RunwayML | Gen-3 Alpha Turbo | **~$30** *(est.)* |
| RunwayML | Gen-3 Alpha | **~$54** *(est.)* |

Runway prices are estimates from credit-tier pricing — verify at
[runwayml.com/pricing](https://runwayml.com/pricing).
    """)

st.markdown("---")
st.caption("Motion Transfer Studio v4 · "
           "[Kling AI docs](https://docs.klingai.com) · "
           "[RunwayML docs](https://docs.dev.runwayml.com)")
