import asyncio
import json
import shlex
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

from .config import settings
from .models import MatchJob
from .report import build_report
from .security import sign_result, validate_remote_url


async def download(url:str,target:Path):
    host=(urlparse(url).hostname or "").lower()
    if host in {"youtube.com","www.youtube.com","m.youtube.com","youtu.be"} or host.endswith(".youtube.com"):
        validate_remote_url(url)
        limit=int(settings.max_download_gb*1024**3)
        process=await asyncio.create_subprocess_exec(
            "yt-dlp","--no-playlist","--max-filesize",str(limit),"--merge-output-format","mp4",
            "-f","bv*[height<=1080]+ba/b[height<=1080]","-o",str(target),url,
            stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,
        )
        try: stdout,stderr=await asyncio.wait_for(process.communicate(),settings.download_timeout_minutes*60)
        except asyncio.TimeoutError:
            process.kill(); await process.wait(); raise RuntimeError("YouTube download timed out")
        if process.returncode or not target.exists(): raise RuntimeError((stderr or stdout).decode(errors="replace")[-1000:])
        if target.stat().st_size>limit: target.unlink(missing_ok=True); raise ValueError("video is larger than configured limit")
        return
    limit=int(settings.max_download_gb*1024**3); size=0; current=url
    async with httpx.AsyncClient(follow_redirects=False,timeout=httpx.Timeout(settings.download_timeout_minutes*60)) as client:
        for _ in range(6):
            validate_remote_url(current)
            async with client.stream("GET",current) as response:
                if response.is_redirect:
                    location=response.headers.get("location")
                    if not location: raise ValueError("redirect has no location")
                    current=str(response.url.join(location)); continue
                response.raise_for_status()
                if int(response.headers.get("content-length",0))>limit: raise ValueError("video is larger than configured limit")
                with target.open("wb") as output:
                    async for chunk in response.aiter_bytes(1024*1024):
                        size+=len(chunk)
                        if size>limit: raise ValueError("video is larger than configured limit")
                        output.write(chunk)
                return
        raise ValueError("too many redirects")


async def run_analyzer(source:Path,job_dir:Path):
    tracks=job_dir/"tracks.json"
    if not settings.analyzer_command:
        raise RuntimeError("ANALYZER_COMMAND is not configured; refusing to invent match statistics")
    command=settings.analyzer_command.format(input=str(source),output=str(job_dir),tracks=str(tracks))
    process=await asyncio.create_subprocess_exec(*shlex.split(command),stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    try: stdout,stderr=await asyncio.wait_for(process.communicate(),settings.analyzer_timeout_minutes*60)
    except asyncio.TimeoutError:
        process.kill(); await process.wait(); raise RuntimeError("analysis timed out")
    if process.returncode: raise RuntimeError((stderr or stdout).decode(errors="replace")[-1000:])
    if not tracks.exists(): raise RuntimeError("analyzer did not create tracks.json")
    return json.loads(tracks.read_text(encoding="utf-8"))


async def process_job(job:MatchJob,store):
    job_dir=settings.data_dir/"jobs"/job.id; job_dir.mkdir(parents=True,exist_ok=True)
    def update(status,progress,stage,error=None):
        job.status=status; job.progress=progress; job.stage=stage; job.error=error; job.updated_at=datetime.now(timezone.utc).isoformat(); store.save(job)
    try:
        source=job_dir/"source.mp4"; cached=job_dir/"analysis.json"
        if cached.exists():
            update("processing",80,"reporting"); result=json.loads(cached.read_text(encoding="utf-8"))
        else:
            update("processing",5,"downloading")
            if job.request.source.type.value=="url": await download(job.request.source.ref,source)
            else:
                upload=settings.data_dir/"uploads"/job.request.source.ref
                if not upload.exists(): raise RuntimeError("uploaded Telegram video not found")
                await asyncio.to_thread(shutil.copyfile,upload,source)
            update("processing",20,"tracking"); result=await run_analyzer(source,job_dir)
            cached.write_text(json.dumps(result,ensure_ascii=False),encoding="utf-8")
        tracker=job.request.target.tracker_id
        if tracker is None:
            base=settings.public_base_url.rstrip("/"); preview=job_dir/"preview.jpg"
            if preview.exists() and base:
                expires,signature=sign_result(job.id,"preview.jpg",settings.api_key,settings.signed_url_ttl_minutes)
                job.result_url=f"{base}/v1/results/{job.id}/preview.jpg?expires={expires}&signature={signature}"
            else: job.result_url=None
            update("awaiting_selection",70,"select_player")
            return
        update("processing",85,"reporting"); build_report(job_dir,result,tracker)
        base=settings.public_base_url.rstrip("/")
        expires,signature=sign_result(job.id,"report.html",settings.api_key,settings.signed_url_ttl_minutes)
        query=f"?expires={expires}&signature={signature}"
        job.report_url=f"{base}/v1/results/{job.id}/report.html{query}" if base else f"/v1/results/{job.id}/report.html{query}"
        job.result_url=job.report_url; update("completed",100,"completed")
    except Exception as exc: update("failed",job.progress,"failed",str(exc)[:1000])
