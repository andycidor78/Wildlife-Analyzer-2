
from fastapi import FastAPI, UploadFile, File, HTTPException, Body, Request, Form
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os, time, httpx, json

app = FastAPI(title="Wildlife Analyzer Backend v4 (robust)")

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
                "L.marker([40.65,-78.85]).addTo(map).bindPopup('Backend v4 running');</script>"
                "</body></html>")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=PlainTextResponse)
def root():
    return "OK - v4 is live. POST a file to /jobs as multipart 'file' or send input_url via JSON, form, or query."

def build_response():
    base = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    report = "/static/report.pdf"
    mapurl = "/static/webmap/index.html"
    if base:
        report = f"{base}{report}"
        mapurl = f"{base}{mapurl}"
    return JSONResponse({"status": "done", "report_url": report, "webmap_url": mapurl})

@app.post("/jobs")
async def jobs(
    request: Request,
    file: UploadFile | None = File(default=None),
    input_url: str | None = Body(default=None),
    input_url_form: str | None = Form(default=None),
):
    try:
        # 1) If a file was uploaded (multipart) → accept immediately
        if file is not None:
            await file.read()  # consume to validate
            time.sleep(0.2)
            return build_response()

        # 2) Try JSON body explicitly
        if input_url:
            time.sleep(0.1)
            return build_response()

        # 3) Try to parse raw body as JSON manually (handles odd headers)
        raw = await request.body()
        if raw:
            try:
                data = json.loads(raw.decode("utf-8"))
                if isinstance(data, dict) and data.get("input_url"):
                    return build_response()
            except Exception:
                pass

        # 4) Try form fields (x-www-form-urlencoded or multipart without file)
        if input_url_form:
            return build_response()
        try:
            form = await request.form()
            if form and form.get("input_url"):
                return build_response()
        except Exception:
            pass

        # 5) Try query string ?input_url=...
        q = request.query_params.get("input_url")
        if q:
            return build_response()

        raise HTTPException(status_code=400, detail="Provide a 'file' upload or JSON/form/query with 'input_url'.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
