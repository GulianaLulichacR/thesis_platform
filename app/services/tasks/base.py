from abc import ABC, abstractmethod
from typing import Any, Callable


class TaskService(ABC):
    """
    Abstract interface for executing background tasks.
    Allows easy migration from FastAPI BackgroundTasks to Celery, Redis Queue, etc.
    """

    @abstractmethod
    def enqueue(self, func: Callable, *args: Any, **kwargs: Any) -> None:
        """Enqueue a background task."""
        pass
