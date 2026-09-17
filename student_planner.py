import datetime
import email
import imaplib
import re
import tkinter as tk
from tkinter import ttk, messagebox


MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def normalize_due_date(raw_due_date):
    if raw_due_date is None:
        raise ValueError("Please enter a due date.")

    raw_due_date = str(raw_due_date).strip()
    current_year = datetime.date.today().year

    if not raw_due_date:
        raise ValueError("Please enter a due date.")

    if "-" in raw_due_date:
        parts = raw_due_date.split("-")

        if len(parts) == 2:
            month, day = parts
            year = current_year
        elif len(parts) == 3:
            year, month, day = parts
        else:
            raise ValueError("Please enter a valid due date in YYYY-MM-DD, MM-DD, or Month Day format.")
    else:
        parts = raw_due_date.split()
        if len(parts) != 2:
            raise ValueError("Please enter a valid due date like August 15 or 08-15.")

        month_name, day = parts
        month = MONTHS.get(month_name.lower())
        if month is None:
            raise ValueError("Please enter a valid month name like August.")
        year = current_year

    try:
        due_date = datetime.date(int(year), int(month), int(day))
    except ValueError:
        raise ValueError("Please enter a valid calendar date.") from None

    if due_date < datetime.date.today():
        raise ValueError("The due date cannot be before today.")

    return due_date.isoformat()


def task_due_status(task, today=None):
    if task.get("status") == "done":
        return "done"

    today = today or datetime.date.today()
    due_date = datetime.date.fromisoformat(task["due_date"])
    return "overdue" if due_date < today else "due"


def create_action_plan(tasks):
    active_tasks = [task for task in tasks if task.get("status") != "done"]
    return sorted(
        active_tasks,
        key=lambda task: (task["due_date"], -task["priority"], task["estimated_time"]),
    )


def task_time_spent(task):
    return task.get("time_spent", 0)


def task_remaining_time(task):
    if task.get("status") == "done":
        return 0
    return max(0, task["estimated_time"] - task_time_spent(task))


def create_reminders(tasks, today=None):
    today = today or datetime.date.today()
    reminders = []

    for task in tasks:
        if task.get("status") == "done":
            continue

        due_date = datetime.date.fromisoformat(task["due_date"])
        days_until_due = (due_date - today).days
        if days_until_due in (0, 1, 2):
            reminders.append((days_until_due, task))

    return sorted(reminders, key=lambda reminder: (reminder[0], reminder[1]["due_date"], reminder[1]["task_name"]))


SCHOOL_EMAIL_KEYWORDS = (
    "assignment", "homework", "project", "quiz", "test", "exam",
    "reminder", "due", "grade", "class", "lesson", "school",
)


def decode_email_header(value):
    if not value:
        return ""

    decoded_parts = email.header.decode_header(value)
    return " ".join(
        part.decode(charset or "utf-8", errors="replace") if isinstance(part, bytes) else part
        for part, charset in decoded_parts
    )


def get_email_text(message):
    parts = message.walk() if message.is_multipart() else [message]
    text_parts = []
    for part in parts:
        if part.get_content_type() != "text/plain" or part.get_content_disposition() == "attachment":
            continue
        payload = part.get_payload(decode=True)
        if payload:
            text_parts.append(payload.decode(part.get_content_charset() or "utf-8", errors="replace"))

    return " ".join(text_parts)


def is_school_update(subject, body):
    searchable_text = f"{subject} {body}".lower()
    return any(re.search(rf"\b{re.escape(keyword)}\b", searchable_text) for keyword in SCHOOL_EMAIL_KEYWORDS)


