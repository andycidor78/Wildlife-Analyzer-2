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

APP_TITLE = "Wildlife Analyzer Backend – Phase 1 (real map + PDF)"
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
        ext = os.path.splitext(url)[1] or ".jpg"
        dest = dest + ext
        with open(dest, "wb") as f:
            f.write(r.content)
    return dest

def build_leaflet_map(job_dir: str, image_path: str) -> str:
    with Image.open(image_path) as im:
        width, height = im.size

    html = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>Wildlife Map</title>
<meta name='viewport' content='width=device-width, initial-scale=1.0'>
<link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'>
<script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>
<style>html,body,#map{{height:100%;margin:0;}}</style></head>
<body><div id='map'></div>
<script>
var map=L.map('map',{{crs:L.CRS.Simple,minZoom:-4}});
var bounds=[[0,0],[{height},{width}]];
L.imageOverlay('./{os.path.basename(image_path)}',bounds).addTo(map);
map.fitBounds(bounds);
L.circle([{height*0.3},{width*0.25}],{{radius:30,color:'#8B4513'}}).addTo(map);
L.circle([{height*0.7},{width*0.6}],{{radius:30,color:'#2E8B57'}}).addTo(map);
</script></body></html>"""
    map_path = os.path.join(job_dir, "map.html")
    with open(map_path, "w") as f: f.write(html)
    return map_path

def build_pdf_report(job_dir: str, image_path: str, webmap_rel: str) -> str:
    pdf_path = os.path.join(job_dir, "report.pdf")
    c = canvas.Canvas(pdf_path, pagesize=letter)
    W,H = letter
    c.setFont("Helvetica-Bold",16)
    c.drawString(72,H-72,"Wildlife Analyzer Report")
    c.setFont("Helvetica",11)
    c.drawString(72,H-100,"Interactive map: "+webmap_rel)
    c.save()
    return pdf_path

def to_public_url(path: str) -> str:
    base = public_base()
    if base: return f"{base}/{path.replace(os.sep,'/')}"
    return f"/{path.replace(os.sep,'/')}"

@app.get("/", response_class=PlainTextResponse)
def root():
    return "OK - Phase 1 live. POST to /jobs with file or JSON {input_url} to get map+PDF."

@app.post("/jobs")
async def jobs(file: Optional[UploadFile]=File(default=None),
               input_url: Optional[str]=Body(default=None)):
    job_id = uuid.uuid4().hex[:12]
    job_dir = make_job_dirs(job_id)
    if file is not None:
        img_path = save_upload_to_job(job_dir,file)
    elif input_url:
        img_path = await fetch_url_to_job(job_dir,input_url)
    else:
        raise HTTPException(status_code=400, detail="Provide file or input_url")
    map_path = build_leaflet_map(job_dir,img_path)
    pdf_path = build_pdf_report(job_dir,img_path,os.path.basename(map_path))
    return JSONResponse({
        "status":"done",
        "report_url":to_public_url(pdf_path),
        "webmap_url":to_public_url(map_path),
        "job_id":job_id
    })

app.mount("/static", StaticFiles(directory=BASE_STATIC_DIR), name="static")
