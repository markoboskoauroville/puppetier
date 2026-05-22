# 🎬 Motion Transfer Studio v2

Animate a static image using a guide video as the motion blueprint.
Supports **Kling AI** and **RunwayML Act-One**.
Frame-accurate chunking via ffmpeg. ZIP export for Avid / Premiere / DaVinci.

---

## Pipeline

```
Guide Video (5 min)
  └─► ffmpeg: frame-accurate split into 30 × 10-second chunks
                                                         ↓
Static Subject Image ──────────────────────────────► API per chunk
                                                         ↓
                                               Output clips (ZIP)
                                                         ↓
                                          Import to NLE → place in sequence
```

---

## Why chunks?

Both Kling AI and RunwayML generate a maximum of **10 seconds per API call**.
A 5-minute guide video therefore requires **30 API calls**, each producing a
10-second clip. The app packages all clips into a ZIP with timecode-accurate
filenames so you can drop them into your NLE timeline in order.

**10 seconds is always chosen as the chunk size** — it is the API maximum and
produces fewer seams than 5-second chunks.

---

## Frame-accurate splitting

```
1. ffprobe  →  exact FPS (e.g. 29.97 = 30000/1001), total frames, duration
2. Chunk boundaries in FRAME NUMBERS — no floating-point drift over 30 chunks
3. ffmpeg decode: -ss AFTER -i (frame-exact, not keyframe seek)
4. keyint=1:min-keyint=1 → every output frame is an I-frame (safe NLE import)
5. -avoid_negative_ts make_zero → each chunk timeline starts at 0
```

---

## Cost — 5-minute video (300 seconds)

| API | Model | Chunk | Clips | Cost |
|-----|-------|-------|-------|------|
| Kling AI | Standard 720p | 10s | 30 | **$2.10** |
| Kling AI | Professional 1080p | 10s | 30 | **$4.20** |
| RunwayML | Gen-3 Alpha Turbo | 10s | 30 | **~$30.00** |
| RunwayML | Gen-3 Alpha | 10s | 30 | **~$54.00** |

Runway prices are estimates from public credit tiers. Verify at runwayml.com/pricing.

---

## Deploy to Streamlit Cloud (Free Tier)

### 1. Push to GitHub

```bash
git init && git add . && git commit -m "initial"
git remote add origin https://github.com/YOUR/YOUR-REPO
git push -u origin main
```

### 2. Create app at share.streamlit.io

Select repo → `app.py` as main file.

### 3. Add Secrets

App Settings → Secrets:

```toml
KLING_API_KEY  = "your-kling-key"
RUNWAY_API_KEY = "your-runway-key"
```

Both are optional — only the one you use needs to be set.

### 4. Deploy

Streamlit Cloud installs `requirements.txt` (Python) and `packages.txt` (ffmpeg via apt).

---

## Local Development

```bash
pip install -r requirements.txt

# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit and add your keys

streamlit run app.py
```

---

## File Structure

```
motion-transfer-studio/
├── app.py                          # Main app (1100+ lines)
├── requirements.txt                # streamlit, requests
├── packages.txt                    # ffmpeg (apt, Streamlit Cloud)
├── .gitignore
└── .streamlit/
    └── secrets.toml.example        # Template — copy to secrets.toml locally
```

---

## API Notes

**Kling AI:** `POST https://api.klingai.com/v1/videos/image2video`
with `motion_video` field containing the base64 segment.
Verify field names at [docs.klingai.com](https://docs.klingai.com).

**RunwayML:** `POST https://api.dev.runwayml.com/v1/image_to_video`
with `promptVideo` field. Requires `X-Runway-Version: 2024-11-06` header.
Verify at [docs.dev.runwayml.com](https://docs.dev.runwayml.com).

Both functions (`kling_submit`, `runway_submit`) are clearly isolated in `app.py`
for easy field-name updates.
