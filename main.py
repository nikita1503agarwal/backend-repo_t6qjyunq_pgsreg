import os
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import Task, ScheduleBlock

app = FastAPI(title="Priority Calendar API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Priority Calendar API Running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    return response


# ---------- Scheduling Logic ----------
class ScheduleRequest(BaseModel):
    start_day: datetime
    end_day: datetime
    workday_start_hour: int = 9
    workday_end_hour: int = 17
    min_block_minutes: int = 15


def generate_schedule(tasks: List[Task], req: ScheduleRequest) -> List[ScheduleBlock]:
    # Filter tasks not done
    pending = [t for t in tasks if t.status != "done"]
    # Sort by priority desc, due date asc (None goes last), then shorter tasks first
    pending.sort(key=lambda t: (
        -t.priority,
        t.due_at or datetime.max,
        t.estimated_duration_minutes,
    ))

    # Build available time slots per day
    cursor = req.start_day
    slots: List[ScheduleBlock] = []
    while cursor.date() <= req.end_day.date():
        day_start = datetime(cursor.year, cursor.month, cursor.day, req.workday_start_hour, 0)
        day_end = datetime(cursor.year, cursor.month, cursor.day, req.workday_end_hour, 0)
        # Skip past time if scheduling starts today and time already passed
        now = datetime.utcnow()
        if day_start.date() == now.date():
            day_start = max(day_start, now)
        # Walk through day and place tasks greedily
        t_ptr = day_start
        for task in pending:
            if getattr(task, "_scheduled", False):
                continue
            duration = timedelta(minutes=max(req.min_block_minutes, task.estimated_duration_minutes))
            # If due_at exists, ensure block ends before due
            due_ok = True
            if task.due_at is not None:
                due_ok = t_ptr + duration <= task.due_at
            if t_ptr + duration <= day_end and due_ok:
                block = ScheduleBlock(
                    title=task.title,
                    task_id=None,  # will be filled when storing
                    start=t_ptr,
                    end=t_ptr + duration,
                    description=task.description,
                )
                slots.append(block)
                setattr(task, "_scheduled", True)
                t_ptr = t_ptr + duration
        cursor = cursor + timedelta(days=1)
    return slots


# ---------- API Endpoints ----------

@app.post("/api/tasks", response_model=dict)
async def create_task(task: Task):
    task_id = create_document("task", task)
    return {"id": task_id}


@app.get("/api/tasks", response_model=List[dict])
async def list_tasks(status: Optional[str] = None):
    flt = {}
    if status:
        flt["status"] = status
    docs = get_documents("task", flt)
    # Convert ObjectId to str for frontend
    for d in docs:
        d["_id"] = str(d.get("_id"))
    return docs


@app.post("/api/schedule", response_model=List[ScheduleBlock])
async def schedule(req: ScheduleRequest):
    # Load tasks
    docs = get_documents("task", {"status": {"$ne": "done"}})
    tasks: List[Task] = []
    for d in docs:
        try:
            # Map Mongo doc to Task - ignore extra fields
            tasks.append(Task(
                title=d.get("title"),
                description=d.get("description"),
                priority=int(d.get("priority", 3)),
                estimated_duration_minutes=int(d.get("estimated_duration_minutes", 30)),
                due_at=d.get("due_at"),
                status=d.get("status", "todo"),
                tags=d.get("tags", []),
            ))
        except Exception:
            continue

    blocks = generate_schedule(tasks, req)
    return blocks


# ---------- Google Calendar Integration (placeholder route) ----------
@app.get("/api/google/auth-url")
async def google_auth_url():
    # In a real implementation, we'd generate an OAuth URL here.
    # For this scaffold, return a placeholder URL for the frontend to open.
    return {"url": "https://accounts.google.com/o/oauth2/v2/auth"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
