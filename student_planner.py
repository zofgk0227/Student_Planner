def get_task_input():
    print("Student Planner Task Input System")
    print("Format: {task name} {task subject} {estimated task time length} {task priority (1-10)} {task due date}")
    print("Example: Math Assignment Science 90 8 2026-08-20\n")

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

    due_date = input("Task due date (YYYY-MM-DD): ")

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
