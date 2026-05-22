# ─────────────────────────────────────────────────────────────────────────────
#  MOTION TRANSFER STUDIO  v7
#  Single-column layout · Fixed CSS · Works at any font size
#  Tab 1 PUPPETEER · Tab 2 ANIMATE · Tab 3 IMAGINE · Tab 4 EDIT
#  Kling AI JWT · RunwayML · Google Drive backup + pull
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import streamlit.components.v1 as components
import requests, time, json, base64, hmac, hashlib, threading, uuid
import math, os, io, zipfile, tempfile, subprocess
from fractions import Fraction

# Module-level task registry — persists across Streamlit reruns and is accessible
# from background threads (unlike st.session_state which is main-thread only).
_TASK_REG  = {}          # session_id -> list[dict]
_REG_LOCK  = threading.Lock()
TASK_FILE  = "/tmp/mts_tasks.json"   # cross-session persistence

st.set_page_config(page_title="Motion Transfer Studio", page_icon=None,
                   layout="wide", initial_sidebar_state="expanded")

# ── CSS ───────────────────────────────────────────────────────────────────────
# IMPORTANT: Never set font-size on * — it breaks Streamlit's internal
# component sizing and causes text to render over itself.
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&display=swap');

/* Apply font only to body-level elements, not * */
body { font-family: 'Space Mono', monospace; }
.stApp { background: #07070f; color: #9d94b0; }

/* Section headers */
.sec {
  border-top: 1px solid #16132a;
  margin: 1.4rem 0 0.8rem 0;
  padding-top: 0.6rem;
  color: #4a4468;
  font-size: 0.7rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  font-family: 'Space Mono', monospace;
}

/* Stat row */
.srow { display: flex; gap: 2.5rem; margin: 0.6rem 0 1rem 0; flex-wrap: wrap; }
.stat .lbl {
  color: #3d3660; font-size: 0.65rem;
  letter-spacing: 0.12em; text-transform: uppercase;
  font-family: 'Space Mono', monospace;
}
.stat .val {
  color: #c8c0dc; font-size: 1.05rem; font-weight: 700;
  font-family: 'Space Mono', monospace;
}

/* Monospace tables */
.mt { width: 100%; border-collapse: collapse; font-family: 'Space Mono', monospace; }
.mt th {
  color: #4a4468; text-align: left; padding: 0.32rem 0.6rem;
  border-bottom: 1px solid #16132a;
  font-size: 0.68rem; letter-spacing: 0.1em; text-transform: uppercase;
}
.mt td { color: #9d94b0; padding: 0.24rem 0.6rem; font-size: 0.76rem; }
.mt tr:hover td { background: #0e0c1c; }
.mt .hl  { color: #a78bfa; font-weight: 700; }
.mt .hlg { color: #34d399; font-weight: 700; }
.mt .muted { color: #3d3660; }
.mt .act td { background: #120f22; }
.mt .sep td {
  background: #0b0a16; color: #3d3660;
  font-size: 0.65rem; letter-spacing: 0.14em; padding: 0.28rem 0.6rem;
}
.mt .err td { color: #f87171; }

/* Chunk grid */
.chunk-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 6px; margin: 0.5rem 0;
}
.chunk-card {
  background: #0c0c1a; border: 1px solid #181428;
  border-radius: 6px; padding: 0.45rem 0.65rem;
  font-family: 'Space Mono', monospace;
}
.chunk-card .cc-id   { color: #3d3660; font-size: 0.68rem; display: block; }
.chunk-card .cc-tc   { color: #6b5f8a; font-size: 0.68rem; display: block; }
.chunk-card .cc-st   { font-size: 0.72rem; font-weight: 700; display: block; margin-top: 2px; }
.s-wait { color: #3d3660; } .s-run  { color: #a78bfa; }
.s-done { color: #34d399; } .s-fail { color: #f87171; } .s-skip { color: #d97706; }

/* Drive */
.drv-ok { color: #34d399; font-size: 0.72rem; font-family: 'Space Mono', monospace; }
.drv-no { color: #3d3660; font-size: 0.72rem; font-family: 'Space Mono', monospace; }

/* Override Streamlit widget labels */
[data-testid="stWidgetLabel"] > div,
[data-testid="stWidgetLabel"] p {
  font-family: 'Space Mono', monospace !important;
  font-size: 0.7rem !important;
  color: #4a4468 !important;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

/* Inputs */
.stTextInput input,
.stNumberInput input,
.stTextArea textarea {
  background: #0a0918 !important;
  border: 1px solid #1a1730 !important;
  border-radius: 3px !important;
  color: #9d94b0 !important;
  font-family: 'Space Mono', monospace !important;
}
.stSelectbox > div > div {
  background: #0a0918 !important;
  border: 1px solid #1a1730 !important;
  color: #9d94b0 !important;
  font-family: 'Space Mono', monospace !important;
}

/* Buttons */
.stButton > button {
  background: #0e0c1c !important;
  border: 1px solid #1e1a32 !important;
  border-radius: 3px !important;
  color: #7a7090 !important;
  font-family: 'Space Mono', monospace !important;
  font-size: 0.76rem !important;
  padding: 0.3rem 0.9rem !important;
  font-weight: 400 !important;
}
.stButton > button:hover {
  border-color: #a78bfa !important;
  color: #a78bfa !important;
}
.stButton > button[kind="primary"] {
  background: #160f2a !important;
  border-color: #5b21b6 !important;
  color: #c4b5fd !important;
}
.stButton > button:disabled { opacity: 0.25 !important; }

/* Download button */
.stDownloadButton > button {
  background: #0e0c1c !important;
  border: 1px solid #1e1a32 !important;
  color: #7a7090 !important;
  font-family: 'Space Mono', monospace !important;
  font-size: 0.76rem !important;
}

/* Slider */
.stSlider > div > div > div > div { background: #5b21b6 !important; }
.stSlider > div > div > div       { background: #1a1730 !important; }

/* Checkbox */
.stCheckbox > label > div > p {
  font-family: 'Space Mono', monospace !important;
  font-size: 0.76rem !important;
  color: #9d94b0 !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
  background: #060510 !important;
  border-right: 1px solid #12102a !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label {
  font-family: 'Space Mono', monospace !important;
}

/* Progress */
.stProgress > div > div { background: #5b21b6 !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
  background: #07070f;
  border-bottom: 1px solid #16132a;
  gap: 0;
}
.stTabs [data-baseweb="tab"] {
  color: #4a4468;
  font-family: 'Space Mono', monospace !important;
  font-size: 0.72rem !important;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 0.5rem 1.4rem;
  background: transparent;
}
.stTabs [aria-selected="true"] {
  color: #a78bfa !important;
  border-bottom: 2px solid #a78bfa !important;
  background: transparent !important;
}

/* Alerts */
.stAlert { border-radius: 3px !important; font-family: 'Space Mono', monospace !important; }
.stAlert p { font-family: 'Space Mono', monospace !important; font-size: 0.76rem !important; }

/* Expander */
.streamlit-expanderHeader {
  font-family: 'Space Mono', monospace !important;
  font-size: 0.72rem !important;
  color: #4a4468 !important;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

/* File uploader */
[data-testid="stFileUploader"] section {
  background: #0a0918 !important;
  border: 1px solid #1a1730 !important;
  border-radius: 3px !important;
}
[data-testid="stFileUploader"] section p {
  font-family: 'Space Mono', monospace !important;
  font-size: 0.72rem !important;
  color: #4a4468 !important;
}

/* Hide Streamlit branding */
#MainMenu, footer, header { visibility: hidden; }

/* Caption text */
.stCaption p {
  font-family: 'Space Mono', monospace !important;
  color: #4a4468 !important;
  font-size: 0.7rem !important;
}

/* Radio */
.stRadio > div { gap: 0.5rem; }
.stRadio label span p {
  font-family: 'Space Mono', monospace !important;
  font-size: 0.76rem !important;
}

/* Metric — hide native, use custom */
div[data-testid="metric-container"] { display: none !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
KLING_BASE  = "https://api.klingai.com"
RUNWAY_BASE = "https://api.dev.runwayml.com/v1"
API_MAX_SEC = 10
MIN_CHUNK   = 3

KLING_VID_PRICE  = {
    "Standard (720p)":      {5: 0.045, 10: 0.070},
    "Professional (1080p)": {5: 0.090, 10: 0.140},
}
RUNWAY_VID_PRICE = {
    "Gen-3 Alpha Turbo": {5: 0.50, 10: 1.00},
    "Gen-3 Alpha":       {5: 0.90, 10: 1.80},
}
KLING_IMG_PRICE  = {
    "kolors":   {"1": 0.008, "4": 0.028},
    "kling-v1": {"1": 0.005, "4": 0.018},
}
KLING_EDIT_PRICE = {
    "Inpaint / Repaint": 0.012,
    "Variation":         0.010,
    "Virtual Try-On":    0.025,
    "Extend Canvas":     0.012,
}
ASPECT_RATIOS = ["1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3", "21:9"]


# ─────────────────────────────────────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
_D = dict(
    guide_bytes=None, guide_fk="", probe=None,
    image_bytes=None, image_fk="",
    cut_points=[], crop_en=False,
    crop_x=0, crop_y=0, crop_w=0, crop_h=0,
    working_bytes=None, working_probe=None,
    active_chunk=None, chunk_settings={}, chunk_previews={},
    t1_chunks=[], t1_results=[], t1_zip=None, t1_csv="", t1_cost=0.0,
    t2_img_bytes=None, t2_img_fk="", t2_results=[], t2_cost=0.0,
    t3_ref_bytes=None, t3_results=[], t3_cost=0.0,
    t4_img_bytes=None, t4_img_fk="",
    t4_aux_bytes=None, t4_aux_fk="",
    t4_results=[], t4_cost=0.0,
    processing=False, log=[],
    session_id=str(uuid.uuid4()),
    bg_tasks=[],
    bg_active=False,
    bg_resumed=False,
)
for k, v in _D.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────────────────────────────────────
#  UTILITY
# ─────────────────────────────────────────────────────────────────────────────
def b64(d): return base64.b64encode(d).decode()
def sec_tc(s, fps=25):
    s = max(0.0, s)
    h = int(s) // 3600
    m = (int(s) % 3600) // 60
    sc = int(s) % 60
    fr = int(round((s % 1) * fps)) % max(1, int(fps))
    return f"{h:02d}:{m:02d}:{sc:02d}:{fr:02d}"
def tc_fn(s): return sec_tc(s).replace(":", "_")
def usd(v): return f"${v:.3f}" if v < 0.1 else f"${v:.2f}"
def alog(m): st.session_state.log.append(f"[{time.strftime('%H:%M:%S')}] {m}")
def gs(k):
    try: return st.secrets[k]
    except: return None
def parse_t(s):
    s = s.strip(); p = s.split(":")
    if len(p) == 1: return float(p[0])
    if len(p) == 2: return int(p[0]) * 60 + float(p[1])
    return int(p[0]) * 3600 + int(p[1]) * 60 + float(p[2])
def get_cs(i, dur):
    if i not in st.session_state.chunk_settings:
        st.session_state.chunk_settings[i] = dict(
            in_pt=0.0, out_pt=dur, loop=False, zoom="1×",
            crop_en=False, cx=0, cy=0, cw=0, ch=0)
    return st.session_state.chunk_settings[i]


# ─────────────────────────────────────────────────────────────────────────────
#  KLING JWT
# ─────────────────────────────────────────────────────────────────────────────
def _bu(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

def kling_jwt(ak, sk):
    h = _bu(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    n = int(time.time())
    p = _bu(json.dumps({"iss": ak, "exp": n + 1800, "nbf": n - 5}).encode())
    m = f"{h}.{p}"
    s = _bu(hmac.new(sk.encode(), m.encode(), hashlib.sha256).digest())
    return f"{m}.{s}"

def kh(ak, sk):
    return {"Authorization": f"Bearer {kling_jwt(ak, sk)}", "Content-Type": "application/json"}


# ─────────────────────────────────────────────────────────────────────────────
#  KLING API
# ─────────────────────────────────────────────────────────────────────────────
def k_post(ak, sk, path, payload):
    r = requests.post(f"{KLING_BASE}{path}", headers=kh(ak, sk), json=payload, timeout=90)
    if not r.ok:
        raise requests.HTTPError(f"Kling {r.status_code}: {r.text[:400]}", response=r)
    return r.json()

def k_poll_vid(ak, sk, tid, endpoint="image2video", mw=600):
    dl = time.time() + mw
    while True:
        if time.time() > dl: raise TimeoutError(f"Timeout {tid}")
        r = requests.get(f"{KLING_BASE}/v1/videos/{endpoint}/{tid}",
                         headers=kh(ak, sk), timeout=30)
        r.raise_for_status()
        d = r.json().get("data", {})
        s = d.get("task_status", "processing")
        if s == "succeed":
            try: return d["task_result"]["videos"][0]["url"]
            except: raise ValueError(f"No URL: {d}")
        if s in ("failed", "error"):
            raise RuntimeError(d.get("task_status_msg", "failed"))
        time.sleep(6)

def k_poll_img(ak, sk, tid, endpoint="generations", mw=300):
    dl = time.time() + mw
    while True:
        if time.time() > dl: raise TimeoutError(f"Timeout {tid}")
        r = requests.get(f"{KLING_BASE}/v1/images/{endpoint}/{tid}",
                         headers=kh(ak, sk), timeout=30)
        r.raise_for_status()
        d = r.json().get("data", {})
        s = d.get("task_status", "processing")
        if s == "succeed":
            try: return [img["url"] for img in d["task_result"]["images"]]
            except: raise ValueError(f"No images: {d}")
        if s in ("failed", "error"):
            raise RuntimeError(d.get("task_status_msg", "failed"))
        time.sleep(5)

def kling_motion_transfer(ak, sk, img_b64, vid_b64, dur, model, prompt):
    d = k_post(ak, sk, "/v1/videos/image2video", {
        "model_name": "kling-v1-5",
        "image":         img_b64,   # raw base64, no data URI prefix
        "motion_video":  vid_b64,   # raw base64, no data URI prefix
        "duration":      int(dur),
        "mode":          "pro" if "1080" in model else "std",
        "cfg_scale":     0.5,
        "prompt":        prompt or "smooth motion, high quality, cinematic",
        "negative_prompt": "blur, artifacts, distortion, watermark",
    })
    tid = d.get("data", {}).get("task_id", "")
    if not tid: raise ValueError(f"No task_id: {d}")
    return tid

def kling_animate(ak, sk, img_b64, prompt, neg, dur, model):
    d = k_post(ak, sk, "/v1/videos/image2video", {
        "model_name":      "kling-v1-5",
        "image":           img_b64,
        "prompt":          prompt,
        "negative_prompt": neg or "",
        "duration":        int(dur),
        "mode":            "pro" if "1080" in model else "std",
        "cfg_scale":       0.5,
    })
    tid = d.get("data", {}).get("task_id", "")
    if not tid: raise ValueError(f"No task_id: {d}")
    return tid

def kling_imagine(ak, sk, prompt, neg, aspect, n, model_name, ref_b64=None, fidelity=0.5):
    payload = {
        "model_name":      model_name,
        "prompt":          prompt,
        "negative_prompt": neg or "",
        "n":               int(n),
        "aspect_ratio":    aspect,
    }
    if ref_b64:
        payload["image_reference"] = ref_b64
        payload["image_fidelity"]  = float(fidelity)
    d = k_post(ak, sk, "/v1/images/generations", payload)
    tid = d.get("data", {}).get("task_id", "")
    if not tid: raise ValueError(f"No task_id: {d}")
    return tid

def kling_edit(ak, sk, img_b64, prompt, neg, fidelity=0.5):
    d = k_post(ak, sk, "/v1/images/generations", {
        "model_name":      "kolors",
        "prompt":          prompt,
        "negative_prompt": neg or "",
        "image_reference": img_b64,
        "image_fidelity":  float(fidelity),
        "n":               1,
    })
    tid = d.get("data", {}).get("task_id", "")
    if not tid: raise ValueError(f"No task_id: {d}")
    return tid

def kling_tryon(ak, sk, human_b64, cloth_b64):
    d = k_post(ak, sk, "/v1/images/kolors-virtual-try-on", {
        "model_name":  "kolors-virtual-try-on-v1",
        "human_image": human_b64,
        "cloth_image": cloth_b64,
    })
    tid = d.get("data", {}).get("task_id", "")
    if not tid: raise ValueError(f"No task_id: {d}")
    return tid


# ─────────────────────────────────────────────────────────────────────────────
#  RUNWAYML API
# ─────────────────────────────────────────────────────────────────────────────
def rh(k):
    return {"Authorization": f"Bearer {k}", "Content-Type": "application/json",
            "X-Runway-Version": "2024-11-06"}

def runway_motion(k, img_b64, vid_b64, dur, model, prompt):
    mime = "image/png" if img_b64.startswith("iVBORw0") else "image/jpeg"
    r = requests.post(f"{RUNWAY_BASE}/image_to_video", headers=rh(k), json={
        "model":       "gen3a_turbo" if "Turbo" in model else "gen3a",
        "promptImage": f"data:{mime};base64,{img_b64}",
        "promptVideo": f"data:video/mp4;base64,{vid_b64}",
        "duration":    int(dur),
        "ratio":       "1280:720",
        "watermark":   False,
        "promptText":  prompt or "smooth motion, high quality",
        "seed":        42,
    }, timeout=90)
    if not r.ok:
        raise requests.HTTPError(f"Runway {r.status_code}: {r.text[:400]}", response=r)
    tid = r.json().get("id", "")
    if not tid: raise ValueError(f"No id: {r.json()}")
    return tid

def runway_poll(k, tid, mw=600):
    dl = time.time() + mw
    while True:
        if time.time() > dl: raise TimeoutError(f"Runway timeout {tid}")
        r = requests.get(f"{RUNWAY_BASE}/tasks/{tid}", headers=rh(k), timeout=30)
        r.raise_for_status()
        d = r.json(); s = d.get("status", "PENDING")
        if s == "SUCCEEDED":
            out = d.get("output", [])
            if out: return out[0]
            raise ValueError(f"No output: {d}")
        if s in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"Runway: {d.get('failure', 'failed')}")
        time.sleep(6)


# ─────────────────────────────────────────────────────────────────────────────
#  FFMPEG
# ─────────────────────────────────────────────────────────────────────────────
def ffok():
    try: subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True); return True
    except: return False

def probe_video(path):
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-select_streams", "v:0",
         "-show_entries", "stream=r_frame_rate,nb_frames,width,height",
         "-show_entries", "format=duration", "-print_format", "json", path],
        capture_output=True, text=True, check=True)
    d = json.loads(r.stdout); st2 = d["streams"][0]
    fps = float(Fraction(st2["r_frame_rate"]))
    dur = float(d["format"]["duration"])
    nf = int(st2["nb_frames"]) if st2.get("nb_frames", "N/A") != "N/A" else int(dur * fps)
    return {"duration": dur, "fps": fps, "total_frames": nf,
            "width": int(st2.get("width", 0)), "height": int(st2.get("height", 0))}

def do_crop(vb, x, y, w, h):
    x, y = x - x % 2, y - y % 2
    w, h = w - w % 2, h - h % 2
    with tempfile.TemporaryDirectory() as t:
        i = os.path.join(t, "i.mp4"); o = os.path.join(t, "o.mp4")
        with open(i, "wb") as f: f.write(vb)
        subprocess.run(["ffmpeg", "-y", "-i", i, "-vf", f"crop={w}:{h}:{x}:{y}",
                        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                        "-pix_fmt", "yuv420p", "-an", o],
                       capture_output=True, check=True)
        with open(o, "rb") as f: return f.read()

def scene_cuts(vb, thresh=0.35):
    with tempfile.TemporaryDirectory() as t:
        i = os.path.join(t, "i.mp4")
        with open(i, "wb") as f: f.write(vb)
        r = subprocess.run(
            ["ffmpeg", "-i", i,
             "-vf", f"select='gt(scene,{thresh})',showinfo",
             "-vsync", "vfr", "-an", "-f", "null", "-"],
            capture_output=True, text=True, timeout=300)
        cuts = []
        for line in r.stderr.split("\n"):
            if "pts_time:" in line and "showinfo" in line:
                try:
                    tv = float(line.split("pts_time:")[1].split()[0])
                    if tv > 0.25: cuts.append(round(tv, 3))
                except: pass
        return sorted(set(cuts))

def fit_chunk_for_api(video_bytes: bytes, max_mb: float = 6.0) -> bytes:
    """
    Ensure chunk fits within Kling API size limit before base64 encoding.
    base64 adds ~33% overhead, so 6MB raw -> ~8MB on the wire.
    Pass 1: lower CRF keeping resolution.
    Pass 2: scale to 720p.
    Pass 3: scale to 540p last resort.
    """
    limit = int(max_mb * 1024 * 1024)
    if len(video_bytes) <= limit:
        return video_bytes
    with tempfile.TemporaryDirectory() as t:
        inp = os.path.join(t, "i.mp4")
        out = os.path.join(t, "o.mp4")
        with open(inp, "wb") as f: f.write(video_bytes)
        for crf, scale in [(28, None), (30, "1280:720"), (32, "960:540")]:
            vf = "scale=trunc(iw/2)*2:trunc(ih/2)*2"
            if scale:
                vf = (f"scale={scale}:force_original_aspect_ratio=decrease,"
                      "scale=trunc(iw/2)*2:trunc(ih/2)*2")
            subprocess.run(
                ["ffmpeg", "-y", "-i", inp,
                 "-c:v", "libx264", "-preset", "fast",
                 "-crf", str(crf), "-vf", vf, "-an", out],
                capture_output=True)
            if os.path.exists(out) and os.path.getsize(out) > 0:
                with open(out, "rb") as f: result = f.read()
                if len(result) <= limit:
                    return result
                with open(inp, "wb") as f: f.write(result)
        with open(out, "rb") as f: return f.read()


def extract_seg(vb, start, end, fps):
    """Frame-accurate extraction. -an always — no audio."""
    sf = int(round(start * fps)); ef = int(round(end * fps)); nf = ef - sf
    sts = sf / fps; dur = nf / fps
    with tempfile.TemporaryDirectory() as t:
        i = os.path.join(t, "i.mp4"); o = os.path.join(t, "o.mp4")
        with open(i, "wb") as f: f.write(vb)
        res = subprocess.run(
            ["ffmpeg", "-y", "-i", i,
             "-ss", f"{sts:.9f}", "-t", f"{dur:.9f}",
             "-c:v", "libx264", "-preset", "fast", "-crf", "18",
             "-pix_fmt", "yuv420p", "-x264opts", "keyint=1:min-keyint=1",
             "-avoid_negative_ts", "make_zero", "-movflags", "+faststart",
             "-an", o], capture_output=True)
        if not os.path.exists(o) or os.path.getsize(o) < 1024:
            raise RuntimeError(f"Extract failed {start:.2f}→{end:.2f}s")
        with open(o, "rb") as f: return f.read()


# ─────────────────────────────────────────────────────────────────────────────
#  CHUNK PLAN
# ─────────────────────────────────────────────────────────────────────────────
def make_plan(dur, cuts, fps):
    cps = sorted({c for c in cuts if 0.1 < c < dur - 0.1})
    bounds = [0.0] + list(cps) + [dur]
    segs = []
    for i in range(len(bounds) - 1):
        s, e = bounds[i], bounds[i + 1]; d = e - s
        if d < 0.1: continue
        if d <= API_MAX_SEC:
            segs.append((s, e, False))
        else:
            n = math.ceil(d / API_MAX_SEC); sub = d / n
            for j in range(n):
                ss = s + j * sub; se = min(s + (j + 1) * sub, e)
                segs.append((ss, se, True))
    out = []
    for i, (s, e, sub) in enumerate(segs):
        d = e - s; nf = int(round(d * fps))
        out.append({"index": i, "start": s, "end": e, "duration": d, "n_frames": nf,
                    "is_sub": sub, "status": "skip" if d < MIN_CHUNK else "wait",
                    "filename": f"chunk_{i+1:04d}_TC_{tc_fn(s)}_to_{tc_fn(e)}.mp4",
                    "output_url": None})
    return out


# ─────────────────────────────────────────────────────────────────────────────
#  CHUNK PLAYER HTML
# ─────────────────────────────────────────────────────────────────────────────
def player_html(vid_b64, in_pt, out_pt, loop, zoom_px):
    lo = "true" if loop else "false"
    return f"""<!DOCTYPE html><html><head><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#07070f;font-family:monospace;font-size:11px;color:#6b6080}}
#w{{display:flex;flex-direction:column;gap:5px;padding:2px}}
video{{width:100%;max-height:{zoom_px}px;background:#000;display:block;cursor:pointer}}
.tl{{height:4px;background:#12102a;border-radius:2px;position:relative;cursor:pointer;margin:1px 0}}
.tlp{{height:100%;background:#3b1d8a;border-radius:2px;pointer-events:none}}
.mk{{position:absolute;top:-4px;width:2px;height:12px;pointer-events:none}}
.mki{{background:#34d399}}.mko{{background:#f87171}}.mkh{{background:#a78bfa;width:1px}}
.inf{{display:flex;justify-content:space-between;padding:0 2px;color:#2d2a48;font-size:10px}}
.acc{{color:#a78bfa}}.grn{{color:#34d399}}.red{{color:#f87171}}
</style></head><body><div id="w">
<video id="v" src="data:video/mp4;base64,{vid_b64}" preload="metadata"></video>
<div class="tl" id="tl">
  <div class="tlp" id="pl"></div>
  <div class="mk mki" id="mi"></div>
  <div class="mk mko" id="mo"></div>
  <div class="mk mkh" id="mh"></div>
</div>
<div class="inf">
  <span>IN <span class="grn">{in_pt:.3f}s</span></span>
  <span class="acc" id="tc">--:--.---</span>
  <span>OUT <span class="red">{out_pt:.3f}s</span></span>
</div></div>
<script>
const v=document.getElementById('v'),inPt={in_pt},outPt={out_pt},doLoop={lo};
let dur=0;
function fmt(s){{const m=Math.floor(s/60),sc=(s%60).toFixed(3);
  return String(m).padStart(2,'0')+':'+String(sc).padStart(6,'0');}}
v.addEventListener('loadedmetadata',()=>{{dur=v.duration;v.currentTime=inPt;
  document.getElementById('mi').style.left=(inPt/dur*100)+'%';
  document.getElementById('mo').style.left=(outPt/dur*100)+'%';}});
v.addEventListener('timeupdate',()=>{{if(!dur)return;
  const p=v.currentTime/dur;
  document.getElementById('pl').style.width=(p*100)+'%';
  document.getElementById('mh').style.left=(p*100)+'%';
  document.getElementById('tc').textContent=fmt(v.currentTime);
  if(doLoop&&v.currentTime>=outPt-.05){{v.currentTime=inPt;v.play();}}}});
v.addEventListener('click',()=>v.paused?v.play():v.pause());
document.getElementById('tl').addEventListener('click',e=>{{
  const r=e.currentTarget.getBoundingClientRect();
  v.currentTime=((e.clientX-r.left)/r.width)*dur;}});
if(doLoop){{v.currentTime=inPt;v.play();}}
</script></body></html>"""


# ─────────────────────────────────────────────────────────────────────────────
#  HTML RENDER HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def stats_html(pairs):
    items = "".join(
        f'<div class="stat"><div class="lbl">{l}</div><div class="val">{v}</div></div>'
        for l, v in pairs)
    return f'<div class="srow">{items}</div>'

def chunk_grid_html(chunks, active, fps=25):
    st_map = {
        "wait": ("s-wait", "QUEUED"), "run": ("s-run", "RUNNING"),
        "done": ("s-done", "DONE"),   "fail": ("s-fail", "FAILED"),
        "skip": ("s-skip", "SKIP"),
    }
    cards = ""
    for ch in chunks:
        i = ch["index"]
        cls, lbl = st_map.get(ch["status"], ("s-wait", ch["status"].upper()))
        active_style = "border-color:#a78bfa;" if i == active else ""
        cs = st.session_state.chunk_settings.get(i, {})
        note = ""
        if cs:
            if cs.get("in_pt", 0) > 0.01 or cs.get("out_pt", ch["duration"]) < ch["duration"] - 0.01:
                note += " [trim]"
            if cs.get("crop_en"): note += " [crop]"
        sub = " SUB" if ch["is_sub"] else ""
        cards += (
            f'<div class="chunk-card" style="{active_style}">'
            f'<span class="cc-id">{i+1:04d}{sub}</span>'
            f'<span class="cc-tc">{sec_tc(ch["start"],fps)} → {sec_tc(ch["end"],fps)}</span>'
            f'<span class="cc-tc">{ch["duration"]:.3f}s · {ch["n_frames"]} fr</span>'
            f'<span class="cc-st {cls}">{lbl}{note}</span>'
            f'</div>'
        )
    return f'<div class="chunk-grid">{cards}</div>'

def cost_tbl_html(n, api, model, dur_key):
    rows = ""
    rows += '<tr class="sep"><td colspan="5">KLING AI</td></tr>'
    for m, p in KLING_VID_PRICE.items():
        for d in [5, 10]:
            t = n * p[d]
            act = (api == "Kling AI" and model == m and dur_key == d)
            rows += (f'<tr class="{"act" if act else ""}">'
                     f'<td>Kling</td><td>{m}</td><td>{n}</td>'
                     f'<td>{usd(p[d])}</td>'
                     f'<td class="{"hl" if act else ""}">{usd(t)}</td></tr>')
    rows += '<tr class="sep"><td colspan="5">RUNWAYML ACT-ONE (estimated)</td></tr>'
    for m, p in RUNWAY_VID_PRICE.items():
        for d in [5, 10]:
            t = n * p[d]
            act = (api == "RunwayML" and model == m and dur_key == d)
            rows += (f'<tr class="{"act" if act else ""}">'
                     f'<td>Runway</td><td>{m}</td><td>{n}</td>'
                     f'<td>{usd(p[d])}</td>'
                     f'<td class="{"hlg" if act else ""}">{usd(t)} *</td></tr>')
    return (f'<table class="mt"><thead><tr>'
            f'<th>API</th><th>MODEL</th><th>CLIPS</th><th>$/CLIP</th><th>TOTAL</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>'
            f'<p style="color:#2d2a48;font-size:0.65rem;margin-top:0.3rem;">'
            f'* runway: estimated from runwayml.com/pricing</p>')


# ─────────────────────────────────────────────────────────────────────────────
#  ZIP
# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
#  GOOGLE DRIVE
# ─────────────────────────────────────────────────────────────────────────────
def drive_configured():
    return bool(gs("GOOGLE_SERVICE_ACCOUNT_JSON") and gs("GOOGLE_DRIVE_FOLDER_ID"))

def _drive_svc():
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        info  = json.loads(gs("GOOGLE_SERVICE_ACCOUNT_JSON"))
        creds = service_account.Credentials.from_service_account_info(
                    info, scopes=["https://www.googleapis.com/auth/drive"])
        return build("drive", "v3", credentials=creds, cache_discovery=False)
    except Exception as e:
        return None

def drive_upload(data_bytes: bytes, filename: str, mime_type: str) -> str:
    try:
        from googleapiclient.http import MediaIoBaseUpload
        svc    = _drive_svc()
        if not svc: return ""
        folder = gs("GOOGLE_DRIVE_FOLDER_ID") or "root"
        meta   = {"name": filename, "parents": [folder]}
        media  = MediaIoBaseUpload(io.BytesIO(data_bytes), mimetype=mime_type)
        f = svc.files().create(body=meta, media_body=media,
                               fields="id,webViewLink").execute()
        return f.get("webViewLink", "")
    except Exception as e:
        return f"error: {e}"

def drive_list(mime_filter=None):
    try:
        svc    = _drive_svc()
        if not svc: return []
        folder = gs("GOOGLE_DRIVE_FOLDER_ID") or "root"
        q      = f"'{folder}' in parents and trashed=false"
        if mime_filter: q += f" and mimeType contains '{mime_filter}'"
        res = svc.files().list(q=q, fields="files(id,name,mimeType)",
                               orderBy="modifiedTime desc", pageSize=40).execute()
        return res.get("files", [])
    except: return []

def drive_download_id(file_id: str):
    try:
        svc = _drive_svc()
        if not svc: return None
        return svc.files().get_media(fileId=file_id).execute()
    except: return None


# ─────────────────────────────────────────────────────────────────────────────
#  TASK STATE PERSISTENCE
# ─────────────────────────────────────────────────────────────────────────────
def save_task_file(tasks: list):
    try:
        with open(TASK_FILE, "w") as f:
            json.dump({"saved_at": time.time(), "tasks": tasks}, f)
    except: pass

def load_task_file() -> list | None:
    try:
        with open(TASK_FILE) as f:
            d = json.load(f)
        if time.time() - d.get("saved_at", 0) < 14400:   # 4-hour window
            return d["tasks"]
    except: pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  ETA + METRICS
# ─────────────────────────────────────────────────────────────────────────────
KLING_EST_SEC = 200   # conservative single-clip estimate (seconds)

def fmt_dur(sec: float) -> str:
    sec = max(0, int(sec))
    h, r = divmod(sec, 3600); m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

def calc_eta(tasks: list) -> dict:
    total    = len(tasks)
    done     = [t for t in tasks if t.get("status") == "done"]
    failed   = [t for t in tasks if t.get("status") == "failed"]
    polling  = [t for t in tasks if t.get("status") == "polling"]
    skipped  = [t for t in tasks if t.get("status") == "skip"]
    uploaded = [t for t in done   if t.get("drive_link")]

    # Average actual time per completed clip
    timed = [t for t in done
             if t.get("completed_at") and t.get("submitted_at")]
    if timed:
        avg_sec = sum(t["completed_at"] - t["submitted_at"] for t in timed) / len(timed)
    else:
        avg_sec = KLING_EST_SEC

    # ETA: Kling processes tasks with some concurrency — we assume ~3 parallel slots
    concurrency  = 3
    eta_sec      = max(0, (len(polling) / max(concurrency, 1)) * avg_sec)

    # Start time from earliest submission
    submit_times = [t.get("submitted_at", time.time()) for t in tasks if t.get("submitted_at")]
    start_time   = min(submit_times) if submit_times else time.time()
    elapsed_sec  = time.time() - start_time

    # Absolute finish time
    finish_ts    = time.time() + eta_sec
    finish_str   = time.strftime("%H:%M", time.localtime(finish_ts))

    return {
        "total":    total,
        "done":     len(done),
        "failed":   len(failed),
        "polling":  len(polling),
        "skipped":  len(skipped),
        "uploaded": len(uploaded),
        "avg_sec":  avg_sec,
        "eta_sec":  eta_sec,
        "elapsed":  elapsed_sec,
        "finish":   finish_str,
        "pct":      int(len(done) / max(total - len(skipped), 1) * 100),
    }

def metrics_html(m: dict) -> str:
    bar_filled = int(m["pct"] / 10)
    bar = "█" * bar_filled + "░" * (10 - bar_filled)
    return f"""
<div style="background:#0c0b18;border:1px solid #1a1730;border-radius:6px;
  padding:1rem 1.2rem;font-family:'Space Mono',monospace;margin:.5rem 0;">
<div style="color:#4a4468;font-size:.65rem;letter-spacing:.18em;
  text-transform:uppercase;margin-bottom:.7rem;">TASK MONITOR</div>
<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));
  gap:.6rem .8rem;margin-bottom:.8rem;">
  <div><div style="color:#3d3660;font-size:.6rem;letter-spacing:.1em;">TOTAL</div>
       <div style="color:#c8c0dc;font-size:1.05rem;font-weight:700;">{m["total"]}</div></div>
  <div><div style="color:#3d3660;font-size:.6rem;letter-spacing:.1em;">DONE</div>
       <div style="color:#34d399;font-size:1.05rem;font-weight:700;">{m["done"]}</div></div>
  <div><div style="color:#3d3660;font-size:.6rem;letter-spacing:.1em;">IN QUEUE</div>
       <div style="color:#a78bfa;font-size:1.05rem;font-weight:700;">{m["polling"]}</div></div>
  <div><div style="color:#3d3660;font-size:.6rem;letter-spacing:.1em;">FAILED</div>
       <div style="color:#f87171;font-size:1.05rem;font-weight:700;">{m["failed"]}</div></div>
  <div><div style="color:#3d3660;font-size:.6rem;letter-spacing:.1em;">DRIVE UP</div>
       <div style="color:#34d399;font-size:1.05rem;font-weight:700;">{m["uploaded"]}</div></div>
  <div><div style="color:#3d3660;font-size:.6rem;letter-spacing:.1em;">ELAPSED</div>
       <div style="color:#9d94b0;font-size:1.05rem;font-weight:700;">{fmt_dur(m["elapsed"])}</div></div>
  <div><div style="color:#3d3660;font-size:.6rem;letter-spacing:.1em;">ETA</div>
       <div style="color:#c8c0dc;font-size:1.05rem;font-weight:700;">{fmt_dur(m["eta_sec"])}</div></div>
  <div><div style="color:#3d3660;font-size:.6rem;letter-spacing:.1em;">AVG/CLIP</div>
       <div style="color:#9d94b0;font-size:1.05rem;font-weight:700;">{fmt_dur(m["avg_sec"])}</div></div>
</div>
<div style="font-size:.75rem;color:#4a4468;margin-bottom:.3rem;">
  PROGRESS  {m["pct"]}%  <span style="color:#a78bfa;letter-spacing:.05em;">{bar}</span>
</div>
<div style="font-size:.7rem;color:#3d3660;">
  Est. completion at <span style="color:#9d94b0;">{m["finish"]}</span> local time
  ·  {m["done"]}/{m["total"] - m["skipped"]} clips done
  {"· <span style=\"color:#34d399\">Drive uploads active</span>" if m["uploaded"] > 0 else ""}
</div>
</div>"""


# ─────────────────────────────────────────────────────────────────────────────
#  BACKGROUND POLLING WORKER
# ─────────────────────────────────────────────────────────────────────────────
def _bg_poll_worker(session_id: str, ak: str, sk: str):
    """
    Daemon thread: polls every 10 seconds until all tasks are settled.
    Writes completed video to Google Drive immediately when available.
    Updates _TASK_REG[session_id] and saves to TASK_FILE for reconnect.
    """
    while True:
        with _REG_LOCK:
            tasks = _TASK_REG.get(session_id, [])

        pending = [t for t in tasks if t.get("status") == "polling"]
        if not pending:
            with _REG_LOCK:
                _TASK_REG[session_id + "_done"] = True
            save_task_file(tasks)
            break

        for task in pending:
            try:
                r = requests.get(
                    f"{KLING_BASE}/v1/videos/image2video/{task['task_id']}",
                    headers=kh(ak, sk), timeout=30)
                r.raise_for_status()
                d = r.json().get("data", {})
                s = d.get("task_status", "processing")

                if s == "succeed":
                    try:
                        url = d["task_result"]["videos"][0]["url"]
                    except (KeyError, IndexError):
                        task["status"] = "failed"; task["error"] = "no URL in response"
                        continue

                    task["url"]          = url
                    task["status"]       = "done"
                    task["completed_at"] = time.time()

                    # Immediately upload to Drive if configured
                    if drive_configured():
                        try:
                            vid_data = requests.get(url, timeout=120).content
                            link = drive_upload(vid_data, task["filename"], "video/mp4")
                            task["drive_link"]   = link
                            task["drive_status"] = "uploaded"
                        except Exception as de:
                            task["drive_status"] = f"upload failed: {de}"

                elif s in ("failed", "error"):
                    task["status"] = "failed"
                    task["error"]  = d.get("task_status_msg", "Kling reported failure")

            except Exception:
                pass   # Don't kill the thread on transient network errors

        save_task_file(tasks)
        time.sleep(10)


def start_background_polling(session_id: str, ak: str, sk: str):
    t = threading.Thread(
        target=_bg_poll_worker,
        args=(session_id, ak, sk),
        daemon=True,       # thread dies if main process exits
        name=f"kling_poll_{session_id[:8]}")
    t.start()
    return t


def build_zip(chunks):
    buf = io.BytesIO()
    done = [c for c in chunks if c["status"] == "done" and c["output_url"]]
    lines = ["chunk,filename,start_tc,end_tc,start_s,end_s,dur_s,frames,url"]
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
        for ch in done:
            r = requests.get(ch["output_url"], timeout=120)
            r.raise_for_status()
            zf.writestr(ch["filename"], r.content)
            lines.append(f"{ch['index']+1},{ch['filename']},"
                         f"{sec_tc(ch['start'])},{sec_tc(ch['end'])},"
                         f"{ch['start']:.4f},{ch['end']:.4f},"
                         f"{ch['duration']:.4f},{ch['n_frames']},{ch['output_url']}")
        csv = "\n".join(lines)
        zf.writestr("MANIFEST.csv", csv)
        zf.writestr("README.txt",
                    "Import MP4s into Avid/Premiere/DaVinci in chunk order.\n"
                    "H.264, no audio, every frame I-frame. See MANIFEST.csv.\n")
    return buf.getvalue(), csv


# ─────────────────────────────────────────────────────────────────────────────
#  GOOGLE DRIVE
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
S_AK = gs("KLING_ACCESS_KEY"); S_SK = gs("KLING_SECRET_KEY"); S_RW = gs("RUNWAY_API_KEY")

with st.sidebar:
    st.markdown("**MOTION TRANSFER STUDIO**")

    st.markdown('<div class="sec">API ENGINE</div>', unsafe_allow_html=True)
    chosen_api = st.radio("API", ["Kling AI", "RunwayML"],
                          horizontal=True, label_visibility="collapsed")

    st.markdown('<div class="sec">CREDENTIALS</div>', unsafe_allow_html=True)
    if chosen_api == "Kling AI":
        if S_AK and S_SK:
            st.caption("Kling Access Key + Secret Key loaded from Secrets.")
            ak, sk = S_AK, S_SK
        else:
            ak = st.text_input("Kling Access Key", type="password")
            sk = st.text_input("Kling Secret Key", type="password")
        rk = None
        keys_ok = bool(ak and sk)
    else:
        ak = sk = None
        if S_RW:
            st.caption("RunwayML API Key loaded from Secrets.")
            rk = S_RW
        else:
            rk = st.text_input("RunwayML API Key", type="password")
        keys_ok = bool(rk)

    st.markdown('<div class="sec">VIDEO MODEL</div>', unsafe_allow_html=True)
    vid_model = st.selectbox(
        "Video model",
        list(KLING_VID_PRICE.keys()) if chosen_api == "Kling AI" else list(RUNWAY_VID_PRICE.keys()),
        index=1 if chosen_api == "Kling AI" else 0,
        label_visibility="collapsed",
    )

    st.markdown('<div class="sec">IMAGE MODEL</div>', unsafe_allow_html=True)
    img_model = st.selectbox("Image model", list(KLING_IMG_PRICE.keys()),
                             label_visibility="collapsed")

    st.markdown('<div class="sec">STYLE PROMPT</div>', unsafe_allow_html=True)
    prompt_txt = st.text_area("Prompt", "", height=60,
                              label_visibility="collapsed",
                              placeholder="cinematic, sharp detail…")


    st.markdown('<div class="sec">GOOGLE DRIVE</div>', unsafe_allow_html=True)
    if drive_configured():
        st.markdown('<span style="color:#34d399;font-size:.72rem;">connected — Drive backup active</span>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<span style="color:#3d3660;font-size:.72rem;">not configured</span>',
                    unsafe_allow_html=True)
        st.caption("Add secrets to enable auto-backup (see setup guide in Puppeteer tab)")

    if st.session_state.log:
        st.markdown('<div class="sec">LOG</div>', unsafe_allow_html=True)
        with st.expander("Show log", expanded=False):
            st.code("\n".join(st.session_state.log[-60:]), language=None)


# ─────────────────────────────────────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("# MOTION TRANSFER STUDIO")
st.caption("Kling AI  ·  RunwayML  ·  Google Drive  ·  Frame-accurate  ·  No audio")

if not ffok():
    st.error("ffmpeg not found — add  ffmpeg  to packages.txt and redeploy")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
#  TABS
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["PUPPETEER", "ANIMATE", "IMAGINE", "EDIT"])


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 1  PUPPETEER
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:

    # ── TASK MONITOR  (shown when background tasks are active or resumable) ──
    session_id = st.session_state.session_id

    # Auto-load saved task state for reconnect
    if not st.session_state.bg_tasks and not st.session_state.bg_resumed:
        saved = load_task_file()
        if saved and any(t.get("status") == "polling" for t in saved):
            st.session_state.bg_tasks    = saved
            st.session_state.bg_active   = True
            st.session_state.bg_resumed  = True
            # Re-register tasks in global registry
            with _REG_LOCK:
                _TASK_REG[session_id] = saved
            # Restart polling thread for remaining tasks
            if st.session_state.get("ak_saved") and st.session_state.get("sk_saved"):
                start_background_polling(
                    session_id,
                    st.session_state.ak_saved,
                    st.session_state.sk_saved)

    # Show monitor whenever we have background tasks
    bg_tasks = _TASK_REG.get(session_id, st.session_state.bg_tasks)
    if bg_tasks:
        m = calc_eta(bg_tasks)
        st.markdown(metrics_html(m), unsafe_allow_html=True)

        # Auto-refresh every 12 seconds while tasks are in flight
        if m["polling"] > 0:
            st.caption(
                f"Auto-refreshing every 12 seconds.  "
                f"You can close this tab — Kling continues processing on their servers, "
                f"and your Drive folder will receive completed clips automatically.")
            time.sleep(12)
            st.rerun()
        else:
            all_done = m["done"] + m["failed"] == m["total"] - m["skipped"]
            if all_done:
                st.success(
                    f"All tasks settled — {m['done']} done, {m['failed']} failed.  "
                    + (f"{m['uploaded']} clips uploaded to Drive." if m["uploaded"] > 0 else ""))
                st.session_state.bg_active = False

        # Task detail table
        rows = ""
        for t in bg_tasks:
            if t.get("status") == "skip": continue
            sc = {"done":"hlg","failed":"err","polling":"","wait":""}.get(t.get("status",""),"")
            drv = ""
            if t.get("drive_link"):
                drv = f'<a href="{t["drive_link"]}" target="_blank" style="color:#34d399;font-size:.65rem;">↗ Drive</a>'
            elif t.get("drive_status","").startswith("upload failed"):
                drv = '<span style="color:#f87171;font-size:.65rem;">⚠ upload err</span>'
            elapsed_s = ""
            if t.get("completed_at") and t.get("submitted_at"):
                elapsed_s = f'{int(t["completed_at"]-t["submitted_at"])}s'
            rows += (f'<tr><td class="muted">{t["index"]+1:04d}</td>'
                     f'<td class="{sc}">{t.get("status","?").upper()}</td>'
                     f'<td class="muted">{elapsed_s}</td>'
                     f'<td>{drv}</td></tr>')
        st.markdown(
            f'<table class="mt"><thead><tr>'
            f'<th>#</th><th>STATUS</th><th>TIME</th><th>DRIVE</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>',
            unsafe_allow_html=True)

        # ZIP download from completed tasks
        done_tasks = [t for t in bg_tasks if t.get("status") == "done" and t.get("url")]
        if done_tasks:
            if st.button(f"Build ZIP from {len(done_tasks)} completed clips", key="bg_zip"):
                with st.spinner("Building ZIP…"):
                    buf = io.BytesIO()
                    lines = ["chunk,filename,status,drive_link,url"]
                    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
                        for t in done_tasks:
                            r2 = requests.get(t["url"], timeout=120); r2.raise_for_status()
                            zf.writestr(t["filename"], r2.content)
                            lines.append(f"{t['index']+1},{t['filename']},"
                                         f"{t.get('status','')},{t.get('drive_link','')},{t['url']}")
                        zf.writestr("MANIFEST.csv", "\n".join(lines))
                    zip_data = buf.getvalue()
                if drive_configured():
                    drive_upload(zip_data, "motion_transfer_background.zip", "application/zip")
                st.download_button("Download ZIP", data=zip_data,
                                   file_name="motion_transfer_output.zip",
                                   mime="application/zip", type="primary")

        st.markdown('<div class="sec">NEW JOB</div>', unsafe_allow_html=True)


    # ── GUIDE VIDEO ──────────────────────────────────────────────────────────
    st.markdown('<div class="sec">GUIDE VIDEO</div>', unsafe_allow_html=True)

    gf = st.file_uploader(
        "Upload motion guide video (MP4, MOV, WEBM, AVI)",
        type=["mp4", "mov", "webm", "avi"], key="gv")
    if gf:
        fk = f"{gf.name}_{gf.size}"
        if st.session_state.guide_fk != fk:
            st.session_state.guide_bytes   = gf.read()
            st.session_state.guide_fk      = fk
            st.session_state.cut_points    = []
            st.session_state.working_bytes = None
            st.session_state.working_probe = None
            st.session_state.crop_en       = False
            st.session_state.active_chunk  = None
            st.session_state.chunk_settings = {}
            st.session_state.chunk_previews = {}
            with tempfile.TemporaryDirectory() as t:
                p = os.path.join(t, "i.mp4")
                with open(p, "wb") as f: f.write(st.session_state.guide_bytes)
                try: st.session_state.probe = probe_video(p)
                except Exception as e: st.warning(f"Probe failed: {e}")
        st.video(gf)
        if st.session_state.probe:
            pr = st.session_state.probe
            st.caption(f"{pr['duration']:.2f}s  ·  {pr['fps']:.3f} fps  ·  {pr['width']}×{pr['height']} px")


    # ── SUBJECT IMAGE ─────────────────────────────────────────────────────────
    st.markdown('<div class="sec">SUBJECT IMAGE</div>', unsafe_allow_html=True)

    imf = st.file_uploader(
        "Upload static subject image (JPG, PNG, WEBP)",
        type=["jpg", "jpeg", "png", "webp"], key="si")
    if imf:
        ik = f"{imf.name}_{imf.size}"
        if st.session_state.image_fk != ik:
            st.session_state.image_bytes = imf.read()
            st.session_state.image_fk    = ik
        st.image(imf, width=400)


    # ── ONLY SHOWN WHEN GUIDE VIDEO IS UPLOADED ───────────────────────────────
    if st.session_state.guide_bytes and st.session_state.probe:
        pr      = st.session_state.probe
        vdur    = pr["duration"]; vfps = pr["fps"]; vw = pr["width"]; vh = pr["height"]
        act_vb  = st.session_state.working_bytes or st.session_state.guide_bytes
        act_pr  = st.session_state.working_probe or st.session_state.probe
        act_dur = act_pr["duration"]; act_fps = act_pr["fps"]

        # ── GLOBAL CROP ───────────────────────────────────────────────────────
        st.markdown('<div class="sec">GLOBAL CROP  —  isolate one person</div>',
                    unsafe_allow_html=True)
        with st.expander("Configure crop" + (" (ACTIVE)" if st.session_state.crop_en else "")):
            st.caption(f"Source resolution: {vw} × {vh} px. All values in pixels, must be even.")

            cx = st.number_input("Left edge  (x)", 0, max(vw - 2, 0),
                                 st.session_state.crop_x, step=2)
            cy = st.number_input("Top edge   (y)", 0, max(vh - 2, 0),
                                 st.session_state.crop_y, step=2)
            cw = st.number_input("Width", 2, vw,
                                 vw if not st.session_state.crop_en else st.session_state.crop_w,
                                 step=2)
            ch = st.number_input("Height", 2, vh,
                                 vh if not st.session_state.crop_en else st.session_state.crop_h,
                                 step=2)

            noop = (cx == 0 and cy == 0 and cw == vw and ch == vh)
            if not noop:
                st.caption(f"Will crop to {cw} × {ch} px starting at ({cx}, {cy})")

            if st.button("Apply Crop", disabled=noop):
                with st.spinner("Cropping…"):
                    try:
                        cr = do_crop(st.session_state.guide_bytes,
                                     int(cx), int(cy), int(cw), int(ch))
                        with tempfile.TemporaryDirectory() as t:
                            p = os.path.join(t, "c.mp4")
                            with open(p, "wb") as f: f.write(cr)
                            np2 = probe_video(p)
                        st.session_state.working_bytes = cr
                        st.session_state.working_probe = np2
                        st.session_state.crop_en = True
                        st.session_state.crop_x = int(cx); st.session_state.crop_y = int(cy)
                        st.session_state.crop_w = int(cw); st.session_state.crop_h = int(ch)
                        st.session_state.chunk_previews = {}
                        act_vb = cr; act_pr = np2; act_dur = np2["duration"]; act_fps = np2["fps"]
                        alog(f"Crop applied {cw}×{ch} at ({cx},{cy})")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Crop failed: {e}")

            if st.session_state.crop_en:
                np2 = st.session_state.working_probe
                st.caption(f"Active crop: {np2['width']} × {np2['height']} px  ·  {np2['duration']:.2f}s")
                if st.button("Reset Crop — use original video"):
                    st.session_state.working_bytes = None
                    st.session_state.working_probe = None
                    st.session_state.crop_en = False
                    st.session_state.chunk_previews = {}
                    st.rerun()

        # ── CUT POINTS ────────────────────────────────────────────────────────
        st.markdown('<div class="sec">CUT POINTS  —  shot boundaries</div>',
                    unsafe_allow_html=True)

        thr = st.slider(
            "Scene detection sensitivity  (lower = more cuts detected)",
            0.10, 0.60, 0.35, 0.05)
        if st.button("Auto-detect scene cuts"):
            with st.spinner("Running ffmpeg scene detection…"):
                found = scene_cuts(act_vb, thr)
                if found:
                    merged = sorted(set(st.session_state.cut_points) | set(found))
                    st.session_state.cut_points = merged
                    alog(f"Detected {len(found)} cuts at threshold {thr}")
                    st.success(f"Found {len(found)} cut(s). Added to list.")
                else:
                    st.info("No cuts found at this threshold. Try lowering it.")

        st.caption("Drag the playhead to a shot change, then click Add Cut.")
        ph = st.slider(
            "Playhead position (seconds)",
            0.0, float(act_dur), 0.0,
            step=round(1.0 / act_fps, 4),
            format="%.3f")
        st.caption(f"Position: {sec_tc(ph, act_fps)}  ({ph:.3f}s)")

        col_add, col_type = st.columns([1, 2])
        with col_add:
            if st.button("Add cut at playhead"):
                t = round(ph, 3)
                if 0.5 < t < act_dur - 0.5 and t not in st.session_state.cut_points:
                    st.session_state.cut_points.append(t)
                    st.session_state.cut_points.sort()
                    alog(f"Manual cut: {t}s")
                    st.rerun()
        with col_type:
            typed = st.text_input(
                "Or type a time  (formats: 83.5  or  1:23.5  or  00:01:23.5)",
                "", placeholder="e.g.  1:23.5")
            if typed:
                try:
                    tv = round(parse_t(typed), 3)
                    if st.button(f"Add cut at {sec_tc(tv, act_fps)}"):
                        if 0.1 < tv < act_dur - 0.1 and tv not in st.session_state.cut_points:
                            st.session_state.cut_points.append(tv)
                            st.session_state.cut_points.sort()
                            st.rerun()
                except:
                    st.caption("Invalid time format.")

        if st.session_state.cut_points:
            st.caption(f"{len(st.session_state.cut_points)} cut point(s):")
            cp_cols = st.columns(min(len(st.session_state.cut_points), 8))
            for j, cp in enumerate(st.session_state.cut_points):
                with cp_cols[j % 8]:
                    if st.button(f"✕  {sec_tc(cp, act_fps)[:8]}", key=f"rm_{cp}"):
                        st.session_state.cut_points.remove(cp)
                        st.rerun()
            if st.button("Clear all cut points"):
                st.session_state.cut_points = []
                st.rerun()
        else:
            st.caption("No cut points set — whole video will be auto-subdivided into 10-second chunks.")

        # ── CHUNK PLAN ────────────────────────────────────────────────────────
        st.markdown('<div class="sec">CHUNK PLAN</div>', unsafe_allow_html=True)

        chunks  = make_plan(act_dur, st.session_state.cut_points, act_fps)
        n_proc  = sum(1 for c in chunks if c["status"] == "wait")
        n_skip  = sum(1 for c in chunks if c["status"] == "skip")

        st.markdown(
            stats_html([("TOTAL", len(chunks)), ("TO PROCESS", n_proc),
                        ("SKIP", n_skip), ("EST. OUTPUT", f"{n_proc * API_MAX_SEC}s")]),
            unsafe_allow_html=True)

        st.markdown(chunk_grid_html(chunks, st.session_state.active_chunk, act_fps),
                    unsafe_allow_html=True)

        st.caption("Click a chunk number to open it in the player:")
        open_cols = st.columns(min(max(len(chunks), 1), 12))
        for ch in chunks:
            idx = ch["index"]
            with open_cols[idx % 12]:
                lbl = "close" if st.session_state.active_chunk == idx else f"{idx+1:04d}"
                if st.button(lbl, key=f"op_{idx}"):
                    st.session_state.active_chunk = (
                        None if st.session_state.active_chunk == idx else idx)
                    st.rerun()

        # ── CHUNK PLAYER ──────────────────────────────────────────────────────
        ac = st.session_state.active_chunk
        if ac is not None and 0 <= ac < len(chunks):
            ch = chunks[ac]
            st.markdown(
                f'<div class="sec">CHUNK PLAYER  —  #{ac+1:04d}  '
                f'{sec_tc(ch["start"], act_fps)} → {sec_tc(ch["end"], act_fps)}'
                f'  ({ch["duration"]:.3f}s)</div>',
                unsafe_allow_html=True)

            if ac not in st.session_state.chunk_previews:
                with st.spinner(f"Extracting chunk {ac+1} for preview…"):
                    try:
                        pb = extract_seg(act_vb, ch["start"], ch["end"], act_fps)
                        st.session_state.chunk_previews[ac] = pb
                    except Exception as e:
                        st.error(f"Extraction failed: {e}")

            if ac in st.session_state.chunk_previews:
                settings   = get_cs(ac, ch["duration"])
                prev_bytes = st.session_state.chunk_previews[ac]

                # Player
                zoom_map = {"1×": 130, "1.5×": 180, "2×": 240, "3×": 320}
                zoom_px  = zoom_map.get(settings.get("zoom", "1×"), 200)
                components.html(
                    player_html(b64(prev_bytes),
                                settings["in_pt"], settings["out_pt"],
                                settings["loop"], zoom_px),
                    height=zoom_px + 60, scrolling=False)
                st.caption("Click video to play/pause.  Click timeline to seek.")

                # Controls below the player — single column
                st.markdown("**In / Out points**  (seconds from chunk start)")
                ni = st.number_input("IN point",  0.0, ch["duration"],
                                     float(settings["in_pt"]),
                                     step=round(1.0 / act_fps, 4),
                                     key=f"in_{ac}", format="%.3f")
                no = st.number_input("OUT point", 0.0, ch["duration"],
                                     float(settings["out_pt"]),
                                     step=round(1.0 / act_fps, 4),
                                     key=f"out_{ac}", format="%.3f")
                if ni > 0.01 or no < ch["duration"] - 0.01:
                    st.caption(f"Effective duration sent to API: {no - ni:.3f}s")

                nl = st.checkbox("Loop between IN and OUT", settings["loop"], key=f"lp_{ac}")
                nz = st.select_slider("Zoom", ["1×", "1.5×", "2×", "3×"],
                                      settings.get("zoom", "1×"), key=f"zm_{ac}")

                st.markdown("**Per-chunk crop override**")
                cren = st.checkbox("Enable crop for this chunk only",
                                   settings.get("crop_en", False), key=f"cren_{ac}")
                nx = ny = nw = nh2 = 0
                if cren:
                    sp  = st.session_state.working_probe or st.session_state.probe
                    pw  = sp["width"]; ph2 = sp["height"]
                    nx  = st.number_input("Crop x", 0, pw - 2,  settings.get("cx", 0),  step=2, key=f"cx_{ac}")
                    ny  = st.number_input("Crop y", 0, ph2 - 2, settings.get("cy", 0),  step=2, key=f"cy_{ac}")
                    nw  = st.number_input("Crop w", 2, pw,      settings.get("cw", pw), step=2, key=f"cw_{ac}")
                    nh2 = st.number_input("Crop h", 2, ph2,     settings.get("ch", ph2),step=2, key=f"ch_{ac}")

                if st.button("Confirm chunk settings", type="primary", key=f"conf_{ac}"):
                    st.session_state.chunk_settings[ac] = dict(
                        in_pt=float(ni), out_pt=float(no), loop=nl, zoom=nz,
                        crop_en=cren, cx=int(nx), cy=int(ny), cw=int(nw), ch=int(nh2))
                    if cren and ac in st.session_state.chunk_previews:
                        del st.session_state.chunk_previews[ac]
                    alog(f"Chunk {ac+1}: IN={ni:.3f} OUT={no:.3f} LOOP={nl} ZOOM={nz}")
                    st.success("Settings saved.")
                    st.rerun()

        # ── COST ─────────────────────────────────────────────────────────────
        st.markdown('<div class="sec">COST ESTIMATE</div>', unsafe_allow_html=True)
        per = (KLING_VID_PRICE if chosen_api == "Kling AI"
               else RUNWAY_VID_PRICE)[vid_model][API_MAX_SEC]
        st.markdown(cost_tbl_html(n_proc, chosen_api, vid_model, API_MAX_SEC),
                    unsafe_allow_html=True)

        # ── GENERATE ─────────────────────────────────────────────────────────
        st.markdown('<div class="sec">GENERATE</div>', unsafe_allow_html=True)

        if not keys_ok:
            st.caption("Enter API credentials in the sidebar.")
        elif not st.session_state.image_bytes:
            st.caption("Upload the subject image above.")
        elif n_proc == 0:
            st.caption("No processable chunks.")
        else:
            est = n_proc * per
            st.caption(
                f"**Mode A — Submit & Exit** submits all {n_proc} chunks to Kling in one pass "
                f"(~{n_proc*2}–{n_proc*4} seconds), then a background thread polls and uploads "
                f"each result to Drive as it finishes. You can close this browser tab immediately "
                f"after submission.  |  "
                f"**Mode B — Wait Here** does the same but streams results live to this page.")

            col_a, col_b = st.columns(2)
            with col_a:
                go_bg = st.button(
                    f"Submit & Exit  ·  {n_proc} clips  ·  {chosen_api}  ·  est. {usd(est)}",
                    type="primary", disabled=st.session_state.processing or not drive_configured(),
                    key="go_bg",
                    help="Submits all tasks to Kling, starts background polling, uploads to Drive. "
                         "Requires Google Drive to be configured in Secrets.")
                if not drive_configured():
                    st.caption("Drive not configured — see setup guide at the bottom of this tab.")
            with col_b:
                go_wait = st.button(
                    f"Wait Here  ·  {n_proc} clips  ·  {chosen_api}  ·  est. {usd(est)}",
                    disabled=st.session_state.processing, key="go_wait",
                    help="Submits and polls inline. Keep this tab open.")

            # ── SHARED EXTRACTION HELPER ──────────────────────────────────────
            def extract_one_chunk(ch, act_vb, act_fps):
                cs2    = st.session_state.chunk_settings.get(ch["index"], {})
                in_pt  = cs2.get("in_pt",  0.0)
                out_pt = cs2.get("out_pt", ch["duration"])
                eff_s  = ch["start"] + in_pt
                eff_e  = ch["start"] + out_pt
                if cs2.get("crop_en") and cs2.get("cw", 0) > 0:
                    seg = extract_seg(act_vb, eff_s, eff_e, act_fps)
                    seg = do_crop(seg, cs2["cx"], cs2["cy"], cs2["cw"], cs2["ch"])
                else:
                    seg = extract_seg(act_vb, eff_s, eff_e, act_fps)
                return fit_chunk_for_api(seg), eff_s, eff_e

            # ── MODE A: SUBMIT & EXIT ─────────────────────────────────────────
            if go_bg:
                st.session_state.processing = True
                prog = st.progress(0, text="Extracting and submitting all chunks…")
                stat = st.empty()
                try:
                    img64    = b64(st.session_state.image_bytes)
                    sid      = st.session_state.session_id
                    task_list = []

                    for ch in chunks:
                        i = ch["index"]
                        if ch["status"] == "skip":
                            task_list.append({**ch, "task_id": None, "url": None,
                                              "drive_link": None, "drive_status": "",
                                              "submitted_at": None, "completed_at": None})
                            continue

                        pct = int((i / len(chunks)) * 90)
                        prog.progress(pct, text=f"Submitting chunk {i+1}/{len(chunks)}…")
                        stat.info(f"Extracting + submitting chunk {i+1}…")

                        try:
                            seg, eff_s, eff_e = extract_one_chunk(ch, act_vb, act_fps)
                            vid64 = b64(seg)
                            alog(f"Chunk {i+1}: {len(seg)//1024}KB")

                            if chosen_api == "Kling AI":
                                tid = kling_motion_transfer(ak, sk, img64, vid64,
                                                            API_MAX_SEC, vid_model, prompt_txt)
                            else:
                                tid = runway_motion(rk, img64, vid64, API_MAX_SEC,
                                                    vid_model, prompt_txt)

                            task_list.append({
                                **ch,
                                "task_id":      tid,
                                "status":       "polling",
                                "url":          None,
                                "drive_link":   None,
                                "drive_status": "",
                                "submitted_at": time.time(),
                                "completed_at": None,
                            })
                            alog(f"Chunk {i+1}: submitted → {tid}")

                        except Exception as e:
                            task_list.append({**ch, "task_id": None, "status": "failed",
                                              "error": str(e), "url": None,
                                              "drive_link": None, "drive_status": "",
                                              "submitted_at": time.time(), "completed_at": None})
                            alog(f"Chunk {i+1}: submit failed — {e}")

                    # Register tasks globally and start background thread
                    with _REG_LOCK:
                        _TASK_REG[sid] = task_list
                    st.session_state.bg_tasks  = task_list
                    st.session_state.bg_active = True
                    # Save API keys for reconnect polling
                    st.session_state.ak_saved  = ak
                    st.session_state.sk_saved  = sk

                    save_task_file(task_list)

                    # Upload task manifest to Drive so user has IDs even if session dies
                    if drive_configured():
                        manifest = json.dumps(task_list, indent=2).encode()
                        drive_upload(manifest, "_task_manifest.json", "application/json")

                    start_background_polling(sid, ak, sk)

                    prog.progress(100, text="All tasks submitted.")
                    n_submitted = sum(1 for t in task_list if t.get("task_id"))
                    stat.success(
                        f"{n_submitted}/{n_proc} tasks submitted to Kling.  "
                        f"Background polling started.  "
                        f"You can now close this tab — results will appear in Drive automatically.  "
                        f"ETA: ~{fmt_dur(n_submitted * KLING_EST_SEC / 3)} "
                        f"(assuming ~3 parallel slots)")

                except Exception as e:
                    stat.error(str(e)); alog(str(e))
                finally:
                    st.session_state.processing = False

            # ── MODE B: WAIT HERE ─────────────────────────────────────────────
            if go_wait:
                for k2, v2 in dict(t1_chunks=[], t1_results=[], t1_zip=None,
                                   t1_csv="", t1_cost=0.0, log=[]).items():
                    st.session_state[k2] = v2
                st.session_state.processing = True
                prog = st.progress(0, text="Preparing…")
                stat = st.empty(); grid = st.empty(); clive = st.empty()
                try:
                    img64 = b64(st.session_state.image_bytes)
                    st.session_state.t1_chunks = chunks
                    cost_now = 0.0; done_n = 0
                    for ch in chunks:
                        i = ch["index"]
                        if ch["status"] == "skip":
                            alog(f"Chunk {i+1}: skip"); continue
                        pct = int(5 + (done_n / max(n_proc, 1)) * 90)
                        prog.progress(pct, text=f"Chunk {i+1}/{len(chunks)}")
                        ch["status"] = "run"
                        grid.markdown(chunk_grid_html(chunks, None, act_fps),
                                      unsafe_allow_html=True)
                        try:
                            stat.info(f"Extracting chunk {i+1}…")
                            seg, eff_s, eff_e = extract_one_chunk(ch, act_vb, act_fps)
                            alog(f"Chunk {i+1}: {len(seg)//1024}KB")
                            vid64 = b64(seg)
                            stat.info(f"Submitting chunk {i+1} to {chosen_api}…")
                            if chosen_api == "Kling AI":
                                tid = kling_motion_transfer(ak, sk, img64, vid64,
                                                            API_MAX_SEC, vid_model, prompt_txt)
                                stat.info(f"Polling chunk {i+1}  (task {tid[:12]}…)")
                                url = k_poll_vid(ak, sk, tid)
                            else:
                                tid = runway_motion(rk, img64, vid64, API_MAX_SEC,
                                                    vid_model, prompt_txt)
                                stat.info(f"Polling chunk {i+1}  (task {tid[:12]}…)")
                                url = runway_poll(rk, tid)
                            ch["output_url"] = url; ch["status"] = "done"
                            cost_now += per; done_n += 1
                            st.session_state.t1_results.append(url)
                            st.session_state.t1_cost = cost_now
                            alog(f"Chunk {i+1}: done")
                            if drive_configured():
                                try:
                                    vid_data = requests.get(url, timeout=120).content
                                    drive_upload(vid_data, ch["filename"], "video/mp4")
                                except: pass
                        except Exception as e:
                            ch["status"] = "fail"
                            alog(f"Chunk {i+1} FAILED: {e}")
                            st.warning(f"Chunk {i+1} failed: {e}")
                        grid.markdown(chunk_grid_html(chunks, None, act_fps),
                                      unsafe_allow_html=True)
                        clive.caption(f"Cost so far: {usd(cost_now)}  ·  {done_n} done  ·  "
                                      f"ETA: {fmt_dur((n_proc-done_n)*KLING_EST_SEC/3)}")
                    done_ch = [c for c in chunks if c["status"] == "done"]
                    if done_ch:
                        prog.progress(97, text="Building ZIP…")
                        try:
                            zb, mc = build_zip(chunks)
                            st.session_state.t1_zip = zb
                            st.session_state.t1_csv = mc
                            if drive_configured():
                                drive_upload(zb, "motion_transfer_output.zip", "application/zip")
                        except Exception as ze:
                            st.warning(f"ZIP failed: {ze}")
                    prog.progress(100, text="Complete")
                    stat.success(f"Done  —  {len(done_ch)}/{n_proc} clips  ·  {usd(cost_now)}")
                except Exception as e:
                    stat.error(str(e)); alog(str(e))
                finally:
                    st.session_state.processing = False

    # ── RESULTS ──────────────────────────────────────────────────────────────
    if st.session_state.t1_results:
        st.markdown('<div class="sec">RESULTS</div>', unsafe_allow_html=True)
        done_ch = [c for c in st.session_state.t1_chunks if c["status"] == "done"]
        fail_ch = [c for c in st.session_state.t1_chunks if c["status"] == "fail"]
        st.markdown(stats_html([("RENDERED", len(done_ch)), ("FAILED", len(fail_ch)),
                                ("COST", usd(st.session_state.t1_cost))]),
                    unsafe_allow_html=True)
        if st.session_state.t1_zip:
            st.download_button(
                "Download ZIP  —  all clips + MANIFEST.csv",
                data=st.session_state.t1_zip,
                file_name="motion_transfer.zip",
                mime="application/zip",
                type="primary")
        if done_ch:
            with st.expander(f"Preview clips ({len(done_ch)})"):
                for c in done_ch:
                    st.caption(f"Chunk {c['index']+1:04d}  "
                               f"{sec_tc(c['start'])} → {sec_tc(c['end'])}  "
                               f"{c['duration']:.3f}s")
                    st.video(c["output_url"])

    with st.expander("Google Drive setup guide — how to connect your personal Drive"):
        st.markdown("""
**Why connect Google Drive?**

When you use *Submit & Exit* mode, the app submits all tasks to Kling then polls
them in the background. As each clip finishes, it is uploaded directly to your
Google Drive folder. You can close this browser tab, shut down your computer, and
come back hours later to find everything waiting in Drive.

**Step-by-step setup (one-time, ~10 minutes)**

**1. Create a Google Cloud project**
- Go to [console.cloud.google.com](https://console.cloud.google.com)
- Click *Select a project* → *New Project* → give it any name → *Create*

**2. Enable the Drive API**
- In your project, go to *APIs & Services* → *Library*
- Search for **Google Drive API** → click it → *Enable*

**3. Create a Service Account**
- Go to *APIs & Services* → *Credentials* → *Create Credentials* → *Service Account*
- Give it any name (e.g. `motion-transfer-bot`) → *Done*
- Click the service account you just created → *Keys* tab → *Add Key* → *Create new key* → **JSON**
- A JSON file downloads to your computer — keep it safe, treat it like a password

**4. Share your Drive folder with the service account**
- In Google Drive, create a new folder (e.g. `Motion Transfer Output`)
- Right-click the folder → *Share* → paste the service account email address
  (it looks like `motion-transfer-bot@your-project.iam.gserviceaccount.com` — found inside the JSON file as `"client_email"`)
- Set permission to **Editor** → *Send*

**5. Get the folder ID**
- Open the folder in Drive — the URL looks like:
  `https://drive.google.com/drive/folders/1aBcDeFgHiJkLmNoPqRsTuVwXyZ`
- The folder ID is the long string at the end: `1aBcDeFgHiJkLmNoPqRsTuVwXyZ`

**6. Add secrets to Streamlit Cloud**
- In your app dashboard on share.streamlit.io → *Settings* → *Secrets*
- Add these two lines:

```toml
GOOGLE_SERVICE_ACCOUNT_JSON = '{"type":"service_account","project_id":"...","private_key_id":"...","private_key":"-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n","client_email":"motion-transfer-bot@...iam.gserviceaccount.com","client_id":"...","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token"}'
GOOGLE_DRIVE_FOLDER_ID = "1aBcDeFgHiJkLmNoPqRsTuVwXyZ"
```

Paste the **entire JSON file contents** as a single line in the first secret.
The sidebar will show *connected* when the credentials are valid.

**What gets saved to Drive?**
- Each rendered clip as soon as it finishes (e.g. `chunk_0001_TC_...mp4`)
- A task manifest JSON (`_task_manifest.json`) right after submission — contains all task IDs so you can recover if the session times out
- The final ZIP with all clips and MANIFEST.csv when you click *Build ZIP*

**Session timeout on Streamlit Community Cloud**
The background polling thread runs as long as the Streamlit server process lives.
On the free tier, sessions time out after approximately 15 minutes of browser inactivity.
For a 30-clip job (~3 min each, 3 parallel), most clips complete in 10 minutes — well within the window.
For longer jobs, the task manifest in Drive contains all task IDs so you can
resume monitoring in a new session.
        """)

    with st.expander("About this tab — PUPPETEER"):
        st.markdown("""
**What it does**

Puppeteer transfers the motion from a guide video onto your static subject image.
Kling AI (or RunwayML Act-One) analyses the pose, trajectory and timing of the
person in the guide video, then animates your image to perform the same movement,
including 3D rotation, jumps and fine gesture.

**Chunk system**

Both APIs generate a maximum of 10 seconds per call. A 5-minute guide video
becomes 30 × 10-second clips processed independently, then packaged as a ZIP
with timecode filenames for import into Avid, Premiere or DaVinci in sequence.

Cut points mark shot boundaries so no hard cut is blended across two API calls.
Any shot longer than 10 seconds is automatically subdivided.

**Chunk player**

Click a chunk number to open it. Set IN and OUT to trim the first or last frames.
Loop plays continuously for close inspection. Zoom enlarges the preview.
Per-chunk crop lets you isolate a different person for each shot if needed.

**Cost — 5-minute video (30 × 10-second clips)**

| API | Quality | Total |
|-----|---------|-------|
| Kling AI | Standard 720p | $2.10 |
| Kling AI | Professional 1080p | $4.20 |
| RunwayML | Gen-3 Alpha Turbo | ~$30.00 |

**Google Drive**

When configured, each clip uploads to Drive immediately after generation,
and the final ZIP is saved there too.
        """)


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 2  ANIMATE
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="sec">SOURCE IMAGE</div>', unsafe_allow_html=True)

    a_img = st.file_uploader(
        "Upload image to animate (JPG, PNG, WEBP)",
        type=["jpg", "jpeg", "png", "webp"], key="a_img")
    if a_img:
        ik = f"{a_img.name}_{a_img.size}"
        if st.session_state.t2_img_fk != ik:
            st.session_state.t2_img_bytes = a_img.read()
            st.session_state.t2_img_fk    = ik
        st.image(a_img, width=400)


    st.markdown('<div class="sec">SETTINGS</div>', unsafe_allow_html=True)

    a_prompt = st.text_area(
        "Animation prompt  —  describe how the figure should move",
        "", height=80,
        placeholder="the figure slowly turns and raises their arm, cinematic lighting")
    a_neg = st.text_input(
        "Negative prompt", "blur, artifacts, distortion, watermark")
    a_dur = st.select_slider(
        "Clip duration", [5, 10], value=10,
        format_func=lambda x: f"{x} seconds")
    a_n = st.select_slider(
        "Number of clips to generate", [1, 2, 4], value=1)

    a_per = KLING_VID_PRICE[vid_model].get(a_dur, 0.07)
    st.markdown(
        stats_html([("DURATION", f"{a_dur}s"), ("CLIPS", a_n),
                    ("COST/CLIP", usd(a_per)), ("TOTAL EST.", usd(a_per * a_n))]),
        unsafe_allow_html=True)
    st.caption("Animate uses Kling AI image-to-video regardless of sidebar API selection.")

    st.markdown('<div class="sec">GENERATE</div>', unsafe_allow_html=True)

    if not keys_ok:
        st.caption("Enter credentials in the sidebar.")
    elif not st.session_state.t2_img_bytes:
        st.caption("Upload an image above.")
    else:
        if st.button(
            f"Animate  {a_n} clip(s)  ·  Kling AI  ·  {vid_model}  ·  est. {usd(a_per * a_n)}",
            type="primary", disabled=st.session_state.processing, key="go2"):
            _ak = ak or S_AK; _sk = sk or S_SK
            if not (_ak and _sk):
                st.error("Kling AI credentials required for this tab.")
            else:
                st.session_state.t2_results = []; st.session_state.t2_cost = 0.0
                st.session_state.processing = True
                prog = st.progress(0); stat = st.empty()
                try:
                    img64 = b64(st.session_state.t2_img_bytes)
                    urls = []; cost_now = 0.0
                    for n2 in range(int(a_n)):
                        prog.progress(int((n2 / a_n) * 90), text=f"Clip {n2+1}/{a_n}…")
                        stat.info(f"Submitting clip {n2+1}…")
                        tid = kling_animate(_ak, _sk, img64, a_prompt, a_neg, a_dur, vid_model)
                        stat.info(f"Polling clip {n2+1}  (task {tid[:12]}…)")
                        url = k_poll_vid(_ak, _sk, tid)
                        urls.append(url); cost_now += a_per
                        alog(f"Animate clip {n2+1}: done")
                    st.session_state.t2_results = urls
                    st.session_state.t2_cost    = cost_now
                    prog.progress(100); stat.success(f"Done  ·  {usd(cost_now)}")
                except Exception as e:
                    stat.error(str(e)); alog(str(e))
                finally:
                    st.session_state.processing = False

    if st.session_state.t2_results:
        st.markdown('<div class="sec">RESULTS</div>', unsafe_allow_html=True)
        st.markdown(stats_html([("CLIPS", len(st.session_state.t2_results)),
                                ("COST",  usd(st.session_state.t2_cost))]),
                    unsafe_allow_html=True)
        for j, url in enumerate(st.session_state.t2_results):
            st.caption(f"Clip {j+1}")
            st.video(url)
            r2 = requests.get(url, timeout=30)
            st.download_button(f"Download clip {j+1}", data=r2.content,
                               file_name=f"animate_{j+1}.mp4", mime="video/mp4",
                               key=f"dl_t2_{j}")

    with st.expander("About this tab — ANIMATE"):
        st.markdown("""
**What it does**

Animate takes a still image and generates a short video using only a text prompt.
There is no motion reference video — you describe the motion in words.

**When to use it**

- Bring a portrait, illustration or product photo to life with a simple description.
- Prototype animation ideas before investing in a full Puppeteer job.
- Social media clips from still photos.

**Prompt tips**

Be specific about movement direction and camera:
*"the figure slowly raises their right arm, camera stays fixed, soft studio lighting."*
Add style words: *cinematic, 4K, sharp detail.*

**Limitations**

Output is a single clip of 5 or 10 seconds. For longer or more precisely controlled
animation, use the Puppeteer tab with a motion reference video.

**Cost**

| Quality | 5s | 10s |
|---------|----|-----|
| Standard 720p | $0.045 | $0.070 |
| Professional 1080p | $0.090 | $0.140 |
        """)


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 3  IMAGINE
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="sec">SETTINGS</div>', unsafe_allow_html=True)

    i_prompt = st.text_area(
        "Image prompt  —  describe what you want to generate",
        "", height=100,
        placeholder="full body portrait, female flamenco dancer, red dress, "
                    "dramatic stage lighting, shallow depth of field, cinematic")
    i_neg = st.text_input(
        "Negative prompt", "blur, text, watermark, artifacts, low quality")
    i_aspect = st.selectbox("Aspect ratio", ASPECT_RATIOS, index=1)
    i_n = st.select_slider("Number of images", [1, 2, 4], value=1)

    st.markdown('<div class="sec">REFERENCE IMAGE  (optional)</div>', unsafe_allow_html=True)
    st.caption("Supply a reference image to guide style or composition.")

    i_ref = st.file_uploader(
        "Reference image (JPG, PNG, WEBP)",
        type=["jpg", "jpeg", "png", "webp"], key="i_ref")
    if i_ref:
        st.image(i_ref, width=200)


    has_ref = bool(i_ref or st.session_state.t3_ref_bytes)
    i_fidelity = 0.5
    if has_ref:
        i_fidelity = st.slider(
            "Reference fidelity  (0 = loosely inspired, 1 = very close)",
            0.0, 1.0, 0.5, 0.05)

    i_price = KLING_IMG_PRICE[img_model][str(i_n)]
    st.markdown(
        stats_html([("MODEL", img_model), ("ASPECT", i_aspect),
                    ("COUNT", i_n),       ("EST. COST", usd(i_price))]),
        unsafe_allow_html=True)

    st.markdown('<div class="sec">GENERATE</div>', unsafe_allow_html=True)

    if not keys_ok:
        st.caption("Enter credentials in the sidebar.")
    elif not i_prompt.strip():
        st.caption("Enter a prompt above.")
    else:
        if st.button(
            f"Generate  {i_n} image(s)  ·  {img_model}  ·  est. {usd(i_price)}",
            type="primary", disabled=st.session_state.processing, key="go3"):
            _ak = ak or S_AK; _sk = sk or S_SK
            if not (_ak and _sk):
                st.error("Kling AI credentials required.")
            else:
                st.session_state.t3_results = []; st.session_state.t3_cost = 0.0
                st.session_state.processing = True
                stat = st.empty(); prog = st.progress(0)
                try:
                    ref_b64 = None
                    if i_ref: ref_b64 = b64(i_ref.read())
                    elif st.session_state.t3_ref_bytes:
                        ref_b64 = b64(st.session_state.t3_ref_bytes)
                    stat.info("Submitting to Kling image generation…"); prog.progress(20)
                    tid = kling_imagine(_ak, _sk, i_prompt, i_neg, i_aspect,
                                       i_n, img_model, ref_b64, i_fidelity)
                    stat.info(f"Polling task {tid[:12]}…"); prog.progress(40)
                    urls = k_poll_img(_ak, _sk, tid)
                    st.session_state.t3_results = urls
                    st.session_state.t3_cost    = i_price
                    prog.progress(100)
                    stat.success(f"Done  ·  {len(urls)} image(s)  ·  {usd(i_price)}")
                    alog(f"Imagine: {len(urls)} images")
                except Exception as e:
                    stat.error(str(e)); alog(str(e))
                finally:
                    st.session_state.processing = False

    if st.session_state.t3_results:
        st.markdown('<div class="sec">RESULTS</div>', unsafe_allow_html=True)
        st.markdown(stats_html([("IMAGES", len(st.session_state.t3_results)),
                                ("COST",   usd(st.session_state.t3_cost))]),
                    unsafe_allow_html=True)
        for j, url in enumerate(st.session_state.t3_results):
            st.image(url, width=600)
            r2 = requests.get(url, timeout=30)
            st.download_button(f"Download image {j+1}", data=r2.content,
                               file_name=f"imagine_{j+1}.jpg", mime="image/jpeg",
                               key=f"dl_t3_{j}")

    with st.expander("About this tab — IMAGINE"):
        st.markdown("""
**What it does**

Imagine generates images from text using Kling AI's Kolors model,
one of the highest-quality text-to-image systems available.

**When to use it**

- Generate character references, background plates, concept art or storyboards.
- Create a subject image for the Puppeteer or Animate tabs.
- Produce social media visuals from a text description.

**Prompt tips**

Be descriptive about subject, lighting, composition and style:
*"full body portrait, female dancer, red dress, dramatic stage lighting,
Sony A7 IV, 85mm, f/1.8, cinematic, sharp detail."*

**Reference image**

Upload a reference to guide style or composition. Fidelity 0 = only loosely
inspired by the reference. Fidelity 1 = very close to it.

**Aspect ratios**

- 16:9 — landscape, video thumbnails
- 9:16 — vertical, social media stories
- 1:1  — square
- 4:3  — standard photo

**Cost**

| Model | 1 image | 4 images |
|-------|---------|----------|
| kolors | ~$0.008 | ~$0.028 |
| kling-v1 | ~$0.005 | ~$0.018 |

Prices are estimates. Verify at klingai.com/pricing.
        """)


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 4  EDIT
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="sec">EDIT MODE</div>', unsafe_allow_html=True)

    edit_mode = st.radio(
        "Edit mode",
        list(KLING_EDIT_PRICE.keys()),
        horizontal=False,
        label_visibility="collapsed")

    st.markdown('<div class="sec">SOURCE IMAGE</div>', unsafe_allow_html=True)

    if edit_mode == "Virtual Try-On":
        st.caption("Upload the PERSON / MODEL photo.")
    else:
        st.caption("Upload the image to edit.")

    e_img = st.file_uploader(
        "Source image (JPG, PNG, WEBP)",
        type=["jpg", "jpeg", "png", "webp"], key="e_img")
    if e_img:
        ek = f"{e_img.name}_{e_img.size}"
        if st.session_state.t4_img_fk != ek:
            st.session_state.t4_img_bytes = e_img.read()
            st.session_state.t4_img_fk    = ek
        st.image(e_img, width=400)


    # Second image for Try-On
    if edit_mode == "Virtual Try-On":
        st.markdown('<div class="sec">GARMENT IMAGE</div>', unsafe_allow_html=True)
        st.caption("Upload the CLOTHING / GARMENT to try on.")
        e_aux = st.file_uploader(
            "Garment image (JPG, PNG, WEBP)",
            type=["jpg", "jpeg", "png", "webp"], key="e_aux")
        if e_aux:
            ak2 = f"{e_aux.name}_{e_aux.size}"
            if st.session_state.t4_aux_fk != ak2:
                st.session_state.t4_aux_bytes = e_aux.read()
                st.session_state.t4_aux_fk    = ak2
            st.image(e_aux, width=400)

    # Edit-specific settings
    st.markdown('<div class="sec">EDIT SETTINGS</div>', unsafe_allow_html=True)
    e_prompt = ""; e_neg = ""; e_fid = 0.5

    if edit_mode == "Inpaint / Repaint":
        e_prompt = st.text_area(
            "Describe what to place in the edited region",
            "", height=80,
            placeholder="a golden crown on the head, photorealistic, matching lighting")
        e_neg = st.text_input("Negative prompt", "blur, artifacts")
        e_fid = st.slider(
            "Fidelity to original structure  (higher = more faithful)",
            0.0, 1.0, 0.7, 0.05)
        st.caption("Describe the change you want. For pixel-precise masking, "
                   "draw a mask in Photoshop/GIMP and upload the masked image as the source.")

    elif edit_mode == "Variation":
        e_prompt = st.text_area(
            "Describe the variation",
            "", height=80,
            placeholder="same composition, oil painting style, warmer tones, impressionist")
        e_neg = st.text_input("Negative prompt", "blur, artifacts")
        e_fid = st.slider(
            "How different from original  (lower = more different)",
            0.0, 1.0, 0.4, 0.05)

    elif edit_mode == "Extend Canvas":
        e_prompt = st.text_area(
            "Describe what to fill in the extended area",
            "", height=80,
            placeholder="continue the background naturally, match existing lighting and perspective")
        e_neg = st.text_input("Negative prompt", "blur, artifacts")
        e_fid = st.slider(
            "Fidelity to original edges",
            0.0, 1.0, 0.8, 0.05)
        e_extend = st.selectbox(
            "Extend direction", ["all sides", "left", "right", "top", "bottom"])
        if e_prompt:
            e_prompt = f"outpaint {e_extend}: {e_prompt}"

    elif edit_mode == "Virtual Try-On":
        st.caption("No additional settings required. "
                   "Upload the person photo and garment photo above, then generate.")

    edit_cost = KLING_EDIT_PRICE.get(edit_mode, 0.012)
    st.markdown(stats_html([("MODE", edit_mode), ("EST. COST", usd(edit_cost))]),
                unsafe_allow_html=True)

    st.markdown('<div class="sec">GENERATE</div>', unsafe_allow_html=True)

    needs_aux = (edit_mode == "Virtual Try-On")
    ready = (bool(st.session_state.t4_img_bytes) and
             (not needs_aux or bool(st.session_state.t4_aux_bytes)))

    if not keys_ok:
        st.caption("Enter credentials in the sidebar.")
    elif not st.session_state.t4_img_bytes:
        st.caption("Upload the source image above.")
    elif needs_aux and not st.session_state.t4_aux_bytes:
        st.caption("Upload the garment image above.")
    else:
        if st.button(
            f"Edit  ·  {edit_mode}  ·  Kling AI  ·  est. {usd(edit_cost)}",
            type="primary", disabled=st.session_state.processing, key="go4"):
            _ak = ak or S_AK; _sk = sk or S_SK
            if not (_ak and _sk):
                st.error("Kling AI credentials required.")
            else:
                st.session_state.t4_results = []; st.session_state.t4_cost = 0.0
                st.session_state.processing = True
                stat = st.empty(); prog = st.progress(0)
                try:
                    img64 = b64(st.session_state.t4_img_bytes)
                    stat.info(f"Submitting {edit_mode}…"); prog.progress(20)
                    if edit_mode == "Virtual Try-On":
                        cloth64 = b64(st.session_state.t4_aux_bytes)
                        tid = kling_tryon(_ak, _sk, img64, cloth64)
                        stat.info(f"Polling try-on task {tid[:12]}…"); prog.progress(40)
                        urls = k_poll_img(_ak, _sk, tid, endpoint="kolors-virtual-try-on")
                    else:
                        tid = kling_edit(_ak, _sk, img64, e_prompt, e_neg, e_fid)
                        stat.info(f"Polling task {tid[:12]}…"); prog.progress(40)
                        urls = k_poll_img(_ak, _sk, tid)
                    st.session_state.t4_results = urls
                    st.session_state.t4_cost    = edit_cost
                    prog.progress(100)
                    stat.success(f"Done  ·  {len(urls)} result(s)  ·  {usd(edit_cost)}")
                    alog(f"Edit ({edit_mode}): {len(urls)} results")
                except Exception as e:
                    stat.error(str(e)); alog(str(e))
                finally:
                    st.session_state.processing = False

    if st.session_state.t4_results:
        st.markdown('<div class="sec">RESULTS</div>', unsafe_allow_html=True)
        st.markdown(stats_html([("RESULTS", len(st.session_state.t4_results)),
                                ("COST",    usd(st.session_state.t4_cost))]),
                    unsafe_allow_html=True)
        for j, url in enumerate(st.session_state.t4_results):
            st.image(url, width=600)
            r2 = requests.get(url, timeout=30)
            st.download_button(f"Download result {j+1}", data=r2.content,
                               file_name=f"edit_{j+1}.jpg", mime="image/jpeg",
                               key=f"dl_t4_{j}")

    with st.expander("About this tab — EDIT"):
        st.markdown("""
**What it does**

The Edit tab modifies an existing image using Kling AI's image editing capabilities.

**Inpaint / Repaint**

Describe a change and the model rewrites that region while preserving the rest.
Examples: change the background, replace clothing, add or remove an object.
Set fidelity high (0.7–0.9) to keep the original structure, lower for more
creative departure. For pixel-precise masking, draw a mask in Photoshop or GIMP
and supply the masked image as the source.

**Variation**

Generate a new version with a stylistic or compositional change.
Useful for exploring alternative colour grades, art styles or lighting.

**Virtual Try-On**

Supply a photo of a person and a photo of a garment.
Kling's Kolors try-on model composites the clothing onto the person with
realistic draping and lighting. Both photos should show the subject clearly
against a simple background.

**Extend Canvas  (outpainting)**

Expand the image beyond its original borders. Choose a direction and describe
what should fill the new area. The model matches existing lighting and perspective.

**API note**

Inpaint, Variation and Extend Canvas use `/v1/images/generations` with an
image reference. Virtual Try-On uses `/v1/images/kolors-virtual-try-on`.
Verify field names at docs.klingai.com.

**Cost**

| Mode | Est. cost |
|------|-----------|
| Inpaint / Repaint | ~$0.012 |
| Variation | ~$0.010 |
| Virtual Try-On | ~$0.025 |
| Extend Canvas | ~$0.012 |
        """)


# ─────────────────────────────────────────────────────────────────────────────
#  FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="margin-top:3rem;color:#1a1730;font-size:0.65rem;'
    'font-family:\'Space Mono\',monospace;">'
    'Motion Transfer Studio v7  ·  docs.klingai.com  ·  docs.dev.runwayml.com'
    '</div>', unsafe_allow_html=True)
