from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.api import deps
from backend.models.task import Task as TaskModel
from backend.schemas.task import Task

router = APIRouter()

@router.get("/", response_model=List[Task])
def read_tasks(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve tasks.
    """
    tasks = db.query(TaskModel).order_by(TaskModel.created_at.desc()).offset(skip).limit(limit).all()
    return tasks

@router.get("/{task_uuid}", response_model=Task)
def read_task(
    *,
    db: Session = Depends(deps.get_db),
    task_uuid: str,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get task by UUID.
    """
    task = db.query(TaskModel).filter(TaskModel.task_uuid == task_uuid).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.delete("/{task_uuid}")
def delete_task(
    *,
    db: Session = Depends(deps.get_db),
    task_uuid: str,
    current_user: Any = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete task record.
    """
    task = db.query(TaskModel).filter(TaskModel.task_uuid == task_uuid).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.delete(task)
    db.commit()
    return {"success": True}
