"""A small SQLite-backed CRUD API for a personal to-do list."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Path as PathParameter, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


app = FastAPI(
    title="Classy Tasks API",
    description=(
        "A beginner-friendly CRUD API. Tasks are stored in a SQLite database"
        "(tasks.db), so they survive server restarts."
    ),
    version="1.0.0",
)

STATIC_DIRECTORY = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIRECTORY), name="static")
# The database is just one file, created automatically next to main.py.
DB_PATH = Path(__file__).parent / "tasks.db"

class TaskCreate(BaseModel):
    """The information needed to create a task."""

    title: Annotated[str, Field(min_length=1, max_length=120, examples=["Read FastAPI docs"])]


class TaskUpdate(BaseModel):
    """One or both task fields to change."""

    title: str | None = Field(default=None, min_length=1, max_length=120, examples=["Read FastAPI docs"])
    done: bool | None = Field(default=None, examples=[True])


class Task(BaseModel):
    """A task as returned by the API."""

    id: int = Field(examples=[1])
    title: str = Field(examples=["Plan the week"])
    done: bool = Field(examples=[False])






@contextmanager
def get_db():
    """Open the database, save changes when done, and always close it."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db() -> None:
    """Create the table if missing, and seed 3 tasks only if it is empty."""
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO tasks (title, done) VALUES (?, ?)",
                [
                    ("Plan the week", 0),
                    ("Finish FastAPI assignment", 0),
                    ("Take an evening walk", 1),
                ],
            )


init_db()

def row_to_task(row: sqlite3.Row) -> Task:
    """Turn a database row into a Task (done is stored as 0/1, so convert it)."""
    return Task(id=row["id"], title=row["title"], done=bool(row["done"]))


def get_task_or_404(task_id: int) -> Task | JSONResponse:
    """Return one task from the database, or the API's consistent JSON 404 error."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})
    return row_to_task(row)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_, exc: RequestValidationError) -> JSONResponse:
    """Use the assignment's required 400 response for an invalid request body."""
    title_problem = any("title" in error["loc"] for error in exc.errors())
    message = "Title is required" if title_problem else "Invalid request body"
    return JSONResponse(status_code=400, content={"error": message})


@app.get("/", tags=["Info"], summary="Describe this API")
def root() -> dict[str, str | list[str]]:
    """Return the required front-door JSON description of the API."""
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/app", include_in_schema=False)
def dashboard() -> FileResponse:
    """Serve the optional browser dashboard without replacing the API root."""
    return FileResponse(STATIC_DIRECTORY / "index.html")


@app.get("/health", tags=["Health"], summary="Check that the API is running")
def health_check() -> dict[str, str]:
    """A quick endpoint for checking the local server."""
    return {"status": "ok"}


@app.get(
    "/tasks",
    response_model=list[Task],
    tags=["Tasks"],
    summary="List every task",
    description="Returns all tasks currently stored in the SQLite database.",
)
def list_tasks() -> list[Task]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
    return [row_to_task(row) for row in rows]
@app.get(
    "/tasks/{task_id}",
    response_model=Task,
    tags=["Tasks"],
    summary="Get one task by ID",
    responses={404: {"description": "Task not found"}},
)
def read_task(task_id: Annotated[int, PathParameter(ge=1, description="The task ID")]) -> Task:
    return get_task_or_404(task_id)


@app.post(
    "/tasks",
    response_model=Task,
    status_code=status.HTTP_201_CREATED,
    tags=["Tasks"],
    summary="Create a new task",
    description="A title is required. The server assigns the ID and sets done to false.",
)
def create_task(task_data: TaskCreate) -> Task | JSONResponse:
    title = task_data.title.strip()
    if not title:
        return JSONResponse(status_code=400, content={"error": "Title is required"})
    with get_db() as conn:
        cursor = conn.execute("INSERT INTO tasks (title, done) VALUES (?, ?)", (title, 0))
        new_id = cursor.lastrowid
    return Task(id=new_id, title=title, done=False)


@app.put(
    "/tasks/{task_id}",
    response_model=Task,
    tags=["Tasks"],
    summary="Replace a task",
    description="Changes the title, done value, or both. Send at least one field.",
    responses={404: {"description": "Task not found"}},
)
def update_task(
    task_id: Annotated[int, PathParameter(ge=1, description="The task ID")], task_data: TaskUpdate
) -> Task | JSONResponse:
    task = get_task_or_404(task_id)
    if isinstance(task, JSONResponse):
        return task
    if not task_data.model_fields_set:
        return JSONResponse(status_code=400, content={"error": "Provide a title or done value"})
    if "title" in task_data.model_fields_set and task_data.title is None:
        return JSONResponse(status_code=400, content={"error": "Title cannot be empty"})
    if "done" in task_data.model_fields_set and task_data.done is None:
        return JSONResponse(status_code=400, content={"error": "Done must be true or false"})
    new_title = task.title
    if task_data.title is not None:
        title = task_data.title.strip()
        if not title:
            return JSONResponse(status_code=400, content={"error": "Title cannot be empty"})
        new_title = title
    new_done = task.done if task_data.done is None else task_data.done
    with get_db() as conn:
        conn.execute(
            "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
            (new_title, int(new_done), task_id),
        )
    return Task(id=task_id, title=new_title, done=new_done)


@app.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Tasks"],
    summary="Delete a task",
    description="Removes a task permanently from the SQLite database.",
    responses={404: {"description": "Task not found"}},
)
def delete_task(task_id: Annotated[int, PathParameter(ge=1, description="The task ID")]) -> Response:
    task = get_task_or_404(task_id)
    if isinstance(task, JSONResponse):
        return task
    with get_db() as conn:
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
