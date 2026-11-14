"use strict";

(() => {
  const STORAGE_KEY = "student-planner.web.tasks.v1";
  const COLORS = ["violet", "pink", "teal", "orange", "blue"];
  const app = document.querySelector("#app");
  const dialog = document.querySelector("#task-dialog");
  const form = document.querySelector("#task-form");
  const importInput = document.querySelector("#import-file");
  const tabs = [...document.querySelectorAll(".tab")];
  const dateFormat = new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" });
  let tasks = loadTasks();
  let activeTab = "today";
  let taskFilter = "upcoming";
  let search = "";
  let selectedDate = new Date();
  let displayedMonth = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), 1);
  let dailyBudget = 120;
  let feedback = "";

  function localDateString(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function loadTasks() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? normalizeTasks(JSON.parse(saved)) : [];
    } catch (error) {
      window.alert(`Saved tasks could not be loaded: ${error.message}`);
      return [];
    }
  }

  function persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
      return true;
    } catch (error) {
      window.alert(`Your changes could not be saved on this device: ${error.message}`);
      return false;
    }
  }

  function normalizeTasks(items) {
    if (!Array.isArray(items)) throw new Error("The JSON file must contain a list of tasks.");
    return items.map((item, index) => {
      const name = String(item.task_name ?? item.name ?? "").trim();
      const subject = String(item.task_subject ?? item.subject ?? "").trim();
      const dueDate = String(item.due_date ?? item.dueDate ?? "");
      const estimatedMinutes = Number(item.estimated_time ?? item.estimatedMinutes);
      const dailyTargetMinutes = Number(item.daily_work_target ?? item.dailyTargetMinutes ?? 30);
      const priority = Number(item.priority ?? 5);
      const loggedMinutes = Number(item.time_spent ?? item.loggedMinutes ?? 0);
      if (!name || !subject || !isValidDate(dueDate) ||
          !Number.isInteger(estimatedMinutes) || estimatedMinutes < 1 ||
          !Number.isInteger(dailyTargetMinutes) || dailyTargetMinutes < 1 ||
          !Number.isInteger(priority) || priority < 1 || priority > 10 ||
          !Number.isFinite(loggedMinutes) || loggedMinutes < 0) {
        throw new Error(`Task ${index + 1} has invalid name, subject, date, time, or priority.`);
      }
      const estimated = Math.min(estimatedMinutes, 1440);
      const logged = Math.min(Math.floor(loggedMinutes), estimated);
      return {
        id: String(item.id ?? makeId()),
        name,
        subject,
        dueDate,
        estimatedMinutes: estimated,
        dailyTargetMinutes: Math.min(dailyTargetMinutes, 600),
        loggedMinutes: logged,
        priority,
        isComplete: Boolean(item.isComplete) || item.status === "done" || logged >= estimated,
      };
    });
  }

  function isValidDate(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
    const date = new Date(`${value}T12:00:00`);
    return Number.isFinite(date.getTime()) && localDateString(date) === value;
  }

  function makeId() {
    return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }

  function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, char => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[char]);
  }

  function dayStart(value) {
    return new Date(`${value}T00:00:00`);
  }

  function isOverdue(task) {
    return !task.isComplete && task.dueDate < localDateString(new Date());
  }

  function remaining(task) {
    return task.isComplete ? 0 : Math.max(0, task.estimatedMinutes - task.loggedMinutes);
  }

  function sortedTasks(items) {
    return [...items].sort((a, b) => a.dueDate.localeCompare(b.dueDate) || b.priority - a.priority || a.name.localeCompare(b.name));
  }

  function makePlan() {
    let remainingBudget = dailyBudget;
    return sortedTasks(tasks.filter(task => !task.isComplete && remaining(task) > 0))
      .map(task => {
        const target = Math.min(Math.max(15, task.dailyTargetMinutes), remaining(task));
        const minutes = Math.min(target, remainingBudget);
        remainingBudget -= minutes;
        return { task, minutes };
      })
      .filter(item => item.minutes > 0);
  }

  function emptyState(icon, title, message) {
    return `<section class="empty-state"><div class="empty-icon" aria-hidden="true">${icon}</div><h3>${title}</h3><p>${message}</p></section>`;
  }

  function statCard(icon, value, label, tint) {
    return `<div class="stat-card"><span class="stat-icon tint-${tint}" aria-hidden="true">${icon}</span><div class="stat-value">${escapeHTML(value)}</div><div class="stat-label">${label}</div></div>`;
  }

  function pageHeading(title, subtitle) {
    return `<header class="page-heading"><h1>${title}</h1><p>${subtitle}</p></header>`;
  }

  function taskCard(task) {
    const done = task.isComplete;
    const dateClass = isOverdue(task) ? "task-date overdue" : "task-date";
    return `
      <article class="task-card">
        <button class="complete-button ${done ? "done" : ""}" data-action="toggle" data-id="${escapeHTML(task.id)}" aria-label="${done ? "Mark incomplete" : "Complete"} ${escapeHTML(task.name)}">${done ? "✓" : "○"}</button>
        <div class="task-copy">
          <strong class="${done ? "struck" : ""}">${escapeHTML(task.name)}</strong>
          <div class="task-meta">
            <span class="subject-pill">${escapeHTML(task.subject)}</span>
            <span class="task-time">${remaining(task)} min left</span>
            <span class="${dateClass}">${dateFormat.format(dayStart(task.dueDate))}</span>
          </div>
        </div>
        <span class="priority-mark">P${task.priority}</span>
        <div class="task-actions">
          ${done ? "" : `<button class="mini-button log" data-action="log" data-id="${escapeHTML(task.id)}" aria-label="Log 15 study minutes">15m</button>`}
          <button class="mini-button" data-action="edit" data-id="${escapeHTML(task.id)}" aria-label="Edit ${escapeHTML(task.name)}">✎</button>
          <button class="mini-button delete" data-action="delete" data-id="${escapeHTML(task.id)}" aria-label="Delete ${escapeHTML(task.name)}">×</button>
        </div>
      </article>`;
  }

  function renderToday() {
    const plan = makePlan();
    const active = tasks.filter(task => !task.isComplete);
    const completeCount = tasks.length - active.length;
    const upcoming = sortedTasks(active)[0];
    const hour = new Date().getHours();
    const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
    const totalMinutes = plan.reduce((sum, item) => sum + item.minutes, 0);
    const options = [30, 45, 60, 90, 120, 150, 180, 240, 300];
    return `
      ${pageHeading(greeting, new Intl.DateTimeFormat(undefined, { weekday: "long", month: "long", day: "numeric" }).format(new Date()))}
      <section class="hero"><p class="hero-kicker">MAKE TODAY COUNT</p><h2>Small steps.<br>Big progress.</h2><p class="hero-note">✦ &nbsp;One thing at a time</p></section>
      <section class="stats-grid" aria-label="Task summary">
        ${statCard("✓", active.length, "To do", "pink")}
        ${statCard("◷", `${totalMinutes}m`, "Study plan", "teal")}
        ${statCard("✦", completeCount, "Done", "orange")}
      </section>
      <div class="section-row"><h2 class="section-title">Your focus plan</h2><span class="small-muted">By due date &amp; priority</span></div>
      <div class="budget-control"><span class="budget-icon" aria-hidden="true">◷</span><label for="daily-budget">Study time</label>
        <select id="daily-budget" aria-label="Daily study time">${options.map(value => `<option value="${value}" ${dailyBudget === value ? "selected" : ""}>${value} min</option>`).join("")}</select>
      </div>
      ${plan.length ? `<div class="plan-list">${plan.map(({ task, minutes }) => `
        <article class="card plan-card"><span class="date-tile">${dayStart(task.dueDate).getDate()}</span>
          <div class="plan-copy"><strong>${escapeHTML(task.name)}</strong><small>${escapeHTML(task.subject)} · due ${dateFormat.format(dayStart(task.dueDate))}</small></div>
          <span class="minute-pill">${minutes}m</span></article>`).join("")}</div>`
        : emptyState("☀", "A clear mind starts here", "Add a task and we’ll help shape your study plan.")}
      ${upcoming ? `<h2 class="section-title">Coming up</h2><article class="card deadline-card"><span class="deadline-stripe"></span><div class="deadline-copy"><strong>${escapeHTML(upcoming.name)}</strong><small>${escapeHTML(upcoming.subject)}</small></div><span class="deadline-date">${dateFormat.format(dayStart(upcoming.dueDate))}</span></article>` : ""}
      ${feedback ? `<p class="small-muted" role="status">${escapeHTML(feedback)}</p>` : ""}`;
  }

  function matchingTasks() {
    const filtered = tasks.filter(task => {
      if (taskFilter === "upcoming") return !task.isComplete && !isOverdue(task);
      if (taskFilter === "overdue") return isOverdue(task);
      if (taskFilter === "completed") return task.isComplete;
      return true;
    });
    const query = search.trim().toLocaleLowerCase();
    return sortedTasks(filtered.filter(task => !query || `${task.name} ${task.subject}`.toLocaleLowerCase().includes(query)));
  }

  function renderTasks() {
    const counts = {
      upcoming: tasks.filter(task => !task.isComplete && !isOverdue(task)).length,
      overdue: tasks.filter(isOverdue).length,
      completed: tasks.filter(task => task.isComplete).length,
      all: tasks.length,
    };
    const chips = [["upcoming", "To do"], ["overdue", "Overdue"], ["completed", "Done"], ["all", "All"]];
    const visible = matchingTasks();
    return `${pageHeading("My tasks", "A little progress adds up.")}
      <label class="search-box"><span aria-hidden="true">⌕</span><input id="task-search" type="search" value="${escapeHTML(search)}" placeholder="Find a task or subject" autocomplete="off"></label>
      <div class="filter-row" aria-label="Filter tasks">${chips.map(([key, title]) => `<button class="filter-chip ${taskFilter === key ? "selected" : ""}" data-filter="${key}">${title} <span>${counts[key]}</span></button>`).join("")}</div>
      ${visible.length ? `<div class="task-list">${visible.map(taskCard).join("")}</div>` : emptyState(taskFilter === "completed" ? "✦" : "✓", search ? "No matches" : "Nothing on your list", search ? "Try another search." : taskFilter === "overdue" ? "You’re all caught up on deadlines." : "Tap + to add your first task.")}`;
  }

  function renderCalendar() {
    const year = displayedMonth.getFullYear();
    const month = displayedMonth.getMonth();
    const firstWeekday = new Date(year, month, 1).getDay();
    const days = new Date(year, month + 1, 0).getDate();
    const today = localDateString(new Date());
    const cells = ["S", "M", "T", "W", "T", "F", "S"].map(day => `<div class="calendar-weekday">${day}</div>`);
    for (let index = 0; index < firstWeekday; index++) cells.push("<div></div>");
    for (let day = 1; day <= days; day++) {
      const date = localDateString(new Date(year, month, day));
      const hasTask = tasks.some(task => task.dueDate === date);
      const disabled = date < today ? "disabled" : "";
      const classes = ["calendar-day", date === today ? "today" : "", date === localDateString(selectedDate) ? "selected" : "", hasTask ? "has-task" : ""].filter(Boolean).join(" ");
      cells.push(`<button type="button" class="${classes}" data-date="${date}" ${disabled} aria-label="${escapeHTML(new Intl.DateTimeFormat(undefined, { dateStyle: "full" }).format(dayStart(date)))}">${day}</button>`);
    }
    return cells.join("");
  }

  function renderSchedule() {
    const dueToday = sortedTasks(tasks.filter(task => task.dueDate === localDateString(selectedDate)));
    const monthTitle = new Intl.DateTimeFormat(undefined, { month: "long", year: "numeric" }).format(displayedMonth);
    const agendaTitle = new Intl.DateTimeFormat(undefined, { weekday: "long", month: "long", day: "numeric" }).format(selectedDate);
    return `${pageHeading("Schedule", "See what’s coming up.")}
      <section class="card schedule-card"><div class="schedule-controls"><strong class="month-title">${monthTitle}</strong><div class="month-nav"><button type="button" data-month="-1" aria-label="Previous month">‹</button><button type="button" data-month="1" aria-label="Next month">›</button></div></div><div class="calendar-grid">${renderCalendar()}</div></section>
      <h2 class="agenda-title">${escapeHTML(agendaTitle)}</h2>
      ${dueToday.length ? `<div class="agenda-list">${dueToday.map(taskCard).join("")}</div>` : emptyState("▦", "A little breathing room", "No deadlines on this day.")}`;
  }

  function renderProgress() {
    const complete = tasks.filter(task => task.isComplete).length;
    const percent = tasks.length ? Math.round(complete / tasks.length * 100) : 0;
    const minutes = tasks.reduce((sum, task) => sum + task.loggedMinutes, 0);
    const subjects = new Map();
    for (const task of tasks) {
      const group = subjects.get(task.subject) ?? { total: 0, complete: 0 };
      group.total++;
      if (task.isComplete) group.complete++;
      subjects.set(task.subject, group);
    }
    const colors = ["var(--violet)", "var(--pink)", "var(--teal)", "var(--orange)", "var(--blue)"];
    return `${pageHeading("Your progress", "Celebrate every step forward.")}
      <section class="card progress-card"><div class="progress-ring" style="--progress:${percent * 3.6}deg"><div class="progress-ring-inner"><strong>${percent}%</strong><small>done</small></div></div><div class="progress-copy"><strong>${complete} of ${tasks.length} tasks</strong><p>${tasks.length ? "Keep the momentum going." : "Add a task to start tracking your progress."}</p></div></section>
      <section class="stats-grid">${statCard("✓", complete, "Completed", "teal")}${statCard("◷", `${Math.floor(minutes / 60)}h ${minutes % 60}m`, "Time studied", "pink")}${statCard("▣", subjects.size, "Subjects", "orange")}</section>
      <h2 class="section-title">Subject snapshot</h2>
      ${subjects.size ? `<section class="card subject-list">${[...subjects.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([subject, group], index) => `<div class="subject-row"><div class="subject-top"><strong>${escapeHTML(subject)}</strong><small>${group.complete}/${group.total}</small></div><div class="progress-track"><div class="progress-fill" style="width:${Math.round(group.complete / group.total * 100)}%;background:${colors[index % colors.length]}"></div></div></div>`).join("")}</section>` : emptyState("▣", "Your subjects will show up here", "Add tasks to see your study mix.")}
      <h2 class="section-title">Move your tasks</h2>
      <section class="data-card"><p>Bring in your desktop planner’s JSON file, or save a copy for later. Import keeps your current tasks and skips duplicates.</p><div class="button-row"><button type="button" class="button primary" data-action="import">↓ &nbsp;Import JSON</button><button type="button" class="button" data-action="export">↑ &nbsp;Export</button></div></section>`;
  }

  function render() {
    tabs.forEach(tab => {
      const selected = tab.dataset.tab === activeTab;
      tab.classList.toggle("active", selected);
      if (selected) tab.setAttribute("aria-current", "page");
      else tab.removeAttribute("aria-current");
    });
    app.innerHTML = activeTab === "today" ? renderToday()
      : activeTab === "tasks" ? renderTasks()
      : activeTab === "schedule" ? renderSchedule()
      : renderProgress();
  }

  function openEditor(task = null) {
    form.reset();
    form.elements.id.value = task?.id ?? "";
    form.elements.name.value = task?.name ?? "";
    form.elements.subject.value = task?.subject ?? "";
    form.elements.dueDate.value = task?.dueDate ?? localDateString(new Date(Date.now() + 86400000));
    form.elements.estimatedMinutes.value = task?.estimatedMinutes ?? 60;
    form.elements.dailyTargetMinutes.value = task?.dailyTargetMinutes ?? 30;
    form.elements.priority.value = task?.priority ?? 5;
    document.querySelector("#dialog-title").textContent = task ? "Edit task" : "New task";
    document.querySelector("#priority-label").textContent = `${form.elements.priority.value} / 10`;
    document.querySelector("#form-error").textContent = "";
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
    setTimeout(() => form.elements.name.focus(), 50);
  }

  function saveTask(event) {
    event.preventDefault();
    const values = new FormData(form);
    const name = String(values.get("name") ?? "").trim();
    const subject = String(values.get("subject") ?? "").trim();
    const dueDate = String(values.get("dueDate") ?? "");
    const estimatedMinutes = Number(values.get("estimatedMinutes"));
    const dailyTargetMinutes = Number(values.get("dailyTargetMinutes"));
    const priority = Number(values.get("priority"));
    const current = tasks.find(task => task.id === values.get("id"));
    if (!name || !subject || !isValidDate(dueDate) || estimatedMinutes < 1 || dailyTargetMinutes < 1 || priority < 1 || priority > 10) {
      document.querySelector("#form-error").textContent = "Check the task name, subject, date, time, and priority.";
      return;
    }
    const next = {
      id: current?.id ?? makeId(), name, subject, dueDate,
      estimatedMinutes, dailyTargetMinutes, priority,
      loggedMinutes: Math.min(current?.loggedMinutes ?? 0, estimatedMinutes),
      isComplete: current?.isComplete ?? false,
    };
    if (current) tasks = tasks.map(task => task.id === current.id ? next : task);
    else tasks.push(next);
    persist();
    dialog.close();
    feedback = current ? "Task updated." : "Task added.";
    render();
  }

  function updateTask(id, action) {
    const task = tasks.find(item => item.id === id);
    if (!task) return;
    if (action === "delete") {
      if (!window.confirm(`Delete “${task.name}”?`)) return;
      tasks = tasks.filter(item => item.id !== id);
    } else if (action === "toggle") {
      task.isComplete = !task.isComplete;
    } else if (action === "log") {
      task.loggedMinutes = Math.min(task.estimatedMinutes, task.loggedMinutes + 15);
      if (task.loggedMinutes >= task.estimatedMinutes) task.isComplete = true;
    } else if (action === "edit") {
      openEditor(task);
      return;
    }
    persist();
    feedback = action === "log" ? `Logged 15 minutes for ${task.name}.` : "";
    render();
  }

  function legacyKey(task) {
    return [task.name.trim().toLocaleLowerCase(), task.subject.trim().toLocaleLowerCase(), task.dueDate, task.estimatedMinutes, task.priority].join("|");
  }

  async function importTasks(file) {
    try {
      const imported = normalizeTasks(JSON.parse(await file.text()));
      const seen = new Set(tasks.map(legacyKey));
      const fresh = imported.filter(task => {
        const key = legacyKey(task);
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });
      tasks.push(...fresh);
      persist();
      feedback = fresh.length ? `Imported ${fresh.length} task${fresh.length === 1 ? "" : "s"}.` : "No new tasks found; existing tasks were kept.";
      render();
    } catch (error) {
      window.alert(`Import failed: ${error.message}`);
    } finally {
      importInput.value = "";
    }
  }

  function exportTasks() {
    const data = tasks.map(task => ({
      task_name: task.name,
      task_subject: task.subject,
      estimated_time: task.estimatedMinutes,
      daily_work_target: task.dailyTargetMinutes,
      time_spent: task.loggedMinutes,
      priority: task.priority,
      due_date: task.dueDate,
      status: task.isComplete ? "done" : "due",
    }));
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "student_planner_tasks.json";
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    feedback = "Task file exported.";
    render();
  }

  document.querySelector(".tabbar").addEventListener("click", event => {
    const tab = event.target.closest("[data-tab]");
    if (!tab) return;
    activeTab = tab.dataset.tab;
    feedback = "";
    render();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
  document.querySelector("#add-top").addEventListener("click", () => openEditor());
  document.querySelector("#close-dialog").addEventListener("click", () => dialog.close());
  form.addEventListener("submit", saveTask);
  form.elements.priority.addEventListener("input", event => {
    document.querySelector("#priority-label").textContent = `${event.target.value} / 10`;
  });
  importInput.addEventListener("change", event => {
    if (event.target.files?.[0]) importTasks(event.target.files[0]);
  });

  app.addEventListener("input", event => {
    if (event.target.id === "task-search") {
      const position = event.target.selectionStart;
      search = event.target.value;
      render();
      const nextSearch = document.querySelector("#task-search");
      nextSearch.focus();
      nextSearch.setSelectionRange(position, position);
    }
    if (event.target.id === "daily-budget") {
      dailyBudget = Number(event.target.value);
      render();
    }
  });

  app.addEventListener("click", event => {
    const filter = event.target.closest("[data-filter]");
    if (filter) {
      taskFilter = filter.dataset.filter;
      render();
      return;
    }
    const month = event.target.closest("[data-month]");
    if (month) {
      displayedMonth = new Date(displayedMonth.getFullYear(), displayedMonth.getMonth() + Number(month.dataset.month), 1);
      render();
      return;
    }
    const date = event.target.closest("[data-date]");
    if (date) {
      selectedDate = dayStart(date.dataset.date);
      render();
      return;
    }
    const action = event.target.closest("[data-action]");
    if (!action) return;
    if (action.dataset.action === "import") importInput.click();
    else if (action.dataset.action === "export") exportTasks();
    else updateTask(action.dataset.id, action.dataset.action);
  });

  render();
  if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("./service-worker.js").catch(error => {
        console.error("Offline support could not be enabled:", error);
      });
    });
  }
})();
