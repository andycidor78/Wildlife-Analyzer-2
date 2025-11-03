from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os, time

app = FastAPI(title="Wildlife Analyzer Simple Backend")

# Create static demo outputs for testing
os.makedirs("static/webmap", exist_ok=True)
pdf_path = "static/report.pdf"
if not os.path.exists(pdf_path):
    with open(pdf_path, "wb") as f:
        f.write(b"%PDF-1.4\n% Placeholder report\n%%EOF")

map_path = "static/webmap/index.html"
if not os.path.exists(map_path):
    with open(map_path, "w") as f:
        f.write("""<!doctype html><html><head><meta charset='utf-8'><title>Webmap</title>
<style>html,body,#m{height:100%;margin:0}</style>
<link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'>
<script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script></head>
<body><div id='m'></div>
<script>
 var map=L.map('m').setView([40.65,-78.85],12);
 L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19}).addTo(map);
 L.marker([40.65,-78.85]).addTo(map).bindPopup('Demo webmap ready');
</script></body></html>""")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.post("/jobs")
async def jobs(file: UploadFile = File(...)):
    try:
        _ = await file.read()
        time.sleep(2)
        base = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
        if not base:
            return JSONResponse({
                "status": "done",
                "report_url": "/static/report.pdf",
                "webmap_url": "/static/webmap/index.html"
            })
        return JSONResponse({
            "status": "done",
            "report_url": f"{base}/static/report.pdf",
            "webmap_url": f"{base}/static/webmap/index.html"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    return {"ok": True, "try": "POST a file to /jobs as multipart form field 'file'."}
