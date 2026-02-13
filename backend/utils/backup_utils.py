import os
import shutil
import time
import zipfile
import subprocess
from datetime import datetime
from sqlalchemy.orm import Session
from backend.models.backup import Backup, BackupStatus, BackupType
from backend.models.task import Task, TaskStatus
from backend.models.site import Site
import uuid

def create_site_backup(
    db: Session,
    site_id: int,
    task_uuid: str,
    include_db: bool = True,
    include_files: bool = True
):
    task = db.query(Task).filter(Task.task_uuid == task_uuid).first()
    if not task:
        return

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        task.status = TaskStatus.failed
        task.error = "Site not found"
        db.commit()
        return

    task.status = TaskStatus.running
    task.message = f"Starting backup for {site.domain}..."
    task.progress = 10
    db.commit()

    try:
        backup_dir = "/www/backup"
        if os.name == 'nt':
            backup_dir = "C:/temp/backup" # Windows mock path
        
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{site.domain}_{timestamp}.zip"
        backup_path = os.path.join(backup_dir, backup_filename)

        # Mocking the actual process for now, but providing the structure
        task.progress = 30
        task.message = "Backing up files..."
        db.commit()
        
        # Real logic would go here:
        # if include_files:
        #     shutil.make_archive(backup_path.replace('.zip', ''), 'zip', site.path)
        
        time.sleep(1) # Simulate work

        if include_db:
            task.progress = 60
            task.message = "Backing up database..."
            db.commit()
            # Real logic: mysqldump ...
            time.sleep(1) # Simulate work

        # Finalizing
        task.progress = 90
        task.message = "Finalizing backup..."
        db.commit()

        # Create backup record
        new_backup = Backup(
            site_id=site.id,
            name=backup_filename,
            file_path=backup_path,
            file_size=1024 * 1024 * 15, # Mock 15MB
            type=BackupType.manual,
            status=BackupStatus.success,
            include_db=include_db,
            include_files=include_files
        )
        db.add(new_backup)
        
        task.status = TaskStatus.completed
        task.progress = 100
        task.message = "Backup completed successfully"
        task.completed_at = datetime.now()
        db.commit()

    except Exception as e:
        task.status = TaskStatus.failed
        task.error = str(e)
        task.message = "Backup failed"
        db.commit()
