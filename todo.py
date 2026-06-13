"""
Terminal To-Do App - Modern Charmbracelet-style TUI

Controls:
    UP/DOWN    Navigate tasks and subtasks
    LEFT       Go up one level / exit card
    a          Add new task
    s          Add subtask to selected task
    e          Edit selected task title
    t          Toggle task/subtask completion (cascades for parents)
    p          Cycle card priority (⚡ magenta / ! white / - cyan)
    d          Delete selected task/subtask
    q          Quit application
"""

from __future__ import annotations
import curses
import uuid
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


# ============================================
# DATA MODEL
# ============================================

@dataclass
class Task:
    id: str
    title: str
    done: bool = False
    priority: int = 3  # Only for main tasks: 1=high, 2=medium, 3=low
    subtasks: List[Task] = field(default_factory=list)

    def update_priority_recursive(self, new_priority: int) -> None:
        """Recursively update priority for this task and all subtasks."""
        self.priority = new_priority
        for subtask in self.subtasks:
            subtask.update_priority_recursive(new_priority)

    def toggle_cascade(self) -> None:
        """Toggle this task and all subtasks recursively."""
        self.done = not self.done
        for subtask in self.subtasks:
            subtask.toggle_cascade()


def get_flat_items(tasks: List[Task], parent_path: Tuple[int, ...] = ()) -> List[Tuple[Task, Tuple[int, ...]]]:
    flat = []
    for i, task in enumerate(tasks):
        current_path = parent_path + (i,)
        flat.append((task, current_path))
        flat.extend(get_flat_items(task.subtasks, current_path))
    return flat


def count_all_tasks(tasks: List[Task]) -> int:
    count = len(tasks)
    for task in tasks:
        count += count_all_tasks(task.subtasks)
    return count


def count_done_tasks(tasks: List[Task]) -> int:
    count = sum(1 for t in tasks if t.done)
    for task in tasks:
        count += count_done_tasks(task.subtasks)
    return count


def count_tasks_in_tree(tasks: List[Task]) -> int:
    count = len(tasks)
    for task in tasks:
        count += count_tasks_in_tree(task.subtasks)
    return count


def count_done_in_tree(tasks: List[Task]) -> int:
    count = sum(1 for t in tasks if t.done)
    for task in tasks:
        count += count_done_in_tree(task.subtasks)
    return count


def get_parent_list_and_index(tasks: List[Task], path: Tuple[int, ...]) -> Optional[Tuple[List[Task], int]]:
    if not path:
        return None
    current = tasks
    for idx in path[:-1]:
        if idx < 0 or idx >= len(current):
            return None
        current = current[idx].subtasks
    final_index = path[-1]
    if final_index < 0 or final_index >= len(current):
        return None
    return (current, final_index)


def wrap_text(text: str, width: int) -> List[str]:
    if width <= 0:
        return []
    words = text.split()
    lines = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > width:
            lines.append(current)
            current = word
        else:
            current += (" " + word if current else word)
    if current:
        lines.append(current)
    return lines if lines else [""]


# ============================================
# DRAWING HELPERS
# ============================================

def draw_progress_bar(stdscr, y: int, x: int, width: int, percent: float, color_pair: int, label: str = "") -> None:
    if width < 10:
        width = 10
    bar_width = width - len(label) - 4
    if bar_width < 4:
        bar_width = 4
    filled = int(percent * bar_width)
    empty = bar_width - filled
    bar = "█" * filled + "░" * empty
    text = f"[{bar}] {int(percent * 100)}% {label}"
    stdscr.addstr(y, x, text[:width], curses.color_pair(color_pair))


def draw_header(stdscr, w: int) -> int:
    header = " T O D O "
    padding = (w - len(header)) // 2
    stdscr.addstr(0, 0, " " * w)
    if w >= len(header):
        stdscr.addstr(0, padding, header, curses.A_BOLD)
    stdscr.addstr(1, 0, "─" * w)
    return 2


