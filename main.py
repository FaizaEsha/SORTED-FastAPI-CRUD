from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

tasks = [
    {"id": 1, "title": "Plan the week", "done": False},
    {"id": 2, "title": "Finish FastAPI assignment", "done": False},
    {"id": 3, "title": "Take an evening walk", "done": True},
]


class TaskCreate(BaseModel):
    title: str


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": "Title is required"},
    )


@app.get("/")
def root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"],
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/tasks")
def list_tasks():
    return tasks


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            return task

    return JSONResponse(
        status_code=404,
        content={"error": f"Task {task_id} not found"},
    )


@app.post("/tasks", status_code=201)
def create_task(task_data: TaskCreate):
    title = task_data.title.strip()

    if not title:
        return JSONResponse(
            status_code=400,
            content={"error": "Title is required"},
        )

    next_id = max(task["id"] for task in tasks) + 1
    new_task = {
        "id": next_id,
        "title": title,
        "done": False,
    }

    tasks.append(new_task)
    return new_task