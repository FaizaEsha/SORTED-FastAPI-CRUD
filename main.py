"""A small in-memory CRUD API for a personal to-do list."""

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
        "A beginner-friendly CRUD API. Tasks live only in memory, so restarting "
        "the server restores the three starter tasks."
    ),
    version="1.0.0",
)

STATIC_DIRECTORY = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIRECTORY), name="static")


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


# The assignment intentionally uses an in-memory list instead of a database.
tasks: list[Task] = [
    Task(id=1, title="Plan the week", done=False),
    Task(id=2, title="Finish FastAPI assignment", done=False),
    Task(id=3, title="Take an evening walk", done=True),
]


def get_task_or_404(task_id: int) -> Task | JSONResponse:
    """Return one task, or raise the API's consistent JSON 404 error."""
    for task in tasks:
        if task.id == task_id:
            return task
    return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})


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
    description="Returns all tasks currently stored in memory.",
)
def list_tasks() -> list[Task]:
    return tasks


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
    next_id = max((task.id for task in tasks), default=0) + 1
    new_task = Task(id=next_id, title=title, done=False)
    tasks.append(new_task)
    return new_task


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
    if task_data.title is not None:
        title = task_data.title.strip()
        if not title:
            return JSONResponse(status_code=400, content={"error": "Title cannot be empty"})
        task.title = title
    if task_data.done is not None:
        task.done = task_data.done
    return task


@app.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Tasks"],
    summary="Delete a task",
    description="Removes a task permanently from the current in-memory list.",
    responses={404: {"description": "Task not found"}},
)
def delete_task(task_id: Annotated[int, PathParameter(ge=1, description="The task ID")]) -> Response:
    task = get_task_or_404(task_id)
    if isinstance(task, JSONResponse):
        return task
    tasks.remove(task)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