def draw_task_line(stdscr, y: int, x: int, task: Task, is_selected: bool, depth: int, parent_priority: int, max_width: int) -> int:
    is_main_task = depth == 0
    indent = "  " * depth
    
    if task.done:
        checkbox = "⭕"
    else:
        checkbox = "○"
    
    if is_main_task:
        p_symbol = {1: "⚡", 2: "!", 3: "-"}[task.priority]
        prefix = f"{checkbox} {p_symbol} "
    else:
        prefix = f"{checkbox} "
    
    prefix_len = len(indent) + len(prefix)
    available_width = max(max_width - prefix_len, 1)
    
    lines = wrap_text(task.title, available_width)
    line_count = len(lines)
    
    for i, line in enumerate(lines):
        actual_y = y + i
        text = f"{indent}{prefix if i == 0 else '  ' * len(prefix)}{line}"
        
        display_priority = task.priority if is_main_task else parent_priority
        color = display_priority if not task.done else 4
        
        stdscr.addstr(actual_y, x, text[:max_width], curses.color_pair(color))
        
        if task.done and i == 0:
            strike_x = x + len(indent) + len(prefix)
            strike_len = min(len(line), max_width - strike_x)
            if strike_len > 0:
                stdscr.addstr(actual_y, strike_x, "─" * strike_len, curses.color_pair(5))
        
        if is_selected and i == 0:
            stdscr.addstr(actual_y, x, ">", curses.color_pair(4))
    
    return line_count


def draw_card(stdscr, y: int, task: Task, selected_path: Tuple[int, ...], current_path: Tuple[int, ...], max_width: int) -> int:
    lines_used = 0
    is_main_card = len(current_path) == 1
    has_subtasks = bool(task.subtasks)
    is_selected = current_path == selected_path
    priority = task.priority
    card_color = priority
    
    if is_main_card:
        card_width = min(max_width, 80)
        if card_width < 10:
            card_width = max_width
        
        stdscr.addstr(y + lines_used, 0, " " * max_width)
        stdscr.addstr(y + lines_used, 0, "┌" + "─" * (card_width - 2) + "┐", curses.color_pair(card_color))
        lines_used += 1
        
        task_lines = draw_task_line(stdscr, y + lines_used, 1, task, is_selected, 0, priority, card_width - 2)
        lines_used += task_lines
        
        if has_subtasks:
            done_count = count_done_in_tree(task.subtasks)
            total_count = count_tasks_in_tree(task.subtasks)
            percent = done_count / total_count if total_count > 0 else 0.0
            pb_width = card_width - 4
            draw_progress_bar(stdscr, y + lines_used, 2, pb_width, percent, card_color, "")
            lines_used += 1
            
            for i, subtask in enumerate(task.subtasks):
                sub_path = current_path + (i,)
                sub_lines = draw_task_line(stdscr, y + lines_used, 2, subtask, sub_path == selected_path, 1, priority, card_width - 4)
                lines_used += sub_lines
            
            stdscr.addstr(y + lines_used, 0, "└" + "─" * (card_width - 2) + "┘", curses.color_pair(card_color))
            lines_used += 1
        else:
            stdscr.addstr(y + lines_used, 0, "└" + "─" * (card_width - 2) + "┘", curses.color_pair(card_color))
            lines_used += 1
        
        lines_used += 1
    else:
        sub_lines = draw_task_line(stdscr, y + lines_used, 0, task, is_selected, len(current_path) - 1, task.priority, max_width)
        lines_used += sub_lines
    
    return lines_used


# ============================================
# MAIN APPLICATION
# ============================================

