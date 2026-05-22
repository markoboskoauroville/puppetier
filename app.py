# ─────────────────────────────────────────────────────────────────────────────
#  MOTION TRANSFER STUDIO  v6
#  Tab 1 PUPPETEER  · Tab 2 ANIMATE  · Tab 3 IMAGINE  · Tab 4 EDIT
#  Kling AI JWT auth · RunwayML Act-One · Google Drive backup + pull
#  Frame-accurate chunking · Chunk player with in/out/loop/zoom/per-chunk crop
#  No audio sent or expected anywhere
#
#  Secrets required:
#    KLING_ACCESS_KEY  KLING_SECRET_KEY  RUNWAY_API_KEY
#    GOOGLE_SERVICE_ACCOUNT_JSON  GOOGLE_DRIVE_FOLDER_ID  (both optional)
#
#  packages.txt: ffmpeg
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import streamlit.components.v1 as components
import requests, time, json, base64, hmac, hashlib, re
import math, os, io, zipfile, tempfile, subprocess
from fractions import Fraction

st.set_page_config(page_title="Motion Transfer Studio", page_icon=None,
                   layout="wide", initial_sidebar_state="expanded")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&display=swap');
*,html,body,[class*="css"]{font-family:'Space Mono',monospace !important;font-size:13px;}
.stApp{background:#07070f;color:#9d94b0;}
h1,h2,h3{color:#c8c0dc;font-weight:700;letter-spacing:.04em;}
.sec{border-top:1px solid #16132a;margin:1.3rem 0 .7rem;padding-top:.6rem;
  color:#4a4468;font-size:.68rem;letter-spacing:.18em;text-transform:uppercase;}
/* tables */
.mt{width:100%;border-collapse:collapse;}
.mt th{color:#4a4468;text-align:left;padding:.3rem .6rem;border-bottom:1px solid #16132a;
  font-size:.68rem;letter-spacing:.1em;text-transform:uppercase;}
.mt td{color:#9d94b0;padding:.25rem .6rem;font-size:.76rem;}
.mt tr:hover td{background:#0e0c1c;}
.mt .hl{color:#a78bfa;font-weight:700;} .mt .hlg{color:#34d399;font-weight:700;}
.mt .muted{color:#3d3660;} .mt .act td{background:#120f22;}
.mt .sep td{background:#0b0a16;color:#3d3660;font-size:.66rem;
  letter-spacing:.14em;padding:.28rem .6rem;}
.mt .err td{color:#f87171;}
/* stats */
.srow{display:flex;gap:2rem;margin:.5rem 0 .8rem;}
.stat .lbl{color:#3d3660;font-size:.66rem;letter-spacing:.1em;text-transform:uppercase;}
.stat .val{color:#c8c0dc;font-size:1.05rem;font-weight:700;}
/* cut pills */
.cp{background:#120f22;border:1px solid #2a2448;border-radius:3px;
  padding:.12rem .5rem;color:#a78bfa;font-size:.7rem;}
/* drive badge */
.drv-ok{color:#34d399;font-size:.7rem;}  .drv-no{color:#3d3660;font-size:.7rem;}
/* buttons */
.stButton>button{background:#0e0c1c !important;border:1px solid #1e1a32 !important;
  border-radius:3px !important;color:#7a7090 !important;
  font-family:'Space Mono',monospace !important;font-size:.76rem !important;
  padding:.28rem .8rem !important;font-weight:400 !important;letter-spacing:.02em !important;}
.stButton>button:hover{border-color:#a78bfa !important;color:#a78bfa !important;}
.stButton>button[kind="primary"]{background:#160f2a !important;
  border-color:#5b21b6 !important;color:#c4b5fd !important;}
.stButton>button:disabled{opacity:.25 !important;}
/* inputs */
.stTextInput>div>div>input,.stNumberInput>div>div>input,
.stSelectbox>div>div,.stTextArea>div>textarea,.stMultiSelect>div>div{
  background:#0a0918 !important;border:1px solid #1a1730 !important;
  border-radius:3px !important;color:#9d94b0 !important;
  font-family:'Space Mono',monospace !important;font-size:.76rem !important;}
label{color:#4a4468 !important;font-size:.68rem !important;
  text-transform:uppercase;letter-spacing:.08em;}
.stCheckbox>label{text-transform:none !important;font-size:.76rem !important;}
.stSlider>div>div>div>div{background:#5b21b6 !important;}
.stSlider>div>div>div{background:#1a1730 !important;}
[data-testid="stSidebar"]{background:#060510 !important;border-right:1px solid #12102a !important;}
.stProgress>div>div{background:#5b21b6 !important;}
.stTabs [data-baseweb="tab-list"]{background:#07070f;border-bottom:1px solid #16132a;}
.stTabs [data-baseweb="tab"]{color:#4a4468;font-size:.76rem;letter-spacing:.1em;
  text-transform:uppercase;padding:.5rem 1.2rem;}
.stTabs [aria-selected="true"]{color:#a78bfa !important;border-bottom:2px solid #a78bfa !important;}
div[data-testid="metric-container"]{display:none;}
#MainMenu,footer,header{visibility:hidden;}
.stAlert{border-radius:3px !important;font-size:.76rem !important;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
KLING_BASE  = "https://api.klingai.com"
RUNWAY_BASE = "https://api.dev.runwayml.com/v1"
API_MAX_SEC = 10
MIN_CHUNK   = 3

KLING_VID_PRICE   = {"Standard (720p)":{5:.045,10:.070},"Professional (1080p)":{5:.090,10:.140}}
RUNWAY_VID_PRICE  = {"Gen-3 Alpha Turbo":{5:.50,10:1.00},"Gen-3 Alpha":{5:.90,10:1.80}}
KLING_IMG_PRICE   = {"kolors":{"1 image":.008,"4 images":.028},"kling-v1":{"1 image":.005,"4 images":.018}}
KLING_EDIT_PRICE  = {"inpaint":.012,"variation":.010,"try-on":.025,"extend":.012}
KLING_ANIMATE_PRICE = {"Standard (720p)":{5:.045,10:.070},"Professional (1080p)":{5:.090,10:.140}}

ASPECT_RATIOS = ["1:1","16:9","9:16","4:3","3:4","3:2","2:3","21:9"]
SEG_COLORS = ["#1e1a32","#1a2232","#221a32","#1a2218","#22201a","#1a1e2a","#2a1a1a","#1a2a1a"]

# ─────────────────────────────────────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
_D = dict(
    # Shared / puppeteer (t1)
    guide_bytes=None, guide_fk="", probe=None,
    image_bytes=None, image_fk="",
    cut_points=[], crop_en=False, crop_x=0,crop_y=0,crop_w=0,crop_h=0,
    working_bytes=None, working_probe=None,
    active_chunk=None, chunk_settings={}, chunk_previews={},
    t1_chunks=[], t1_results=[], t1_zip=None, t1_csv="", t1_cost=0.0,
    # Animate (t2)
    t2_img_bytes=None, t2_img_fk="",
    t2_results=[], t2_cost=0.0,
    # Imagine (t3)
    t3_results=[], t3_cost=0.0,
    # Edit (t4)
    t4_img_bytes=None, t4_img_fk="",
    t4_aux_bytes=None, t4_aux_fk="",
    t4_results=[], t4_cost=0.0,
    # Global
    processing=False, log=[],
)
for k,v in _D.items():
    if k not in st.session_state: st.session_state[k]=v

# ─────────────────────────────────────────────────────────────────────────────
#  UTILITY
# ─────────────────────────────────────────────────────────────────────────────
def b64(d): return base64.b64encode(d).decode()
def sec_tc(s,fps=25):
    s=max(0.,s);h=int(s)//3600;m=(int(s)%3600)//60
    sc=int(s)%60;fr=int(round((s%1)*fps))%max(1,int(fps))
    return f"{h:02d}:{m:02d}:{sc:02d}:{fr:02d}"
def tc_fn(s): return sec_tc(s).replace(":","_")
def usd(v): return f"${v:.3f}" if v<.1 else f"${v:.2f}"
def alog(m): st.session_state.log.append(f"[{time.strftime('%H:%M:%S')}] {m}")
def gs(k):
    try: return st.secrets[k]
    except: return None
def parse_t(s):
    s=s.strip();p=s.split(":")
    if len(p)==1: return float(p[0])
    if len(p)==2: return int(p[0])*60+float(p[1])
    return int(p[0])*3600+int(p[1])*60+float(p[2])
def get_cs(i,dur):
    if i not in st.session_state.chunk_settings:
        st.session_state.chunk_settings[i]=dict(in_pt=0.,out_pt=dur,loop=False,zoom="1×",
                                                  crop_en=False,cx=0,cy=0,cw=0,ch=0)
    return st.session_state.chunk_settings[i]
def img_mime(d): return "image/png" if d.startswith("iVBORw0") else "image/jpeg"

# ─────────────────────────────────────────────────────────────────────────────
#  KLING JWT
# ─────────────────────────────────────────────────────────────────────────────
def _bu(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
def kling_jwt(ak,sk):
    h=_bu(json.dumps({"alg":"HS256","typ":"JWT"}).encode())
    n=int(time.time())
    p=_bu(json.dumps({"iss":ak,"exp":n+1800,"nbf":n-5}).encode())
    m=f"{h}.{p}"
    s=_bu(hmac.new(sk.encode(),m.encode(),hashlib.sha256).digest())
    return f"{m}.{s}"
def kh(ak,sk): return {"Authorization":f"Bearer {kling_jwt(ak,sk)}","Content-Type":"application/json"}

# ─────────────────────────────────────────────────────────────────────────────
#  KLING API CALLS
# ─────────────────────────────────────────────────────────────────────────────
def k_post(ak,sk,path,payload):
    r=requests.post(f"{KLING_BASE}{path}",headers=kh(ak,sk),json=payload,timeout=90)
    if not r.ok: raise requests.HTTPError(f"Kling {r.status_code}: {r.text[:400]}",response=r)
    return r.json()

def k_poll_vid(ak,sk,tid,endpoint="image2video",mw=600):
    dl=time.time()+mw
    while True:
        if time.time()>dl: raise TimeoutError(f"Timeout {tid}")
        r=requests.get(f"{KLING_BASE}/v1/videos/{endpoint}/{tid}",headers=kh(ak,sk),timeout=30)
        r.raise_for_status();d=r.json().get("data",{})
        s=d.get("task_status","processing")
        if s=="succeed":
            try: return d["task_result"]["videos"][0]["url"]
            except: raise ValueError(f"No URL: {d}")
        if s in("failed","error"): raise RuntimeError(d.get("task_status_msg","failed"))
        time.sleep(6)

def k_poll_img(ak,sk,tid,endpoint="generations",mw=300):
    dl=time.time()+mw
    while True:
        if time.time()>dl: raise TimeoutError(f"Timeout {tid}")
        r=requests.get(f"{KLING_BASE}/v1/images/{endpoint}/{tid}",headers=kh(ak,sk),timeout=30)
        r.raise_for_status();d=r.json().get("data",{})
        s=d.get("task_status","processing")
        if s=="succeed":
            try: return [img["url"] for img in d["task_result"]["images"]]
            except: raise ValueError(f"No images: {d}")
        if s in("failed","error"): raise RuntimeError(d.get("task_status_msg","failed"))
        time.sleep(5)

def kling_motion_transfer(ak,sk,img_b64,vid_b64,dur,model,prompt):
    """Tab 1 — motion reference image-to-video. Raw base64, no data URI prefix."""
    d=k_post(ak,sk,"/v1/videos/image2video",{
        "model_name":"kling-v1-5","image":img_b64,"motion_video":vid_b64,
        "duration":int(dur),"mode":"professional" if "1080" in model else "standard",
        "cfg_scale":0.5,"prompt":prompt or "smooth motion, high quality, cinematic",
        "negative_prompt":"blur, artifacts, distortion, watermark"})
    tid=d.get("data",{}).get("task_id","")
    if not tid: raise ValueError(f"No task_id: {d}")
    return tid

def kling_animate(ak,sk,img_b64,prompt,neg,dur,model):
    """Tab 2 — image to video with text prompt (no motion reference)."""
    d=k_post(ak,sk,"/v1/videos/image2video",{
        "model_name":"kling-v1-5","image":img_b64,
        "prompt":prompt,"negative_prompt":neg or "",
        "duration":int(dur),"mode":"professional" if "1080" in model else "standard",
        "cfg_scale":0.5})
    tid=d.get("data",{}).get("task_id","")
    if not tid: raise ValueError(f"No task_id: {d}")
    return tid

def kling_imagine(ak,sk,prompt,neg,aspect,n,model_name,ref_b64=None,fidelity=0.5):
    """Tab 3 — text to image (Kolors / Kling image model)."""
    payload={"model_name":model_name,"prompt":prompt,
             "negative_prompt":neg or "","n":int(n),"aspect_ratio":aspect}
    if ref_b64:
        payload["image_reference"]=ref_b64
        payload["image_fidelity"]=float(fidelity)
    d=k_post(ak,sk,"/v1/images/generations",payload)
    tid=d.get("data",{}).get("task_id","")
    if not tid: raise ValueError(f"No task_id: {d}")
    return tid

def kling_edit_inpaint(ak,sk,img_b64,prompt,neg,fidelity=0.3):
    """Tab 4 — image editing / variation / inpainting via img2img."""
    # Kling inpainting uses image_reference with a high fidelity for variation,
    # lower fidelity for more creative departure. Verify at docs.klingai.com.
    payload={"model_name":"kolors","prompt":prompt,"negative_prompt":neg or "",
             "image_reference":img_b64,"image_fidelity":float(fidelity),"n":1}
    d=k_post(ak,sk,"/v1/images/generations",payload)
    tid=d.get("data",{}).get("task_id","")
    if not tid: raise ValueError(f"No task_id: {d}")
    return tid

def kling_tryon(ak,sk,human_b64,cloth_b64):
    """Tab 4 — virtual try-on. Verify at docs.klingai.com/image/virtual-try-on"""
    d=k_post(ak,sk,"/v1/images/kolors-virtual-try-on",{
        "model_name":"kolors-virtual-try-on-v1",
        "human_image":human_b64,"cloth_image":cloth_b64})
    tid=d.get("data",{}).get("task_id","")
    if not tid: raise ValueError(f"No task_id: {d}")
    return tid

# RunwayML
def rh(k): return {"Authorization":f"Bearer {k}","Content-Type":"application/json","X-Runway-Version":"2024-11-06"}
def runway_motion(k,img_b64,vid_b64,dur,model,prompt):
    mime=img_mime(img_b64)
    r=requests.post(f"{RUNWAY_BASE}/image_to_video",headers=rh(k),json={
        "model":"gen3a_turbo" if "Turbo" in model else "gen3a",
        "promptImage":f"data:{mime};base64,{img_b64}",
        "promptVideo":f"data:video/mp4;base64,{vid_b64}",
        "duration":int(dur),"ratio":"1280:720","watermark":False,
        "promptText":prompt or "smooth motion, high quality","seed":42},timeout=90)
    if not r.ok: raise requests.HTTPError(f"Runway {r.status_code}: {r.text[:400]}",response=r)
    tid=r.json().get("id","")
    if not tid: raise ValueError(f"No id: {r.json()}")
    return tid

def runway_poll(k,tid,mw=600):
    dl=time.time()+mw
    while True:
        if time.time()>dl: raise TimeoutError(f"Runway timeout {tid}")
        r=requests.get(f"{RUNWAY_BASE}/tasks/{tid}",headers=rh(k),timeout=30)
        r.raise_for_status();d=r.json();s=d.get("status","PENDING")
        if s=="SUCCEEDED":
            out=d.get("output",[])
            if out: return out[0]
            raise ValueError(f"No output: {d}")
        if s in("FAILED","CANCELLED"): raise RuntimeError(f"Runway: {d.get('failure','failed')}")
        time.sleep(6)

# ─────────────────────────────────────────────────────────────────────────────
#  FFMPEG
# ─────────────────────────────────────────────────────────────────────────────
def ffok():
    try: subprocess.run(["ffmpeg","-version"],capture_output=True,check=True); return True
    except: return False

def probe(path):
    r=subprocess.run(["ffprobe","-v","quiet","-select_streams","v:0",
        "-show_entries","stream=r_frame_rate,nb_frames,width,height",
        "-show_entries","format=duration","-print_format","json",path],
        capture_output=True,text=True,check=True)
    d=json.loads(r.stdout);st2=d["streams"][0]
    fps=float(Fraction(st2["r_frame_rate"]))
    dur=float(d["format"]["duration"])
    nf=int(st2["nb_frames"]) if st2.get("nb_frames","N/A")!="N/A" else int(dur*fps)
    return {"duration":dur,"fps":fps,"total_frames":nf,
            "width":int(st2.get("width",0)),"height":int(st2.get("height",0))}

def do_crop(vb,x,y,w,h):
    x,y=x-x%2,y-y%2;w,h=w-w%2,h-h%2
    with tempfile.TemporaryDirectory() as t:
        i=os.path.join(t,"i.mp4");o=os.path.join(t,"o.mp4")
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

def extract_seg(vb,start,end,fps):
    """Frame-accurate extraction. -an always (no audio, ever)."""
    sf=int(round(start*fps));ef=int(round(end*fps));nf=ef-sf
    sts=sf/fps;dur=nf/fps
    with tempfile.TemporaryDirectory() as t:
        i=os.path.join(t,"i.mp4");o=os.path.join(t,"o.mp4")
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
        s,e=bounds[i],bounds[i+1];d=e-s
        if d<0.1: continue
        if d<=API_MAX_SEC: segs.append((s,e,False))
        else:
            n=math.ceil(d/API_MAX_SEC);sub=d/n
            for j in range(n):
                ss=s+j*sub;se=min(s+(j+1)*sub,e)
                segs.append((ss,se,True))
    out=[]
    for i,(s,e,sub) in enumerate(segs):
        d=e-s;nf=int(round(d*fps))
        out.append({"index":i,"start":s,"end":e,"duration":d,"n_frames":nf,
                    "is_sub":sub,"status":"skip" if d<MIN_CHUNK else "wait",
                    "filename":f"chunk_{i+1:04d}_TC_{tc_fn(s)}_to_{tc_fn(e)}.mp4",
                    "output_url":None})
    return out

# ─────────────────────────────────────────────────────────────────────────────
#  CHUNK PLAYER HTML
# ─────────────────────────────────────────────────────────────────────────────
def player_html(vid_b64,in_pt,out_pt,loop,zoom_px):
    lo="true" if loop else "false"
    return f"""<!DOCTYPE html><html><head><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#07070f;font-family:'Space Mono',monospace;font-size:11px;color:#6b6080;}}
#w{{display:flex;flex-direction:column;gap:5px;padding:2px 0;}}
video{{width:100%;max-height:{zoom_px}px;background:#000;display:block;cursor:pointer;}}
.tl{{height:4px;background:#12102a;border-radius:2px;position:relative;cursor:pointer;margin:0 1px;}}
.tlp{{height:100%;background:#3b1d8a;border-radius:2px;pointer-events:none;}}
.mk{{position:absolute;top:-4px;width:2px;height:12px;pointer-events:none;}}
.mki{{background:#34d399;}}.mko{{background:#f87171;}}.mkh{{background:#a78bfa;width:1px;}}
.inf{{display:flex;justify-content:space-between;padding:0 2px;color:#2d2a48;font-size:10px;}}
.acc{{color:#a78bfa;}}.grn{{color:#34d399;}}.red{{color:#f87171;}}
</style></head><body><div id="w">
<video id="v" src="data:video/mp4;base64,{vid_b64}" preload="metadata"></video>
<div class="tl" id="tl"><div class="tlp" id="pl"></div>
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
#  TABLE RENDERERS
# ─────────────────────────────────────────────────────────────────────────────
def chunk_tbl(chunks,active,fps=25):
    rows=""
    for ch in chunks:
        i=ch["index"]
        sc={"wait":"","done":"hlg","fail":"err","run":"","skip":"muted"}.get(ch["status"],"")
        act=" act" if i==active else ""
        cs=st.session_state.chunk_settings.get(i,{})
        note=" [trim]" if cs and (cs.get("in_pt",0)>.01 or cs.get("out_pt",ch["duration"])<ch["duration"]-.01) else ""
        note+=(" [crop]" if cs and cs.get("crop_en") else "")
        rows+=(f'<tr class="{act}"><td class="muted">{i+1:04d}</td>'
               f'<td>{sec_tc(ch["start"],fps)} → {sec_tc(ch["end"],fps)}</td>'
               f'<td>{ch["duration"]:.3f}s</td><td class="muted">{ch["n_frames"]}</td>'
               f'<td class="muted">{"SUB" if ch["is_sub"] else "FULL"}</td>'
               f'<td class="{sc}">{ch["status"].upper()}{note}</td></tr>')
    return (f'<table class="mt"><thead><tr><th>#</th><th>RANGE</th>'
            f'<th>DUR</th><th>FR</th><th>TYPE</th><th>STATUS</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>')

def vid_cost_tbl(n,api,model,dur_key):
    rows=""
    rows+='<tr class="sep"><td colspan="5">KLING AI</td></tr>'
    for m,p in KLING_VID_PRICE.items():
        for d in[5,10]:
            t=n*p[d];act=(api=="Kling AI" and model==m and dur_key==d)
            rows+=(f'<tr class="{"act" if act else ""}"><td>Kling</td><td>{m}</td>'
                   f'<td>{n}</td><td>{usd(p[d])}</td>'
                   f'<td class="{"hl" if act else ""}">{usd(t)}</td></tr>')
    rows+='<tr class="sep"><td colspan="5">RUNWAYML ACT-ONE  (estimated)</td></tr>'
    for m,p in RUNWAY_VID_PRICE.items():
        for d in[5,10]:
            t=n*p[d];act=(api=="RunwayML" and model==m and dur_key==d)
            rows+=(f'<tr class="{"act" if act else ""}"><td>Runway</td><td>{m}</td>'
                   f'<td>{n}</td><td>{usd(p[d])}</td>'
                   f'<td class="{"hlg" if act else ""}">{usd(t)} *</td></tr>')
    return (f'<table class="mt"><thead><tr><th>API</th><th>MODEL</th>'
            f'<th>CLIPS</th><th>$/CLIP</th><th>TOTAL</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>'
            f'<div style="color:#2d2a48;font-size:.63rem;margin-top:.25rem;">'
            f'* runway estimated · verify runwayml.com/pricing</div>')

def stats_html(pairs):
    inner="".join(f'<div class="stat"><div class="lbl">{l}</div>'
                  f'<div class="val">{v}</div></div>' for l,v in pairs)
    return f'<div class="srow">{inner}</div>'

# ─────────────────────────────────────────────────────────────────────────────
#  ZIP BUILDER
# ─────────────────────────────────────────────────────────────────────────────
def build_zip(chunks):
    buf=io.BytesIO()
    done=[c for c in chunks if c["status"]=="done" and c["output_url"]]
    lines=["chunk,filename,start_tc,end_tc,start_s,end_s,duration_s,frames,url"]
    with zipfile.ZipFile(buf,"w",zipfile.ZIP_STORED) as zf:
        for ch in done:
            r=requests.get(ch["output_url"],timeout=120);r.raise_for_status()
            zf.writestr(ch["filename"],r.content)
            lines.append(f"{ch['index']+1},{ch['filename']},"
                f"{sec_tc(ch['start'])},{sec_tc(ch['end'])},"
                f"{ch['start']:.4f},{ch['end']:.4f},{ch['duration']:.4f},"
                f"{ch['n_frames']},{ch['output_url']}")
        csv="\n".join(lines)
        zf.writestr("MANIFEST.csv",csv)
        zf.writestr("README.txt","Import MP4s into Avid/Premiere/DaVinci in chunk order.\n"
            "H.264, no audio, every frame I-frame. See MANIFEST.csv for timecodes.\n")
    return buf.getvalue(),"\n".join(lines)

# ─────────────────────────────────────────────────────────────────────────────
#  GOOGLE DRIVE
# ─────────────────────────────────────────────────────────────────────────────
def _drive_svc():
    """Return an authenticated Drive service, or None if not configured."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        creds_json=gs("GOOGLE_SERVICE_ACCOUNT_JSON")
        if not creds_json: return None
        info=json.loads(creds_json)
        creds=service_account.Credentials.from_service_account_info(
            info,scopes=["https://www.googleapis.com/auth/drive"])
        return build("drive","v3",credentials=creds,cache_discovery=False)
    except Exception as e:
        alog(f"Drive init failed: {e}")
        return None

def drive_upload(data_bytes,filename,mime_type):
    """Upload bytes to configured Drive folder. Returns webViewLink or None."""
    try:
        from googleapiclient.http import MediaIoBaseUpload
        svc=_drive_svc()
        if not svc: return None
        folder=gs("GOOGLE_DRIVE_FOLDER_ID") or "root"
        meta={"name":filename,"parents":[folder]}
        media=MediaIoBaseUpload(io.BytesIO(data_bytes),mimetype=mime_type,resumable=False)
        f=svc.files().create(body=meta,media_body=media,fields="id,webViewLink").execute()
        return f.get("webViewLink","")
    except Exception as e:
        alog(f"Drive upload failed: {e}"); return None

def drive_list(mime_filter=None):
    """List files in configured Drive folder."""
    try:
        svc=_drive_svc()
        if not svc: return []
        folder=gs("GOOGLE_DRIVE_FOLDER_ID") or "root"
        q=f"'{folder}' in parents and trashed=false"
        if mime_filter: q+=f" and mimeType contains '{mime_filter}'"
        res=svc.files().list(q=q,fields="files(id,name,mimeType,size)",
                              orderBy="modifiedTime desc",pageSize=50).execute()
        return res.get("files",[])
    except Exception as e:
        alog(f"Drive list failed: {e}"); return []

def drive_download_id(file_id):
    """Download a Drive file by ID."""
    try:
        svc=_drive_svc()
        if not svc: return None
        return svc.files().get_media(fileId=file_id).execute()
    except Exception as e:
        alog(f"Drive download failed: {e}"); return None

def fetch_any_url(url):
    """Download from any URL including Google Drive share links."""
    url=url.strip()
    # Convert Drive share link to direct download
    m=re.search(r'/d/([a-zA-Z0-9_-]{10,})',url)
    if m:
        fid=m.group(1)
        # Try Drive API first
        data=drive_download_id(fid)
        if data: return data
        # Fallback: direct download URL (works for public files)
        url=f"https://drive.google.com/uc?id={fid}&export=download&confirm=t"
    r=requests.get(url,allow_redirects=True,timeout=60,
                   headers={"User-Agent":"Mozilla/5.0"})
    r.raise_for_status()
    return r.content

def drive_configured():
    return bool(gs("GOOGLE_SERVICE_ACCOUNT_JSON") and gs("GOOGLE_DRIVE_FOLDER_ID"))

def drive_btn(data,filename,mime,label="save to Drive"):
    if not drive_configured(): return
    if st.button(label,key=f"drv_{filename[:30]}"):
        with st.spinner("uploading…"):
            link=drive_upload(data,filename,mime)
            if link: st.success(f"saved — {link}")
            else: st.error("upload failed (check log)")

def url_loader(label="load from URL or Drive link",key="url_load"):
    """Small URL fetch widget. Returns bytes or None."""
    u=st.text_input(label,placeholder="https://drive.google.com/... or any URL",key=key)
    if u:
        if st.button("fetch",key=f"fetch_{key}"):
            with st.spinner("fetching…"):
                try: return fetch_any_url(u)
                except Exception as e: st.error(f"fetch failed: {e}")
    return None

def drive_file_picker(mime_filter=None,key="drv_pick"):
    """Let user pick a file from their Drive folder."""
    if not drive_configured(): return None
    files=drive_list(mime_filter)
    if not files:
        st.caption("no files found in Drive folder")
        return None
    names=["— select —"]+[f["name"] for f in files]
    sel=st.selectbox("pick from Drive",names,key=key,label_visibility="collapsed")
    if sel!="— select —":
        fid=next(f["id"] for f in files if f["name"]==sel)
        if st.button("load",key=f"load_{key}"):
            with st.spinner(f"downloading {sel}…"):
                return drive_download_id(fid)
    return None

# ─────────────────────────────────────────────────────────────────────────────
#  LOAD SECRETS + SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
S_AK=gs("KLING_ACCESS_KEY"); S_SK=gs("KLING_SECRET_KEY"); S_RW=gs("RUNWAY_API_KEY")

with st.sidebar:
    st.markdown("**MOTION TRANSFER STUDIO**")
    st.markdown('<div class="sec">API ENGINE</div>',unsafe_allow_html=True)
    chosen_api=st.radio("api",["Kling AI","RunwayML"],horizontal=True,label_visibility="collapsed")

    st.markdown('<div class="sec">CREDENTIALS</div>',unsafe_allow_html=True)
    if chosen_api=="Kling AI":
        if S_AK and S_SK:
            st.caption("Kling Access + Secret loaded.")
            ak,sk=S_AK,S_SK
        else:
            ak=st.text_input("Access Key",type="password",key="ak")
            sk=st.text_input("Secret Key",type="password",key="sk")
        rk=None; keys_ok=bool(ak and sk)
    else:
        ak=sk=None
        if S_RW: st.caption("Runway key loaded."); rk=S_RW
        else: rk=st.text_input("API Key",type="password",key="rk")
        keys_ok=bool(rk)

    st.markdown('<div class="sec">VIDEO MODEL</div>',unsafe_allow_html=True)
    vid_model=st.selectbox("vm",
        list(KLING_VID_PRICE.keys()) if chosen_api=="Kling AI" else list(RUNWAY_VID_PRICE.keys()),
        index=1 if chosen_api=="Kling AI" else 0,label_visibility="collapsed")

    st.markdown('<div class="sec">IMAGE MODEL</div>',unsafe_allow_html=True)
    img_model=st.selectbox("im",list(KLING_IMG_PRICE.keys()),label_visibility="collapsed")

    st.markdown('<div class="sec">PROMPT</div>',unsafe_allow_html=True)
    prompt_txt=st.text_area("pt","",height=50,label_visibility="collapsed",
                            placeholder="cinematic, sharp detail…")

    st.markdown('<div class="sec">GOOGLE DRIVE</div>',unsafe_allow_html=True)
    if drive_configured():
        st.markdown('<span class="drv-ok">connected — auto-backup available</span>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<span class="drv-no">not configured — add secrets to enable</span>',
                    unsafe_allow_html=True)
        st.caption("GOOGLE_SERVICE_ACCOUNT_JSON + GOOGLE_DRIVE_FOLDER_ID")

    if st.session_state.log:
        st.markdown('<div class="sec">LOG</div>',unsafe_allow_html=True)
        with st.expander("show",expanded=False):
            st.code("\n".join(st.session_state.log[-60:]),language=None)

# ─────────────────────────────────────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("# MOTION TRANSFER STUDIO")
st.markdown('<div style="color:#2d2a48;font-size:.7rem;margin-bottom:.8rem;">'
            'Kling AI · RunwayML · Google Drive · Frame-accurate · No audio</div>',
            unsafe_allow_html=True)

if not ffok():
    st.error("ffmpeg not found — add 'ffmpeg' to packages.txt and redeploy")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
#  TABS
# ─────────────────────────────────────────────────────────────────────────────
tab1,tab2,tab3,tab4 = st.tabs(["PUPPETEER","ANIMATE","IMAGINE","EDIT"])

# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 1 — PUPPETEER (motion transfer)
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown('<div class="sec">FILES</div>',unsafe_allow_html=True)
    c_v,c_i=st.columns(2,gap="large")

    with c_v:
        st.caption("GUIDE VIDEO")
        gf=st.file_uploader("gv",type=["mp4","mov","webm","avi"],key="gv",label_visibility="collapsed")
        if gf:
            fk=f"{gf.name}_{gf.size}"
            if st.session_state.guide_fk!=fk:
                st.session_state.guide_bytes=gf.read()
                st.session_state.guide_fk=fk
                st.session_state.cut_points=[]
                st.session_state.working_bytes=None; st.session_state.working_probe=None
                st.session_state.crop_en=False; st.session_state.active_chunk=None
                st.session_state.chunk_settings={}; st.session_state.chunk_previews={}
                with tempfile.TemporaryDirectory() as t:
                    p=os.path.join(t,"i.mp4")
                    with open(p,"wb") as f: f.write(st.session_state.guide_bytes)
                    try: st.session_state.probe=probe(p)
                    except Exception as e: st.warning(f"probe: {e}")
            st.video(gf)
            if st.session_state.probe:
                pr=st.session_state.probe
                st.caption(f"{pr['duration']:.2f}s · {pr['fps']:.3f}fps · {pr['width']}×{pr['height']}px")
        # Or load from URL/Drive
        with st.expander("load from URL or Drive",expanded=False):
            loaded=url_loader("URL or Drive link",key="t1_url")
            if loaded:
                st.session_state.guide_bytes=loaded
                st.session_state.guide_fk=f"url_{len(loaded)}"
                with tempfile.TemporaryDirectory() as t:
                    p=os.path.join(t,"i.mp4")
                    with open(p,"wb") as f: f.write(loaded)
                    try: st.session_state.probe=probe(p)
                    except: pass
                st.rerun()
            if drive_configured():
                d=drive_file_picker("video",key="t1_drv")
                if d: st.session_state.guide_bytes=d; st.rerun()

    with c_i:
        st.caption("SUBJECT IMAGE")
        imf=st.file_uploader("si",type=["jpg","jpeg","png","webp"],key="si",label_visibility="collapsed")
        if imf:
            ik=f"{imf.name}_{imf.size}"
            if st.session_state.image_fk!=ik:
                st.session_state.image_bytes=imf.read()
                st.session_state.image_fk=ik
            st.image(imf,use_container_width=True)
        with st.expander("load from URL or Drive",expanded=False):
            loaded=url_loader("URL or Drive link",key="t1_img_url")
            if loaded: st.session_state.image_bytes=loaded; st.rerun()
            if drive_configured():
                d=drive_file_picker("image",key="t1_img_drv")
                if d: st.session_state.image_bytes=d; st.rerun()

    # ── SETUP ────────────────────────────────────────────────────────────────
    if st.session_state.guide_bytes and st.session_state.probe:
        pr=st.session_state.probe
        vdur=pr["duration"]; vfps=pr["fps"]; vw=pr["width"]; vh=pr["height"]
        act_vb=st.session_state.working_bytes or st.session_state.guide_bytes
        act_pr=st.session_state.working_probe or st.session_state.probe
        act_dur=act_pr["duration"]; act_fps=act_pr["fps"]

        # ── CROP ─────────────────────────────────────────────────────────────
        st.markdown('<div class="sec">GLOBAL CROP</div>',unsafe_allow_html=True)
        with st.expander("configure crop — isolate one person",expanded=False):
            st.caption(f"source: {vw}×{vh}px · all values in pixels · must be even")
            c1,c2=st.columns(2)
            cx=c1.number_input("x",0,vw-2,st.session_state.crop_x,step=2,key="cx")
            cy=c2.number_input("y",0,vh-2,st.session_state.crop_y,step=2,key="cy")
            cw=c1.number_input("w",2,vw,vw if not st.session_state.crop_en else st.session_state.crop_w,step=2,key="cw")
            ch=c2.number_input("h",2,vh,vh if not st.session_state.crop_en else st.session_state.crop_h,step=2,key="ch")
            noop=(cx==0 and cy==0 and cw==vw and ch==vh)
            cc1,cc2=st.columns(2)
            with cc1:
                if st.button("apply crop",disabled=noop,key="do_crop"):
                    with st.spinner("cropping…"):
                        try:
                            cr=do_crop(st.session_state.guide_bytes,int(cx),int(cy),int(cw),int(ch))
                            with tempfile.TemporaryDirectory() as t:
                                p=os.path.join(t,"c.mp4")
                                with open(p,"wb") as f: f.write(cr)
                                np2=probe(p)
                            st.session_state.working_bytes=cr; st.session_state.working_probe=np2
                            st.session_state.crop_en=True
                            st.session_state.crop_x=int(cx);st.session_state.crop_y=int(cy)
                            st.session_state.crop_w=int(cw);st.session_state.crop_h=int(ch)
                            st.session_state.chunk_previews={}
                            act_vb=cr; act_pr=np2; act_dur=np2["duration"]; act_fps=np2["fps"]
                            alog(f"Crop {cw}×{ch} at ({cx},{cy})"); st.rerun()
                        except Exception as e: st.error(f"crop failed: {e}")
            with cc2:
                if st.session_state.crop_en and st.button("reset crop",key="rst_crop"):
                    st.session_state.working_bytes=None; st.session_state.working_probe=None
                    st.session_state.crop_en=False; st.session_state.chunk_previews={}; st.rerun()
            if st.session_state.crop_en:
                np2=st.session_state.working_probe
                st.caption(f"active: {np2['width']}×{np2['height']}px · {np2['duration']:.2f}s")

        # ── CUT POINTS ───────────────────────────────────────────────────────
        st.markdown('<div class="sec">CUT POINTS</div>',unsafe_allow_html=True)
        d1,d2=st.columns([1,2])
        with d2:
            thr=st.slider("sensitivity",0.10,0.60,0.35,0.05,key="thr")
        with d1:
            st.markdown("")
            if st.button("auto-detect cuts",key="det"):
                with st.spinner("scene detection…"):
                    found=scene_cuts(act_vb,thr)
                    if found:
                        st.session_state.cut_points=sorted(set(st.session_state.cut_points)|set(found))
                        alog(f"Detected {len(found)} cuts")
                    else: st.info("no cuts found")

        ph=st.slider("playhead",0.,float(act_dur),0.,step=round(1./act_fps,4),
                     format="%.3f",key="ph",label_visibility="collapsed")
        p1,p2,p3=st.columns([2,1,1])
        with p1: st.caption(f"{sec_tc(ph,act_fps)}  ({ph:.3f}s)")
        with p2:
            if st.button("add cut",key="addph"):
                t=round(ph,3)
                if .5<t<act_dur-.5 and t not in st.session_state.cut_points:
                    st.session_state.cut_points.append(t); st.session_state.cut_points.sort()
                    alog(f"Cut: {t}s"); st.rerun()
        with p3:
            typed=st.text_input("type time","",key="typed",placeholder="1:23.5",label_visibility="collapsed")
        if typed:
            try:
                tv=round(parse_t(typed),3)
                if st.button(f"add {sec_tc(tv,act_fps)}",key="addtyped"):
                    if .1<tv<act_dur-.1 and tv not in st.session_state.cut_points:
                        st.session_state.cut_points.append(tv); st.session_state.cut_points.sort(); st.rerun()
            except: st.caption("invalid time")

        if st.session_state.cut_points:
            cps=st.session_state.cut_points
            cols=st.columns(min(len(cps),9))
            for j,cp in enumerate(cps):
                with cols[j%9]:
                    if st.button(f"✕ {sec_tc(cp,act_fps)[:8]}",key=f"rm_{cp}"):
                        st.session_state.cut_points.remove(cp); st.rerun()
            if st.button("clear all",key="clr"): st.session_state.cut_points=[]; st.rerun()
        else:
            st.caption("no cuts — whole video auto-subdivided into 10s chunks")

        # ── CHUNK PLAN ───────────────────────────────────────────────────────
        st.markdown('<div class="sec">CHUNK PLAN</div>',unsafe_allow_html=True)
        chunks=make_plan(act_dur,st.session_state.cut_points,act_fps)
        n_proc=sum(1 for c in chunks if c["status"]=="wait")
        n_skip=sum(1 for c in chunks if c["status"]=="skip")
        st.markdown(stats_html([("TOTAL",len(chunks)),("PROCESS",n_proc),
                                ("SKIP",n_skip),("EST OUTPUT",f"{n_proc*API_MAX_SEC}s")]),
                    unsafe_allow_html=True)
        st.markdown(chunk_tbl(chunks,st.session_state.active_chunk,act_fps),unsafe_allow_html=True)

        # OPEN buttons
        open_cols=st.columns(min(max(len(chunks),1),12))
        for ch in chunks:
            with open_cols[ch["index"]%12]:
                lbl=("close" if st.session_state.active_chunk==ch["index"]
                     else f"{ch['index']+1:04d}")
                if st.button(lbl,key=f"op_{ch['index']}"):
                    st.session_state.active_chunk=(None if st.session_state.active_chunk==ch["index"]
                                                   else ch["index"])
                    st.rerun()

        # ── CHUNK PLAYER ─────────────────────────────────────────────────────
        ac=st.session_state.active_chunk
        if ac is not None and 0<=ac<len(chunks):
            ch=chunks[ac]
            st.markdown(f'<div class="sec">CHUNK PLAYER  #{ac+1:04d}  '
                        f'{sec_tc(ch["start"],act_fps)} → {sec_tc(ch["end"],act_fps)}'
                        f'  {ch["duration"]:.3f}s</div>',unsafe_allow_html=True)
            if ac not in st.session_state.chunk_previews:
                with st.spinner(f"extracting chunk {ac+1}…"):
                    try:
                        pb=extract_seg(act_vb,ch["start"],ch["end"],act_fps)
                        st.session_state.chunk_previews[ac]=pb
                    except Exception as e: st.error(f"extraction: {e}")
            if ac in st.session_state.chunk_previews:
                settings=get_cs(ac,ch["duration"])
                prev_b=st.session_state.chunk_previews[ac]
                cp_l,cp_r=st.columns([3,1],gap="large")
                with cp_l:
                    zoom_map={"1×":200,"1.5×":300,"2×":420,"3×":580}
                    zoom_px=zoom_map.get(settings.get("zoom","1×"),200)
                    components.html(
                        player_html(b64(prev_b),settings["in_pt"],settings["out_pt"],
                                    settings["loop"],zoom_px),
                        height=zoom_px+58,scrolling=False)
                    st.caption("click video to play/pause · click timeline to seek")
                with cp_r:
                    st.caption("IN / OUT  (seconds from chunk start)")
                    ni=st.number_input("IN",0.,ch["duration"],float(settings["in_pt"]),
                                       step=round(1./act_fps,4),key=f"in_{ac}",format="%.3f")
                    no=st.number_input("OUT",0.,ch["duration"],float(settings["out_pt"]),
                                       step=round(1./act_fps,4),key=f"out_{ac}",format="%.3f")
                    nl=st.checkbox("LOOP",settings["loop"],key=f"lp_{ac}")
                    nz=st.select_slider("ZOOM",["1×","1.5×","2×","3×"],
                                        settings.get("zoom","1×"),key=f"zm_{ac}")
                    st.markdown("---")
                    st.caption("CROP OVERRIDE")
                    cren=st.checkbox("per-chunk crop",settings.get("crop_en",False),key=f"cren_{ac}")
                    nx=ny=nw=nh2=0
                    if cren:
                        sp=st.session_state.working_probe or st.session_state.probe
                        pw=sp["width"]; ph2=sp["height"]
                        nx=st.number_input("x",0,pw-2,settings.get("cx",0),step=2,key=f"cx_{ac}")
                        ny=st.number_input("y",0,ph2-2,settings.get("cy",0),step=2,key=f"cy_{ac}")
                        nw=st.number_input("w",2,pw,settings.get("cw",pw),step=2,key=f"cw_{ac}")
                        nh2=st.number_input("h",2,ph2,settings.get("ch",ph2),step=2,key=f"ch_{ac}")
                    if st.button("confirm",key=f"conf_{ac}",type="primary"):
                        st.session_state.chunk_settings[ac]=dict(
                            in_pt=float(ni),out_pt=float(no),loop=nl,zoom=nz,
                            crop_en=cren,cx=int(nx),cy=int(ny),cw=int(nw),ch=int(nh2))
                        if cren and ac in st.session_state.chunk_previews:
                            del st.session_state.chunk_previews[ac]
                        alog(f"Chunk {ac+1}: IN={ni:.3f} OUT={no:.3f} LOOP={nl} ZOOM={nz}")
                        st.success("saved"); st.rerun()
                    if settings["in_pt"]>.01 or settings["out_pt"]<ch["duration"]-.01:
                        eff=settings["out_pt"]-settings["in_pt"]
                        st.caption(f"effective: {eff:.3f}s to API")

        # ── COST ─────────────────────────────────────────────────────────────
        st.markdown('<div class="sec">COST</div>',unsafe_allow_html=True)
        per=(KLING_VID_PRICE if chosen_api=="Kling AI" else RUNWAY_VID_PRICE)[vid_model][API_MAX_SEC]
        st.markdown(vid_cost_tbl(n_proc,chosen_api,vid_model,API_MAX_SEC),unsafe_allow_html=True)

        # ── GENERATE ─────────────────────────────────────────────────────────
        st.markdown('<div class="sec">GENERATE</div>',unsafe_allow_html=True)
        if not keys_ok: st.caption("enter credentials in sidebar")
        elif not st.session_state.image_bytes: st.caption("upload subject image")
        elif n_proc==0: st.caption("no processable chunks")
        else:
            est=n_proc*per
            go=st.button(f"generate  {n_proc} clips · {chosen_api} · {vid_model} · est. {usd(est)}",
                         type="primary",disabled=st.session_state.processing,key="go1")
            if go:
                for k2,v2 in dict(t1_chunks=[],t1_results=[],t1_zip=None,t1_csv="",t1_cost=0.,log=[]).items():
                    st.session_state[k2]=v2
                st.session_state.processing=True
                prog=st.progress(0,text="preparing…"); stat=st.empty(); grid=st.empty(); clive=st.empty()
                try:
                    img64=b64(st.session_state.image_bytes)
                    st.session_state.t1_chunks=chunks
                    cost_now=0.; done_n=0
                    for ch in chunks:
                        i=ch["index"]
                        if ch["status"]=="skip": alog(f"Chunk {i+1}: skip"); continue
                        pct=int(5+(done_n/max(n_proc,1))*90)
                        prog.progress(pct,text=f"chunk {i+1}/{len(chunks)}")
                        ch["status"]="run"
                        grid.markdown(chunk_tbl(chunks,None,act_fps),unsafe_allow_html=True)
                        try:
                            cs2=st.session_state.chunk_settings.get(i,{})
                            in_pt=cs2.get("in_pt",0.); out_pt=cs2.get("out_pt",ch["duration"])
                            eff_s=ch["start"]+in_pt; eff_e=ch["start"]+out_pt
                            stat.info(f"extracting chunk {i+1}…")
                            if cs2.get("crop_en") and cs2.get("cw",0)>0:
                                seg=extract_seg(act_vb,eff_s,eff_e,act_fps)
                                seg=do_crop(seg,cs2["cx"],cs2["cy"],cs2["cw"],cs2["ch"])
                            else:
                                seg=extract_seg(act_vb,eff_s,eff_e,act_fps)
                            vid64=b64(seg)
                            stat.info(f"submitting chunk {i+1} to {chosen_api}…")
                            if chosen_api=="Kling AI":
                                tid=kling_motion_transfer(ak,sk,img64,vid64,API_MAX_SEC,vid_model,prompt_txt)
                                stat.info(f"polling chunk {i+1}…")
                                url=k_poll_vid(ak,sk,tid)
                            else:
                                tid=runway_motion(rk,img64,vid64,API_MAX_SEC,vid_model,prompt_txt)
                                stat.info(f"polling chunk {i+1}…")
                                url=runway_poll(rk,tid)
                            ch["output_url"]=url; ch["status"]="done"
                            cost_now+=per; done_n+=1
                            st.session_state.t1_results.append(url)
                            st.session_state.t1_cost=cost_now
                            alog(f"Chunk {i+1}: done")
                            # Auto-upload to Drive
                            if drive_configured():
                                r2=requests.get(url,timeout=60); r2.raise_for_status()
                                link=drive_upload(r2.content,ch["filename"],"video/mp4")
                                if link: alog(f"Chunk {i+1} → Drive")
                        except Exception as e:
                            ch["status"]="fail"; alog(f"Chunk {i+1} FAILED: {e}")
                            st.warning(f"chunk {i+1}: {e}")
                        grid.markdown(chunk_tbl(chunks,None,act_fps),unsafe_allow_html=True)
                        clive.caption(f"cost so far: {usd(cost_now)} · {done_n} done")
                    done_ch=[c for c in chunks if c["status"]=="done"]
                    if done_ch:
                        prog.progress(97,text="packaging zip…")
                        try:
                            zb,mc=build_zip(chunks)
                            st.session_state.t1_zip=zb; st.session_state.t1_csv=mc
                            if drive_configured():
                                drive_upload(zb,"motion_transfer_output.zip","application/zip")
                                alog("ZIP → Drive")
                        except Exception as ze: st.warning(f"zip: {ze}")
                    prog.progress(100,text="complete")
                    stat.success(f"done  {len(done_ch)}/{n_proc} clips · {usd(cost_now)}")
                except Exception as e: stat.error(str(e)); alog(str(e))
                finally: st.session_state.processing=False

    # ── RESULTS ──────────────────────────────────────────────────────────────
    if st.session_state.t1_results:
        st.markdown('<div class="sec">RESULTS</div>',unsafe_allow_html=True)
        done_ch=[c for c in st.session_state.t1_chunks if c["status"]=="done"]
        fail_ch=[c for c in st.session_state.t1_chunks if c["status"]=="fail"]
        st.markdown(stats_html([("RENDERED",len(done_ch)),("FAILED",len(fail_ch)),
                                ("COST",usd(st.session_state.t1_cost))]),unsafe_allow_html=True)
        if st.session_state.t1_zip:
            st.download_button("download ZIP  (all clips + MANIFEST.csv)",
                data=st.session_state.t1_zip,file_name="motion_transfer.zip",
                mime="application/zip",type="primary")
        if done_ch:
            with st.expander(f"preview clips ({len(done_ch)})",expanded=False):
                for c in done_ch:
                    st.caption(f"chunk {c['index']+1:04d}  {sec_tc(c['start'])} → {sec_tc(c['end'])}  {c['duration']:.3f}s")
                    st.video(c["output_url"])

    # ── DOC ──────────────────────────────────────────────────────────────────
    with st.expander("ABOUT THIS TAB — PUPPETEER",expanded=False):
        st.markdown("""
**What it does**

Puppeteer transfers the motion from a guide video onto your static subject image.
Kling AI analyses the pose, trajectory and timing of the figure in the guide video
frame by frame, then animates your image to perform the exact same movement —
including 3D rotation, jumps and fine gesture.

**When to use it**

- You have a video of a dancer, athlete or performer and want your character to do the same thing.
- You want to bring a portrait, illustration or product photo to life using real motion reference.

**Chunk system**

Both APIs generate a maximum of 10 seconds per call. A 5-minute guide video becomes
30 × 10-second clips, each processed independently, then packaged for import into
your NLE (Avid, Premiere, DaVinci) in exact sequence. Chunk boundaries can be placed
at shot changes so no hard cut is ever blended across two API calls.

**Chunk player controls**

Open any chunk to preview it before generation. Set an IN point to skip a
flash frame at the start, or an OUT point to trim a late settle at the end.
Enable per-chunk crop to isolate a different person or region for that specific shot.
Loop plays continuously between IN and OUT for close inspection.

**Cost (5-minute video · 30 × 10s clips)**

| API | Quality | Total |
|-----|---------|-------|
| Kling AI | Standard 720p | $2.10 |
| Kling AI | Professional 1080p | $4.20 |
| RunwayML | Gen-3 Alpha Turbo | ~$30.00 |

**Google Drive**

If configured, each clip is uploaded to your Drive folder immediately after generation,
and the final ZIP is saved there too. No work is lost even if the browser closes.
        """)

# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 2 — ANIMATE (image to video with prompt)
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="sec">INPUT IMAGE</div>',unsafe_allow_html=True)
    a_c1,a_c2=st.columns([1,1],gap="large")

    with a_c1:
        st.caption("IMAGE TO ANIMATE")
        a_img=st.file_uploader("a_img",type=["jpg","jpeg","png","webp"],
                               key="a_img",label_visibility="collapsed")
        if a_img:
            ik=f"{a_img.name}_{a_img.size}"
            if st.session_state.t2_img_fk!=ik:
                st.session_state.t2_img_bytes=a_img.read()
                st.session_state.t2_img_fk=ik
            st.image(a_img,use_container_width=True)
        with st.expander("load from URL or Drive",expanded=False):
            ld=url_loader("URL or Drive link",key="t2_url")
            if ld: st.session_state.t2_img_bytes=ld; st.rerun()
            if drive_configured():
                d=drive_file_picker("image",key="t2_drv")
                if d: st.session_state.t2_img_bytes=d; st.rerun()

    with a_c2:
        st.markdown('<div class="sec">SETTINGS</div>',unsafe_allow_html=True)
        a_prompt=st.text_area("animation prompt","",height=80,
                              placeholder="the figure slowly turns and waves, cinematic",
                              key="a_prompt")
        a_neg=st.text_input("negative prompt","blur, artifacts, distortion",key="a_neg")
        a_dur=st.select_slider("duration",[5,10],value=10,
                               format_func=lambda x:f"{x}s",key="a_dur")
        a_n=st.select_slider("clips to generate",[1,2,4],value=1,key="a_n")
        a_per=(KLING_VID_PRICE if chosen_api=="Kling AI" else RUNWAY_VID_PRICE)[vid_model][a_dur]
        st.caption(f"cost per clip: {usd(a_per)} · total: {usd(a_per*a_n)}")
        st.caption("(Runway not supported for simple animate — uses Kling API only for this tab)")

    st.markdown('<div class="sec">GENERATE</div>',unsafe_allow_html=True)
    if not keys_ok: st.caption("enter credentials in sidebar")
    elif not st.session_state.t2_img_bytes: st.caption("upload an image above")
    else:
        if st.button(f"animate  {a_n} clip(s) · Kling AI · est. {usd(a_per*a_n)}",
                     type="primary",disabled=st.session_state.processing,key="go2"):
            if not (S_AK or ak):
                st.error("Tab 2 requires Kling AI credentials")
            else:
                _ak=ak or S_AK; _sk=sk or S_SK
                st.session_state.t2_results=[]; st.session_state.t2_cost=0.
                st.session_state.processing=True
                prog=st.progress(0); stat=st.empty()
                try:
                    img64=b64(st.session_state.t2_img_bytes)
                    urls=[]; cost_now=0.
                    for n2 in range(int(a_n)):
                        prog.progress(int((n2/a_n)*90),text=f"clip {n2+1}/{a_n}…")
                        stat.info(f"submitting clip {n2+1}…")
                        tid=kling_animate(_ak,_sk,img64,a_prompt,a_neg,a_dur,vid_model)
                        stat.info(f"polling clip {n2+1}…")
                        url=k_poll_vid(_ak,_sk,tid)
                        urls.append(url); cost_now+=a_per
                        if drive_configured():
                            r2=requests.get(url,timeout=60);r2.raise_for_status()
                            drive_upload(r2.content,f"animate_clip_{n2+1}.mp4","video/mp4")
                        alog(f"Animate clip {n2+1}: done")
                    st.session_state.t2_results=urls
                    st.session_state.t2_cost=cost_now
                    prog.progress(100); stat.success(f"done · {usd(cost_now)}")
                except Exception as e: stat.error(str(e)); alog(str(e))
                finally: st.session_state.processing=False

    if st.session_state.t2_results:
        st.markdown('<div class="sec">RESULTS</div>',unsafe_allow_html=True)
        st.markdown(stats_html([("CLIPS",len(st.session_state.t2_results)),
                                ("COST",usd(st.session_state.t2_cost))]),unsafe_allow_html=True)
        for j,url in enumerate(st.session_state.t2_results):
            st.caption(f"clip {j+1}")
            st.video(url)
            r2=requests.get(url,timeout=60)
            drive_btn(r2.content,f"animate_{j+1}.mp4","video/mp4")

    with st.expander("ABOUT THIS TAB — ANIMATE",expanded=False):
        st.markdown("""
**What it does**

Animate takes a still image and brings it to life using only a text prompt.
There is no motion reference video — you describe the desired motion in words
and Kling AI's image-to-video model generates the animation.

**When to use it**

- You have a portrait, product shot or illustration and want a short video clip.
- You want to prototype an animation idea before spending time on a motion-reference guide video.
- Social media clips from still photography.

**Prompt tips**

Be specific about movement direction and camera: *"the figure slowly raises their right arm,
camera stays fixed, soft studio lighting."* Add style words at the end: *cinematic, 4K, sharp.*

**Negative prompt**

List things to avoid: *blur, artifacts, watermark, text, distortion.*

**Limitations**

- Output is a single clip of 5 or 10 seconds.
- For longer animation or more complex motion, use the Puppeteer tab with a motion reference video.
- The model may not follow complex instructions perfectly — iterate with different prompts.

**Cost**

| Quality | Duration | Cost |
|---------|----------|------|
| Standard 720p | 5s | $0.045 |
| Standard 720p | 10s | $0.070 |
| Professional 1080p | 5s | $0.090 |
| Professional 1080p | 10s | $0.140 |
        """)

# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 3 — IMAGINE (text to image)
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="sec">SETTINGS</div>',unsafe_allow_html=True)
    i_c1,i_c2=st.columns([1,1],gap="large")

    with i_c1:
        i_prompt=st.text_area("image prompt","",height=100,
                              placeholder="a dancer in red silk dress on dark stage, dramatic lighting, cinematic",
                              key="i_prompt")
        i_neg=st.text_input("negative prompt","blur, text, watermark, artifacts",key="i_neg")
        i_ref=st.file_uploader("reference image (optional — guides style/composition)",
                               type=["jpg","jpeg","png","webp"],key="i_ref",
                               label_visibility="visible")
        if i_ref: st.image(i_ref,width=120)
        with st.expander("reference from URL or Drive",expanded=False):
            ld=url_loader("URL or Drive link",key="t3_ref_url")
            if ld:
                st.session_state["t3_ref_bytes"]=ld
            if drive_configured():
                d=drive_file_picker("image",key="t3_ref_drv")
                if d: st.session_state["t3_ref_bytes"]=d

    with i_c2:
        i_aspect=st.selectbox("aspect ratio",ASPECT_RATIOS,index=1,key="i_asp")
        i_n=st.select_slider("images to generate",[1,2,4],value=1,key="i_n")
        i_fidelity=st.slider("reference fidelity",0.0,1.0,0.5,0.05,key="i_fid",
                             help="0 = ignore reference, 1 = copy it closely") if (i_ref or st.session_state.get("t3_ref_bytes")) else 0.5
        i_price=KLING_IMG_PRICE[img_model][f"{i_n} image{'s' if i_n>1 else ''}"]
        st.markdown(stats_html([("MODEL",img_model),("ASPECT",i_aspect),
                                ("COUNT",i_n),("EST. COST",usd(i_price))]),unsafe_allow_html=True)

    st.markdown('<div class="sec">GENERATE</div>',unsafe_allow_html=True)
    if not keys_ok: st.caption("enter credentials in sidebar")
    elif not i_prompt.strip(): st.caption("enter a prompt above")
    else:
        if st.button(f"generate  {i_n} image(s) · {img_model} · est. {usd(i_price)}",
                     type="primary",disabled=st.session_state.processing,key="go3"):
            _ak=ak or S_AK; _sk=sk or S_SK
            if not (_ak and _sk): st.error("Tab 3 requires Kling AI credentials"); st.stop()
            st.session_state.t3_results=[]; st.session_state.t3_cost=0.
            st.session_state.processing=True
            stat=st.empty(); prog=st.progress(0)
            try:
                ref_b64=None
                if i_ref: ref_b64=b64(i_ref.read())
                elif st.session_state.get("t3_ref_bytes"): ref_b64=b64(st.session_state["t3_ref_bytes"])
                stat.info("submitting to Kling image generation…")
                prog.progress(20)
                tid=kling_imagine(_ak,_sk,i_prompt,i_neg,i_aspect,i_n,img_model,ref_b64,i_fidelity)
                stat.info(f"polling task {tid[:12]}…")
                prog.progress(40)
                urls=k_poll_img(_ak,_sk,tid)
                st.session_state.t3_results=urls
                st.session_state.t3_cost=i_price
                prog.progress(100)
                stat.success(f"done · {len(urls)} image(s) · {usd(i_price)}")
                if drive_configured():
                    for j,url in enumerate(urls):
                        r2=requests.get(url,timeout=60);r2.raise_for_status()
                        drive_upload(r2.content,f"imagine_{j+1}.jpg","image/jpeg")
                alog(f"Imagine: {len(urls)} images")
            except Exception as e: stat.error(str(e)); alog(str(e))
            finally: st.session_state.processing=False

    if st.session_state.t3_results:
        st.markdown('<div class="sec">RESULTS</div>',unsafe_allow_html=True)
        st.markdown(stats_html([("IMAGES",len(st.session_state.t3_results)),
                                ("COST",usd(st.session_state.t3_cost))]),unsafe_allow_html=True)
        img_cols=st.columns(min(len(st.session_state.t3_results),4))
        for j,(col,url) in enumerate(zip(img_cols,st.session_state.t3_results)):
            with col:
                st.image(url,use_container_width=True)
                r2=requests.get(url,timeout=30)
                st.download_button(f"download {j+1}",data=r2.content,
                                   file_name=f"imagine_{j+1}.jpg",mime="image/jpeg",key=f"dli_{j}")
                drive_btn(r2.content,f"imagine_{j+1}.jpg","image/jpeg",f"save {j+1} to Drive")

    with st.expander("ABOUT THIS TAB — IMAGINE",expanded=False):
        st.markdown("""
**What it does**

Imagine generates images from text using Kling AI's Kolors image model,
one of the highest-quality text-to-image models available.

**When to use it**

- Generate character references, background plates, concept art or storyboard frames.
- Create a subject image for the Puppeteer or Animate tabs.
- Produce social media visuals, thumbnails or artwork from a description.

**Prompt tips**

Be descriptive about subject, lighting, composition and style:
*"full body portrait of a female flamenco dancer, red dress, dramatic stage lighting,
shallow depth of field, Sony A7 IV, 85mm, f/1.8, cinematic."*

**Reference image**

If you supply a reference image, the model uses it as a style or composition guide.
Fidelity 0 = only loosely inspired. Fidelity 1 = very close to the reference.

**Aspect ratios**

Choose the aspect ratio that matches your intended output:
16:9 for landscape video thumbnails, 9:16 for vertical/social, 1:1 for square.

**Cost**

| Model | 1 image | 4 images |
|-------|---------|----------|
| kolors | ~$0.008 | ~$0.028 |
| kling-v1 | ~$0.005 | ~$0.018 |

Prices estimated — verify at klingai.com/pricing.
        """)

# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 4 — EDIT (image editing)
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="sec">EDIT MODE</div>',unsafe_allow_html=True)
    edit_mode=st.radio("edit_mode",
        ["INPAINT / REPAINT","VARIATION","VIRTUAL TRY-ON","EXTEND CANVAS"],
        horizontal=True,label_visibility="collapsed",key="edit_mode")

    st.markdown('<div class="sec">INPUT IMAGE</div>',unsafe_allow_html=True)
    e_c1,e_c2=st.columns([1,1],gap="large")

    with e_c1:
        if edit_mode=="VIRTUAL TRY-ON":
            st.caption("PERSON / MODEL PHOTO")
        else:
            st.caption("SOURCE IMAGE")
        e_img=st.file_uploader("e_img",type=["jpg","jpeg","png","webp"],
                               key="e_img",label_visibility="collapsed")
        if e_img:
            ek=f"{e_img.name}_{e_img.size}"
            if st.session_state.t4_img_fk!=ek:
                st.session_state.t4_img_bytes=e_img.read()
                st.session_state.t4_img_fk=ek
            st.image(e_img,use_container_width=True)
        with st.expander("load from URL or Drive",expanded=False):
            ld=url_loader("URL or Drive link",key="t4_url")
            if ld: st.session_state.t4_img_bytes=ld; st.rerun()
            if drive_configured():
                d=drive_file_picker("image",key="t4_drv")
                if d: st.session_state.t4_img_bytes=d; st.rerun()

    with e_c2:
        if edit_mode=="VIRTUAL TRY-ON":
            st.caption("GARMENT / CLOTHING IMAGE")
            e_aux=st.file_uploader("e_aux",type=["jpg","jpeg","png","webp"],
                                   key="e_aux",label_visibility="collapsed")
            if e_aux:
                ak2=f"{e_aux.name}_{e_aux.size}"
                if st.session_state.t4_aux_fk!=ak2:
                    st.session_state.t4_aux_bytes=e_aux.read()
                    st.session_state.t4_aux_fk=ak2
                st.image(e_aux,use_container_width=True)
            with st.expander("load from URL or Drive",expanded=False):
                ld=url_loader("URL or Drive link",key="t4_aux_url")
                if ld: st.session_state.t4_aux_bytes=ld; st.rerun()
                if drive_configured():
                    d=drive_file_picker("image",key="t4_aux_drv")
                    if d: st.session_state.t4_aux_bytes=d; st.rerun()
        else:
            st.markdown('<div class="sec">EDIT SETTINGS</div>',unsafe_allow_html=True)
            if edit_mode=="INPAINT / REPAINT":
                e_prompt=st.text_area("what to put there","",height=80,
                    placeholder="a golden crown on the head, photorealistic",key="e_prompt")
                e_neg=st.text_input("negative prompt","blur, artifacts",key="e_neg")
                e_fid=st.slider("fidelity to original",0.0,1.0,0.7,0.05,key="e_fid",
                                help="higher = stays closer to original image structure")
                st.caption("describe the region to change in the prompt. "
                           "For precise masking, use a dedicated inpainting tool and supply the masked image.")
            elif edit_mode=="VARIATION":
                e_prompt=st.text_area("variation description","",height=80,
                    placeholder="same composition, oil painting style, warmer tones",key="e_prompt2")
                e_neg=st.text_input("negative prompt","blur, artifacts",key="e_neg2")
                e_fid=st.slider("how different",0.0,1.0,0.4,0.05,key="e_fid2",
                                help="0 = very different, 1 = very similar to original")
            elif edit_mode=="EXTEND CANVAS":
                e_prompt=st.text_area("what to fill in extended area","",height=80,
                    placeholder="continue the background naturally, match lighting",key="e_prompt3")
                e_neg=st.text_input("negative prompt","blur, artifacts",key="e_neg3")
                e_fid=st.slider("fidelity to original edges",0.0,1.0,0.8,0.05,key="e_fid3")
                e_extend=st.selectbox("extend direction",
                    ["all sides","left","right","top","bottom"],key="e_ext")
                st.caption(f"extend: {e_extend}")
            st.markdown(stats_html([("EST. COST",usd(KLING_EDIT_PRICE.get(
                {"INPAINT / REPAINT":"inpaint","VARIATION":"variation","EXTEND CANVAS":"extend"}.get(edit_mode,"inpaint"),0.012)
            ))]),unsafe_allow_html=True)

    st.markdown('<div class="sec">GENERATE</div>',unsafe_allow_html=True)
    if not keys_ok: st.caption("enter credentials in sidebar")
    elif not st.session_state.t4_img_bytes: st.caption("upload source image above")
    elif edit_mode=="VIRTUAL TRY-ON" and not st.session_state.t4_aux_bytes:
        st.caption("upload garment image above")
    else:
        edit_cost=KLING_EDIT_PRICE.get(
            {"INPAINT / REPAINT":"inpaint","VARIATION":"variation",
             "VIRTUAL TRY-ON":"try-on","EXTEND CANVAS":"extend"}.get(edit_mode,"inpaint"),0.012)
        if st.button(f"edit  · {edit_mode} · Kling AI · est. {usd(edit_cost)}",
                     type="primary",disabled=st.session_state.processing,key="go4"):
            _ak=ak or S_AK; _sk=sk or S_SK
            if not (_ak and _sk): st.error("Tab 4 requires Kling AI credentials"); st.stop()
            st.session_state.t4_results=[]; st.session_state.t4_cost=0.
            st.session_state.processing=True
            stat=st.empty(); prog=st.progress(0)
            try:
                img64=b64(st.session_state.t4_img_bytes)
                stat.info(f"submitting {edit_mode}…"); prog.progress(20)
                if edit_mode=="VIRTUAL TRY-ON":
                    human64=b64(st.session_state.t4_img_bytes)
                    cloth64=b64(st.session_state.t4_aux_bytes)
                    tid=kling_tryon(_ak,_sk,human64,cloth64)
                    stat.info(f"polling try-on task {tid[:12]}…"); prog.progress(40)
                    urls=k_poll_img(_ak,_sk,tid,endpoint="kolors-virtual-try-on")
                else:
                    prompt_key={"INPAINT / REPAINT":"e_prompt","VARIATION":"e_prompt2",
                                "EXTEND CANVAS":"e_prompt3"}.get(edit_mode,"e_prompt")
                    neg_key={"INPAINT / REPAINT":"e_neg","VARIATION":"e_neg2",
                             "EXTEND CANVAS":"e_neg3"}.get(edit_mode,"e_neg")
                    fid_key={"INPAINT / REPAINT":"e_fid","VARIATION":"e_fid2",
                             "EXTEND CANVAS":"e_fid3"}.get(edit_mode,"e_fid")
                    ep=st.session_state.get(prompt_key,"")
                    en=st.session_state.get(neg_key,"")
                    ef=st.session_state.get(fid_key,0.5)
                    if edit_mode=="EXTEND CANVAS" and st.session_state.get("e_ext"):
                        ep=f"outpaint {st.session_state['e_ext']}: {ep}"
                    tid=kling_edit_inpaint(_ak,_sk,img64,ep,en,ef)
                    stat.info(f"polling task {tid[:12]}…"); prog.progress(40)
                    urls=k_poll_img(_ak,_sk,tid)
                st.session_state.t4_results=urls
                st.session_state.t4_cost=edit_cost
                prog.progress(100); stat.success(f"done · {len(urls)} result(s) · {usd(edit_cost)}")
                if drive_configured():
                    for j,url in enumerate(urls):
                        r2=requests.get(url,timeout=60);r2.raise_for_status()
                        drive_upload(r2.content,f"edit_{edit_mode.lower()[:8]}_{j+1}.jpg","image/jpeg")
                alog(f"Edit ({edit_mode}): {len(urls)} results")
            except Exception as e: stat.error(str(e)); alog(str(e))
            finally: st.session_state.processing=False

    if st.session_state.t4_results:
        st.markdown('<div class="sec">RESULTS</div>',unsafe_allow_html=True)
        st.markdown(stats_html([("RESULTS",len(st.session_state.t4_results)),
                                ("COST",usd(st.session_state.t4_cost))]),unsafe_allow_html=True)
        r_cols=st.columns(min(len(st.session_state.t4_results),4))
        for j,(col,url) in enumerate(zip(r_cols,st.session_state.t4_results)):
            with col:
                st.image(url,use_container_width=True)
                r2=requests.get(url,timeout=30)
                st.download_button(f"download {j+1}",data=r2.content,
                                   file_name=f"edit_{j+1}.jpg",mime="image/jpeg",key=f"dle_{j}")
                drive_btn(r2.content,f"edit_{j+1}.jpg","image/jpeg",f"save {j+1} to Drive")

    with st.expander("ABOUT THIS TAB — EDIT",expanded=False):
        st.markdown("""
**What it does**

The Edit tab uses Kling AI's image editing capabilities to modify, extend or
transform an existing image without recreating it from scratch.

**INPAINT / REPAINT**

Describe a change and the model rewrites that part of the image while preserving
the rest. Examples: change the background, replace clothing, add or remove objects.
Set fidelity high (0.7–0.9) to keep most of the original structure, lower to
allow more creative departure. For pixel-precise masking, draw a mask in a
dedicated tool (Photoshop, GIMP) and supply the masked image as the source.

**VARIATION**

Generate a new version of the image with a stylistic or compositional change.
Useful for exploring alternative colour grades, art styles, or lighting setups.

**VIRTUAL TRY-ON**

Supply a photo of a person and a photo of a garment. Kling's Kolors try-on model
composites the clothing onto the person with realistic draping and lighting.
The person and garment should each be clearly visible against a simple background.

**EXTEND CANVAS**

Outpainting — expand the image beyond its original borders. Choose a direction
and describe what should fill the new space. The model matches the existing
lighting, perspective and style.

**Endpoint note**

All edit modes except Try-On route through `/v1/images/generations` with an
image reference. Try-On uses `/v1/images/kolors-virtual-try-on`.
Verify current field names at docs.klingai.com as Kling updates their API.

**Cost (estimated)**

| Mode | Cost per result |
|------|----------------|
| Inpaint / Repaint | ~$0.012 |
| Variation | ~$0.010 |
| Virtual Try-On | ~$0.025 |
| Extend Canvas | ~$0.012 |
        """)

# ─────────────────────────────────────────────────────────────────────────────
#  FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="margin-top:3rem;color:#1a1730;font-size:.63rem;">'
    'Motion Transfer Studio v6 · docs.klingai.com · docs.dev.runwayml.com'
    '</div>',unsafe_allow_html=True)
