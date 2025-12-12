"""Task management service for CRUD operations."""

from typing import List, Optional
from datetime import datetime

from backend.models import Task, Priority


class TaskManager:
    """Service for managing tasks."""

    def __init__(self):
        self.tasks: List[Task] = []

    def add_task(
        self,
        name: str,
        subject: str,
        estimated_hours: float,
        deadline: datetime,
        priority: Priority,
        can_be_split: bool = True,
        description: Optional[str] = None
    ) -> Task:
        """Add a new task."""
        task_id = str(len(self.tasks) + 1)
        task = Task(
            id=task_id,
            name=name,
            subject=subject,
            estimated_hours=estimated_hours,
            deadline=deadline,
            priority=priority,
            can_be_split=can_be_split,
            description=description
        )
        self.tasks.append(task)
        return task

    def remove_task(self, task_id: str) -> bool:
        """Remove a task by ID."""
        initial_count = len(self.tasks)
        self.tasks = [t for t in self.tasks if t.id != task_id]
        return len(self.tasks) < initial_count

    def get_all_tasks(self) -> List[Task]:
        """Get all tasks."""
        return self.tasks.copy()

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Get a specific task."""
        return next((t for t in self.tasks if t.id == task_id), None)

    def clear_all_tasks(self):
        """Remove all tasks."""
        self.tasks.clear()

    @property
    def total_hours(self) -> float:
        """Calculate total estimated hours for all tasks."""
        return sum(task.estimated_hours for task in self.tasks)