def main(stdscr):
    curses.curs_set(0)
    curses.start_color()
    
    # Color pairs: 1=magenta, 2=white, 3=cyan, 4=green, 5=dim/white, 6=white
    curses.init_pair(1, curses.COLOR_MAGENTA, curses.COLOR_BLACK)  # High priority
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)    # Medium priority
    curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)     # Low priority
    curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)    # Done
    curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)    # Dim/strikethrough
    curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLACK)    # Header/borders

    tasks: List[Task] = []
    selected_path: Tuple[int, ...] = ()

    groceries = Task(str(uuid.uuid4()), "Buy groceries", False, 1)
    groceries.subtasks = [
        Task(str(uuid.uuid4()), "Get milk from the store", False),
        Task(str(uuid.uuid4()), "Eggs", True),
        Task(str(uuid.uuid4()), "Whole grain bread and also some butter", False),
    ]
    
    work = Task(str(uuid.uuid4()), "Finish project documentation and review code", False, 3)
    work.subtasks = [
        Task(str(uuid.uuid4()), "Write README", False),
        Task(str(uuid.uuid4()), "Update CHANGELOG", False),
        Task(str(uuid.uuid4()), "Review pull request #123", True),
    ]
    
    personal = Task(str(uuid.uuid4()), "Call parents", False, 2)
    
    tasks.append(groceries)
    tasks.append(work)
    tasks.append(personal)
    
    if tasks:
        selected_path = (0,)

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        header_lines = draw_header(stdscr, w)
        
        total_all = count_all_tasks(tasks)
        done_all = count_done_tasks(tasks)
        global_percent = done_all / total_all if total_all > 0 else 0.0
        draw_progress_bar(stdscr, header_lines, 0, w - 1, global_percent, 6, "global")
        header_lines += 1
        
        active_y = header_lines
        for i, task in enumerate(tasks):
            if not task.done:
                current_path = (i,)
                lines = draw_card(stdscr, active_y, task, selected_path, current_path, w)
                active_y += lines
        
        completed_y = active_y
        if count_done_tasks(tasks) > 0:
            stdscr.addstr(completed_y, 0, "─" * w, curses.color_pair(5))
            completed_header = " COMPLETED "
            padding = (w - len(completed_header)) // 2
            stdscr.addstr(completed_y, padding, completed_header, curses.A_DIM | curses.color_pair(5))
            completed_y += 1
            
            for i, task in enumerate(tasks):
                if task.done:
                    current_path = (i,)
                    lines = draw_card(stdscr, completed_y, task, selected_path, current_path, w)
                    completed_y += lines
        
        if h > 0:
            instructions = "↑↓ nav | a add | s subtask | e edit | t toggle | p priority | d del | ← back | q quit"
            stdscr.addstr(h - 1, 0, " " * w)
            stdscr.addstr(h - 1, 0, instructions[:w], curses.A_DIM | curses.color_pair(5))

        stdscr.refresh()

        key = stdscr.getch()
        flat_items = get_flat_items(tasks)
        
        try:
            current_index = [path for (_, path) in flat_items].index(selected_path)
        except (ValueError, IndexError):
            current_index = -1
        
        if key == curses.KEY_DOWN and current_index < len(flat_items) - 1:
            selected_path = flat_items[current_index + 1][1]
        elif key == curses.KEY_UP and current_index > 0:
            selected_path = flat_items[current_index - 1][1]
        elif key == curses.KEY_LEFT and selected_path:
            selected_path = selected_path[:-1]
            if not selected_path:
                selected_path = ()
        elif key == ord("a"):
            curses.echo()
            stdscr.addstr(h - 1, 0, "Task: ")
            stdscr.refresh()
            try:
                title = stdscr.getstr(h - 1, 6).decode()
            except:
                title = ""
            curses.noecho()
            if title:
                new_task = Task(str(uuid.uuid4()), title)
                tasks.append(new_task)
                selected_path = (len(tasks) - 1,)
        elif key == ord("s") and selected_path:
            result = get_parent_list_and_index(tasks, selected_path)
            if result:
                parent_list, parent_idx = result
                parent_task = parent_list[parent_idx]
                curses.echo()
                stdscr.addstr(h - 1, 0, "Subtask: ")
                stdscr.refresh()
                try:
                    title = stdscr.getstr(h - 1, 9).decode()
                except:
                    title = ""
                curses.noecho()
                if title:
                    new_subtask = Task(str(uuid.uuid4()), title, False)
                    parent_task.subtasks.append(new_subtask)
                    selected_path = selected_path + (len(parent_task.subtasks) - 1,)
        elif key == ord("e") and selected_path:
            result = get_parent_list_and_index(tasks, selected_path)
            if result:
                parent_list, parent_idx = result
                task_to_edit = parent_list[parent_idx]
                curses.echo()
                prompt = f"Edit [{task_to_edit.title[:20]}]: "
                stdscr.addstr(h - 1, 0, prompt)
                stdscr.refresh()
                try:
                    new_title = stdscr.getstr(h - 1, len(prompt)).decode()
                except:
                    new_title = ""
                curses.noecho()
                if new_title:
                    task_to_edit.title = new_title
        elif key == ord("t") and selected_path:
            result = get_parent_list_and_index(tasks, selected_path)
            if result:
                parent_list, parent_idx = result
                task = parent_list[parent_idx]
                if len(selected_path) == 1:
                    task.toggle_cascade()
                else:
                    task.done = not task.done
        elif key == ord("p") and selected_path and len(selected_path) == 1:
            result = get_parent_list_and_index(tasks, selected_path)
            if result:
                parent_list, parent_idx = result
                new_priority = parent_list[parent_idx].priority % 3 + 1
                parent_list[parent_idx].update_priority_recursive(new_priority)
        elif key == ord("d") and selected_path:
            result = get_parent_list_and_index(tasks, selected_path)
            if result:
                parent_list, parent_idx = result
                del parent_list[parent_idx]
                if not parent_list:
                    selected_path = selected_path[:-1]
                    if not selected_path:
                        selected_path = ()
                else:
                    new_idx = min(parent_idx, len(parent_list) - 1)
                    selected_path = selected_path[:-1] + (new_idx,)
        elif key == ord("q"):
            break


if __name__ == "__main__":
    curses.wrapper(main)
