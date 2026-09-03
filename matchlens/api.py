import asyncio
import secrets
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse

from .config import settings
from .models import MatchCreate, MatchJob, TargetSelection
from .pipeline import process_job
from .security import verify_result
from .store import JobStore

store=JobStore(settings.data_dir/"jobs.sqlite3"); queue:asyncio.Queue[str]=asyncio.Queue()

def authenticate(x_api_key:str|None=Header(default=None)):
    if settings.api_key and (not x_api_key or not secrets.compare_digest(x_api_key,settings.api_key)):
        raise HTTPException(401,"invalid API key")

async def worker():
    while True:
        job_id=await queue.get()
        try:
            job=store.get(job_id)
            if job: await process_job(job,store)
        finally: queue.task_done()

@asynccontextmanager
async def lifespan(app:FastAPI):
    if settings.public_base_url and not settings.api_key:
        raise RuntimeError("API_KEY is required when PUBLIC_BASE_URL is configured")
    store.init(); tasks=[asyncio.create_task(worker()) for _ in range(max(1,settings.worker_concurrency))]
    yield
    for task in tasks: task.cancel()

app=FastAPI(title="MatchLens Worker",version="0.1.0",lifespan=lifespan)

@app.get("/health")
def health(): return {"status":"ok","queue":queue.qsize(),"analyzer_ready":bool(settings.analyzer_command)}

@app.post("/v1/matches",dependencies=[Depends(authenticate)])
async def create_match(request:MatchCreate):
    job=MatchJob(id=uuid.uuid4().hex,status="queued",request=request); store.save(job); await queue.put(job.id)
    return {"id":job.id,"job_id":job.id,"status":job.status}

@app.post("/v1/uploads",dependencies=[Depends(authenticate)])
async def upload_video(file:UploadFile=File(...)):
    upload_id=uuid.uuid4().hex+".mp4"; folder=settings.data_dir/"uploads"; folder.mkdir(parents=True,exist_ok=True)
    target=folder/upload_id; limit=int(settings.max_download_gb*1024**3); size=0
    try:
        with target.open("wb") as output:
            while chunk:=await file.read(1024*1024):
                size+=len(chunk)
                if size>limit: raise HTTPException(413,"video is larger than configured limit")
                output.write(chunk)
    except Exception:
        target.unlink(missing_ok=True); raise
    finally: await file.close()
    return {"ref":upload_id,"size":size}

@app.get("/v1/matches/{job_id}",dependencies=[Depends(authenticate)])
def get_match(job_id:str):
    job=store.get(job_id)
    if not job: raise HTTPException(404,"job not found")
    payload=job.model_dump(); metrics=settings.data_dir/"jobs"/job_id/"metrics.json"
    if metrics.exists():
        import json
        payload["metrics"]=json.loads(metrics.read_text(encoding="utf-8"))
    return payload

@app.post("/v1/matches/{job_id}/target",dependencies=[Depends(authenticate)])
async def select_target(job_id:str,selection:TargetSelection):
    job=store.get(job_id)
    if not job: raise HTTPException(404,"job not found")
    if job.status not in {"awaiting_selection","failed"}: raise HTTPException(409,"job is not waiting for player selection")
    job.request.target.tracker_id=selection.tracker_id; job.status="queued"; job.stage="selected"; job.error=None; store.save(job)
    await queue.put(job.id); return {"id":job.id,"status":job.status,"tracker_id":selection.tracker_id}

@app.get("/v1/results/{job_id}/{filename}")
def result(job_id:str,filename:str,expires:int=0,signature:str="",x_api_key:str|None=Header(default=None)):
    if filename not in {"report.html","radar.svg","metrics.json","annotated.mp4","preview.jpg"}: raise HTTPException(404)
    keyed=bool(x_api_key and settings.api_key and secrets.compare_digest(x_api_key,settings.api_key))
    signed=bool(signature and verify_result(job_id,filename,expires,signature,settings.api_key))
    if not keyed and not signed: raise HTTPException(401,"invalid or expired result link")
    path=settings.data_dir/"jobs"/job_id/filename
    if not path.exists(): raise HTTPException(404)
    return FileResponse(path)