class CalendarPopup(tk.Toplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("Choose Due Date")
        self.callback = callback
        self.selected_date = None

        self.geometry("440x320")
        self.transient(parent)
        self.grab_set()

        self.current_year = datetime.date.today().year
        self.current_month = datetime.date.today().month

        top_bar = ttk.Frame(self, padding=(10, 10, 10, 0))
        top_bar.pack(fill="x")

        ttk.Button(top_bar, text="<", command=self.previous_month).pack(side="left")
        self.month_var = tk.StringVar(value=datetime.date(self.current_year, self.current_month, 1).strftime("%B"))
        self.year_var = tk.StringVar(value=str(self.current_year))
        ttk.Label(top_bar, textvariable=self.month_var, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(16, 8))
        ttk.Label(top_bar, textvariable=self.year_var, font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Button(top_bar, text=">", command=self.next_month).pack(side="right")

        days_frame = ttk.Frame(self)
        days_frame.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        for weekday in ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]:
            ttk.Label(days_frame, text=weekday, width=4, anchor="center").grid(row=0, column=len(days_frame.grid_slaves()) if False else 0)

        day_headers = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        for index, weekday in enumerate(day_headers):
            ttk.Label(days_frame, text=weekday, width=4, anchor="center", font=("Segoe UI", 9, "bold")).grid(row=0, column=index, padx=2, pady=2)

        self.day_buttons = {}
        self.days_grid = days_frame
        self.render_calendar()

    def previous_month(self):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.render_calendar()

    def next_month(self):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.render_calendar()

    def render_calendar(self):
        for widget in self.days_grid.grid_slaves():
            if int(widget.grid_info()["row"]) > 0:
                widget.destroy()

        self.month_var.set(datetime.date(self.current_year, self.current_month, 1).strftime("%B"))
        self.year_var.set(str(self.current_year))

        first_day = datetime.date(self.current_year, self.current_month, 1)
        last_day = datetime.date(self.current_year, self.current_month + 1, 1) - datetime.timedelta(days=1) if self.current_month < 12 else datetime.date(self.current_year + 1, 1, 1) - datetime.timedelta(days=1)
        first_weekday = first_day.weekday()

        day_number = 1
        for row in range(1, 7):
            for col in range(7):
                index = (row - 1) * 7 + col
                if index < first_weekday or day_number > last_day.day:
                    ttk.Label(self.days_grid, text="", width=4).grid(row=row, column=col, padx=2, pady=2)
                    continue

                date_value = datetime.date(self.current_year, self.current_month, day_number)
                button = ttk.Button(
                    self.days_grid,
                    text=str(day_number),
                    width=4,
                    state="disabled" if date_value < datetime.date.today() else "normal",
                    command=lambda value=date_value: self.select_date(value),
                )
                button.grid(row=row, column=col, padx=2, pady=2)
                self.day_buttons[day_number] = button
                day_number += 1

    def select_date(self, date_value):
        self.callback(date_value)
        self.destroy()


class TaskCalendarPopup(tk.Toplevel):
    def __init__(self, parent, tasks):
        super().__init__(parent)
        self.title("Task Calendar")
        self.geometry("850x650")
        self.transient(parent)
        self.tasks = tasks
        today = datetime.date.today()
        self.current_year = today.year
        self.current_month = today.month

        top_bar = ttk.Frame(self, padding=12)
        top_bar.pack(fill="x")
        ttk.Button(top_bar, text="<", command=self.previous_month).pack(side="left")
        self.month_var = tk.StringVar()
        ttk.Label(top_bar, textvariable=self.month_var, font=("Segoe UI", 14, "bold")).pack(side="left", expand=True)
        ttk.Button(top_bar, text=">", command=self.next_month).pack(side="right")

        self.calendar_grid = ttk.Frame(self, padding=(12, 0, 12, 12))
        self.calendar_grid.pack(fill="both", expand=True)
        for column in range(7):
            self.calendar_grid.columnconfigure(column, weight=1)
        for row in range(1, 7):
            self.calendar_grid.rowconfigure(row, weight=1)
        self.render_calendar()

    def previous_month(self):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.render_calendar()

    def next_month(self):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.render_calendar()

    def render_calendar(self):
        for widget in self.calendar_grid.winfo_children():
            widget.destroy()

        month_start = datetime.date(self.current_year, self.current_month, 1)
        next_month = month_start.replace(day=28) + datetime.timedelta(days=4)
        month_end = next_month - datetime.timedelta(days=next_month.day)
        self.month_var.set(month_start.strftime("%B %Y"))

        for column, weekday in enumerate(("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")):
            ttk.Label(self.calendar_grid, text=weekday, anchor="center", font=("Segoe UI", 9, "bold")).grid(
                row=0, column=column, sticky="ew", padx=2, pady=(0, 4)
            )

        tasks_by_date = {}
        for task in self.tasks:
            tasks_by_date.setdefault(task["due_date"], []).append(task)

        first_weekday = (month_start.weekday() + 1) % 7
        for day_number in range(1, month_end.day + 1):
            date_value = datetime.date(self.current_year, self.current_month, day_number)
            cell_index = first_weekday + day_number - 1
            row, column = divmod(cell_index, 7)
            cell = tk.Frame(self.calendar_grid, bg="#ffffff", highlightbackground="#c9d6e3", highlightthickness=1)
            cell.grid(row=row + 1, column=column, sticky="nsew", padx=2, pady=2)
            tk.Label(cell, text=str(day_number), bg="#ffffff", fg="#1d3557", font=("Segoe UI", 10, "bold")).pack(
                anchor="nw", padx=6, pady=(4, 2)
            )
            for task in tasks_by_date.get(date_value.isoformat(), []):
                tk.Label(
                    cell,
                    text=task["task_name"],
                    bg="#d9edf7",
                    fg="#16324f",
                    anchor="w",
                    justify="left",
                    wraplength=100,
                ).pack(fill="x", padx=4, pady=2)


class StudentPlannerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Student Planner")
        self.geometry("1200x820")
        self.minsize(1050, 720)
        self.configure(bg="#eef5ff")

        self.tasks = []

        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#1d3557")
        self.style.configure("Section.TLabel", font=("Segoe UI", 11, "bold"), foreground="#264653")
        self.style.configure("TEntry", padding=6)
        self.style.configure("TButton", padding=(10, 6))

        page_canvas = tk.Canvas(self, highlightthickness=0, background="#eef5ff")
        page_scrollbar = ttk.Scrollbar(self, orient="vertical", command=page_canvas.yview)
        page_canvas.configure(yscrollcommand=page_scrollbar.set)
        page_scrollbar.pack(side="right", fill="y")
        page_canvas.pack(side="left", fill="both", expand=True)

        main_container = ttk.Frame(page_canvas, padding=20)
        page_window = page_canvas.create_window((0, 0), window=main_container, anchor="nw")

        def update_scroll_region(event=None):
            page_canvas.configure(scrollregion=page_canvas.bbox("all"))
            page_canvas.itemconfigure(page_window, width=page_canvas.winfo_width())

        main_container.bind("<Configure>", update_scroll_region)
        page_canvas.bind("<Configure>", update_scroll_region)
        page_canvas.bind_all("<MouseWheel>", lambda event: page_canvas.yview_scroll(int(-event.delta / 120), "units"))

        left_panel = ttk.Frame(main_container, padding=12)
        left_panel.pack(side="left", fill="y", padx=(0, 18))

        ttk.Label(left_panel, text="Add a task", style="Header.TLabel").pack(anchor="w", pady=(0, 12))

        ttk.Label(left_panel, text="Task name:", style="Section.TLabel").pack(anchor="w")
        self.task_name_entry = ttk.Entry(left_panel, width=38)
        self.task_name_entry.pack(fill="x", pady=(0, 10))

        ttk.Label(left_panel, text="Subject:", style="Section.TLabel").pack(anchor="w")
        self.subject_entry = ttk.Entry(left_panel, width=38)
        self.subject_entry.pack(fill="x", pady=(0, 10))

        ttk.Label(left_panel, text="Estimated time (minutes):", style="Section.TLabel").pack(anchor="w")
        time_values = ["15", "30", "45", "60", "90", "120", "180", "240"]
        self.time_var = tk.StringVar(value=time_values[1])
        self.time_dropdown = ttk.Combobox(left_panel, textvariable=self.time_var, values=time_values, state="readonly", width=35)
        self.time_dropdown.pack(fill="x", pady=(0, 10))

        ttk.Label(left_panel, text="Priority (1-10):", style="Section.TLabel").pack(anchor="w")
        priority_values = [str(value) for value in range(1, 11)]
        self.priority_var = tk.StringVar(value="5")
        self.priority_dropdown = ttk.Combobox(left_panel, textvariable=self.priority_var, values=priority_values, state="readonly", width=35)
        self.priority_dropdown.pack(fill="x", pady=(0, 10))

        ttk.Label(left_panel, text="Due date:", style="Section.TLabel").pack(anchor="w")
        date_frame = ttk.Frame(left_panel)
        date_frame.pack(fill="x", pady=(0, 12))
        self.due_date_var = tk.StringVar()
        self.date_entry = ttk.Entry(date_frame, textvariable=self.due_date_var, width=28, state="readonly")
        self.date_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(date_frame, text="Pick Date", command=self.open_calendar).pack(side="left", padx=(8, 0))

        button_row = ttk.Frame(left_panel)
        button_row.pack(fill="x", pady=(8, 0))
        ttk.Button(button_row, text="Add Task", command=self.add_task).pack(side="left", padx=(0, 10))
        ttk.Button(button_row, text="Clear", command=self.clear_form).pack(side="left")
        ttk.Button(left_panel, text="View Task Calendar", command=self.open_task_calendar).pack(anchor="w", pady=(10, 0))

        ttk.Separator(left_panel, orient="horizontal").pack(fill="x", pady=18)
        ttk.Label(left_panel, text="School email", style="Header.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Label(left_panel, text="IMAP server:", style="Section.TLabel").pack(anchor="w")
        self.email_server_entry = ttk.Entry(left_panel, width=38)
        self.email_server_entry.insert(0, "imap.gmail.com")
        self.email_server_entry.pack(fill="x", pady=(0, 8))

        ttk.Label(left_panel, text="Email address:", style="Section.TLabel").pack(anchor="w")
        self.email_address_entry = ttk.Entry(left_panel, width=38)
        self.email_address_entry.pack(fill="x", pady=(0, 8))

        ttk.Label(left_panel, text="Gmail app password:", style="Section.TLabel").pack(anchor="w")
        self.email_password_entry = ttk.Entry(left_panel, width=38, show="*")
        self.email_password_entry.pack(fill="x", pady=(0, 10))
        ttk.Button(left_panel, text="Check for Updates", command=self.check_email).pack(anchor="w")
        self.email_status = tk.StringVar(value="No email checked yet.")
        ttk.Label(left_panel, textvariable=self.email_status, wraplength=250).pack(anchor="w", pady=(8, 0))
        ttk.Label(
            left_panel,
            text="Gmail does not accept your normal password here. Create an app password in your Google Account first.",
            wraplength=250,
        ).pack(anchor="w", pady=(8, 0))

        right_panel = ttk.Frame(main_container, padding=12)
        right_panel.pack(side="left", fill="both", expand=True)

        ttk.Label(right_panel, text="Added Tasks", style="Header.TLabel").pack(anchor="w", pady=(0, 10))
        self.current_task_category = "due"
        self.category_frame = ttk.Frame(right_panel)
        self.category_frame.pack(fill="x", pady=(0, 10))
        self.category_buttons = {}
        for category_key, category_label in (("due", "Due"), ("overdue", "Overdue"), ("done", "Done")):
            button = ttk.Button(
                self.category_frame,
                text=category_label,
                command=lambda key=category_key: self.set_task_category(key),
            )
            button.pack(side="left", padx=(0, 8))
            self.category_buttons[category_key] = button

        self.task_tree = ttk.Treeview(
            right_panel,
            columns=("check", "status", "name", "subject", "time", "priority", "due_date"),
            show="headings",
            height=10,
        )
        self.task_tree.heading("check", text="")
        self.task_tree.heading("status", text="Status")
        self.task_tree.heading("name", text="Task")
        self.task_tree.heading("subject", text="Subject")
        self.task_tree.heading("time", text="Time")
        self.task_tree.heading("priority", text="Priority")
        self.task_tree.heading("due_date", text="Due Date")
        self.task_tree.column("check", width=34, anchor="center", stretch=False)
        self.task_tree.column("status", width=90, anchor="center")
        self.task_tree.column("name", width=180, anchor="center")
        self.task_tree.column("subject", width=140, anchor="center")
        self.task_tree.column("time", width=100, anchor="center")
        self.task_tree.column("priority", width=80, anchor="center")
        self.task_tree.column("due_date", width=110, anchor="center")
        self.task_tree.tag_configure("due", background="#eaf7ea", foreground="#1d3557")
        self.task_tree.tag_configure("overdue", background="#fdecea", foreground="#7a1d1d")
        self.task_tree.tag_configure("done", background="#edf3ff", foreground="#2f4154")
        self.task_tree.bind("<Button-1>", self.check_off_task)
        self.task_tree.pack(fill="both", expand=True)

        ttk.Label(right_panel, text="Reminders", style="Header.TLabel").pack(anchor="w", pady=(14, 10))
        self.reminders_list = tk.Listbox(right_panel, height=4, font=("Segoe UI", 10), bg="#fff8e1")
        self.reminders_list.pack(fill="x")

        timing_frame = ttk.LabelFrame(right_panel, text="Log time for selected task", padding=10)
        timing_frame.pack(fill="x", pady=(12, 0))
        ttk.Label(timing_frame, text="Start (HH:MM):").grid(row=0, column=0, padx=(0, 6), sticky="w")
        self.start_time_entry = ttk.Entry(timing_frame, width=10)
        self.start_time_entry.grid(row=0, column=1, padx=(0, 12), sticky="w")
        ttk.Label(timing_frame, text="End (HH:MM):").grid(row=0, column=2, padx=(0, 6), sticky="w")
        self.end_time_entry = ttk.Entry(timing_frame, width=10)
        self.end_time_entry.grid(row=0, column=3, padx=(0, 12), sticky="w")
        ttk.Button(timing_frame, text="Log Time", command=self.log_task_time).grid(row=0, column=4, sticky="w")
        self.timing_status = tk.StringVar(value="Select a task, then enter its start and end times.")
        ttk.Label(timing_frame, textvariable=self.timing_status).grid(row=1, column=0, columnspan=5, pady=(8, 0), sticky="w")

        ttk.Label(right_panel, text="Task Progress", style="Header.TLabel").pack(anchor="w", pady=(14, 10))
        self.progress_frame = ttk.Frame(right_panel)
        self.progress_frame.pack(fill="x")

        ttk.Label(right_panel, text="Action Plan", style="Header.TLabel").pack(anchor="w", pady=(14, 10))
        self.action_plan = tk.Listbox(right_panel, height=12, font=("Segoe UI", 10), bg="#ffffff")
        self.action_plan.pack(fill="both", expand=True)

        ttk.Label(right_panel, text="School Email Updates", style="Header.TLabel").pack(anchor="w", pady=(14, 10))
        self.email_tree = ttk.Treeview(right_panel, columns=("date", "sender", "subject", "preview"), show="headings", height=6)
        self.email_tree.heading("date", text="Date")
        self.email_tree.heading("sender", text="From")
        self.email_tree.heading("subject", text="Subject")
        self.email_tree.heading("preview", text="Preview")
        self.email_tree.column("date", width=110, anchor="center")
        self.email_tree.column("sender", width=150, anchor="w")
        self.email_tree.column("subject", width=220, anchor="w")
        self.email_tree.column("preview", width=260, anchor="w")
        self.email_tree.pack(fill="both", expand=True)

    def open_calendar(self):
        CalendarPopup(self, self.set_due_date)

    def set_due_date(self, selected_date):
        self.due_date_var.set(selected_date.strftime("%Y-%m-%d"))

    def clear_form(self):
        self.task_name_entry.delete(0, tk.END)
        self.subject_entry.delete(0, tk.END)
        self.time_var.set("30")
        self.priority_var.set("5")
        self.due_date_var.set("")

    def add_task(self):
        task_name = self.task_name_entry.get().strip()
        subject = self.subject_entry.get().strip()
        estimated_time = self.time_var.get().strip()
        priority = self.priority_var.get().strip()
        due_date = self.due_date_var.get().strip()

        if not task_name or not subject:
            messagebox.showerror("Missing information", "Please enter both a task name and a subject.")
            return

        if not due_date:
            messagebox.showerror("Missing information", "Please choose a due date.")
            return

        try:
            normalized_due_date = normalize_due_date(due_date)
            estimated_time_value = int(estimated_time)
            priority_value = int(priority)

            if estimated_time_value <= 0:
                raise ValueError("Estimated time must be greater than zero.")
            if not 1 <= priority_value <= 10:
                raise ValueError("Priority must be between 1 and 10.")
        except ValueError as exc:
            messagebox.showerror("Invalid data", str(exc))
            return

        task = {
            "task_name": task_name,
            "task_subject": subject,
            "estimated_time": estimated_time_value,
            "time_spent": 0,
            "priority": priority_value,
            "due_date": normalized_due_date,
            "status": "due",
        }

        self.tasks.append(task)
        self.refresh_task_list()
        self.update_action_plan()
        self.clear_form()

    def open_task_calendar(self):
        TaskCalendarPopup(self, self.tasks)

    def set_task_category(self, category):
        self.current_task_category = category
        for key, button in self.category_buttons.items():
            button.configure(style="TButton" if key != category else "Accent.TButton")
        self.refresh_task_list()

    def log_task_time(self):
        selected_items = self.task_tree.selection()
        if not selected_items:
            messagebox.showerror("No task selected", "Select a task before logging time.")
            return

        start_text = self.start_time_entry.get().strip()
        end_text = self.end_time_entry.get().strip()
        try:
            start_time = datetime.datetime.strptime(start_text, "%H:%M")
            end_time = datetime.datetime.strptime(end_text, "%H:%M")
        except ValueError:
            messagebox.showerror("Invalid time", "Enter start and end times using 24-hour HH:MM format, such as 09:30.")
            return

        task_index = self.task_row_lookup.get(selected_items[0])
        if task_index is None:
            messagebox.showerror("Task not found", "That task could not be found in the current list.")
            return

        task = self.tasks[task_index]
        duration = int((end_time - start_time).total_seconds() // 60)
        if duration <= 0:
            messagebox.showerror("Invalid time range", "The end time must be later than the start time.")
            return

        task["time_spent"] = task_time_spent(task) + duration
        self.refresh_task_list()
        self.update_action_plan()
        self.refresh_progress_bars()
        self.timing_status.set(f"Logged {duration} minutes for {task['task_name']}.")
        self.start_time_entry.delete(0, tk.END)
        self.end_time_entry.delete(0, tk.END)

    def check_off_task(self, event):
        if self.task_tree.identify_column(event.x) != "#1":
            return

        task_id = self.task_tree.identify_row(event.y)
        if not task_id:
            return

        task_index = self.task_row_lookup.get(task_id)
        if task_index is None:
            return

        self.task_tree.set(task_id, "check", "☑")
        self.after(150, lambda: self.remove_completed_task(task_index))

    def remove_completed_task(self, task_index):
        task = self.tasks[task_index]
        task["status"] = "done"
        task["time_spent"] = task["estimated_time"]
        self.refresh_task_list()
        self.update_action_plan()

    def refresh_task_list(self):
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)

        self.task_row_lookup = {}
        for task in self.tasks:
            task["status"] = task_due_status(task)

        visible_tasks = [
            task for task in self.tasks if task["status"] == self.current_task_category
        ]
        visible_tasks.sort(key=lambda task: (task["due_date"], -task["priority"], task["task_name"]))

        self.task_tree.heading("status", text=self.current_task_category.title())
        for task_index, task in enumerate(self.tasks):
            if task["status"] != self.current_task_category:
                continue

            row_id = f"task_{task_index}"
            self.task_row_lookup[row_id] = task_index
            status_label = {"due": "Due", "overdue": "Overdue", "done": "Done"}[task["status"]]
            self.task_tree.insert(
                "",
                tk.END,
                iid=row_id,
                values=(
                    "☐" if task["status"] != "done" else "☑",
                    status_label,
                    task["task_name"],
                    task["task_subject"],
                    f"{task_remaining_time(task)} min left" if task["status"] != "done" else "Completed",
                    task["priority"],
                    task["due_date"],
                ),
                tags=(task["status"],),
            )
            self.task_tree.item(row_id, tags=(task["status"],))
        self.refresh_progress_bars()
        self.refresh_reminders()

    def refresh_reminders(self):
        self.reminders_list.delete(0, tk.END)
        reminders = create_reminders(self.tasks)

        if not reminders:
            self.reminders_list.insert(tk.END, "No assignments due today or in the next 2 days.")
            return

        for days_until_due, task in reminders:
            day_label = {0: "today", 1: "tomorrow", 2: "in 2 days"}[days_until_due]
            self.reminders_list.insert(
                tk.END,
                f"Due {day_label}: {task['task_name']} ({task['task_subject']}) - {task_remaining_time(task)} minutes remaining",
            )

    def refresh_progress_bars(self):
        for widget in self.progress_frame.winfo_children():
            widget.destroy()

        for task in self.tasks:
            spent = task_time_spent(task)
            progress = min(100, spent / task["estimated_time"] * 100)
            row = ttk.Frame(self.progress_frame)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=task["task_name"], width=24, anchor="w").pack(side="left")
            progress_bar = ttk.Progressbar(row, maximum=100, value=progress)
            progress_bar.pack(side="left", fill="x", expand=True, padx=8)
            ttk.Label(row, text=f"{spent}/{task['estimated_time']} min").pack(side="left")

    def update_action_plan(self):
        self.action_plan.delete(0, tk.END)
        sorted_tasks = create_action_plan(self.tasks)

        for position, task in enumerate(sorted_tasks, start=1):
            self.action_plan.insert(
                tk.END,
                f"{position}. {task['task_name']} ({task['task_subject']}) - Due {task['due_date']}, "
                f"Priority {task['priority']}/10, {task_remaining_time(task)} minutes remaining",
            )

    def check_email(self):
        server_name = self.email_server_entry.get().strip()
        email_address = self.email_address_entry.get().strip()
        password = self.email_password_entry.get()

        if not server_name or not email_address or not password:
            messagebox.showerror("Missing email information", "Enter the IMAP server, email address, and password or app password.")
            return

        try:
            mailbox = imaplib.IMAP4_SSL(server_name)
            mailbox.login(email_address, password)
            mailbox.select("INBOX", readonly=True)
            _, search_data = mailbox.uid("search", None, "ALL")
            message_ids = search_data[0].split()[-30:]
            updates = []

            for message_id in reversed(message_ids):
                _, message_data = mailbox.uid("fetch", message_id, "(BODY.PEEK[])")
                raw_message = next(
                    (part[1] for part in message_data if isinstance(part, tuple)),
                    None,
                )
                if not raw_message:
                    continue

                message = email.message_from_bytes(raw_message)
                subject = decode_email_header(message.get("Subject")) or "(No subject)"
                body = get_email_text(message)
                if is_school_update(subject, body):
                    sender = decode_email_header(message.get("From"))
                    date = decode_email_header(message.get("Date"))
                    preview = " ".join(body.split())[:110]
                    updates.append((date, sender, subject, preview))

            mailbox.logout()
        except imaplib.IMAP4.error as exc:
            self.email_status.set("Email check failed.")
            error_text = str(exc)
            if "auth" in error_text.lower() or "login" in error_text.lower() or "credential" in error_text.lower():
                error_text = (
                    "Gmail requires an app password for this IMAP connection; your normal Gmail password will be rejected. "
                    "Turn on 2-Step Verification, create a Google app password, and enter that 16-character password here. "
                    "For an HDSB account, use the CHATT email address. Basic IMAP access may also be disabled by HDSB.\n\n"
                    f"Server response: {exc}"
                )
            messagebox.showerror("Email login failed", error_text)
            return
        except (OSError, UnicodeError) as exc:
            self.email_status.set("Email check failed.")
            messagebox.showerror("Email error", f"Could not read the mailbox:\n{exc}")
            return

        for item in self.email_tree.get_children():
            self.email_tree.delete(item)
        for update in updates:
            self.email_tree.insert("", tk.END, values=update)

        self.email_status.set(f"Found {len(updates)} school update(s).")


if __name__ == "__main__":
    app = StudentPlannerApp()
    app.mainloop()
