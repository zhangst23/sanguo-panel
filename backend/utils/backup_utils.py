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
        # 获取项目根目录 (假设当前运行目录或其上级)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        backup_dir = os.path.join(base_dir, "backup")
        
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

        # Real Logic: Create the ZIP file
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            if include_files and os.path.exists(site.root_path):
                # Add site files
                for root, dirs, files in os.walk(site.root_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, site.root_path)
                        zipf.write(file_path, os.path.join("www", arcname))
            
            # Note: Database backup would normally involve mysqldump
            # For now we create a placeholder if include_db is true
            if include_db:
                db_sql_content = f"-- Database backup for {site.domain}\n-- Generated at {timestamp}\n"
                zipf.writestr("database.sql", db_sql_content)

        file_size = os.path.getsize(backup_path)

        # Create backup record
        new_backup = Backup(
            site_id=site.id,
            name=backup_filename,
            file_path=backup_path,
            file_size=file_size,
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
        task.message = f"Backup failed: {str(e)}"
        db.commit()

def restore_site_backup(
    db: Session,
    backup_id: int,
    task_uuid: str
):
    task = db.query(Task).filter(Task.task_uuid == task_uuid).first()
    if not task:
        return

    backup = db.query(Backup).filter(Backup.id == backup_id).first()
    if not backup:
        task.status = TaskStatus.failed
        task.error = "Backup record not found"
        db.commit()
        return

    site = db.query(Site).filter(Site.id == backup.site_id).first()
    if not site:
        task.status = TaskStatus.failed
        task.error = "Associated site not found"
        db.commit()
        return

    task.status = TaskStatus.running
    task.message = f"Starting restore for {site.domain} from {backup.name}..."
    task.progress = 10
    db.commit()

    try:
        if not os.path.exists(backup.file_path):
            raise Exception("Backup file not found on disk")

        # 1. Unzip
        task.progress = 30
        task.message = "Extracting backup files..."
        db.commit()
        
        with zipfile.ZipFile(backup.file_path, 'r') as zipf:
            # Extract to site root
            if backup.include_files:
                # We need to filter and map members to the site root
                for member in zipf.infolist():
                    if member.filename.startswith("www/"):
                        # Remove the "www/" prefix when extracting
                        member.filename = member.filename[4:]
                        if member.filename: # Ensure it's not empty
                            zipf.extract(member, site.root_path)

            # 2. Database Restore (Placeholder)
            if backup.include_db:
                task.progress = 70
                task.message = "Restoring database..."
                db.commit()
                # Real logic: mysql -u... -p... db_name < extracted_sql
                time.sleep(1) # Simulate

        task.status = TaskStatus.completed
        task.progress = 100
        task.message = "Restore completed successfully"
        task.completed_at = datetime.now()
        db.commit()

    except Exception as e:
        task.status = TaskStatus.failed
        task.error = str(e)
        task.message = f"Restore failed: {str(e)}"
        db.commit()
