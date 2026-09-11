import datetime
import email
import imaplib
import re
import tkinter as tk
from pathlib import Path
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
            return f"{current_year}-{int(month):02d}-{int(day):02d}"

        if len(parts) == 3:
            year, month, day = parts
            return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

        raise ValueError("Please enter a valid due date in YYYY-MM-DD, MM-DD, or Month Day format.")

    parts = raw_due_date.split()
    if len(parts) == 2:
        month_name, day = parts
        month_number = MONTHS.get(month_name.lower())
        if month_number is None:
            raise ValueError("Please enter a valid month name like August.")
        return f"{current_year}-{month_number:02d}-{int(day):02d}"

    raise ValueError("Please enter a valid due date like August 15 or 08-15.")


def create_action_plan(tasks):
    return sorted(
        tasks,
        key=lambda task: (task["due_date"], -task["priority"], task["estimated_time"]),
    )


def escape_ical_text(value):
    return str(value).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def create_calendar_file(tasks, file_path):
    calendar_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Student Planner//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for task in tasks:
        due_date = datetime.date.fromisoformat(task["due_date"])
        event_id = f"{due_date.isoformat()}-{task['task_name']}-{task['task_subject']}"
        description = (
            f"Subject: {task['task_subject']}\\n"
            f"Priority: {task['priority']}/10\\n"
            f"Estimated time: {task['estimated_time']} minutes"
        )
        calendar_lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{escape_ical_text(event_id)}@student-planner",
                f"DTSTAMP:{datetime.datetime.now(datetime.timezone.utc):%Y%m%dT%H%M%SZ}",
                f"DTSTART;VALUE=DATE:{due_date:%Y%m%d}",
                f"DTEND;VALUE=DATE:{due_date + datetime.timedelta(days=1):%Y%m%d}",
                f"SUMMARY:{escape_ical_text(task['task_name'])}",
                f"DESCRIPTION:{escape_ical_text(description)}",
                "END:VEVENT",
            ]
        )

    calendar_lines.append("END:VCALENDAR")
    Path(file_path).write_text("\r\n".join(calendar_lines) + "\r\n", encoding="utf-8")


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

        self.geometry("360x320")
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
        self.task_tree = ttk.Treeview(right_panel, columns=("name", "subject", "time", "priority", "due_date"), show="headings", height=10)
        self.task_tree.heading("name", text="Task")
        self.task_tree.heading("subject", text="Subject")
        self.task_tree.heading("time", text="Time")
        self.task_tree.heading("priority", text="Priority")
        self.task_tree.heading("due_date", text="Due Date")
        self.task_tree.column("name", width=180, anchor="center")
        self.task_tree.column("subject", width=140, anchor="center")
        self.task_tree.column("time", width=80, anchor="center")
        self.task_tree.column("priority", width=80, anchor="center")
        self.task_tree.column("due_date", width=110, anchor="center")
        self.task_tree.pack(fill="both", expand=True)

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
            "priority": priority_value,
            "due_date": normalized_due_date,
        }

        self.tasks.append(task)
        self.refresh_task_list()
        self.update_action_plan()
        self.save_calendar_file()
        self.clear_form()

    def calendar_file_path(self):
        return Path(__file__).resolve().parent / "student_planner_calendar.ics"

    def save_calendar_file(self):
        try:
            create_calendar_file(self.tasks, self.calendar_file_path())
        except OSError as exc:
            messagebox.showerror("Calendar file error", f"Could not save the calendar file:\n{exc}")

    def open_task_calendar(self):
        TaskCalendarPopup(self, self.tasks)

    def refresh_task_list(self):
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)

        for task in self.tasks:
            self.task_tree.insert(
                "",
                tk.END,
                values=(
                    task["task_name"],
                    task["task_subject"],
                    f"{task['estimated_time']} min",
                    task["priority"],
                    task["due_date"],
                ),
            )

    def update_action_plan(self):
        self.action_plan.delete(0, tk.END)
        sorted_tasks = create_action_plan(self.tasks)

        for position, task in enumerate(sorted_tasks, start=1):
            self.action_plan.insert(
                tk.END,
                f"{position}. {task['task_name']} ({task['task_subject']}) - Due {task['due_date']}, "
                f"Priority {task['priority']}/10, Estimated {task['estimated_time']} minutes",
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
