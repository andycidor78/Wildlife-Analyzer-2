from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os, uuid
import httpx
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

APP_TITLE = "Wildlife Analyzer Backend – Phase 1 (map + PDF + viewer)"
BASE_STATIC_DIR = "static"
JOBS_DIR = os.path.join(BASE_STATIC_DIR, "jobs")

app = FastAPI(title=APP_TITLE)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

os.makedirs(JOBS_DIR, exist_ok=True)

def public_base() -> str:
    return (os.getenv("PUBLIC_BASE_URL") or "").rstrip("/")

def make_job_dirs(job_id: str) -> str:
    job_dir = os.path.join(JOBS_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    return job_dir

def save_upload_to_job(job_dir: str, upload: UploadFile) -> str:
    ext = os.path.splitext(upload.filename or "upload")[1] or ".bin"
    dest = os.path.join(job_dir, "input" + ext)
    with open(dest, "wb") as f:
        f.write(upload.file.read())
    return dest

async def fetch_url_to_job(job_dir: str, url: str) -> str:
    dest = os.path.join(job_dir, "input_from_url")
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(url)
        r.raise_for_status()
        ext = os.path.splitext(url)[1]
        if not ext:
            ct = r.headers.get("content-type","")
            if "png" in ct: ext = ".png"
            elif "jpeg" in ct or "jpg" in ct: ext = ".jpg"
            elif "tiff" in ct or "tif" in ct: ext = ".tif"
            else: ext = ".bin"
        dest = dest + ext
        with open(dest, "wb") as f:
            f.write(r.content)
    return dest

def build_leaflet_map(job_dir: str, image_path: str) -> str:
    try:
        with Image.open(image_path) as im:
            width, height = im.size
    except Exception:
        width, height = 2000, 1500

    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Wildlife Web Map – {os.path.basename(job_dir)}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    html, body, #map {{ height: 100%; margin: 0; }}
    .legend {{ position:absolute; bottom:10px; left:10px; background:rgba(255,255,255,.95);
               padding:10px 12px; border-radius:8px; font:13px sans-serif; border:1px solid #d8d8d8; }}
    .swatch {{ display:inline-block; width:12px; height:12px; margin-right:6px; border:1px solid #333; }}
    .brown {{ background:#8B4513; }} .green {{ background:#2E8B57; }} .red {{ background:#b30d0d; }}
    .brand {{ position:absolute; top:10px; right:10px; background:#a68a6a; color:#fff; padding:6px 10px; border-radius:6px; font:13px sans-serif; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <div class="brand">Wildlife Analyzer — Contact: andycidor78@gmail.com • 814-418-0534</div>
  <div class="legend">
    <div><span class="swatch brown"></span>Potential Bedding</div>
    <div><span class="swatch green"></span>Potential Feeding</div>
    <div><span class="swatch red"></span>Travel Corridor</div>
  </div>
  <script>
    const w = {width}, h = {height};
    const map = L.map('map', {{ crs: L.CRS.Simple, minZoom: -4 }});
    const bounds = [[0,0],[h,w]];
    L.imageOverlay('./{os.path.basename(image_path)}', bounds).addTo(map);
    map.fitBounds(bounds);
    L.circle([h*0.30, w*0.25], {{radius: 30, color:'#8B4513'}}).addTo(map).bindPopup('Potential Bedding (demo)');
    L.circle([h*0.70, w*0.60], {{radius: 30, color:'#2E8B57'}}).addTo(map).bindPopup('Potential Feeding (demo)');
    L.polyline([[h*0.30,w*0.25],[h*0.50,w*0.43],[h*0.70,w*0.60]], {{color:'#b30d0d', dashArray:'4,6'}}).addTo(map).bindPopup('Travel Corridor (demo)');
  </script>
</body>
</html>"""
    map_path = os.path.join(job_dir, "map.html")
    with open(map_path, "w", encoding="utf-8") as f:
        f.write(html)
    return map_path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def build_pdf_report(job_dir: str, image_path: str, webmap_rel: str) -> str:
    pdf_path = os.path.join(job_dir, "report.pdf")
    c = canvas.Canvas(pdf_path, pagesize=letter)
    W, H = letter

    def header_footer(title):
        c.setFillColorRGB(0.29, 0.20, 0.13); c.rect(0, H-70, W, 70, stroke=0, fill=1)
        c.setFillColorRGB(0.65, 0.74, 0.52); c.rect(0, H-78, W, 8, stroke=0, fill=1)
        c.setFillColorRGB(1,1,1); c.setFont("Helvetica-Bold", 16)
        c.drawString(72, H-50, title)
        c.setFillColorRGB(0.65, 0.74, 0.52); c.rect(0, 0, W, 40, stroke=0, fill=1)
        c.setFillColorRGB(0,0,0); c.setFont("Helvetica", 9)
        c.drawCentredString(W/2, 15, "Andy Cidor  •  Nicktown, PA  •  814-418-0534  •  andycidor78@gmail.com")

    header_footer("Wildlife Analyzer — Habitat Mapping & Deer Movement Analysis")
    c.setFillColorRGB(0,0,0); c.setFont("Helvetica-Bold", 24); c.drawString(72, H-140, "Client Report")
    c.setFont("Helvetica", 12)
    c.drawString(72, H-170, "Prepared for: ________________________________")
    c.drawString(72, H-190, "Property / Tract: _____________________________")
    c.drawString(72, H-210, "Acreage: __________   Date of Imagery: __________")
    c.setFont("Helvetica", 11)
    txt = c.beginText(72, H-260)
    txt.textLines([
        "This report summarizes imagery-based observations to support deer habitat planning.",
        "It includes a web map link, preliminary observations, and actionable recommendations.",
        "Use this as a starting point for ongoing management across the seasons."
    ])
    c.drawText(txt); c.showPage()

    header_footer("Summary & Observations")
    c.setFont("Helvetica-Bold", 14); c.drawString(72, H-120, "Summary")
    c.setFont("Helvetica", 11)
    t = c.beginText(72, H-140)
    t.textLines([
        "• Imagery analyzed: RGB/thermal (where available); resolution adequate for structural features.",
        "• Terrain context: edges, cover density, and likely movement paths reviewed at a property scale.",
        "• Notes: This version provides preliminary AI-assisted markings; verify in-field and refine over time."
    ])
    c.drawText(t)
    c.setFont("Helvetica-Bold", 14); c.drawString(72, H-220, "Key Findings")
    c.setFont("Helvetica", 11)
    t = c.beginText(72, H-240)
    t.textLines([
        "• Bedding areas (brown): sheltered zones with adjacent escape cover, leeward tendencies where applicable.",
        "• Feeding areas (green): openings/edges likely to draw activity at dusk/dawn; prioritize quiet approach.",
        "• Travel corridors (dashed red): connect bedding-to-feed; use wind-smart access."
    ])
    c.drawText(t); c.showPage()

    header_footer("Interactive Web Map")
    c.setFont("Helvetica", 11)
    c.drawString(72, H-120, "Open the interactive web map to view markers and overlays for this analysis:")
    c.setFillColorRGB(0,0,1)
    c.drawString(72, H-140, webmap_rel)
    c.linkURL(webmap_rel, (72, H-145, 340, H-130), relative=1)
    c.setFillColorRGB(0,0,0)
    c.drawString(72, H-170, "Tip: Use the legend and tap markers for details (bedding, feeding, corridors).")
    c.showPage()

    header_footer("Recommendations & Next Steps")
    c.setFont("Helvetica-Bold", 14); c.drawString(72, H-120, "Management Recommendations")
    c.setFont("Helvetica", 11)
    t = c.beginText(72, H-140)
    t.textLines([
        "• Access & Wind: Plan entry/exit to avoid crossing projected travel routes.",
        "• Plantings: Add soft mast and conifers near edges for year-round attraction and cover.",
        "• Stand Sites: Prioritize downwind edges near corridor intersections; adjust by season.",
        "• Monitoring: Re-fly in late summer and late winter to update movement patterns."
    ])
    c.drawText(t)
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(72, 80, "This report aids planning and should be combined with on-site observations and local regulations.")
    c.showPage(); c.save()
    return pdf_path

def build_report_viewer(job_dir: str, pdf_filename: str) -> str:
    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Wildlife Analyzer – Report</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>html,body,iframe{{height:100%;width:100%;margin:0;border:0}} .bar{{padding:8px 12px;background:#a68a6a;color:#fff;font:14px sans-serif}}</style>
</head>
<body>
  <div class="bar">Wildlife Analyzer — <a href="./{pdf_filename}" style="color:#fff;text-decoration:underline">Download PDF</a></div>
  <iframe src="./{pdf_filename}" title="Report PDF"></iframe>
</body>
</html>"""
    viewer_path = os.path.join(job_dir, "report.html")
    with open(viewer_path, "w", encoding="utf-8") as f:
        f.write(html)
    return viewer_path

def to_public_url(path: str) -> str:
    base = public_base()
    if base:
        return f"{base}/{path.replace(os.sep, '/')}"
    return f"/{path.replace(os.sep, '/')}"

@app.get("/", response_class=PlainTextResponse)
def root():
    return "OK - Phase 1 (with viewer) live. POST to /jobs with file or JSON {input_url}."

@app.post("/jobs")
async def jobs(file: Optional[UploadFile] = File(default=None),
               input_url: Optional[str] = Body(default=None)):
    job_id = uuid.uuid4().hex[:12]
    job_dir = make_job_dirs(job_id)

    if file is not None:
        img_path = save_upload_to_job(job_dir, file)
    elif input_url:
        img_path = await fetch_url_to_job(job_dir, input_url)
    else:
        raise HTTPException(status_code=400, detail="Provide a 'file' upload or JSON body with 'input_url'.")

    map_path = build_leaflet_map(job_dir, img_path)
    pdf_path = build_pdf_report(job_dir, img_path, os.path.basename(map_path))
    viewer_path = build_report_viewer(job_dir, os.path.basename(pdf_path))

    return JSONResponse({
        "status": "done",
        "report_url": to_public_url(pdf_path),
        "report_viewer_url": to_public_url(viewer_path),
        "webmap_url": to_public_url(map_path),
        "job_id": job_id
    })

app.mount("/static", StaticFiles(directory=BASE_STATIC_DIR), name="static")
