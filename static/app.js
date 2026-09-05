const taskList = document.querySelector("#task-list");
const template = document.querySelector("#task-template");
const form = document.querySelector("#new-task-form");
const titleInput = document.querySelector("#new-task-title");
const count = document.querySelector("#task-count");
const message = document.querySelector("#message");

function showMessage(text, isError = false) {
  message.textContent = text;
  message.classList.toggle("error", isError);
}

function updateCount(tasks) {
  const open = tasks.filter((task) => !task.done).length;
  count.textContent = `${open} ${open === 1 ? "task" : "tasks"} to tend`;
}

function renderTasks(tasks) {
  taskList.replaceChildren();
  updateCount(tasks);
  if (!tasks.length) {
    taskList.innerHTML = '<li class="empty-state">Your list is clear. Breathe easy.</li>';
    return;
  }
  tasks.forEach((task) => {
    const item = template.content.cloneNode(true);
    const row = item.querySelector(".task-item");
    const checkbox = item.querySelector(".task-check");
    const title = item.querySelector(".task-title");
    checkbox.checked = task.done;
    title.textContent = task.title;
    row.classList.toggle("is-done", task.done);
    checkbox.addEventListener("change", () => saveTask({ ...task, done: checkbox.checked }));
    item.querySelector(".delete-button").addEventListener("click", () => deleteTask(task.id));
    taskList.append(item);
  });
}

async function request(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const issue = await response.json().catch(() => ({}));
    throw new Error(issue.detail || "Something went wrong. Please try again.");
  }
  return response.status === 204 ? null : response.json();
}

async function loadTasks() {
  try {
    const tasks = await request("/tasks");
    renderTasks(tasks);
  } catch (error) {
    showMessage(error.message, true);
  }
}

async function saveTask(task) {
  try {
    await request(`/tasks/${task.id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title: task.title, done: task.done }) });
    showMessage(task.done ? "A small win, beautifully done." : "Back on the list.");
    await loadTasks();
  } catch (error) {
    showMessage(error.message, true);
    await loadTasks();
  }
}

async function deleteTask(id) {
  try {
    await request(`/tasks/${id}`, { method: "DELETE" });
    showMessage("Task removed.");
    await loadTasks();
  } catch (error) { showMessage(error.message, true); }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const title = titleInput.value.trim();
  if (!title) return showMessage("Add a few words for your task.", true);
  try {
    await request("/tasks", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title, done: false }) });
    titleInput.value = "";
    showMessage("Added to your list.");
    await loadTasks();
    titleInput.focus();
  } catch (error) { showMessage(error.message, true); }
});

loadTasks();
