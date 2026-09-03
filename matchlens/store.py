import json
import sqlite3
from pathlib import Path

from .models import MatchCreate, MatchJob


class JobStore:
    def __init__(self,path:Path): self.path=path
    def init(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS jobs(
              id TEXT PRIMARY KEY,payload TEXT NOT NULL,status TEXT NOT NULL,progress INTEGER NOT NULL,
              stage TEXT NOT NULL,result_url TEXT,report_url TEXT,error TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)""")
    def save(self,job:MatchJob):
        data=job.model_dump(mode="json")
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT OR REPLACE INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?)",(job.id,json.dumps(data["request"],ensure_ascii=False),
              job.status,job.progress,job.stage,job.result_url,job.report_url,job.error,job.created_at,job.updated_at))
    def get(self,job_id:str):
        with sqlite3.connect(self.path) as db:
            row=db.execute("SELECT * FROM jobs WHERE id=?",(job_id,)).fetchone()
        if not row:return None
        return MatchJob(id=row[0],request=MatchCreate.model_validate(json.loads(row[1])),status=row[2],progress=row[3],stage=row[4],
                        result_url=row[5],report_url=row[6],error=row[7],created_at=row[8],updated_at=row[9])
