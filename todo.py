"""
Terminal To-Do App
A simple keyboard-driven task manager using curses.

Controls:
    UP/DOWN    Navigate tasks
    a          Add new task
    t          Toggle task completion
    p          Cycle priority (⚡ -> ! -> -)
    d          Delete selected task
    q          Quit application
"""

import curses
import uuid
from dataclasses import dataclass
from typing import List

# ============================================
# DATA MODEL
# ============================================


@dataclass
class Task:
    """
    Represents a single to-do task.

    Attributes:
        id: Unique identifier for the task
        title: The task description text
        done: Whether the task is completed (True/False)
        priority: Task priority level
            1 = High priority (displayed as ⚡ and colored red)
            2 = Medium priority (displayed as ! and colored yellow)
            3 = Low priority (displayed as - and colored white)
    """

    id: str
    title: str
    done: bool = False
    priority: int = 3


# ============================================
# MAIN APPLICATION
# ============================================


def main(stdscr):
    """
    Main function that runs the TUI application.

    stdscr: The curses window object - our canvas to draw on.
            Provided automatically by curses.wrapper().
    """

    # --- CURSES SETUP ---
    curses.curs_set(0)  # Hide blinking cursor
    curses.start_color()  # Enable color support

    # Define color pairs (foreground, background)
    curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)  # High priority
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Medium priority
    curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLACK)  # Low priority
    curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Done tasks

    # --- APP STATE ---
    tasks: List[Task] = []  # All tasks
    selected = 0  # Currently selected task index

    # Sample data
    tasks.append(Task(str(uuid.uuid4()), "Buy milk", False, 1))
    tasks.append(Task(str(uuid.uuid4()), "Call mom", False, 3))

    # ============================================
    # MAIN LOOP
    # ============================================
    while True:
        # --- DRAW UI ---
        stdscr.clear()
        h, w = stdscr.getmaxyx()  # Terminal height, width

        # Header with controls
        stdscr.addstr(
            0,
            0,
            "TODO (↑↓ navigate | a add | t toggle | p priority | d delete | q quit)",
            curses.A_BOLD,
        )

        # Draw each task
        for i, task in enumerate(tasks):
            y = i + 2  # Start drawing tasks from row 2
            prefix = "✓" if task.done else "✗"
            p_symbol = {1: "⚡", 2: "!", 3: "-"}[task.priority]
            color = task.priority if not task.done else 4
            stdscr.addstr(
                y, 0, f"{prefix} {p_symbol} {task.title}", curses.color_pair(color)
            )

            # Highlight selected task with >
            if i == selected:
                stdscr.addstr(y, 0, ">", curses.color_pair(4))

        stdscr.refresh()

        # --- HANDLE INPUT ---
        key = stdscr.getch()

        # Navigation
        if key == curses.KEY_UP and selected > 0:
            selected -= 1
        elif key == curses.KEY_DOWN and selected < len(tasks) - 1:
            selected += 1

        # Add task
        elif key == ord("a"):
            curses.echo()  # Show typed characters
            stdscr.addstr(h - 1, 0, "Task: ")
            stdscr.refresh()
            title = stdscr.getstr(h - 1, 6).decode()
            curses.noecho()  # Hide typed characters again
            if title:
                tasks.append(Task(str(uuid.uuid4()), title))
                selected = len(tasks) - 1

        # Toggle completion
        elif key == ord("t") and tasks:
            tasks[selected].done = not tasks[selected].done

        # Cycle priority: 1 -> 2 -> 3 -> 1
        elif key == ord("p") and tasks:
            tasks[selected].priority = tasks[selected].priority % 3 + 1

        # Delete task
        elif key == ord("d") and tasks:
            tasks.pop(selected)
            selected = max(0, selected - 1)

        # Quit
        elif key == ord("q"):
            break


# curses.wrapper() handles init/cleanup and passes screen object to main()
if __name__ == "__main__":
    curses.wrapper(main)
