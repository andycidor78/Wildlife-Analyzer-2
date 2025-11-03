
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os, time, httpx

app = FastAPI(title="Wildlife Analyzer Backend v3")

# CORS: allow calls from any frontend (Lovable, local, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create simple static outputs at startup
os.makedirs("static/webmap", exist_ok=True)
if not os.path.exists("static/report.pdf"):
    with open("static/report.pdf", "wb") as f:
        f.write(b"%PDF-1.4\n% Simple placeholder report\n%%EOF")
if not os.path.exists("static/webmap/index.html"):
    with open("static/webmap/index.html", "w") as f:
        f.write("<!doctype html><html><head><meta charset='utf-8'><title>Map</title>"
                "<style>html,body,#m{height:100%;margin:0}</style>"
                "<link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'>"
                "<script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>"
                "</head><body><div id='m'></div>"
                "<script>var map=L.map('m').setView([40.65,-78.85],12);"
                "L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19}).addTo(map);"
                "L.marker([40.65,-78.85]).addTo(map).bindPopup('Backend v3 running');</script>"
                "</body></html>")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=PlainTextResponse)
def root():
    return "OK - v3 is live. POST a file to /jobs as multipart 'file' or JSON with {'input_url': 'https://...'}."

@app.post("/jobs")
async def jobs(
    file: UploadFile | None = File(default=None),
    input_url: str | None = Body(default=None)
):
    try:
        # Accept either a direct file upload OR a JSON body with an input_url to fetch
        if file is not None:
            await file.read()  # prove the upload works
        elif input_url:
            # Fetch the file to prove the URL is reachable (ignore contents)
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(input_url)
                r.raise_for_status()
        else:
            raise HTTPException(status_code=400, detail="Provide a 'file' upload or JSON body with 'input_url'.")

        time.sleep(1)
        base = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
        report = "/static/report.pdf"
        mapurl = "/static/webmap/index.html"
        if base:
            report = f"{base}{report}"
            mapurl = f"{base}{mapurl}"

        return JSONResponse({
            "status": "done",
            "report_url": report,
            "webmap_url": mapurl
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
