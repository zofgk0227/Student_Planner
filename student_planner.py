import datetime


MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def normalize_due_date(raw_due_date):
    current_year = datetime.date.today().year
    raw_due_date = raw_due_date.strip()

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


def get_task_input():
    print("Student Planner Task Input System")
    print("Format: {task name} {task subject} {estimated task time length} {task priority (1-10)} {task due date}")
    print(f"Example: Math Assignment Science 90 8 August 20\n")

    task_name = input("Task name: ")
    task_subject = input("Task subject: ")

    while True:
        try:
            estimated_time = int(input("Estimated task time length (in minutes): "))
            if estimated_time > 0:
                break
            print("Please enter a positive number for the time estimate.")
        except ValueError:
            print("Please enter a valid number for the time estimate.")

    while True:
        try:
            priority = int(input("Task priority (1-10, 10 = highest): "))
            if 1 <= priority <= 10:
                break
            print("Please enter a number from 1 to 10.")
        except ValueError:
            print("Please enter a valid number from 1 to 10.")

    while True:
        try:
            raw_due_date = input(f"Task due date (Month Day, MM-DD, or YYYY-MM-DD): ")
            due_date = normalize_due_date(raw_due_date)
            break
        except ValueError as exc:
            print(exc)

    return {
        "task_name": task_name,
        "task_subject": task_subject,
        "estimated_time": estimated_time,
        "priority": priority,
        "due_date": due_date,
    }


def display_task(task):
    print("\nTask saved successfully.")
    print("-----------------------------------")
    print(f"Name: {task['task_name']}")
    print(f"Subject: {task['task_subject']}")
    print(f"Estimated Time: {task['estimated_time']} minutes")
    print(f"Priority: {task['priority']}/10")
    print(f"Due Date: {task['due_date']}")
    print("-----------------------------------")


if __name__ == "__main__":
    task = get_task_input()
    display_task(task)
