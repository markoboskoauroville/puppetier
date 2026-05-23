# Motion Transfer Studio v9d — Streamlit Cloud / GitHub version
# Secrets loaded from Streamlit Cloud → app Settings → Secrets
# All results logged to Google Sheet + /tmp/klinglog.txt (session-level)

import streamlit as st
import streamlit.components.v1 as components
import requests, time, json, base64, hmac, hashlib, threading, uuid
import math, os, io, zipfile, tempfile, subprocess
from fractions import Fraction

_TASK_REG = {}
_REG_LOCK = threading.Lock()
TASK_FILE = "/tmp/mts_tasks.json"
KLING_LOG = "/tmp/klinglog.txt"

st.set_page_config(page_title="MTS", page_icon=None,
                   layout="wide", initial_sidebar_state="collapsed")

# ── CSS ── black & white, no colors ──────────────────────────────────────────
st.markdown("""
<style>
body { font-family: monospace; }
.stApp { background: #000; color: #ccc; }
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stSidebar"] { display: none !important; }

.sec {
  border-top: 1px solid #222;
  margin: 1.2rem 0 0.7rem;
  padding-top: 0.5rem;
  color: #555;
  font-size: 0.68rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
}

/* tables */
.mt { width:100%; border-collapse:collapse; font-family:monospace; }
.mt th { color:#444; text-align:left; padding:.28rem .55rem;
  border-bottom:1px solid #1a1a1a; font-size:.66rem;
  letter-spacing:.12em; text-transform:uppercase; }
.mt td { color:#999; padding:.22rem .55rem; font-size:.75rem; }
.mt tr:hover td { background:#0a0a0a; }
.mt .hl  { color:#fff; font-weight:700; }
.mt .hlg { color:#bbb; font-weight:700; }
.mt .muted { color:#444; }
.mt .act td { background:#0f0f0f; }
.mt .sep td { background:#0a0a0a; color:#444; font-size:.64rem;
  letter-spacing:.16em; padding:.26rem .55rem; }
.mt .err td { color:#888; }

/* stats */
.srow { display:flex; gap:2rem; margin:.5rem 0 .9rem; flex-wrap:wrap; }
.stat .lbl { color:#444; font-size:.62rem; letter-spacing:.12em;
  text-transform:uppercase; font-family:monospace; }
.stat .val { color:#fff; font-size:1rem; font-weight:700; font-family:monospace; }

/* chunk grid */
.chunk-grid { display:grid;
  grid-template-columns:repeat(auto-fill,minmax(180px,1fr)); gap:5px; margin:.4rem 0; }
.chunk-card { background:#080808; border:1px solid #1a1a1a;
  border-radius:3px; padding:.4rem .6rem; font-family:monospace; }
.chunk-card .cc-id { color:#333; font-size:.66rem; display:block; }
.chunk-card .cc-tc  { color:#555; font-size:.66rem; display:block; }
.chunk-card .cc-st  { font-size:.7rem; font-weight:700; display:block; margin-top:2px; }
.s-wait{color:#444;} .s-run{color:#aaa;} .s-done{color:#fff;}
.s-fail{color:#888;} .s-skip{color:#444;}

/* metrics */
.metrics-box { background:#080808; border:1px solid #1a1a1a;
  border-radius:3px; padding:.9rem 1rem; margin:.5rem 0; font-family:monospace; }
.metrics-box .mhdr { color:#444; font-size:.62rem; letter-spacing:.2em;
  text-transform:uppercase; margin-bottom:.6rem; }
.metrics-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(110px,1fr));
  gap:.5rem .8rem; margin-bottom:.7rem; }
.mg-item .mg-l { color:#444; font-size:.6rem; letter-spacing:.1em; text-transform:uppercase; }
.mg-item .mg-v { color:#fff; font-size:.95rem; font-weight:700; }
.mg-item .mg-v.dim { color:#777; }
.prog-bar { font-size:.7rem; color:#555; margin-bottom:.25rem; font-family:monospace; }
.prog-bar span { color:#fff; }
.eta-line { font-size:.68rem; color:#444; font-family:monospace; }
.eta-line span { color:#aaa; }

/* inputs */
.stTextInput input, .stNumberInput input, .stTextArea textarea {
  background:#080808 !important; border:1px solid #222 !important;
  border-radius:2px !important; color:#ccc !important; font-family:monospace !important; }
.stSelectbox > div > div {
  background:#080808 !important; border:1px solid #222 !important;
  color:#ccc !important; font-family:monospace !important; }
.stSelectbox > div > div > div { color:#ccc !important; }

/* radio */
.stRadio > div { gap:.5rem; }
.stRadio > label { color:#555 !important; font-size:.66rem !important;
  text-transform:uppercase; letter-spacing:.1em; }
.stRadio > div > label > div > p { font-family:monospace !important;
  font-size:.8rem !important; color:#aaa !important; }

/* checkbox */
.stCheckbox > label > div > p { font-family:monospace !important;
  font-size:.78rem !important; color:#aaa !important; }

/* buttons */
.stButton > button {
  background:#000 !important; border:1px solid #333 !important;
  border-radius:2px !important; color:#777 !important;
  font-family:monospace !important; font-size:.76rem !important;
  padding:.28rem .85rem !important; font-weight:400 !important; }
.stButton > button:hover { border-color:#fff !important; color:#fff !important; }
.stButton > button[kind="primary"] {
  background:#fff !important; color:#000 !important;
  border-color:#fff !important; font-weight:700 !important; }
.stButton > button:disabled { opacity:.2 !important; }

.stDownloadButton > button {
  background:#000 !important; border:1px solid #333 !important;
  color:#777 !important; font-family:monospace !important; font-size:.76rem !important; }
.stDownloadButton > button:hover { border-color:#fff !important; color:#fff !important; }

/* sliders */
.stSlider > div > div > div > div { background:#fff !important; }
.stSlider > div > div > div { background:#222 !important; }

/* progress */
.stProgress > div > div { background:#fff !important; }

/* tabs */
.stTabs [data-baseweb="tab-list"] {
  background:#000; border-bottom:1px solid #1a1a1a; gap:0; }
.stTabs [data-baseweb="tab"] {
  color:#444; font-family:monospace !important; font-size:.7rem !important;
  letter-spacing:.12em; text-transform:uppercase; padding:.45rem 1.2rem;
  background:transparent; }
.stTabs [aria-selected="true"] {
  color:#fff !important; border-bottom:1px solid #fff !important;
  background:transparent !important; }

/* labels */
[data-testid="stWidgetLabel"] > div, [data-testid="stWidgetLabel"] p {
  font-family:monospace !important; font-size:.66rem !important;
  color:#555 !important; text-transform:uppercase; letter-spacing:.1em; }

/* file uploader */
[data-testid="stFileUploader"] section {
  background:#080808 !important; border:1px solid #1a1a1a !important;
  border-radius:2px !important; padding:.4rem !important; }
[data-testid="stFileUploader"] section p {
  font-family:monospace !important; font-size:.68rem !important; color:#333 !important; }
[data-testid="stFileUploader"] section small {
  font-family:monospace !important; color:#2a2a2a !important; font-size:.6rem !important; }

/* alerts */
.stAlert { border-radius:2px !important; }
.stAlert p { font-family:monospace !important; font-size:.76rem !important; }

/* expander */
.streamlit-expanderHeader p {
  font-family:monospace !important; font-size:.7rem !important;
  color:#555 !important; text-transform:uppercase; letter-spacing:.12em; }

/* captions */
.stCaption p { font-family:monospace !important; color:#444 !important;
  font-size:.68rem !important; }

/* code blocks */
.stCodeBlock code { font-size:.72rem !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
KLING_BASE   = "https://api.klingai.com"
RUNWAY_BASE  = "https://api.dev.runwayml.com/v1"
API_MAX_SEC  = 10
MIN_CHUNK    = 3
KLING_EST_SEC = 200

KLING_VID_PRICE  = {"std": {5:.045, 10:.070}, "pro": {5:.090, 10:.140}}
RUNWAY_VID_PRICE = {"Gen-3 Alpha Turbo": {5:.50, 10:1.00}, "Gen-3 Alpha": {5:.90, 10:1.80}}
KLING_IMG_PRICE  = {"kolors": {1:.008, 4:.028}, "kling-v1": {1:.005, 4:.018}}
KLING_EDIT_PRICE = {"Inpaint/Repaint":.012, "Variation":.010,
                    "Virtual Try-On":.025, "Extend Canvas":.012}
ASPECT_RATIOS = ["1:1","16:9","9:16","4:3","3:4","3:2","2:3","21:9"]

VIDEO_SIZE_OPTS = ["25%","33%","50%","75%","100%"]
VIDEO_SIZE_PX   = {"25%":160, "33%":210, "50%":300, "75%":440, "100%":580}
VIDEO_SIZE_COL  = {"25%":[1,3], "33%":[1,2], "50%":[1,1], "75%":[3,1], "100%":[10,0]}

SHEET_HEADERS = ["YYYYMMDDHHMM (CRO)","Type","#","Prompt","Model","URL (expires ~30d)","⏱ Proc Time","Notes"]

# ─────────────────────────────────────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
_D = dict(
    # settings (live in session, configurable in Settings tab)
    chosen_api="Kling AI", vid_model="pro", img_model="kolors",
    video_size="25%", style_prompt="",
    # file state
    guide_bytes=None, guide_fk="", probe=None,
    image_bytes=None, image_fk="",
    cut_points=[], crop_en=False,
    crop_x=0, crop_y=0, crop_w=0, crop_h=0,
    working_bytes=None, working_probe=None,
    active_chunk=None, chunk_settings={}, chunk_previews={},
    # tab1 results
    t1_chunks=[], t1_results=[], t1_zip=None, t1_cost=0.0,
    # tab2
    t2_img_bytes=None, t2_img_fk="", t2_results=[], t2_cost=0.0,
    # tab3
    t3_ref_bytes=None, t3_results=[], t3_cost=0.0,
    # tab4
    t4_img_bytes=None, t4_img_fk="",
    t4_aux_bytes=None, t4_aux_fk="",
    t4_results=[], t4_cost=0.0,
    # background
    session_id=str(uuid.uuid4()),
    bg_tasks=[], bg_active=False, bg_resumed=False,
    ak_saved="", sk_saved="",
    # global
    processing=False, log=[],
)
for k, v in _D.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────────────────────
#  UTILITY
# ─────────────────────────────────────────────────────────────────────────────
def b64(d): return base64.b64encode(d).decode()
def sec_tc(s, fps=25):
    s=max(0.,s); h=int(s)//3600; m=(int(s)%3600)//60
    sc=int(s)%60; fr=int(round((s%1)*fps))%max(1,int(fps))
    return f"{h:02d}:{m:02d}:{sc:02d}:{fr:02d}"
def tc_fn(s): return sec_tc(s).replace(":","_")
def usd(v): return f"${v:.3f}" if v<.1 else f"${v:.2f}"
def alog(m): st.session_state.log.append(f"[{time.strftime('%H:%M:%S')}] {m}")

def local_log(message: str):
    """Append to /tmp/klinglog.txt — persists for the session duration on Streamlit Cloud."""
    try:
        with open(KLING_LOG, "a", encoding="utf-8") as _lf:
            _lf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except Exception: pass

def gs(k):
    """Get a secret value from Streamlit Secrets (set in app Settings → Secrets)."""
    try: return st.secrets[k]
    except: return None

def _get_gcp_sa() -> dict | None:
    """Return gcp_service_account dict from Streamlit Secrets."""
    try: return dict(st.secrets["gcp_service_account"])
    except: return None
def parse_t(s):
    s=s.strip(); p=s.split(":")
    if len(p)==1: return float(p[0])
    if len(p)==2: return int(p[0])*60+float(p[1])
    return int(p[0])*3600+int(p[1])*60+float(p[2])
def get_cs(i, dur):
    if i not in st.session_state.chunk_settings:
        st.session_state.chunk_settings[i]=dict(in_pt=0.,out_pt=dur,loop=False,
                                                  zoom=st.session_state.video_size,
                                                  crop_en=False,cx=0,cy=0,cw=0,ch=0)
    return st.session_state.chunk_settings[i]
def fmt_dur(sec):
    sec=max(0,int(sec)); h,r=divmod(sec,3600); m,s=divmod(r,60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

# Apply dynamic video size CSS
_vpct = int(st.session_state.video_size.replace("%",""))
st.markdown(
    f"<style>[data-testid='stVideo']{{max-width:{_vpct}%!important;}}"
    f"[data-testid='stImage'] img{{max-width:{_vpct}%!important;}}</style>",
    unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  KLING JWT
# ─────────────────────────────────────────────────────────────────────────────
def _bu(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
def kling_jwt(ak, sk):
    h=_bu(json.dumps({"alg":"HS256","typ":"JWT"}).encode())
    n=int(time.time())
    p=_bu(json.dumps({"iss":ak,"exp":n+1800,"nbf":n-5}).encode())
    m=f"{h}.{p}"
    s=_bu(hmac.new(sk.encode(),m.encode(),hashlib.sha256).digest())
    return f"{m}.{s}"
def kh(ak,sk):
    return {"Authorization":f"Bearer {kling_jwt(ak,sk)}","Content-Type":"application/json"}

# ─────────────────────────────────────────────────────────────────────────────
#  KLING API
# ─────────────────────────────────────────────────────────────────────────────
def k_post(ak,sk,path,payload):
    r=requests.post(f"{KLING_BASE}{path}",headers=kh(ak,sk),json=payload,timeout=90)
    if not r.ok: raise requests.HTTPError(f"{r.status_code}: {r.text[:300]}",response=r)
    return r.json()

def k_poll_vid(ak,sk,tid,endpoint="image2video",mw=600,status_cb=None,t0=None):
    if t0 is None: t0=time.time()
    dl=time.time()+mw
    while True:
        if time.time()>dl: raise TimeoutError(f"Timeout {tid}")
        if status_cb:
            try: status_cb(tid, time.time()-t0)
            except: pass
        r=requests.get(f"{KLING_BASE}/v1/videos/{endpoint}/{tid}",
                       headers=kh(ak,sk),timeout=30)
        r.raise_for_status(); d=r.json().get("data",{})
        s=d.get("task_status","processing")
        if s=="succeed":
            try: return d["task_result"]["videos"][0]["url"]
            except: raise ValueError(f"No URL: {d}")
        if s in("failed","error"): raise RuntimeError(d.get("task_status_msg","failed"))
        time.sleep(6)

def k_poll_img(ak,sk,tid,endpoint="generations",mw=300,status_cb=None,t0=None):
    if t0 is None: t0=time.time()
    dl=time.time()+mw
    while True:
        if time.time()>dl: raise TimeoutError(f"Timeout {tid}")
        if status_cb:
            try: status_cb(tid, time.time()-t0)
            except: pass
        r=requests.get(f"{KLING_BASE}/v1/images/{endpoint}/{tid}",
                       headers=kh(ak,sk),timeout=30)
        r.raise_for_status(); d=r.json().get("data",{})
        s=d.get("task_status","processing")
        if s=="succeed":
            try: return [img["url"] for img in d["task_result"]["images"]]
            except: raise ValueError(f"No images: {d}")
        if s in("failed","error"): raise RuntimeError(d.get("task_status_msg","failed"))
        time.sleep(5)

def kling_motion_transfer(ak,sk,img_b64,vid_b64,dur,model,prompt):
    mode="pro" if model=="pro" else "std"
    d=k_post(ak,sk,"/v1/videos/image2video",{
        "model_name":"kling-v1-5","image":img_b64,"motion_video":vid_b64,
        "duration":int(dur),"mode":mode,"cfg_scale":0.5,
        "prompt":prompt or "smooth motion, high quality, cinematic",
        "negative_prompt":"blur, artifacts, distortion, watermark"})
    tid=d.get("data",{}).get("task_id","")
    if not tid: raise ValueError(f"No task_id: {d}")
    return tid

def kling_animate(ak,sk,img_b64,prompt,neg,dur,model):
    mode="pro" if model=="pro" else "std"
    d=k_post(ak,sk,"/v1/videos/image2video",{
        "model_name":"kling-v1-5","image":img_b64,"prompt":prompt,
        "negative_prompt":neg or "","duration":int(dur),"mode":mode,"cfg_scale":0.5})
    tid=d.get("data",{}).get("task_id","")
    if not tid: raise ValueError(f"No task_id: {d}")
    return tid

def kling_imagine(ak,sk,prompt,neg,aspect,n,model_name,ref_b64=None,fidelity=0.5):
    payload={"model_name":model_name,"prompt":prompt,
             "negative_prompt":neg or "","n":int(n),"aspect_ratio":aspect}
    if ref_b64:
        payload["image_reference"]=ref_b64; payload["image_fidelity"]=float(fidelity)
    d=k_post(ak,sk,"/v1/images/generations",payload)
    tid=d.get("data",{}).get("task_id","")
    if not tid: raise ValueError(f"No task_id: {d}")
    return tid

def kling_edit(ak,sk,img_b64,prompt,neg,fidelity=0.5):
    d=k_post(ak,sk,"/v1/images/generations",{
        "model_name":"kolors","prompt":prompt,"negative_prompt":neg or "",
        "image_reference":img_b64,"image_fidelity":float(fidelity),"n":1})
    tid=d.get("data",{}).get("task_id","")
    if not tid: raise ValueError(f"No task_id: {d}")
    return tid

def kling_tryon(ak,sk,human_b64,cloth_b64):
    d=k_post(ak,sk,"/v1/images/kolors-virtual-try-on",{
        "model_name":"kolors-virtual-try-on-v1",
        "human_image":human_b64,"cloth_image":cloth_b64})
    tid=d.get("data",{}).get("task_id","")
    if not tid: raise ValueError(f"No task_id: {d}")
    return tid

def kling_list_history(ak,sk,endpoint="image2video",page=1,size=30):
    r=requests.get(f"{KLING_BASE}/v1/videos/{endpoint}",
                   headers=kh(ak,sk),
                   params={"page_num":page,"page_size":size},timeout=30)
    r.raise_for_status()
    d=r.json().get("data",{})
    return d.get("tasks",d.get("list",[]))

# ─────────────────────────────────────────────────────────────────────────────
#  RUNWAYML
# ─────────────────────────────────────────────────────────────────────────────
def rh(k):
    return {"Authorization":f"Bearer {k}","Content-Type":"application/json",
            "X-Runway-Version":"2024-11-06"}

def runway_motion(k,img_b64,vid_b64,dur,model,prompt):
    mime="image/png" if img_b64.startswith("iVBORw0") else "image/jpeg"
    r=requests.post(f"{RUNWAY_BASE}/image_to_video",headers=rh(k),json={
        "model":"gen3a_turbo" if "Turbo" in model else "gen3a",
        "promptImage":f"data:{mime};base64,{img_b64}",
        "promptVideo":f"data:video/mp4;base64,{vid_b64}",
        "duration":int(dur),"ratio":"1280:720","watermark":False,
        "promptText":prompt or "smooth motion, high quality","seed":42},timeout=90)
    if not r.ok: raise requests.HTTPError(f"{r.status_code}: {r.text[:300]}",response=r)
    tid=r.json().get("id","")
    if not tid: raise ValueError(f"No id: {r.json()}")
    return tid

def runway_poll(k,tid,mw=600,status_cb=None,t0=None):
    if t0 is None: t0=time.time()
    dl=time.time()+mw
    while True:
        if time.time()>dl: raise TimeoutError(f"Runway timeout {tid}")
        if status_cb:
            try: status_cb(tid, time.time()-t0)
            except: pass
        r=requests.get(f"{RUNWAY_BASE}/tasks/{tid}",headers=rh(k),timeout=30)
        r.raise_for_status(); d=r.json(); s=d.get("status","PENDING")
        if s=="SUCCEEDED":
            out=d.get("output",[])
            if out: return out[0]
            raise ValueError(f"No output: {d}")
        if s in("FAILED","CANCELLED"): raise RuntimeError(f"{d.get('failure','failed')}")
        time.sleep(6)

# ─────────────────────────────────────────────────────────────────────────────
#  GOOGLE SHEETS
# ─────────────────────────────────────────────────────────────────────────────
def sheets_configured():
    return bool(gs("GOOGLE_SHEET_URL") and _get_gcp_sa())

def _sheets_svc():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    info = _get_gcp_sa()
    if not info: raise ValueError("No gcp_service_account configured")
    creds=service_account.Credentials.from_service_account_info(
        info,scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return build("sheets","v4",credentials=creds,cache_discovery=False)

def _sheet_id():
    url=gs("GOOGLE_SHEET_URL") or ""
    try: return url.split("/spreadsheets/d/")[1].split("/")[0]
    except: return ""

def ensure_sheet_header():
    try:
        svc=_sheets_svc(); sid=_sheet_id()
        ex=svc.spreadsheets().values().get(
            spreadsheetId=sid,range="Sheet1!A1").execute()
        if not ex.get("values"):
            svc.spreadsheets().values().update(
                spreadsheetId=sid,range="Sheet1!A1",
                valueInputOption="RAW",
                body={"values":[SHEET_HEADERS]}).execute()
    except Exception as e: alog(f"Sheet header: {e}")


def sheet_ts() -> str:
    """
    Timestamp as yyyymmddhhmm in Croatian local time (CET/CEST).
    Uses zoneinfo if available (Python 3.9+), otherwise approximates.
    Change "Europe/Zagreb" to any IANA timezone string for other regions.
    """
    try:
        from zoneinfo import ZoneInfo
        from datetime import datetime
        return datetime.now(ZoneInfo("Europe/Zagreb")).strftime("%Y%m%d%H%M")
    except Exception:
        # Fallback: UTC+1 (CET) Nov-Mar, UTC+2 (CEST) Apr-Oct
        utc_secs = time.time()
        month = time.gmtime(utc_secs).tm_mon
        offset = 7200 if 4 <= month <= 10 else 3600
        return time.strftime("%Y%m%d%H%M", time.gmtime(utc_secs + offset))

def log_to_sheet(row:list):
    """Append one row to the Google Sheet results log."""
    try:
        svc=_sheets_svc(); sid=_sheet_id()
        svc.spreadsheets().values().append(
            spreadsheetId=sid,range="Sheet1",
            valueInputOption="USER_ENTERED",
            body={"values":[row]}).execute()
    except Exception as e: alog(f"Sheets: {e}")

def log_url(tab:str, chunk_num:str, prompt:str, model:str, url:str,
            notes:str="", process_secs:float=None):
    ts   = sheet_ts()
    link = f'=HYPERLINK("{url}","Download")'
    proc = fmt_dur(int(process_secs)) if process_secs is not None else ""
    log_to_sheet([ts,tab,chunk_num,prompt,model,link,proc,notes])
    local_log(f"{tab} | #{chunk_num} | {model} | ⏱{proc} | {prompt[:60]} | {url}")

def read_sheet_rows():
    try:
        svc=_sheets_svc(); sid=_sheet_id()
        res=svc.spreadsheets().values().get(
            spreadsheetId=sid,range="Sheet1").execute()
        return res.get("values",[])
    except Exception as e:
        alog(f"Sheet read: {e}"); return []

# ─────────────────────────────────────────────────────────────────────────────
#  FFMPEG
# ─────────────────────────────────────────────────────────────────────────────
def ffok():
    try: subprocess.run(["ffmpeg","-version"],capture_output=True,check=True); return True
    except: return False

def probe_video(path):
    r=subprocess.run(["ffprobe","-v","quiet","-select_streams","v:0",
        "-show_entries","stream=r_frame_rate,nb_frames,width,height",
        "-show_entries","format=duration","-print_format","json",path],
        capture_output=True,text=True,check=True)
    d=json.loads(r.stdout); s=d["streams"][0]
    fps=float(Fraction(s["r_frame_rate"]))
    dur=float(d["format"]["duration"])
    nf=int(s["nb_frames"]) if s.get("nb_frames","N/A")!="N/A" else int(dur*fps)
    return {"duration":dur,"fps":fps,"total_frames":nf,
            "width":int(s.get("width",0)),"height":int(s.get("height",0))}

def do_crop(vb,x,y,w,h):
    x,y=x-x%2,y-y%2; w,h=w-w%2,h-h%2
    with tempfile.TemporaryDirectory() as t:
        i=os.path.join(t,"i.mp4"); o=os.path.join(t,"o.mp4")
        with open(i,"wb") as f: f.write(vb)
        subprocess.run(["ffmpeg","-y","-i",i,"-vf",f"crop={w}:{h}:{x}:{y}",
            "-c:v","libx264","-preset","fast","-crf","18",
            "-pix_fmt","yuv420p","-an",o],capture_output=True,check=True)
        with open(o,"rb") as f: return f.read()

def scene_cuts(vb,thresh=0.35):
    with tempfile.TemporaryDirectory() as t:
        i=os.path.join(t,"i.mp4")
        with open(i,"wb") as f: f.write(vb)
        r=subprocess.run(["ffmpeg","-i",i,
            "-vf",f"select='gt(scene,{thresh})',showinfo",
            "-vsync","vfr","-an","-f","null","-"],
            capture_output=True,text=True,timeout=300)
        cuts=[]
        for line in r.stderr.split("\n"):
            if "pts_time:" in line and "showinfo" in line:
                try:
                    tv=float(line.split("pts_time:")[1].split()[0])
                    if tv>0.25: cuts.append(round(tv,3))
                except: pass
        return sorted(set(cuts))

def fit_chunk_for_api(video_bytes:bytes,max_mb:float=6.0)->bytes:
    limit=int(max_mb*1024*1024)
    if len(video_bytes)<=limit: return video_bytes
    with tempfile.TemporaryDirectory() as t:
        inp=os.path.join(t,"i.mp4"); out=os.path.join(t,"o.mp4")
        with open(inp,"wb") as f: f.write(video_bytes)
        for crf,scale in [(28,None),(30,"1280:720"),(32,"960:540")]:
            vf="scale=trunc(iw/2)*2:trunc(ih/2)*2"
            if scale:
                vf=(f"scale={scale}:force_original_aspect_ratio=decrease,"
                    "scale=trunc(iw/2)*2:trunc(ih/2)*2")
            subprocess.run(["ffmpeg","-y","-i",inp,
                "-c:v","libx264","-preset","fast","-crf",str(crf),
                "-vf",vf,"-an",out],capture_output=True)
            if os.path.exists(out) and os.path.getsize(out)>0:
                with open(out,"rb") as f: result=f.read()
                if len(result)<=limit: return result
                with open(inp,"wb") as f: f.write(result)
        with open(out,"rb") as f: return f.read()

def extract_seg(vb,start,end,fps):
    sf=int(round(start*fps)); ef=int(round(end*fps)); nf=ef-sf
    sts=sf/fps; dur=nf/fps
    with tempfile.TemporaryDirectory() as t:
        i=os.path.join(t,"i.mp4"); o=os.path.join(t,"o.mp4")
        with open(i,"wb") as f: f.write(vb)
        res=subprocess.run(["ffmpeg","-y","-i",i,
            "-ss",f"{sts:.9f}","-t",f"{dur:.9f}",
            "-c:v","libx264","-preset","fast","-crf","18",
            "-pix_fmt","yuv420p","-x264opts","keyint=1:min-keyint=1",
            "-avoid_negative_ts","make_zero","-movflags","+faststart","-an",o],
            capture_output=True)
        if not os.path.exists(o) or os.path.getsize(o)<1024:
            raise RuntimeError(f"Extract failed {start:.2f}→{end:.2f}s")
        with open(o,"rb") as f: return f.read()

# ─────────────────────────────────────────────────────────────────────────────
#  CHUNK PLAN
# ─────────────────────────────────────────────────────────────────────────────
def make_plan(dur,cuts,fps):
    cps=sorted({c for c in cuts if 0.1<c<dur-0.1})
    bounds=[0.]+list(cps)+[dur]
    segs=[]
    for i in range(len(bounds)-1):
        s,e=bounds[i],bounds[i+1]; d=e-s
        if d<0.1: continue
        if d<=API_MAX_SEC: segs.append((s,e,False))
        else:
            n=math.ceil(d/API_MAX_SEC); sub=d/n
            for j in range(n):
                ss=s+j*sub; se=min(s+(j+1)*sub,e)
                segs.append((ss,se,True))
    out=[]
    for i,(s,e,sub) in enumerate(segs):
        d=e-s; nf=int(round(d*fps))
        out.append({"index":i,"start":s,"end":e,"duration":d,"n_frames":nf,
                    "is_sub":sub,"status":"skip" if d<MIN_CHUNK else "wait",
                    "filename":f"chunk_{i+1:04d}_TC_{tc_fn(s)}_to_{tc_fn(e)}.mp4",
                    "output_url":None})
    return out

# ─────────────────────────────────────────────────────────────────────────────
#  PLAYER HTML
# ─────────────────────────────────────────────────────────────────────────────
def player_html(vid_b64,in_pt,out_pt,loop,zoom_px):
    lo="true" if loop else "false"
    return f"""<!DOCTYPE html><html><head><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#000;font-family:monospace;font-size:11px;color:#444}}
#w{{display:flex;flex-direction:column;gap:4px;padding:2px}}
video{{width:100%;max-height:{zoom_px}px;background:#000;display:block;cursor:pointer}}
.tl{{height:3px;background:#1a1a1a;border-radius:1px;position:relative;
  cursor:pointer;margin:1px 0}}
.tlp{{height:100%;background:#555;border-radius:1px;pointer-events:none}}
.mk{{position:absolute;top:-4px;width:2px;height:11px;pointer-events:none}}
.mki{{background:#aaa}}.mko{{background:#555}}.mkh{{background:#fff;width:1px}}
.inf{{display:flex;justify-content:space-between;padding:0 2px;color:#333;font-size:10px}}
.acc{{color:#fff}}.grn{{color:#bbb}}.red{{color:#777}}
</style></head><body><div id="w">
<video id="v" src="data:video/mp4;base64,{vid_b64}" preload="metadata"></video>
<div class="tl" id="tl">
<div class="tlp" id="pl"></div>
<div class="mk mki" id="mi"></div><div class="mk mko" id="mo"></div>
<div class="mk mkh" id="mh"></div></div>
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
#  RENDERERS
# ─────────────────────────────────────────────────────────────────────────────
def stats_html(pairs):
    items="".join(
        f'<div class="stat"><div class="lbl">{l}</div><div class="val">{v}</div></div>'
        for l,v in pairs)
    return f'<div class="srow">{items}</div>'

def chunk_grid_html(chunks,active,fps=25):
    st_map={"wait":("s-wait","QUEUED"),"run":("s-run","RUNNING"),
            "done":("s-done","DONE"),"fail":("s-fail","FAILED"),"skip":("s-skip","SKIP")}
    cards=""
    for ch in chunks:
        i=ch["index"]; cls,lbl=st_map.get(ch["status"],("s-wait","?"))
        ast="border-color:#fff;" if i==active else ""
        cs=st.session_state.chunk_settings.get(i,{})
        note=""
        if cs:
            if cs.get("in_pt",0)>.01 or cs.get("out_pt",ch["duration"])<ch["duration"]-.01:
                note+=" [trim]"
            if cs.get("crop_en"): note+=" [crop]"
        sub=" SUB" if ch["is_sub"] else ""
        cards+=(f'<div class="chunk-card" style="{ast}">'
                f'<span class="cc-id">{i+1:04d}{sub}</span>'
                f'<span class="cc-tc">{sec_tc(ch["start"],fps)} → {sec_tc(ch["end"],fps)}</span>'
                f'<span class="cc-tc">{ch["duration"]:.3f}s · {ch["n_frames"]}fr</span>'
                f'<span class="cc-st {cls}">{lbl}{note}</span></div>')
    return f'<div class="chunk-grid">{cards}</div>'

def cost_tbl_html(n,api,model,dur_key):
    rows='<tr class="sep"><td colspan="5">KLING AI</td></tr>'
    for label,mode in [("Standard","std"),("Professional","pro")]:
        p=KLING_VID_PRICE[mode]
        for d in[5,10]:
            t=n*p[d]; act=(api=="Kling AI" and model==mode and dur_key==d)
            rows+=(f'<tr class="{"act" if act else ""}"><td>Kling</td><td>{label}</td>'
                   f'<td>{n}</td><td>{usd(p[d])}</td>'
                   f'<td class="{"hl" if act else ""}">{usd(t)}</td></tr>')
    rows+='<tr class="sep"><td colspan="5">RUNWAYML (estimated)</td></tr>'
    for m,p in RUNWAY_VID_PRICE.items():
        for d in[5,10]:
            t=n*p[d]; act=(api=="RunwayML" and model==m and dur_key==d)
            rows+=(f'<tr class="{"act" if act else ""}"><td>Runway</td><td>{m}</td>'
                   f'<td>{n}</td><td>{usd(p[d])}</td>'
                   f'<td class="{"hlg" if act else ""}">{usd(t)} *</td></tr>')
    return (f'<table class="mt"><thead><tr><th>API</th><th>MODEL</th>'
            f'<th>CLIPS</th><th>$/CLIP</th><th>TOTAL</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>'
            f'<p style="color:#333;font-size:.62rem;margin-top:.25rem;">'
            f'* runway estimated — verify runwayml.com/pricing</p>')

def calc_eta(tasks):
    done=[t for t in tasks if t.get("status")=="done"]
    polling=[t for t in tasks if t.get("status")=="polling"]
    failed=[t for t in tasks if t.get("status")=="failed"]
    skipped=[t for t in tasks if t.get("status")=="skip"]
    uploaded=sum(1 for t in done if t.get("sheet_logged"))
    timed=[t for t in done if t.get("completed_at") and t.get("submitted_at")]
    avg=sum(t["completed_at"]-t["submitted_at"] for t in timed)/len(timed) if timed else KLING_EST_SEC
    eta=max(0,(len(polling)/max(3,1))*avg)
    sts=[t.get("submitted_at",time.time()) for t in tasks if t.get("submitted_at")]
    elapsed=time.time()-min(sts) if sts else 0
    finish=time.strftime("%H:%M",time.localtime(time.time()+eta))
    pct=int(len(done)/max(len(tasks)-len(skipped),1)*100)
    return {"total":len(tasks),"done":len(done),"failed":len(failed),
            "polling":len(polling),"skipped":len(skipped),"uploaded":uploaded,
            "avg":avg,"eta":eta,"elapsed":elapsed,"finish":finish,"pct":pct}

def metrics_html(m):
    bar_w=int(m["pct"]/10); bar="█"*bar_w+"░"*(10-bar_w)
    return f"""
<div class="metrics-box">
<div class="mhdr">TASK MONITOR</div>
<div class="metrics-grid">
<div class="mg-item"><div class="mg-l">TOTAL</div><div class="mg-v">{m["total"]}</div></div>
<div class="mg-item"><div class="mg-l">DONE</div><div class="mg-v">{m["done"]}</div></div>
<div class="mg-item"><div class="mg-l">QUEUE</div><div class="mg-v dim">{m["polling"]}</div></div>
<div class="mg-item"><div class="mg-l">FAILED</div><div class="mg-v dim">{m["failed"]}</div></div>
<div class="mg-item"><div class="mg-l">IN SHEET</div><div class="mg-v dim">{m["uploaded"]}</div></div>
<div class="mg-item"><div class="mg-l">ELAPSED</div><div class="mg-v dim">{fmt_dur(m["elapsed"])}</div></div>
<div class="mg-item"><div class="mg-l">ETA</div><div class="mg-v">{fmt_dur(m["eta"])}</div></div>
<div class="mg-item"><div class="mg-l">AVG/CLIP</div><div class="mg-v dim">{fmt_dur(m["avg"])}</div></div>
</div>
<div class="prog-bar">PROGRESS  {m["pct"]}%  <span>{bar}</span></div>
<div class="eta-line">Est. completion <span>{m["finish"]}</span> · {m["done"]}/{m["total"]-m["skipped"]} clips
{"· <span>Sheet updated</span>" if m["uploaded"]>0 else ""}</div>
</div>"""

# ─────────────────────────────────────────────────────────────────────────────
#  ZIP
# ─────────────────────────────────────────────────────────────────────────────
def build_zip(chunks):
    buf=io.BytesIO()
    done=[c for c in chunks if c["status"]=="done" and c["output_url"]]
    lines=["chunk,filename,start_tc,end_tc,dur_s,frames,url"]
    with zipfile.ZipFile(buf,"w",zipfile.ZIP_STORED) as zf:
        for ch in done:
            r=requests.get(ch["output_url"],timeout=120); r.raise_for_status()
            zf.writestr(ch["filename"],r.content)
            lines.append(f"{ch['index']+1},{ch['filename']},"
                         f"{sec_tc(ch['start'])},{sec_tc(ch['end'])},"
                         f"{ch['duration']:.4f},{ch['n_frames']},{ch['output_url']}")
        zf.writestr("MANIFEST.csv","\n".join(lines))
    return buf.getvalue()

# ─────────────────────────────────────────────────────────────────────────────
#  TASK STATE PERSISTENCE
# ─────────────────────────────────────────────────────────────────────────────
def save_task_file(tasks):
    try:
        with open(TASK_FILE,"w") as f:
            json.dump({"saved_at":time.time(),"tasks":tasks},f)
    except: pass

def load_task_file():
    try:
        with open(TASK_FILE) as f: d=json.load(f)
        if time.time()-d.get("saved_at",0)<14400: return d["tasks"]
    except: pass
    return None

# ─────────────────────────────────────────────────────────────────────────────
#  BACKGROUND THREAD
# ─────────────────────────────────────────────────────────────────────────────
def _bg_poll_worker(session_id,ak,sk):
    while True:
        with _REG_LOCK:
            tasks=_TASK_REG.get(session_id,[])
        pending=[t for t in tasks if t.get("status")=="polling"]
        if not pending: break
        for task in pending:
            try:
                r=requests.get(
                    f"{KLING_BASE}/v1/videos/image2video/{task['task_id']}",
                    headers=kh(ak,sk),timeout=30)
                r.raise_for_status()
                d=r.json().get("data",{})
                s=d.get("task_status","processing")
                if s=="succeed":
                    try: url=d["task_result"]["videos"][0]["url"]
                    except:
                        task["status"]="failed"; continue
                    task["url"]=url; task["status"]="done"
                    task["completed_at"]=time.time()
                    _bgp=(task["completed_at"]-task["submitted_at"]
                          if task.get("submitted_at") else None)
                    # Log to Google Sheet + klinglog.txt with processing time
                    if sheets_configured():
                        try:
                            log_url("Puppeteer",str(task.get("index","")+1),
                                    task.get("prompt",""),task.get("model",""),url,
                                    f"chunk {task.get('filename','')}",
                                    process_secs=_bgp)
                            task["sheet_logged"]=True
                        except: pass
                elif s in("failed","error"):
                    task["status"]="failed"
                    task["error"]=d.get("task_status_msg","failed")
            except: pass
        save_task_file(tasks)
        time.sleep(10)
    with _REG_LOCK:
        _TASK_REG[session_id+"_done"]=True

def start_bg_poll(session_id,ak,sk):
    t=threading.Thread(target=_bg_poll_worker,args=(session_id,ak,sk),
                       daemon=True,name=f"poll_{session_id[:8]}")
    t.start(); return t

# ─────────────────────────────────────────────────────────────────────────────
#  LOAD SECRETS (read once at module level)
# ─────────────────────────────────────────────────────────────────────────────
S_AK=gs("KLING_ACCESS_KEY"); S_SK=gs("KLING_SECRET_KEY")
# Runway is optional
S_RW=gs("RUNWAY_API_KEY")

# Active API keys — prefer secrets, fallback to settings tab inputs
def active_ak(): return S_AK or st.session_state.get("s_ak","")
def active_sk(): return S_SK or st.session_state.get("s_sk","")
def active_rk(): return S_RW or st.session_state.get("s_rw","")
def keys_ok():
    if st.session_state.chosen_api=="Kling AI":
        return bool(active_ak() and active_sk())
    return bool(active_rk())

# ─────────────────────────────────────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div style="color:#333;font-size:.62rem;font-family:monospace;'
            'letter-spacing:.2em;text-transform:uppercase;margin-bottom:.5rem;">'
            'MTS · Kling AI · RunwayML</div>', unsafe_allow_html=True)

if not ffok():
    st.error("ffmpeg not found — add 'ffmpeg' to packages.txt"); st.stop()

# ─────────────────────────────────────────────────────────────────────────────
#  TABS
# ─────────────────────────────────────────────────────────────────────────────
tab1,tab2,tab3,tab4,tab5,tab6 = st.tabs(["PUPPETEER","ANIMATE","IMAGINE","EDIT","HISTORY","SETTINGS"])

# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 5 — HISTORY
# ═══════════════════════════════════════════════════════════════════════════════
with tab5:

    st.markdown('<div class="sec">PULL FROM KLING</div>',unsafe_allow_html=True)
    st.caption("Kling keeps results ~30 days. Pull here to recover work "
               "after crashes, session loss, or expired browser tabs.")

    h_type = st.radio(
        "Task type",
        ["video · image2video","video · text2video","image · generations"],
        horizontal=False, label_visibility="collapsed")
    type_map = {
        "video · image2video": ("video","image2video"),
        "video · text2video":  ("video","text2video"),
        "image · generations": ("image","generations"),
    }
    h_media, h_endpoint = type_map[h_type]

    hc1, hc2 = st.columns([1,3])
    with hc1:
        h_page = st.number_input("Page", 1, 50, 1)
    with hc2:
        h_size = st.radio("Per page",["10","20","30","50"],
                          horizontal=True, label_visibility="collapsed", index=2)

    col_pull, col_log = st.columns(2)
    with col_pull:
        do_pull = st.button("Pull from Kling", type="primary", key="h_pull")
    with col_log:
        do_log_all = st.button("Log all to Sheet", key="h_log_all",
                               disabled="h_pulled_tasks" not in st.session_state)

    if do_pull:
        if not (active_ak() and active_sk()):
            st.error("Kling credentials required — set them in Settings.")
        else:
            with st.spinner("Fetching…"):
                try:
                    base_path = (f"/v1/videos/{h_endpoint}"
                                 if h_media == "video"
                                 else f"/v1/images/{h_endpoint}")
                    r = requests.get(
                        f"{KLING_BASE}{base_path}",
                        headers=kh(active_ak(), active_sk()),
                        params={"page_num": h_page, "page_size": int(h_size)},
                        timeout=30)
                    r.raise_for_status()
                    raw  = r.json()
                    data = raw.get("data", raw)   # some versions return list directly
                    if isinstance(data, list):
                        tasks = data
                    elif isinstance(data, dict):
                        tasks = (data.get("tasks") or data.get("list") or
                                 data.get("data") or [])
                    else:
                        tasks = []
                    st.session_state.h_pulled_tasks = tasks
                    st.session_state.h_pulled_type  = h_type
                    alog(f"Pulled {len(tasks)} tasks ({h_type} p{h_page})")
                except Exception as e:
                    st.error(f"Pull failed: {e}")

    if "h_pulled_tasks" in st.session_state and st.session_state.h_pulled_tasks:
        tasks = st.session_state.h_pulled_tasks
        rows  = ""
        for t in tasks:
            status = t.get("task_status","?")
            created = t.get("created_at","")
            if isinstance(created,(int,float)):
                utc_secs = created / 1000
                month    = time.gmtime(utc_secs).tm_mon
                offset   = 7200 if 4 <= month <= 10 else 3600
                created  = time.strftime("%Y%m%d%H%M", time.gmtime(utc_secs + offset))
            tid = t.get("task_id","")
            tid_disp = (tid[:14]+"…") if len(tid)>14 else tid
            url = ""
            try:
                res = t.get("task_result",{})
                if res.get("videos"):   url = res["videos"][0].get("url","")
                elif res.get("images"): url = res["images"][0].get("url","")
            except: pass
            prompt_txt = (t.get("task_input",{}).get("prompt","") or
                          t.get("prompt",""))[:40]
            lnk = (f'<a href="{url}" target="_blank" style="color:#ccc;font-weight:700;">↗</a>'
                   if url else "—")
            sc  = "hl" if status=="succeed" else ("err" if "fail" in status else "muted")
            rows += (
                f'<tr><td class="muted">{created}</td>'
                f'<td class="muted" style="font-size:.64rem;">{tid_disp}</td>'
                f'<td class="{sc}">{status}</td>'
                f'<td class="muted" style="max-width:160px;overflow:hidden;'
                f'white-space:nowrap;text-overflow:ellipsis;">{prompt_txt}</td>'
                f'<td>{lnk}</td></tr>'
            )
        st.markdown(
            '<table class="mt"><thead><tr>'
            '<th>CREATED (CRO)</th><th>TASK ID</th>'
            '<th>STATUS</th><th>PROMPT</th><th>LINK</th>'
            '</tr></thead><tbody>' + rows + '</tbody></table>',
            unsafe_allow_html=True)
        st.caption(f"{len(tasks)} tasks · page {h_page} · ~30-day storage")

        if do_log_all:
            if not sheets_configured():
                st.warning("Sheet not configured — check Settings.")
            else:
                logged = 0; skipped = 0
                with st.spinner("Logging to Sheet…"):
                    ensure_sheet_header()
                    for t in tasks:
                        url = ""
                        try:
                            res = t.get("task_result",{})
                            if res.get("videos"):   url = res["videos"][0].get("url","")
                            elif res.get("images"): url = res["images"][0].get("url","")
                        except: pass
                        if url and t.get("task_status") == "succeed":
                            try:
                                prompt_txt = (t.get("task_input",{}).get("prompt","") or
                                              t.get("prompt","") or "")[:80]
                                log_url(st.session_state.h_pulled_type,
                                        t.get("task_id","")[:12],
                                        prompt_txt, "kling-pull", url,
                                        "from Kling history")
                                logged += 1
                            except: skipped += 1
                        else: skipped += 1
                st.success(f"Logged {logged} · skipped {skipped}")

    # ── CREDITS & USAGE ───────────────────────────────────────────────────────
    st.markdown('<div class="sec">CREDITS & USAGE</div>', unsafe_allow_html=True)

    if st.button("Check Kling balance", key="check_balance"):
        if not (active_ak() and active_sk()):
            st.error("Kling credentials required.")
        else:
            with st.spinner("Querying Kling account endpoints…"):
                results = {}
                # Try every known and speculative endpoint
                for path in ["/v1/account/costs",
                             "/v1/account/balance",
                             "/v1/account/info",
                             "/v1/user/balance",
                             "/v1/user/info",
                             "/account/costs",
                             "/account/balance"]:
                    try:
                        r = requests.get(f"{KLING_BASE}{path}",
                                         headers=kh(active_ak(), active_sk()),
                                         timeout=8)
                        results[path] = {"status": r.status_code, "body": r.json()}
                    except Exception as _be:
                        results[path] = {"status": "error", "body": str(_be)}

                # Show all responses so user can see what Kling returns
                any_ok = any(v.get("status") == 200 for v in results.values())
                if any_ok:
                    for path, res in results.items():
                        if res.get("status") == 200:
                            st.caption(f"✓ {path}")
                            st.json(res["body"])
                else:
                    st.warning(
                        "Kling AI does not currently expose account balance "
                        "via the API key system. Check your credit balance at:\n\n"
                        "**klingai.com → top right avatar → Credits / Billing**\n\n"
                        "Raw responses from all tried endpoints:")
                    rows = ""
                    for path, res in results.items():
                        code = res.get("status","?")
                        rows += f"<tr><td style='color:#555'>{path}</td><td style='color:#777'>{code}</td></tr>"
                    st.markdown(
                        '<table class="mt"><thead><tr><th>ENDPOINT</th><th>STATUS</th></tr></thead>'
                        f'<tbody>{rows}</tbody></table>', unsafe_allow_html=True)

    with st.expander("Kling storage & pricing reference"):
        st.markdown("""
**Storage**  Videos kept ~30 days from generation date. Download before expiry.
Task IDs remain queryable — Pull tab can fetch a fresh URL within the 30-day window.

**Credits (approximate)**

| Operation | Duration | Mode | Cost |
|---|---|---|---|
| image2video | 5s | Standard | $0.045 |
| image2video | 10s | Standard | $0.070 |
| image2video | 5s | Professional | $0.090 |
| image2video | 10s | Professional | $0.140 |
| Image (Kolors) | — | — | ~$0.008/image |
| Virtual Try-On | — | — | ~$0.025 |

Top up at klingai.com → Developer Console → Credits.
        """)

# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 6 — SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.markdown('<div class="sec">API ENGINE</div>',unsafe_allow_html=True)
    st.session_state.chosen_api=st.radio(
        "API",["Kling AI","RunwayML"],
        horizontal=True,label_visibility="collapsed",
        index=0 if st.session_state.chosen_api=="Kling AI" else 1)

    st.markdown('<div class="sec">KLING CREDENTIALS</div>',unsafe_allow_html=True)
    if S_AK and S_SK:
        st.caption(f"Loaded from Secrets · Access Key: {S_AK[:8]}…")
    else:
        st.session_state.s_ak=st.text_input("Kling Access Key",
            st.session_state.get("s_ak",""),type="password")
        st.session_state.s_sk=st.text_input("Kling Secret Key",
            st.session_state.get("s_sk",""),type="password")

    st.markdown('<div class="sec">RUNWAY CREDENTIALS (optional)</div>',unsafe_allow_html=True)
    if S_RW:
        st.caption("RunwayML key loaded from Secrets.")
    else:
        st.session_state.s_rw=st.text_input("RunwayML API Key",
            st.session_state.get("s_rw",""),type="password")

    st.markdown('<div class="sec">VIDEO MODEL</div>',unsafe_allow_html=True)
    _vm=st.radio("Video Model",["Standard","Professional"],horizontal=True,
                 label_visibility="collapsed",
                 index=1 if st.session_state.vid_model=="pro" else 0)
    st.session_state.vid_model="pro" if _vm=="Professional" else "std"

    st.markdown('<div class="sec">IMAGE MODEL</div>',unsafe_allow_html=True)
    st.session_state.img_model=st.radio(
        "Image Model",["kolors","kling-v1"],horizontal=True,
        label_visibility="collapsed",
        index=0 if st.session_state.img_model=="kolors" else 1)

    st.markdown('<div class="sec">VIDEO PREVIEW SIZE</div>',unsafe_allow_html=True)
    st.session_state.video_size=st.radio(
        "Preview Size",VIDEO_SIZE_OPTS,horizontal=True,
        label_visibility="collapsed",
        index=VIDEO_SIZE_OPTS.index(st.session_state.video_size))
    st.caption("Applied to all video and image previews in the app.")

    st.markdown('<div class="sec">GLOBAL STYLE PROMPT</div>',unsafe_allow_html=True)
    st.session_state.style_prompt=st.text_input(
        "Style prompt","",
        placeholder="cinematic, sharp detail, high quality",
        label_visibility="collapsed")

    # ── GOOGLE SHEET ──────────────────────────────────────────────────────────
    st.markdown('<div class="sec">GOOGLE SHEET — RESULTS LOG</div>',unsafe_allow_html=True)

    sheet_url=gs("GOOGLE_SHEET_URL") or ""
    if sheet_url:
        st.caption(f"Sheet: {sheet_url[:60]}…")
        if sheets_configured():
            if st.button("Test Sheet connection"):
                with st.spinner("Testing…"):
                    try:
                        ensure_sheet_header()
                        rows=read_sheet_rows()
                        st.success(f"Connected — {max(0,len(rows)-1)} result rows in sheet.")
                    except Exception as e: st.error(f"Failed: {e}")
            if st.button("Open Sheet"):
                st.markdown(f'<a href="{sheet_url}" target="_blank">'
                            f'Open in Google Sheets ↗</a>',unsafe_allow_html=True)
    else:
        st.caption("Add GOOGLE_SHEET_URL to Streamlit Secrets.")

    with st.expander("Sheet setup guide"):
        st.markdown("""
**What the Sheet does**

Every generated video URL is logged as a row with timestamp, type, prompt, model
and a clickable Download link. Kling stores videos for approximately **30 days**.
The Sheet is your permanent record — click the link to download before they expire.

**To set up:**

1. Create a new Google Sheet (or use your existing one at the URL in secrets).
2. Share it with the service account email:
   `marko-sheets@marko-transcribe.iam.gserviceaccount.com` — give **Editor** access.
3. The app automatically creates headers on first log.
4. Test the connection in this tab.

**Secrets needed (already set in your Streamlit Secrets):**
```
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/..."
[gcp_service_account]   ← the marko-sheets service account block
```

**Kling video storage**

Generated videos are stored by Kling for approximately **30 days** from creation.
The task record (task_id) is also available for about 30 days — you can re-query
the task to get a fresh URL if the original has expired. Download anything you
want to keep before the 30-day window closes.
        """)

    # ── KLING HISTORY PULL ────────────────────────────────────────────────────
    st.markdown('<div class="sec">KLING HISTORY — PULL RECENT TASKS</div>',unsafe_allow_html=True)
    st.caption("Pull your recent Kling tasks. Note: Kling stores results for ~30 days.")

    h_type=st.radio("Task type",["image2video","text2video"],horizontal=True,
                    label_visibility="collapsed")
    h_page=st.number_input("Page",1,20,1,label_visibility="visible")

    if st.button("Pull from Kling"):
        if not (active_ak() and active_sk()):
            st.error("Kling credentials required.")
        else:
            with st.spinner("Fetching…"):
                try:
                    tasks=kling_list_history(active_ak(),active_sk(),h_type,h_page)
                    if not tasks:
                        st.info("No tasks found for this page.")
                    else:
                        rows=""
                        for t in tasks:
                            status=t.get("task_status","?")
                            created=t.get("created_at","")
                            if isinstance(created,(int,float)):
                                created=time.strftime("%Y-%m-%d %H:%M",time.localtime(created/1000))
                            tid=t.get("task_id","")[:14]+"…"
                            try:
                                url=t.get("task_result",{}).get("videos",[{}])[0].get("url","")
                            except: url=""
                            link=f'<a href="{url}" target="_blank" style="color:#aaa">↗ Download</a>' if url else ""
                            rows+=(f'<tr><td class="muted">{created}</td>'
                                   f'<td class="muted">{tid}</td>'
                                   f'<td class="{"hl" if status=="succeed" else "muted"}">'
                                   f'{status}</td><td>{link}</td></tr>')
                        st.markdown(
                            f'<table class="mt"><thead><tr>'
                            f'<th>CREATED</th><th>TASK ID</th>'
                            f'<th>STATUS</th><th>LINK</th>'
                            f'</tr></thead><tbody>{rows}</tbody></table>',
                            unsafe_allow_html=True)
                        st.caption(f"Showing {len(tasks)} tasks from page {h_page}. "
                                   f"Kling keeps results ~30 days.")
                except Exception as e: st.error(f"Failed: {e}")

    # ── SHEET VIEWER ──────────────────────────────────────────────────────────
    st.markdown('<div class="sec">RECENT RESULTS FROM SHEET</div>',unsafe_allow_html=True)
    if st.button("Load sheet results"):
        if not sheets_configured():
            st.warning("Sheet not configured.")
        else:
            with st.spinner("Loading…"):
                rows=read_sheet_rows()
                if len(rows)<=1:
                    st.info("Sheet is empty.")
                else:
                    tbl_rows=""
                    for row in reversed(rows[1:][-30:]):  # last 30, newest first
                        while len(row)<7: row.append("")
                        ts,typ,num,prompt,model,url_cell,notes=row[:7]
                        # url_cell may be a HYPERLINK formula or plain URL
                        if url_cell.startswith("=HYPERLINK"):
                            try: raw_url=url_cell.split('"')[1]
                            except: raw_url=url_cell
                        else: raw_url=url_cell
                        link=(f'<a href="{raw_url}" target="_blank" '
                              f'style="color:#aaa;">↗</a>' if raw_url else "")
                        tbl_rows+=(f'<tr><td class="muted">{ts}</td>'
                                   f'<td class="muted">{typ}</td>'
                                   f'<td class="muted">{num}</td>'
                                   f'<td style="max-width:180px;overflow:hidden;'
                                   f'text-overflow:ellipsis;white-space:nowrap;">'
                                   f'{prompt[:40]}</td>'
                                   f'<td class="muted">{model}</td>'
                                   f'<td>{link}</td></tr>')
                    st.markdown(
                        f'<table class="mt"><thead><tr>'
                        f'<th>TIME</th><th>TYPE</th><th>#</th>'
                        f'<th>PROMPT</th><th>MODEL</th><th>LINK</th>'
                        f'</tr></thead><tbody>{tbl_rows}</tbody></table>',
                        unsafe_allow_html=True)

    # ── LOG ───────────────────────────────────────────────────────────────────
    if st.session_state.log:
        st.markdown('<div class="sec">SESSION LOG</div>',unsafe_allow_html=True)
        with st.expander("Show log",expanded=False):
            st.code("\n".join(st.session_state.log[-60:]),language=None)


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS used across tabs
# ═══════════════════════════════════════════════════════════════════════════════
_vpct2=int(st.session_state.video_size.replace("%",""))

def show_video(file_or_bytes,key_sfx=""):
    """Show video constrained to the selected preview size."""
    ratio=VIDEO_SIZE_COL.get(st.session_state.video_size,[1,3])
    if ratio[1]>0:
        c,_=st.columns(ratio)
        with c: st.video(file_or_bytes)
    else:
        st.video(file_or_bytes)

def show_image(img,width_ratio=None):
    """Show image at preview size."""
    w=int(600*_vpct2/100)
    st.image(img,width=w)

def _prompt(): return st.session_state.style_prompt

# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 1 — PUPPETEER
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:

    # ── TASK MONITOR ─────────────────────────────────────────────────────────
    sid=st.session_state.session_id
    if not st.session_state.bg_tasks and not st.session_state.bg_resumed:
        saved=load_task_file()
        if saved and any(t.get("status")=="polling" for t in saved):
            st.session_state.bg_tasks=saved; st.session_state.bg_active=True
            st.session_state.bg_resumed=True
            with _REG_LOCK: _TASK_REG[sid]=saved
            if st.session_state.ak_saved and st.session_state.sk_saved:
                start_bg_poll(sid,st.session_state.ak_saved,st.session_state.sk_saved)

    bg_tasks=_TASK_REG.get(sid,st.session_state.bg_tasks)
    if bg_tasks:
        m=calc_eta(bg_tasks)
        st.markdown(metrics_html(m),unsafe_allow_html=True)
        if m["polling"]>0:
            st.caption("Background polling active. Completed clips logged to Sheet automatically.")
            time.sleep(12); st.rerun()
        else:
            if m["done"]>0:
                st.success(f"{m['done']} clips done · {m['failed']} failed · {m['uploaded']} logged to Sheet")
            st.session_state.bg_active=False

        rows=""
        for t in bg_tasks:
            if t.get("status")=="skip": continue
            sc={"done":"hl","failed":"err","polling":"muted"}.get(t.get("status",""),"muted")
            elapsed_s=""
            if t.get("completed_at") and t.get("submitted_at"):
                elapsed_s=f'{int(t["completed_at"]-t["submitted_at"])}s'
            url=t.get("url","")
            lnk=(f'<a href="{url}" target="_blank" style="color:#aaa">↗</a>'
                 if url else "")
            rows+=(f'<tr><td class="muted">{t["index"]+1:04d}</td>'
                   f'<td class="{sc}">{t.get("status","?").upper()}</td>'
                   f'<td class="muted">{elapsed_s}</td><td>{lnk}</td></tr>')
        st.markdown(
            f'<table class="mt"><thead><tr><th>#</th><th>STATUS</th>'
            f'<th>TIME</th><th>LINK</th></tr></thead><tbody>{rows}</tbody></table>',
            unsafe_allow_html=True)

        done_tasks=[t for t in bg_tasks if t.get("status")=="done" and t.get("url")]
        if done_tasks and st.button(f"Build ZIP ({len(done_tasks)} clips)",key="bg_zip"):
            with st.spinner("Building ZIP…"):
                buf=io.BytesIO()
                lns=["chunk,filename,url"]
                with zipfile.ZipFile(buf,"w",zipfile.ZIP_STORED) as zf:
                    for t in done_tasks:
                        r2=requests.get(t["url"],timeout=120); r2.raise_for_status()
                        zf.writestr(t["filename"],r2.content)
                        lns.append(f"{t['index']+1},{t['filename']},{t['url']}")
                    zf.writestr("MANIFEST.csv","\n".join(lns))
                st.download_button("Download ZIP",data=buf.getvalue(),
                                   file_name="motion_transfer.zip",
                                   mime="application/zip",type="primary")
        st.markdown('<div class="sec">NEW JOB</div>',unsafe_allow_html=True)

    # ── VIDEO ─────────────────────────────────────────────────────────────────
    st.markdown('<div class="sec">VIDEO</div>',unsafe_allow_html=True)
    gf=st.file_uploader("Video",type=["mp4","mov","webm","avi"],
                        key="gv",label_visibility="collapsed")
    if gf:
        fk=f"{gf.name}_{gf.size}"
        if st.session_state.guide_fk!=fk:
            st.session_state.guide_bytes=gf.read(); st.session_state.guide_fk=fk
            st.session_state.cut_points=[]; st.session_state.working_bytes=None
            st.session_state.working_probe=None; st.session_state.crop_en=False
            st.session_state.active_chunk=None
            st.session_state.chunk_settings={}; st.session_state.chunk_previews={}
            with tempfile.TemporaryDirectory() as t:
                p=os.path.join(t,"i.mp4")
                with open(p,"wb") as f: f.write(st.session_state.guide_bytes)
                try: st.session_state.probe=probe_video(p)
                except Exception as e: st.warning(f"Probe: {e}")
        show_video(gf,key_sfx="gv")
        if st.session_state.probe:
            pr=st.session_state.probe
            st.caption(f"{pr['duration']:.2f}s · {pr['fps']:.3f}fps · {pr['width']}×{pr['height']}px")

    # ── STILL ─────────────────────────────────────────────────────────────────
    st.markdown('<div class="sec">STILL</div>',unsafe_allow_html=True)
    imf=st.file_uploader("Still",type=["jpg","jpeg","png","webp"],
                         key="si",label_visibility="collapsed")
    if imf:
        ik=f"{imf.name}_{imf.size}"
        if st.session_state.image_fk!=ik:
            st.session_state.image_bytes=imf.read(); st.session_state.image_fk=ik
        show_image(imf)

    # ── SETUP (only when guide uploaded) ─────────────────────────────────────
    if st.session_state.guide_bytes and st.session_state.probe:
        pr=st.session_state.probe
        vdur=pr["duration"]; vfps=pr["fps"]; vw=pr["width"]; vh=pr["height"]
        act_vb=st.session_state.working_bytes or st.session_state.guide_bytes
        act_pr=st.session_state.working_probe or st.session_state.probe
        act_dur=act_pr["duration"]; act_fps=act_pr["fps"]

        # ── CROP ────────────────────────────────────────────────────────────
        st.markdown('<div class="sec">CROP</div>',unsafe_allow_html=True)
        with st.expander("Configure crop" + (" (ACTIVE)" if st.session_state.crop_en else ""),
                         expanded=False):
            st.caption(f"Source: {vw}×{vh}px")
            cx=st.number_input("x",0,max(vw-2,0),st.session_state.crop_x,step=2)
            cy=st.number_input("y",0,max(vh-2,0),st.session_state.crop_y,step=2)
            cw=st.number_input("w",2,vw,vw if not st.session_state.crop_en else st.session_state.crop_w,step=2)
            ch=st.number_input("h",2,vh,vh if not st.session_state.crop_en else st.session_state.crop_h,step=2)
            noop=(cx==0 and cy==0 and cw==vw and ch==vh)
            if not noop: st.caption(f"Crop to {cw}×{ch} at ({cx},{cy})")
            if st.button("Apply",disabled=noop,key="do_crop"):
                with st.spinner("Cropping…"):
                    try:
                        cr=do_crop(st.session_state.guide_bytes,int(cx),int(cy),int(cw),int(ch))
                        with tempfile.TemporaryDirectory() as t:
                            p=os.path.join(t,"c.mp4")
                            with open(p,"wb") as f: f.write(cr)
                            np2=probe_video(p)
                        st.session_state.working_bytes=cr; st.session_state.working_probe=np2
                        st.session_state.crop_en=True
                        st.session_state.crop_x=int(cx); st.session_state.crop_y=int(cy)
                        st.session_state.crop_w=int(cw); st.session_state.crop_h=int(ch)
                        st.session_state.chunk_previews={}
                        act_vb=cr; act_pr=np2; act_dur=np2["duration"]; act_fps=np2["fps"]
                        alog(f"Crop {cw}×{ch} at ({cx},{cy})"); st.rerun()
                    except Exception as e: st.error(f"Crop failed: {e}")
            if st.session_state.crop_en:
                np2=st.session_state.working_probe
                st.caption(f"Active: {np2['width']}×{np2['height']}px")
                if st.button("Reset",key="rst_crop"):
                    st.session_state.working_bytes=None; st.session_state.working_probe=None
                    st.session_state.crop_en=False; st.session_state.chunk_previews={}; st.rerun()

        # ── CUT POINTS ──────────────────────────────────────────────────────
        st.markdown('<div class="sec">CUT POINTS</div>',unsafe_allow_html=True)

        thr_col,det_col=st.columns([3,1])
        with thr_col:
            thr=st.radio("Sensitivity",["0.20","0.35","0.50"],horizontal=True,
                         label_visibility="collapsed",index=1)
            thr_f=float(thr)
        with det_col:
            if st.button("Auto-detect",key="det"):
                with st.spinner("Detecting…"):
                    found=scene_cuts(act_vb,thr_f)
                    if found:
                        st.session_state.cut_points=sorted(
                            set(st.session_state.cut_points)|set(found))
                        alog(f"Detected {len(found)} cuts")
                    else: st.info("No cuts found.")

        # Playhead — immediately below the video in the UI flow
        st.caption("Drag to shot change, then Add")
        ph=st.slider("Playhead",0.,float(act_dur),0.,
                     step=round(1./act_fps,4),format="%.3f",
                     key="ph",label_visibility="collapsed")
        st.caption(f"{sec_tc(ph,act_fps)}  ({ph:.3f}s)")

        ph_col,type_col=st.columns([1,2])
        with ph_col:
            if st.button("Add cut",key="addph"):
                t=round(ph,3)
                if .5<t<act_dur-.5 and t not in st.session_state.cut_points:
                    st.session_state.cut_points.append(t)
                    st.session_state.cut_points.sort()
                    st.rerun()
        with type_col:
            typed=st.text_input("",placeholder="or type: 1:23.5",
                                key="typed",label_visibility="collapsed")
            if typed:
                try:
                    tv=round(parse_t(typed),3)
                    if st.button(f"Add {sec_tc(tv,act_fps)}",key="addtyped"):
                        if .1<tv<act_dur-.1 and tv not in st.session_state.cut_points:
                            st.session_state.cut_points.append(tv)
                            st.session_state.cut_points.sort(); st.rerun()
                except: st.caption("invalid")

        if st.session_state.cut_points:
            cps=st.session_state.cut_points
            cols=st.columns(min(len(cps),8))
            for j,cp in enumerate(cps):
                with cols[j%8]:
                    if st.button(f"✕ {sec_tc(cp,act_fps)[:8]}",key=f"rm_{cp}"):
                        st.session_state.cut_points.remove(cp); st.rerun()
            if st.button("Clear all",key="clr"):
                st.session_state.cut_points=[]; st.rerun()
        else:
            st.caption("No cuts — video auto-subdivided into 10s chunks")

        # ── CHUNK PLAN ───────────────────────────────────────────────────────
        st.markdown('<div class="sec">CHUNK PLAN</div>',unsafe_allow_html=True)
        chunks=make_plan(act_dur,st.session_state.cut_points,act_fps)
        n_proc=sum(1 for c in chunks if c["status"]=="wait")
        n_skip=sum(1 for c in chunks if c["status"]=="skip")
        st.markdown(stats_html([("TOTAL",len(chunks)),("PROCESS",n_proc),
                                ("SKIP",n_skip),("EST. OUTPUT",f"{n_proc*API_MAX_SEC}s")]),
                    unsafe_allow_html=True)
        st.markdown(chunk_grid_html(chunks,st.session_state.active_chunk,act_fps),
                    unsafe_allow_html=True)

        open_cols=st.columns(min(max(len(chunks),1),12))
        for ch in chunks:
            with open_cols[ch["index"]%12]:
                lbl="close" if st.session_state.active_chunk==ch["index"] else f"{ch['index']+1:04d}"
                if st.button(lbl,key=f"op_{ch['index']}"):
                    st.session_state.active_chunk=(
                        None if st.session_state.active_chunk==ch["index"] else ch["index"])
                    st.rerun()

        # ── CHUNK PLAYER ────────────────────────────────────────────────────
        ac=st.session_state.active_chunk
        if ac is not None and 0<=ac<len(chunks):
            ch=chunks[ac]
            st.markdown(f'<div class="sec">PLAYER #{ac+1:04d} · '
                        f'{sec_tc(ch["start"],act_fps)} → {sec_tc(ch["end"],act_fps)} · '
                        f'{ch["duration"]:.3f}s</div>',unsafe_allow_html=True)
            if ac not in st.session_state.chunk_previews:
                with st.spinner(f"Extracting chunk {ac+1}…"):
                    try:
                        pb=extract_seg(act_vb,ch["start"],ch["end"],act_fps)
                        st.session_state.chunk_previews[ac]=pb
                    except Exception as e: st.error(f"Extraction: {e}")
            if ac in st.session_state.chunk_previews:
                settings=get_cs(ac,ch["duration"])
                prev_b=st.session_state.chunk_previews[ac]
                zoom_px=VIDEO_SIZE_PX.get(st.session_state.video_size,160)
                components.html(
                    player_html(b64(prev_b),settings["in_pt"],
                                settings["out_pt"],settings["loop"],zoom_px),
                    height=zoom_px+55,scrolling=False)
                st.caption("Click video: play/pause · Click timeline: seek")

                # Controls immediately below player
                ni=st.number_input("IN",0.,ch["duration"],float(settings["in_pt"]),
                                   step=round(1./act_fps,4),key=f"in_{ac}",format="%.3f")
                no=st.number_input("OUT",0.,ch["duration"],float(settings["out_pt"]),
                                   step=round(1./act_fps,4),key=f"out_{ac}",format="%.3f")
                if ni>.01 or no<ch["duration"]-.01:
                    st.caption(f"Effective: {no-ni:.3f}s to API")

                pl_col,zm_col=st.columns(2)
                with pl_col:
                    nl=st.checkbox("Loop",settings["loop"],key=f"lp_{ac}")
                with zm_col:
                    nz=st.radio("Zoom",VIDEO_SIZE_OPTS,horizontal=True,
                                key=f"zm_{ac}",label_visibility="collapsed",
                                index=VIDEO_SIZE_OPTS.index(
                                    settings.get("zoom",st.session_state.video_size)))

                cren=st.checkbox("Per-chunk crop",settings.get("crop_en",False),key=f"cren_{ac}")
                nx=ny=nw=nh2=0
                if cren:
                    sp=st.session_state.working_probe or st.session_state.probe
                    pw=sp["width"]; ph2=sp["height"]
                    nx=st.number_input("cx",0,pw-2,settings.get("cx",0),step=2,key=f"cx_{ac}")
                    ny=st.number_input("cy",0,ph2-2,settings.get("cy",0),step=2,key=f"cy_{ac}")
                    nw=st.number_input("cw",2,pw,settings.get("cw",pw),step=2,key=f"cw_{ac}")
                    nh2=st.number_input("ch",2,ph2,settings.get("ch",ph2),step=2,key=f"ch_{ac}")

                if st.button("Confirm",key=f"conf_{ac}",type="primary"):
                    st.session_state.chunk_settings[ac]=dict(
                        in_pt=float(ni),out_pt=float(no),loop=nl,zoom=nz,
                        crop_en=cren,cx=int(nx),cy=int(ny),cw=int(nw),ch=int(nh2))
                    if cren and ac in st.session_state.chunk_previews:
                        del st.session_state.chunk_previews[ac]
                    st.success("Saved"); st.rerun()

        # ── COST ────────────────────────────────────────────────────────────
        st.markdown('<div class="sec">COST</div>',unsafe_allow_html=True)
        per=KLING_VID_PRICE[st.session_state.vid_model][API_MAX_SEC]
        st.markdown(cost_tbl_html(n_proc,st.session_state.chosen_api,
                                  st.session_state.vid_model,API_MAX_SEC),
                    unsafe_allow_html=True)

        # ── GENERATE ────────────────────────────────────────────────────────
        st.markdown('<div class="sec">GENERATE</div>',unsafe_allow_html=True)

        if not keys_ok(): st.caption("Enter credentials in Settings tab.")
        elif not st.session_state.image_bytes: st.caption("Upload still image above.")
        elif n_proc==0: st.caption("No processable chunks.")
        else:
            est=n_proc*per
            st.caption(f"{n_proc} clips · {st.session_state.chosen_api} · "
                       f"{'Professional' if st.session_state.vid_model=='pro' else 'Standard'} · "
                       f"est. {usd(est)}")

            def extract_one(ch,vb,fps):
                cs2=st.session_state.chunk_settings.get(ch["index"],{})
                in_pt=cs2.get("in_pt",0.); out_pt=cs2.get("out_pt",ch["duration"])
                eff_s=ch["start"]+in_pt; eff_e=ch["start"]+out_pt
                if cs2.get("crop_en") and cs2.get("cw",0)>0:
                    seg=extract_seg(vb,eff_s,eff_e,fps)
                    seg=do_crop(seg,cs2["cx"],cs2["cy"],cs2["cw"],cs2["ch"])
                else:
                    seg=extract_seg(vb,eff_s,eff_e,fps)
                return fit_chunk_for_api(seg),eff_s,eff_e

            col_a,col_b=st.columns(2)
            with col_a:
                go_bg=st.button("Submit & Exit",type="primary",
                                disabled=st.session_state.processing,key="go_bg",)
            with col_b:
                go_wait=st.button("Wait Here",
                                  disabled=st.session_state.processing,key="go_wait")

            st.caption("Submit & Exit — submit all, background polls, logs to Sheet. "
                       "Wait Here — stream results live.")

            # ── SUBMIT & EXIT ───────────────────────────────────────────────
            if go_bg:
                st.session_state.processing=True
                prog=st.progress(0); stat=st.empty()
                try:
                    img64=b64(st.session_state.image_bytes)
                    _sid=st.session_state.session_id; task_list=[]
                    ensure_sheet_header()
                    for ch in chunks:
                        i=ch["index"]
                        if ch["status"]=="skip":
                            task_list.append({**ch,"task_id":None,"url":None,
                                              "submitted_at":None,"completed_at":None,
                                              "sheet_logged":False,
                                              "prompt":_prompt(),"model":st.session_state.vid_model})
                            continue
                        pct=int((i/len(chunks))*90)
                        prog.progress(pct,text=f"Submitting {i+1}/{len(chunks)}…")
                        stat.info(f"Extracting + submitting chunk {i+1}…")
                        try:
                            seg,eff_s,eff_e=extract_one(ch,act_vb,act_fps)
                            vid64=b64(seg); alog(f"Chunk {i+1}: {len(seg)//1024}KB")
                            if st.session_state.chosen_api=="Kling AI":
                                tid=kling_motion_transfer(active_ak(),active_sk(),
                                                          img64,vid64,API_MAX_SEC,
                                                          st.session_state.vid_model,_prompt())
                            else:
                                tid=runway_motion(active_rk(),img64,vid64,API_MAX_SEC,
                                                  st.session_state.vid_model,_prompt())
                            task_list.append({**ch,"task_id":tid,"status":"polling",
                                              "url":None,"submitted_at":time.time(),
                                              "completed_at":None,"sheet_logged":False,
                                              "prompt":_prompt(),"model":st.session_state.vid_model})
                            alog(f"Chunk {i+1}: submitted {tid}")
                        except Exception as e:
                            task_list.append({**ch,"task_id":None,"status":"failed",
                                              "error":str(e),"url":None,
                                              "submitted_at":time.time(),"completed_at":None,
                                              "sheet_logged":False,"prompt":_prompt(),"model":st.session_state.vid_model})
                            alog(f"Chunk {i+1}: submit failed {e}")
                    with _REG_LOCK: _TASK_REG[_sid]=task_list
                    st.session_state.bg_tasks=task_list; st.session_state.bg_active=True
                    st.session_state.ak_saved=active_ak(); st.session_state.sk_saved=active_sk()
                    save_task_file(task_list)
                    start_bg_poll(_sid,active_ak(),active_sk())
                    n_sub=sum(1 for t in task_list if t.get("task_id"))
                    prog.progress(100)
                    stat.success(f"{n_sub}/{n_proc} submitted. Background polling started. "
                                 f"Results will appear in your Google Sheet. "
                                 f"ETA ~{fmt_dur(n_sub*KLING_EST_SEC//3)}")
                except Exception as e: stat.error(str(e))
                finally: st.session_state.processing=False

            # ── WAIT HERE ───────────────────────────────────────────────────
            if go_wait:
                st.session_state.t1_chunks=[]; st.session_state.t1_results=[]
                st.session_state.t1_zip=None; st.session_state.t1_cost=0.
                st.session_state.processing=True
                prog=st.progress(0); stat=st.empty(); grid=st.empty(); clive=st.empty()
                try:
                    img64=b64(st.session_state.image_bytes)
                    st.session_state.t1_chunks=chunks; cost_now=0.; done_n=0
                    ensure_sheet_header()
                    for ch in chunks:
                        i=ch["index"]
                        if ch["status"]=="skip": continue
                        pct=int(5+(done_n/max(n_proc,1))*90)
                        prog.progress(pct,text=f"Chunk {i+1}/{len(chunks)}")
                        ch["status"]="run"
                        grid.markdown(chunk_grid_html(chunks,None,act_fps),unsafe_allow_html=True)
                        _url=None; _process_secs=None
                        try:
                            stat.info(f"Extracting chunk {i+1}…")
                            seg,eff_s,eff_e=extract_one(ch,act_vb,act_fps)
                            alog(f"Chunk {i+1}: {len(seg)//1024}KB")
                            vid64=b64(seg)
                            stat.info(f"Submitting chunk {i+1}…")
                            _t0=time.time()
                            if st.session_state.chosen_api=="Kling AI":
                                tid=kling_motion_transfer(active_ak(),active_sk(),
                                                          img64,vid64,API_MAX_SEC,
                                                          st.session_state.vid_model,_prompt())
                                _url=k_poll_vid(active_ak(),active_sk(),tid,
                                    status_cb=lambda _t,_e,_s=stat:
                                        _s.info(f"Polling {_t[:12]}… ⏱ {fmt_dur(int(_e))}"),
                                    t0=_t0)
                            else:
                                tid=runway_motion(active_rk(),img64,vid64,API_MAX_SEC,
                                                  st.session_state.vid_model,_prompt())
                                _url=runway_poll(active_rk(),tid,
                                    status_cb=lambda _t,_e,_s=stat:
                                        _s.info(f"Polling {_t[:12]}… ⏱ {fmt_dur(int(_e))}"),
                                    t0=_t0)
                            _process_secs=time.time()-_t0
                            ch["output_url"]=_url; ch["status"]="done"
                            cost_now+=per; done_n+=1
                            st.session_state.t1_results.append(_url)
                            st.session_state.t1_cost=cost_now
                            alog(f"Chunk {i+1}: done in {fmt_dur(int(_process_secs))}")
                        except Exception as e:
                            ch["status"]="fail"; alog(f"Chunk {i+1}: {e}")
                            st.warning(f"Chunk {i+1}: {e}")
                        finally:
                            if _url:
                                try:
                                    log_url("Puppeteer",str(i+1),_prompt(),
                                            st.session_state.vid_model,_url,
                                            ch["filename"],process_secs=_process_secs)
                                except Exception as _le:
                                    alog(f"Sheet log chunk {i+1}: {_le}")
                        grid.markdown(chunk_grid_html(chunks,None,act_fps),unsafe_allow_html=True)
                        clive.caption(f"{usd(cost_now)} · {done_n} done · "
                                      f"ETA {fmt_dur((n_proc-done_n)*KLING_EST_SEC//3)}")
                    done_ch=[c for c in chunks if c["status"]=="done"]
                    if done_ch:
                        prog.progress(97,text="Building ZIP…")
                        try:
                            zb=build_zip(chunks)
                            st.session_state.t1_zip=zb
                        except Exception as ze: st.warning(f"ZIP: {ze}")
                    prog.progress(100); stat.success(f"{len(done_ch)}/{n_proc} done · {usd(cost_now)}")
                except Exception as e: stat.error(str(e))
                finally: st.session_state.processing=False

    # ── RESULTS ──────────────────────────────────────────────────────────────
    if st.session_state.t1_results:
        st.markdown('<div class="sec">RESULTS</div>',unsafe_allow_html=True)
        done_ch=[c for c in st.session_state.t1_chunks if c["status"]=="done"]
        fail_ch=[c for c in st.session_state.t1_chunks if c["status"]=="fail"]
        st.markdown(stats_html([("RENDERED",len(done_ch)),("FAILED",len(fail_ch)),
                                ("COST",usd(st.session_state.t1_cost))]),unsafe_allow_html=True)
        if st.session_state.t1_zip:
            st.download_button("Download ZIP",data=st.session_state.t1_zip,
                               file_name="motion_transfer.zip",
                               mime="application/zip",type="primary")
        with st.expander(f"Preview clips ({len(done_ch)})"):
            for c in done_ch:
                st.caption(f"Chunk {c['index']+1:04d} · {sec_tc(c['start'])} → {sec_tc(c['end'])}")
                show_video(c["output_url"])

# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 2 — ANIMATE
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="sec">STILL</div>',unsafe_allow_html=True)
    a_img=st.file_uploader("Still",type=["jpg","jpeg","png","webp"],
                           key="a_img",label_visibility="collapsed")
    if a_img:
        ik=f"{a_img.name}_{a_img.size}"
        if st.session_state.t2_img_fk!=ik:
            st.session_state.t2_img_bytes=a_img.read(); st.session_state.t2_img_fk=ik
        show_image(a_img)

    st.markdown('<div class="sec">SETTINGS</div>',unsafe_allow_html=True)
    a_prompt=st.text_area("Prompt","",placeholder="the figure slowly turns and waves",
                          key="a_prompt",label_visibility="collapsed",height=70)
    a_neg=st.text_input("Negative","blur, artifacts, watermark",
                        key="a_neg",label_visibility="collapsed")
    a_dur_r=st.radio("Duration",["5s","10s"],horizontal=True,
                     label_visibility="collapsed",index=1)
    a_dur=5 if a_dur_r=="5s" else 10
    a_n_r=st.radio("Clips",["1","2","4"],horizontal=True,label_visibility="collapsed")
    a_n=int(a_n_r)
    a_per=KLING_VID_PRICE[st.session_state.vid_model].get(a_dur,0.07)
    st.markdown(stats_html([("DURATION",f"{a_dur}s"),("CLIPS",a_n),
                            ("EST.",usd(a_per*a_n))]),unsafe_allow_html=True)

    st.markdown('<div class="sec">GENERATE</div>',unsafe_allow_html=True)
    if not keys_ok(): st.caption("Enter credentials in Settings.")
    elif not st.session_state.t2_img_bytes: st.caption("Upload still above.")
    else:
        if st.button(f"Animate · {a_n} clip(s) · est. {usd(a_per*a_n)}",
                     type="primary",disabled=st.session_state.processing,key="go2"):
            _ak=active_ak(); _sk=active_sk()
            if not(_ak and _sk): st.error("Kling credentials required for Animate.")
            else:
                st.session_state.t2_results=[]; st.session_state.t2_cost=0.
                st.session_state.processing=True; prog=st.progress(0); stat=st.empty()
                try:
                    img64=b64(st.session_state.t2_img_bytes); urls=[]; cost_now=0.
                    ensure_sheet_header()
                    for n2 in range(a_n):
                        prog.progress(int((n2/a_n)*90),text=f"Clip {n2+1}/{a_n}…")
                        stat.info(f"Submitting clip {n2+1}…")
                        _t0a=time.time()
                        tid=kling_animate(_ak,_sk,img64,a_prompt,a_neg,a_dur,
                                          st.session_state.vid_model)
                        url=k_poll_vid(_ak,_sk,tid,
                            status_cb=lambda _t,_e,_s=stat:
                                _s.info(f"Polling {_t[:12]}… ⏱ {fmt_dur(int(_e))}"),
                            t0=_t0a)
                        _proca=time.time()-_t0a
                        urls.append(url); cost_now+=a_per
                        log_url("Animate",str(n2+1),a_prompt,
                                st.session_state.vid_model,url,
                                process_secs=_proca)
                    st.session_state.t2_results=urls; st.session_state.t2_cost=cost_now
                    prog.progress(100); stat.success(f"Done · {usd(cost_now)}")
                except Exception as e: stat.error(str(e))
                finally: st.session_state.processing=False

    if st.session_state.t2_results:
        st.markdown('<div class="sec">RESULTS</div>',unsafe_allow_html=True)
        st.markdown(stats_html([("CLIPS",len(st.session_state.t2_results)),
                                ("COST",usd(st.session_state.t2_cost))]),unsafe_allow_html=True)
        for j,url in enumerate(st.session_state.t2_results):
            st.caption(f"Clip {j+1}")
            show_video(url)
            r2=requests.get(url,timeout=30)
            st.download_button(f"Download {j+1}",data=r2.content,
                               file_name=f"animate_{j+1}.mp4",mime="video/mp4",key=f"dl_t2_{j}")

# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 3 — IMAGINE
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="sec">PROMPT</div>',unsafe_allow_html=True)
    i_prompt=st.text_area("Prompt","",
                          placeholder="full body portrait, dancer, dramatic lighting, cinematic",
                          key="i_prompt",label_visibility="collapsed",height=90)
    i_neg=st.text_input("Negative","blur, text, watermark, artifacts",
                        key="i_neg",label_visibility="collapsed")

    st.markdown('<div class="sec">REFERENCE (optional)</div>',unsafe_allow_html=True)
    i_ref=st.file_uploader("Reference",type=["jpg","jpeg","png","webp"],
                           key="i_ref",label_visibility="collapsed")
    if i_ref: show_image(i_ref)
    i_fidelity=0.5
    if i_ref or st.session_state.t3_ref_bytes:
        i_fidelity=st.slider("Fidelity",0.0,1.0,0.5,0.05,label_visibility="visible")

    st.markdown('<div class="sec">SETTINGS</div>',unsafe_allow_html=True)
    i_aspect=st.radio("Aspect",ASPECT_RATIOS[:5],horizontal=True,
                      label_visibility="collapsed",index=1)
    i_n_r=st.radio("Count",["1","2","4"],horizontal=True,
                   label_visibility="collapsed")
    i_n=int(i_n_r)
    i_price=KLING_IMG_PRICE[st.session_state.img_model][i_n]
    st.markdown(stats_html([("MODEL",st.session_state.img_model),
                            ("ASPECT",i_aspect),("COUNT",i_n),
                            ("EST.",usd(i_price))]),unsafe_allow_html=True)

    st.markdown('<div class="sec">GENERATE</div>',unsafe_allow_html=True)
    if not keys_ok(): st.caption("Enter credentials in Settings.")
    elif not i_prompt.strip(): st.caption("Enter a prompt above.")
    else:
        if st.button(f"Generate {i_n} image(s) · est. {usd(i_price)}",
                     type="primary",disabled=st.session_state.processing,key="go3"):
            _ak=active_ak(); _sk=active_sk()
            if not(_ak and _sk): st.error("Kling credentials required.")
            else:
                st.session_state.t3_results=[]; st.session_state.t3_cost=0.
                st.session_state.processing=True; stat=st.empty(); prog=st.progress(0)
                try:
                    ref_b64=None
                    if i_ref: ref_b64=b64(i_ref.read())
                    elif st.session_state.t3_ref_bytes: ref_b64=b64(st.session_state.t3_ref_bytes)
                    stat.info("Submitting…"); prog.progress(20)
                    _t0i=time.time()
                    tid=kling_imagine(_ak,_sk,i_prompt,i_neg,i_aspect,i_n,
                                      st.session_state.img_model,ref_b64,i_fidelity)
                    prog.progress(40)
                    urls=k_poll_img(_ak,_sk,tid,
                        status_cb=lambda _t,_e,_s=stat:
                            _s.info(f"Polling {_t[:12]}… ⏱ {fmt_dur(int(_e))}"))
                    _proci=time.time()-_t0i
                    st.session_state.t3_results=urls; st.session_state.t3_cost=i_price
                    prog.progress(100)
                    stat.success(f"Done · {len(urls)} image(s) · {usd(i_price)} · ⏱ {fmt_dur(int(_proci))}")
                    ensure_sheet_header()
                    for j,u in enumerate(urls):
                        log_url("Imagine",str(j+1),i_prompt,
                                st.session_state.img_model,u,process_secs=_proci)
                except Exception as e: stat.error(str(e))
                finally: st.session_state.processing=False

    if st.session_state.t3_results:
        st.markdown('<div class="sec">RESULTS</div>',unsafe_allow_html=True)
        st.markdown(stats_html([("IMAGES",len(st.session_state.t3_results)),
                                ("COST",usd(st.session_state.t3_cost))]),unsafe_allow_html=True)
        for j,url in enumerate(st.session_state.t3_results):
            show_image(url)
            r2=requests.get(url,timeout=30)
            st.download_button(f"Download {j+1}",data=r2.content,
                               file_name=f"imagine_{j+1}.jpg",mime="image/jpeg",key=f"dl_t3_{j}")

# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 4 — EDIT
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="sec">MODE</div>',unsafe_allow_html=True)
    edit_mode=st.radio("Mode",list(KLING_EDIT_PRICE.keys()),
                       horizontal=False,label_visibility="collapsed")

    st.markdown('<div class="sec">SOURCE</div>',unsafe_allow_html=True)
    st.caption("Person photo" if edit_mode=="Virtual Try-On" else "Image to edit")
    e_img=st.file_uploader("Source",type=["jpg","jpeg","png","webp"],
                           key="e_img",label_visibility="collapsed")
    if e_img:
        ek=f"{e_img.name}_{e_img.size}"
        if st.session_state.t4_img_fk!=ek:
            st.session_state.t4_img_bytes=e_img.read(); st.session_state.t4_img_fk=ek
        show_image(e_img)

    if edit_mode=="Virtual Try-On":
        st.markdown('<div class="sec">GARMENT</div>',unsafe_allow_html=True)
        e_aux=st.file_uploader("Garment",type=["jpg","jpeg","png","webp"],
                               key="e_aux",label_visibility="collapsed")
        if e_aux:
            ak2=f"{e_aux.name}_{e_aux.size}"
            if st.session_state.t4_aux_fk!=ak2:
                st.session_state.t4_aux_bytes=e_aux.read(); st.session_state.t4_aux_fk=ak2
            show_image(e_aux)

    e_prompt=""; e_neg=""; e_fid=0.5
    if edit_mode!="Virtual Try-On":
        st.markdown('<div class="sec">EDIT PROMPT</div>',unsafe_allow_html=True)
        mode_placeholders={
            "Inpaint/Repaint":"a golden crown on the head, photorealistic",
            "Variation":"same scene, oil painting style, warm tones",
            "Extend Canvas":"continue background naturally, match lighting",
        }
        e_prompt=st.text_area("Prompt","",
                              placeholder=mode_placeholders.get(edit_mode,""),
                              key="e_prompt",label_visibility="collapsed",height=70)
        e_neg=st.text_input("Negative","blur, artifacts",
                            key="e_neg",label_visibility="collapsed")
        e_fid=st.slider("Fidelity",0.0,1.0,
                        0.7 if edit_mode=="Inpaint/Repaint" else 0.5,0.05)
        if edit_mode=="Extend Canvas":
            e_dir=st.radio("Direction",["all sides","left","right","top","bottom"],
                           horizontal=True,label_visibility="collapsed")
            if e_prompt: e_prompt=f"outpaint {e_dir}: {e_prompt}"

    edit_cost=KLING_EDIT_PRICE.get(edit_mode,0.012)
    st.markdown(stats_html([("MODE",edit_mode),("EST.",usd(edit_cost))]),unsafe_allow_html=True)

    st.markdown('<div class="sec">GENERATE</div>',unsafe_allow_html=True)
    needs_aux=edit_mode=="Virtual Try-On"
    if not keys_ok(): st.caption("Enter credentials in Settings.")
    elif not st.session_state.t4_img_bytes: st.caption("Upload source above.")
    elif needs_aux and not st.session_state.t4_aux_bytes: st.caption("Upload garment above.")
    else:
        if st.button(f"Edit · {edit_mode} · est. {usd(edit_cost)}",
                     type="primary",disabled=st.session_state.processing,key="go4"):
            _ak=active_ak(); _sk=active_sk()
            if not(_ak and _sk): st.error("Kling credentials required.")
            else:
                st.session_state.t4_results=[]; st.session_state.t4_cost=0.
                st.session_state.processing=True; stat=st.empty(); prog=st.progress(0)
                try:
                    img64=b64(st.session_state.t4_img_bytes)
                    stat.info(f"Submitting {edit_mode}…"); prog.progress(20)
                    _t0e=time.time()
                    if edit_mode=="Virtual Try-On":
                        cloth64=b64(st.session_state.t4_aux_bytes)
                        tid=kling_tryon(_ak,_sk,img64,cloth64)
                        prog.progress(40)
                        urls=k_poll_img(_ak,_sk,tid,endpoint="kolors-virtual-try-on",
                            status_cb=lambda _t,_e,_s=stat:
                                _s.info(f"Polling {_t[:12]}… ⏱ {fmt_dur(int(_e))}"))
                    else:
                        tid=kling_edit(_ak,_sk,img64,e_prompt,e_neg,e_fid)
                        prog.progress(40)
                        urls=k_poll_img(_ak,_sk,tid,
                            status_cb=lambda _t,_e,_s=stat:
                                _s.info(f"Polling {_t[:12]}… ⏱ {fmt_dur(int(_e))}"))
                    _proce=time.time()-_t0e
                    st.session_state.t4_results=urls; st.session_state.t4_cost=edit_cost
                    prog.progress(100)
                    stat.success(f"Done · {len(urls)} result(s) · {usd(edit_cost)} · ⏱ {fmt_dur(int(_proce))}")
                    ensure_sheet_header()
                    for j,u in enumerate(urls):
                        log_url("Edit",str(j+1),e_prompt,edit_mode,u,process_secs=_proce)
                except Exception as e: stat.error(str(e))
                finally: st.session_state.processing=False

    if st.session_state.t4_results:
        st.markdown('<div class="sec">RESULTS</div>',unsafe_allow_html=True)
        st.markdown(stats_html([("RESULTS",len(st.session_state.t4_results)),
                                ("COST",usd(st.session_state.t4_cost))]),unsafe_allow_html=True)
        for j,url in enumerate(st.session_state.t4_results):
            show_image(url)
            r2=requests.get(url,timeout=30)
            st.download_button(f"Download {j+1}",data=r2.content,
                               file_name=f"edit_{j+1}.jpg",mime="image/jpeg",key=f"dl_t4_{j}")

st.markdown('<div style="margin-top:2rem;color:#1a1a1a;font-size:.6rem;'
            'font-family:monospace;">mts v9</div>',unsafe_allow_html=True)
