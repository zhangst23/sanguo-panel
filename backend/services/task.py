from sqlalchemy.orm import Session
from backend.models.task import Task, TaskStatus
import uuid
from datetime import datetime
from typing import Optional, Any, Dict

class TaskService:
    @staticmethod
    def create_task(
        db: Session,
        task_type: str,
        user_id: int,
        site_id: Optional[int] = None,
        message: str = "Task started"
    ) -> Task:
        task = Task(
            task_uuid=str(uuid.uuid4()),
            type=task_type,
            site_id=site_id,
            status=TaskStatus.running,
            progress=0,
            message=message,
            created_by=user_id,
            started_at=datetime.utcnow()
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def update_progress(
        db: Session,
        task_uuid: str,
        progress: int,
        message: Optional[str] = None
    ):
        task = db.query(Task).filter(Task.task_uuid == task_uuid).first()
        if task:
            task.progress = progress
            if message:
                task.message = message
            db.commit()

    @staticmethod
    def complete_task(
        db: Session,
        task_uuid: str,
        result: Optional[Dict[str, Any]] = None,
        message: str = "Task completed"
    ):
        task = db.query(Task).filter(Task.task_uuid == task_uuid).first()
        if task:
            task.status = TaskStatus.completed
            task.progress = 100
            task.message = message
            task.result = result
            task.completed_at = datetime.utcnow()
            db.commit()

    @staticmethod
    def fail_task(
        db: Session,
        task_uuid: str,
        error: str,
        message: str = "Task failed"
    ):
        task = db.query(Task).filter(Task.task_uuid == task_uuid).first()
        if task:
            task.status = TaskStatus.failed
            task.error = error
            task.message = message
            task.completed_at = datetime.utcnow()
            db.commit()

task_service = TaskService()
