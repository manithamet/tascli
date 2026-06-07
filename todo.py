"""
Terminal To-Do App
A simple keyboard-driven task manager using curses.

Controls:
    UP/DOWN    Navigate tasks and subtasks
    a          Add new task
    s          Add subtask to selected task
    t          Toggle task/subtask completion
    p          Cycle priority (⚡ -> ! -> -)
    d          Delete selected task/subtask
    LEFT       Move up one level (out of subtasks)
    q          Quit application
"""

from __future__ import annotations

import curses
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# ============================================
# DATA MODEL
# ============================================


@dataclass
class Task:
    """
    Represents a single to-do task or subtask.

    Attributes:
        id: Unique identifier for the task
        title: The task description text
        done: Whether the task is completed (True/False)
        priority: Task priority level (1=⚡/red, 2=!/yellow, 3=-/white)
        subtasks: List of child subtasks (inherits parent's priority)
    """

    id: str
    title: str
    done: bool = False
    priority: int = 3
    subtasks: List[Task] = field(default_factory=list)


def get_flat_items(
    tasks: List[Task], parent_path: Tuple[int, ...] = ()
) -> List[Tuple[Task, Tuple[int, ...]]]:
    """
    Flatten the nested task hierarchy into a list of (task, path) tuples.
    Path is the sequence of indices to reach the task.
    Example: (0,) = first task, (0,1) = first task's second subtask
    """
    flat = []
    for i, task in enumerate(tasks):
        current_path = parent_path + (i,)
        flat.append((task, current_path))
        flat.extend(get_flat_items(task.subtasks, current_path))
    return flat


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
    tasks: List[Task] = []  # All root-level tasks

    # selected_path is a tuple of indices representing the path to current selection
    # () = no selection, (0,) = first task, (0,1) = first task's second subtask
    selected_path: Tuple[int, ...] = ()

    # Sample data with subtasks
    groceries = Task(str(uuid.uuid4()), "Buy groceries", False, 1)
    groceries.subtasks = [
        Task(str(uuid.uuid4()), "Milk", False, 1),
        Task(str(uuid.uuid4()), "Eggs", True, 1),
        Task(str(uuid.uuid4()), "Bread", False, 1),
    ]
    tasks.append(groceries)
    tasks.append(Task(str(uuid.uuid4()), "Call parents", False, 3))

    # Select the first task by default
    if tasks:
        selected_path = (0,)

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
            "TODO (↑↓ navigate | a add task | s add subtask | t toggle | p priority | ← back | d delete | q quit)",
            curses.A_BOLD,
        )

        # Draw each task recursively
        def draw_tasks(
            task_list: List[Task], path_prefix: Tuple[int, ...], y_offset: int
        ) -> int:
            """
            Draw tasks and their subtasks recursively.
            Returns the number of lines used.
            """
            line_count = 0
            for i, task in enumerate(task_list):
                current_path = path_prefix + (i,)
                y = y_offset + line_count

                # Calculate indent based on depth
                depth = len(path_prefix)
                indent = "  " * depth

                # Determine the priority to display (inherited from parent if subtask)
                display_priority = task.priority

                # Draw the task
                prefix = "✓" if task.done else "✗"
                p_symbol = {1: "⚡", 2: "!", 3: "-"}[display_priority]
                color = display_priority if not task.done else 4

                task_text = f"{indent}{prefix} {p_symbol} {task.title}"
                stdscr.addstr(y, 0, task_text, curses.color_pair(color))

                # Highlight selected task
                if current_path == selected_path:
                    stdscr.addstr(y, 0, ">", curses.color_pair(4))

                line_count += 1

                # Recursively draw subtasks
                if task.subtasks:
                    line_count += draw_tasks(task.subtasks, current_path, y + 1)

            return line_count

        draw_tasks(tasks, (), 2)

        stdscr.refresh()

        # --- HANDLE INPUT ---
        key = stdscr.getch()

        # Get all flat items for navigation
        flat_items = get_flat_items(tasks)

        # Find current index in flat list
        try:
            current_index = [path for (_, path) in flat_items].index(selected_path)
        except ValueError:
            current_index = -1

        # Navigation: Move down
        if key == curses.KEY_DOWN and current_index < len(flat_items) - 1:
            selected_path = flat_items[current_index + 1][1]

        # Navigation: Move up
        elif key == curses.KEY_UP and current_index > 0:
            selected_path = flat_items[current_index - 1][1]

        # Navigation: Move up one level (go to parent)
        elif key == curses.KEY_LEFT and selected_path:
            selected_path = selected_path[:-1]
            if not selected_path:
                selected_path = ()

        # Add new task
        elif key == ord("a"):
            curses.echo()
            stdscr.addstr(h - 1, 0, "Task: ")
            stdscr.refresh()
            title = stdscr.getstr(h - 1, 6).decode()
            curses.noecho()
            if title:
                new_task = Task(str(uuid.uuid4()), title)
                tasks.append(new_task)
                selected_path = (len(tasks) - 1,)

        # Add subtask to selected task
        elif key == ord("s") and selected_path:
            # Navigate to parent task
            parent_task = tasks
            for idx in selected_path[:-1]:
                parent_task = parent_task[idx].subtasks

            parent_task = parent_task[selected_path[-1]]

            curses.echo()
            stdscr.addstr(h - 1, 0, "Subtask: ")
            stdscr.refresh()
            title = stdscr.getstr(h - 1, 9).decode()
            curses.noecho()
            if title:
                # Subtasks inherit parent's priority
                new_subtask = Task(
                    str(uuid.uuid4()), title, False, parent_task.priority
                )
                parent_task.subtasks.append(new_subtask)
                selected_path = selected_path + (len(parent_task.subtasks) - 1,)

        # Toggle completion
        elif key == ord("t") and selected_path:
            parent_task = tasks
            for idx in selected_path[:-1]:
                parent_task = parent_task[idx].subtasks
            parent_task[selected_path[-1]].done = not parent_task[
                selected_path[-1]
            ].done

        # Cycle priority: 1 -> 2 -> 3 -> 1
        elif key == ord("p") and selected_path:
            parent_task = tasks
            for idx in selected_path[:-1]:
                parent_task = parent_task[idx].subtasks
            parent_task[selected_path[-1]].priority = (
                parent_task[selected_path[-1]].priority % 3 + 1
            )

        # Delete task/subtask
        elif key == ord("d") and selected_path:
            parent_task = tasks
            for idx in selected_path[:-1]:
                parent_task = parent_task[idx].subtasks

            del parent_task[selected_path[-1]]

            if not parent_task:
                selected_path = selected_path[:-1]
                if not selected_path:
                    selected_path = ()
            else:
                new_idx = min(selected_path[-1], len(parent_task) - 1)
                selected_path = selected_path[:-1] + (new_idx,)

        # Quit
        elif key == ord("q"):
            break


# curses.wrapper() handles init/cleanup and passes screen object to main()
if __name__ == "__main__":
    curses.wrapper(main)
