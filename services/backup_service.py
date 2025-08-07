import asyncio
import gzip
import json
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from models.task import Task
from models.gmail_channel import GmailChannel
from config.settings import settings
from database import async_session

logger = structlog.get_logger()

class BackupServiceError(Exception):
    """Backup service specific errors"""
    pass

class BackupService:
    """Service for creating and managing database backups"""
    
    def __init__(self):
        self.backup_directory = Path(settings.backup_directory)
        self.retention_days = settings.backup_retention_days
        self.max_tasks_limit = settings.max_tasks_limit
        
        # Ensure backup directory exists
        self.backup_directory.mkdir(parents=True, exist_ok=True)
    
    async def create_daily_backup(self) -> Dict[str, Any]:
        """
        Create a daily backup of the database with gzip compression
        
        Returns:
            Backup creation result
        """
        try:
            logger.info("Starting daily backup creation")
            
            # Generate backup filename with timestamp
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"backup_{timestamp}.json.gz"
            backup_path = self.backup_directory / backup_filename
            
            # Export data from database
            backup_data = await self._export_database_data()
            
            # Compress and save backup
            with gzip.open(backup_path, 'wt', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, default=str)
            
            # Get backup file size
            backup_size = backup_path.stat().st_size
            
            # Clean up old backups
            cleaned_count = await self._cleanup_old_backups()
            
            logger.info(
                "Daily backup created successfully",
                backup_file=backup_filename,
                backup_size_bytes=backup_size,
                backup_size_mb=round(backup_size / 1024 / 1024, 2),
                tasks_count=backup_data.get("metadata", {}).get("tasks_count", 0),
                channels_count=backup_data.get("metadata", {}).get("channels_count", 0),
                cleaned_backups=cleaned_count
            )
            
            return {
                "status": "success",
                "backup_file": backup_filename,
                "backup_path": str(backup_path),
                "backup_size_bytes": backup_size,
                "backup_size_mb": round(backup_size / 1024 / 1024, 2),
                "tasks_count": backup_data.get("metadata", {}).get("tasks_count", 0),
                "channels_count": backup_data.get("metadata", {}).get("channels_count", 0),
                "cleaned_backups": cleaned_count,
                "timestamp": timestamp
            }
            
        except Exception as e:
            logger.error("Failed to create daily backup", error=str(e), exc_info=True)
            raise BackupServiceError(f"Failed to create daily backup: {str(e)}")
    
    async def restore_from_backup(self, backup_filename: str) -> Dict[str, Any]:
        """
        Restore database from a backup file
        
        Args:
            backup_filename: Name of the backup file to restore from
            
        Returns:
            Restore operation result
        """
        try:
            backup_path = self.backup_directory / backup_filename
            
            if not backup_path.exists():
                raise BackupServiceError(f"Backup file not found: {backup_filename}")
            
            logger.info("Starting database restore", backup_file=backup_filename)
            
            # Load backup data
            with gzip.open(backup_path, 'rt', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Validate backup data
            if not self._validate_backup_data(backup_data):
                raise BackupServiceError("Invalid backup data format")
            
            # Restore data to database
            restore_result = await self._restore_database_data(backup_data)
            
            logger.info(
                "Database restored successfully",
                backup_file=backup_filename,
                tasks_restored=restore_result.get("tasks_restored", 0),
                channels_restored=restore_result.get("channels_restored", 0)
            )
            
            return {
                "status": "success",
                "backup_file": backup_filename,
                "tasks_restored": restore_result.get("tasks_restored", 0),
                "channels_restored": restore_result.get("channels_restored", 0),
                "restore_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(
                "Failed to restore from backup",
                backup_file=backup_filename,
                error=str(e),
                exc_info=True
            )
            raise BackupServiceError(f"Failed to restore from backup: {str(e)}")
    
    async def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backup files
        
        Returns:
            List of backup file information
        """
        try:
            backups = []
            
            for backup_file in self.backup_directory.glob("backup_*.json.gz"):
                try:
                    stat = backup_file.stat()
                    
                    # Extract timestamp from filename
                    filename = backup_file.name
                    timestamp_str = filename.replace("backup_", "").replace(".json.gz", "")
                    
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                    except ValueError:
                        timestamp = datetime.fromtimestamp(stat.st_mtime)
                    
                    backups.append({
                        "filename": filename,
                        "path": str(backup_file),
                        "size_bytes": stat.st_size,
                        "size_mb": round(stat.st_size / 1024 / 1024, 2),
                        "created_at": timestamp.isoformat(),
                        "age_days": (datetime.utcnow() - timestamp).days
                    })
                    
                except Exception as e:
                    logger.warning(
                        "Failed to process backup file",
                        file=str(backup_file),
                        error=str(e)
                    )
                    continue
            
            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x["created_at"], reverse=True)
            
            return backups
            
        except Exception as e:
            logger.error("Failed to list backups", error=str(e))
            raise BackupServiceError(f"Failed to list backups: {str(e)}")
    
    async def get_backup_stats(self) -> Dict[str, Any]:
        """
        Get backup statistics and storage information
        
        Returns:
            Backup statistics
        """
        try:
            backups = await self.list_backups()
            
            total_size = sum(backup["size_bytes"] for backup in backups)
            oldest_backup = min(backups, key=lambda x: x["created_at"]) if backups else None
            newest_backup = max(backups, key=lambda x: x["created_at"]) if backups else None
            
            # Get current database stats
            async with async_session() as db:
                tasks_count_result = await db.execute(select(func.count(Task.id)))
                tasks_count = tasks_count_result.scalar()
                
                channels_count_result = await db.execute(select(func.count(GmailChannel.id)))
                channels_count = channels_count_result.scalar()
            
            return {
                "backup_count": len(backups),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "retention_days": self.retention_days,
                "backup_directory": str(self.backup_directory),
                "oldest_backup": oldest_backup,
                "newest_backup": newest_backup,
                "current_database": {
                    "tasks_count": tasks_count,
                    "channels_count": channels_count,
                    "tasks_limit": self.max_tasks_limit,
                    "tasks_limit_usage_percent": round((tasks_count / self.max_tasks_limit) * 100, 2)
                }
            }
            
        except Exception as e:
            logger.error("Failed to get backup stats", error=str(e))
            raise BackupServiceError(f"Failed to get backup stats: {str(e)}")
    
    async def run_daily_backup_scheduler(self):
        """
        Background task to create daily backups at scheduled time
        """
        logger.info("Starting daily backup scheduler")
        
        while True:
            try:
                # Calculate next backup time (2:00 AM UTC)
                now = datetime.utcnow()
                next_backup = now.replace(hour=2, minute=0, second=0, microsecond=0)
                
                # If we've passed today's backup time, schedule for tomorrow
                if now >= next_backup:
                    next_backup += timedelta(days=1)
                
                # Calculate sleep time
                sleep_seconds = (next_backup - now).total_seconds()
                
                logger.info(
                    "Next backup scheduled",
                    next_backup=next_backup.isoformat(),
                    sleep_seconds=sleep_seconds
                )
                
                # Sleep until backup time
                await asyncio.sleep(sleep_seconds)
                
                # Create backup
                result = await self.create_daily_backup()
                
                logger.info(
                    "Scheduled backup completed",
                    result=result
                )
                
            except Exception as e:
                logger.error(
                    "Error in backup scheduler",
                    error=str(e),
                    exc_info=True
                )
                # Sleep for 1 hour before retrying
                await asyncio.sleep(3600)
    
    async def _export_database_data(self) -> Dict[str, Any]:
        """Export all data from the database"""
        try:
            async with async_session() as db:
                # Export tasks
                tasks_result = await db.execute(select(Task))
                tasks = tasks_result.scalars().all()
                tasks_data = [task.to_dict() for task in tasks]
                
                # Export Gmail channels
                channels_result = await db.execute(select(GmailChannel))
                channels = channels_result.scalars().all()
                channels_data = [channel.to_dict() for channel in channels]
                
                # Create backup data structure
                backup_data = {
                    "metadata": {
                        "backup_version": "1.0",
                        "created_at": datetime.utcnow().isoformat(),
                        "tasks_count": len(tasks_data),
                        "channels_count": len(channels_data),
                        "database_url": settings.database_url,
                        "max_tasks_limit": self.max_tasks_limit
                    },
                    "tasks": tasks_data,
                    "gmail_channels": channels_data
                }
                
                return backup_data
                
        except Exception as e:
            logger.error("Failed to export database data", error=str(e))
            raise
    
    async def _restore_database_data(self, backup_data: Dict[str, Any]) -> Dict[str, Any]:
        """Restore data to the database"""
        try:
            async with async_session() as db:
                # Clear existing data (be careful!)
                await db.execute("DELETE FROM tasks")
                await db.execute("DELETE FROM gmail_channels")
                
                # Restore tasks
                tasks_data = backup_data.get("tasks", [])
                tasks_restored = 0
                
                for task_dict in tasks_data:
                    try:
                        # Create task object
                        task = Task(
                            title=task_dict["title"],
                            due=datetime.fromisoformat(task_dict["due"]) if task_dict.get("due") else None,
                            status=task_dict["status"],
                            source=task_dict["source"],
                            priority=task_dict["priority"]
                        )
                        
                        db.add(task)
                        tasks_restored += 1
                        
                    except Exception as e:
                        logger.warning(
                            "Failed to restore task",
                            task_data=task_dict,
                            error=str(e)
                        )
                        continue
                
                # Restore Gmail channels
                channels_data = backup_data.get("gmail_channels", [])
                channels_restored = 0
                
                for channel_dict in channels_data:
                    try:
                        # Create channel object
                        channel = GmailChannel(
                            email=channel_dict["email"],
                            channel_id=channel_dict["channel_id"],
                            history_id=channel_dict["history_id"],
                            expiration=datetime.fromisoformat(channel_dict["expiration"])
                        )
                        
                        db.add(channel)
                        channels_restored += 1
                        
                    except Exception as e:
                        logger.warning(
                            "Failed to restore channel",
                            channel_data=channel_dict,
                            error=str(e)
                        )
                        continue
                
                # Commit all changes
                await db.commit()
                
                return {
                    "tasks_restored": tasks_restored,
                    "channels_restored": channels_restored
                }
                
        except Exception as e:
            logger.error("Failed to restore database data", error=str(e))
            raise
    
    def _validate_backup_data(self, backup_data: Dict[str, Any]) -> bool:
        """Validate backup data structure"""
        try:
            # Check required keys
            required_keys = ["metadata", "tasks", "gmail_channels"]
            for key in required_keys:
                if key not in backup_data:
                    logger.error(f"Missing required key in backup data: {key}")
                    return False
            
            # Check metadata
            metadata = backup_data["metadata"]
            if not isinstance(metadata, dict):
                logger.error("Invalid metadata format")
                return False
            
            # Check data arrays
            if not isinstance(backup_data["tasks"], list):
                logger.error("Invalid tasks data format")
                return False
            
            if not isinstance(backup_data["gmail_channels"], list):
                logger.error("Invalid channels data format")
                return False
            
            return True
            
        except Exception as e:
            logger.error("Failed to validate backup data", error=str(e))
            return False
    
    async def _cleanup_old_backups(self) -> int:
        """Clean up backups older than retention period"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
            cleaned_count = 0
            
            for backup_file in self.backup_directory.glob("backup_*.json.gz"):
                try:
                    # Get file modification time
                    file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    
                    if file_time < cutoff_date:
                        backup_file.unlink()
                        cleaned_count += 1
                        
                        logger.info(
                            "Cleaned up old backup",
                            file=backup_file.name,
                            age_days=(datetime.utcnow() - file_time).days
                        )
                        
                except Exception as e:
                    logger.warning(
                        "Failed to clean up backup file",
                        file=str(backup_file),
                        error=str(e)
                    )
                    continue
            
            return cleaned_count
            
        except Exception as e:
            logger.error("Failed to cleanup old backups", error=str(e))
            return 0