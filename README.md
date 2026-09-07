# ✦ SORTED.

> A quiet, considered to-do list, built as a FastAPI CRUD API, with a small browser space for the things that matter.

**SORTED.** is an Assignment for FlyRank's Backend AI Engineering Track (Week 2 — *Build your first CRUD API*). At its core is a deliberately small, in-memory Task API: create, read, update, and delete tasks, with all four CRUD operations mapped cleanly onto their HTTP methods. A lightweight beige, brown, and black dashboard sits on top, so the same API is genuinely usable, not just a set of endpoints on paper.

It was built to make the request → response loop feel tangible — one task, one endpoint, one clear answer at a time.

---

## ✦ Highlights

- ✅ **Full CRUD** — create, list, read, update, and delete tasks
- 🐍 **Python + FastAPI** — an approachable backend framework with automatic docs
- 📛 **Correct status codes throughout** — `200`, `201`, `204`, `400`, `404`, each with a clear JSON error where it applies
- 🛡️ **Server-side validation** — a missing or empty title is rejected before it ever reaches the list
- 📚 **Swagger UI** — interactive docs and a full "Try it out" CRUD cycle at `/docs`
- 🧠 **In-memory storage, on purpose** — no database yet; restarting resets the list, and that's the lesson, not a bug
- 🎨 **SORTED. dashboard** — a responsive personal task interface at `/app`
- 🧪 **curl-testable** — every endpoint verified from the terminal, not just the browser

---

## 🛠️ Built With

- **Python 3.10+**
- **FastAPI** — API framework, with OpenAPI/Swagger built in
- **Uvicorn** — local dev server
- **HTML, CSS, and JavaScript** — the SORTED. dashboard

---

## 🚀 Run It

```bash
git clone https://github.com/FaizaEsha/SORTED-FastAPI-CRUD.git
cd SORTED-FastAPI-CRUD
py -m venv .venv
.\.venv\Scripts\Activate.ps1        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Then start the server — **this is the one command that runs everything**:

```bash
uvicorn main:app --reload
```

| Page | Address |
|---|---|
| API front door | `http://127.0.0.1:8000/` |
| SORTED. dashboard | `http://127.0.0.1:8000/app` |
| Swagger UI | `http://127.0.0.1:8000/docs` |
| Health check | `http://127.0.0.1:8000/health` |

Stop with `Ctrl + C`. Restart it and the list returns to its three original tasks — see [The Mortality Experiment](#️-the-mortality-experiment).

---

## 🔗 API Endpoints

| Method | Path | What it does | Success | Errors |
|---|---|---|---|---|
| `GET` | `/` | Describes the API | `200` | — |
| `GET` | `/health` | Checks the server is alive | `200` `{"status":"ok"}` | — |
| `GET` | `/tasks` | Returns every task | `200` + list | — |
| `GET` | `/tasks/{id}` | Returns one task | `200` + task | `404` unknown id |
| `POST` | `/tasks` | Creates a task | `201` + created task | `400` missing/empty title |
| `PUT` | `/tasks/{id}` | Updates title and/or done | `200` + updated task | `400` invalid body · `404` unknown id |
| `DELETE` | `/tasks/{id}` | Removes a task | `204 No Content` | `404` unknown id |

Every error returns a plain JSON message, e.g.:
```json
{ "error": "Task 99 not found" }
```

---

## 🧪 Tested with curl

```bash
curl -i http://127.0.0.1:8000/tasks
```

```text
HTTP/1.1 200 OK
content-type: application/json

[
  {"title":"Plan the week","done":false,"id":1},
  {"title":"Finish FastAPI assignment","done":false,"id":2},
  {"title":"Take an evening walk","done":true,"id":3}
]
```

Creating a task (PowerShell — write the body to a temp file first):
```powershell
curl.exe -i -X POST http://127.0.0.1:8000/tasks -H "Content-Type: application/json" --data-binary "@create-task.json"
```
```json
{ "title": "Practice CRUD" }
```

---

## 📚 Swagger UI

FastAPI generates interactive docs automatically at `/docs` — no setup required. Every endpoint is listed, and the full create → read → update → delete cycle works through **Try it out**, no curl needed.

![Swagger UI screenshot](docs/swagger_post_response.png)

---

## 📁 Project Structure

```text
├── static/
│   ├── index.html       # SORTED. dashboard structure
│   ├── styles.css       # Beige, brown, and black responsive styling
│   └── app.js           # Frontend requests to the FastAPI CRUD endpoints
├── main.py              # Models, seed tasks, routes, validation, error handling
├── requirements.txt     # FastAPI and Uvicorn
├── .gitignore
└── README.md
```

---

## 🕯️ The Mortality Experiment

I created a few tasks, stopped the server, and started it again. The new tasks disappeared and the three seed tasks came back — because the task list lives only in the server's memory, and stopping the server clears it. That's intentional: this assignment is about learning CRUD cleanly before a database enters the picture.

---

## 🎯 What I Learned

- Mapping CRUD to `POST`, `GET`, `PUT`, and `DELETE`, and choosing the right status code for each outcome
- Writing server-side validation instead of trusting the client
- Using Swagger UI to both document and test an API
- Why in-memory data resets on restart — and why that's a feature at this stage, not a flaw
- Wiring a small frontend to a backend API with `fetch`

---

## Note

Built to run locally as part of FlyRank's Backend AI Engineering Track. No database, accounts, authentication, or cloud deployment deliberately, since those would distract from the CRUD learning goal of this stage.

## Author

**Faiza Ahmed Esha**

## License

You're welcome to clone this, run it locally, and test it end to end, that's the best way to see how the CRUD cycle actually behaves. Please don't submit this code, or a lightly edited copy of it, as your own coursework; use it to learn from, not to hand in.
