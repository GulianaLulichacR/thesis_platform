from typing import Any, Callable

from fastapi import BackgroundTasks

from app.services.tasks.base import TaskService


class FastAPITaskService(TaskService):
    """
    Implementation of TaskService using FastAPI BackgroundTasks.
    Good for MVP Phase 1.
    """

    def __init__(self, background_tasks: BackgroundTasks) -> None:
        self.background_tasks = background_tasks

    def enqueue(self, func: Callable, *args: Any, **kwargs: Any) -> None:
        self.background_tasks.add_task(func, *args, **kwargs)
