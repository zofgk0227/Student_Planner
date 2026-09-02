import datetime
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


class StudentPlannerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Student Planner")
        self.geometry("980x620")
        self.minsize(900, 560)
        self.configure(bg="#eef5ff")

        self.tasks = []

        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#1d3557")
        self.style.configure("Section.TLabel", font=("Segoe UI", 11, "bold"), foreground="#264653")
        self.style.configure("TEntry", padding=6)
        self.style.configure("TButton", padding=(10, 6))

        main_container = ttk.Frame(self, padding=20)
        main_container.pack(fill="both", expand=True)

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
        self.clear_form()

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


if __name__ == "__main__":
    app = StudentPlannerApp()
    app.mainloop()
