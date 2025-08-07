import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from models.task import Task, Priority, TaskStatus
from services.task_service import TaskService
from services.telegram_service import TelegramService
from config.settings import settings
from database import async_session

logger = structlog.get_logger()

class SummaryServiceError(Exception):
    """Summary service specific errors"""
    pass

class SummaryService:
    """Service for generating and sending daily task summaries"""
    
    def __init__(self):
        self.timezone = settings.timezone
        self.summary_time = "07:00"  # 7:00 AM Mexico City time
    
    async def generate_daily_summary(self, task_service: TaskService) -> Dict[str, Any]:
        """
        Generate daily task summary with aggregation by priority
        
        Args:
            task_service: Task service instance
            
        Returns:
            Summary data with tasks grouped by priority
        """
        try:
            logger.info("Generating daily task summary")
            
            # Get tasks grouped by priority
            tasks_by_priority = await task_service.get_tasks_for_summary()
            
            # Calculate summary statistics
            total_tasks = sum(len(tasks) for tasks in tasks_by_priority.values())
            urgent_count = len(tasks_by_priority.get(Priority.URGENT.value, []))
            high_count = len(tasks_by_priority.get(Priority.HIGH.value, []))
            normal_count = len(tasks_by_priority.get(Priority.NORMAL.value, []))
            low_count = len(tasks_by_priority.get(Priority.LOW.value, []))
            
            # Get overdue tasks
            overdue_tasks = await self._get_overdue_tasks(task_service)
            
            # Get tasks due today
            today_tasks = await self._get_tasks_due_today(task_service)
            
            summary_data = {
                "date": datetime.utcnow().strftime('%Y-%m-%d'),
                "total_tasks": total_tasks,
                "tasks_by_priority": tasks_by_priority,
                "priority_counts": {
                    "urgent": urgent_count,
                    "high": high_count,
                    "normal": normal_count,
                    "low": low_count
                },
                "overdue_tasks": overdue_tasks,
                "today_tasks": today_tasks,
                "overdue_count": len(overdue_tasks),
                "today_count": len(today_tasks)
            }
            
            logger.info(
                "Daily summary generated",
                total_tasks=total_tasks,
                urgent_count=urgent_count,
                overdue_count=len(overdue_tasks),
                today_count=len(today_tasks)
            )
            
            return summary_data
            
        except Exception as e:
            logger.error("Failed to generate daily summary", error=str(e), exc_info=True)
            raise SummaryServiceError(f"Failed to generate daily summary: {str(e)}")
    
    def format_summary_for_telegram(self, summary_data: Dict[str, Any]) -> str:
        """
        Format summary data for Telegram with Markdown formatting
        
        Args:
            summary_data: Summary data from generate_daily_summary
            
        Returns:
            Formatted Markdown text for Telegram
        """
        try:
            date = summary_data.get("date", "Unknown")
            total_tasks = summary_data.get("total_tasks", 0)
            priority_counts = summary_data.get("priority_counts", {})
            overdue_count = summary_data.get("overdue_count", 0)
            today_count = summary_data.get("today_count", 0)
            tasks_by_priority = summary_data.get("tasks_by_priority", {})
            
            # Build message parts
            message_parts = [
                f"🌅 **Daily Task Summary - {date}**",
                ""
            ]
            
            # Overview section
            if total_tasks == 0:
                message_parts.extend([
                    "✅ **No open tasks! Great job!**",
                    "",
                    "🎉 You're all caught up. Time to relax or tackle new challenges!"
                ])
                return "\n".join(message_parts)
            
            # Task counts overview
            message_parts.extend([
                f"📊 **Overview:**",
                f"• Total open tasks: **{total_tasks}**",
                f"• Overdue tasks: **{overdue_count}** {'🚨' if overdue_count > 0 else '✅'}",
                f"• Due today: **{today_count}** {'⏰' if today_count > 0 else '✅'}",
                ""
            ])
            
            # Priority breakdown
            message_parts.append("📋 **Tasks by Priority:**")
            
            for priority_name, emoji, count_key in [
                ("Urgent", "🔴", "urgent"),
                ("High", "🟡", "high"),
                ("Normal", "🟢", "normal"),
                ("Low", "⚪", "low")
            ]:
                count = priority_counts.get(count_key, 0)
                tasks = tasks_by_priority.get(priority_name.lower(), [])
                
                if count > 0:
                    message_parts.append(f"• {emoji} **{priority_name}:** {count}")
                    
                    # Show top 2 tasks for urgent and high priority
                    if priority_name.lower() in ["urgent", "high"] and tasks:
                        for task in tasks[:2]:
                            due_text = ""
                            if task.due:
                                due_text = f" (Due: {task.due.strftime('%m-%d %H:%M')})"
                            message_parts.append(f"  - [{task.id}] {task.title[:50]}{'...' if len(task.title) > 50 else ''}{due_text}")
                        
                        if len(tasks) > 2:
                            message_parts.append(f"  ... and {len(tasks) - 2} more")
            
            message_parts.append("")
            
            # Overdue tasks alert
            if overdue_count > 0:
                message_parts.extend([
                    "🚨 **Overdue Tasks Alert:**",
                    f"You have **{overdue_count}** overdue tasks that need immediate attention!",
                    ""
                ])
            
            # Today's tasks
            if today_count > 0:
                message_parts.extend([
                    "⏰ **Due Today:**",
                    f"**{today_count}** tasks are due today. Stay focused!",
                    ""
                ])
            
            # Action items
            message_parts.extend([
                "💡 **Quick Actions:**",
                "• Use /list to see all tasks",
                "• Use /done `<id>` to mark tasks complete",
                "• Use /add `<task>` to create new tasks",
                ""
            ])
            
            # Motivational message based on task load
            if urgent_count > 5:
                message_parts.append("💪 **You've got this!** Focus on urgent tasks first.")
            elif total_tasks > 20:
                message_parts.append("🎯 **Stay organized!** Break down large tasks into smaller ones.")
            elif overdue_count == 0:
                message_parts.append("⭐ **Great job!** No overdue tasks. Keep up the momentum!")
            else:
                message_parts.append("🌟 **Have a productive day!**")
            
            return "\n".join(message_parts)
            
        except Exception as e:
            logger.error("Failed to format summary for Telegram", error=str(e))
            return f"📋 Daily Summary ({summary_data.get('date', 'Unknown')})\n\nError formatting summary. Please check logs."
    
    async def send_daily_summary(
        self,
        task_service: TaskService,
        telegram_service: TelegramService,
        chat_id: int
    ) -> Dict[str, Any]:
        """
        Generate and send daily summary to Telegram
        
        Args:
            task_service: Task service instance
            telegram_service: Telegram service instance
            chat_id: Telegram chat ID to send summary to
            
        Returns:
            Result of the summary operation
        """
        try:
            # Generate summary
            summary_data = await self.generate_daily_summary(task_service)
            
            # Format for Telegram
            formatted_message = self.format_summary_for_telegram(summary_data)
            
            # Send to Telegram
            success = await telegram_service.send_daily_summary(
                chat_id, 
                summary_data.get("tasks_by_priority", {})
            )
            
            if success:
                logger.info(
                    "Daily summary sent successfully",
                    chat_id=chat_id,
                    total_tasks=summary_data.get("total_tasks", 0)
                )
                return {
                    "status": "sent",
                    "chat_id": chat_id,
                    "summary_data": summary_data
                }
            else:
                logger.error("Failed to send daily summary", chat_id=chat_id)
                return {
                    "status": "failed",
                    "error": "Failed to send Telegram message",
                    "chat_id": chat_id
                }
                
        except Exception as e:
            logger.error(
                "Failed to send daily summary",
                chat_id=chat_id,
                error=str(e),
                exc_info=True
            )
            return {
                "status": "error",
                "error": str(e),
                "chat_id": chat_id
            }
    
    async def run_daily_scheduler(
        self,
        task_service: TaskService,
        telegram_service: TelegramService
    ):
        """
        Background task to send daily summaries at scheduled time
        
        Args:
            task_service: Task service instance
            telegram_service: Telegram service instance
        """
        logger.info("Starting daily summary scheduler")
        
        while True:
            try:
                # Calculate next summary time (7:00 AM Mexico City time)
                now = datetime.utcnow()
                
                # TODO: Implement proper timezone handling
                # For now, assume UTC and adjust manually
                # Mexico City is UTC-6 (or UTC-5 during DST)
                # So 7:00 AM Mexico City = 13:00 UTC (or 12:00 UTC during DST)
                target_hour = 13  # 7:00 AM Mexico City in UTC (adjust for DST as needed)
                
                # Calculate next summary time
                next_summary = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
                
                # If we've passed today's summary time, schedule for tomorrow
                if now >= next_summary:
                    next_summary += timedelta(days=1)
                
                # Calculate sleep time
                sleep_seconds = (next_summary - now).total_seconds()
                
                logger.info(
                    "Next daily summary scheduled",
                    next_summary=next_summary.isoformat(),
                    sleep_seconds=sleep_seconds
                )
                
                # Sleep until summary time
                await asyncio.sleep(sleep_seconds)
                
                # TODO: Get chat IDs from user configuration
                # For now, this would need to be configured per user
                chat_ids = []  # This should come from user settings/database
                
                if chat_ids:
                    for chat_id in chat_ids:
                        try:
                            result = await self.send_daily_summary(
                                task_service,
                                telegram_service,
                                chat_id
                            )
                            
                            logger.info(
                                "Scheduled daily summary sent",
                                chat_id=chat_id,
                                result=result
                            )
                            
                        except Exception as e:
                            logger.error(
                                "Failed to send scheduled summary",
                                chat_id=chat_id,
                                error=str(e)
                            )
                else:
                    logger.info("No chat IDs configured for daily summary")
                
            except Exception as e:
                logger.error(
                    "Error in daily summary scheduler",
                    error=str(e),
                    exc_info=True
                )
                # Sleep for 1 hour before retrying
                await asyncio.sleep(3600)
    
    async def _get_overdue_tasks(self, task_service: TaskService) -> List[Task]:
        """Get tasks that are overdue"""
        try:
            async with async_session() as db:
                task_service_instance = TaskService(db)
                
                # Get all open tasks
                result = await task_service_instance.list_tasks(
                    status=[TaskStatus.OPEN],
                    size=1000  # Get all tasks
                )
                
                # Filter overdue tasks
                now = datetime.utcnow()
                overdue_tasks = []
                
                for task_dict in result.get("items", []):
                    if task_dict.get("due"):
                        due_date = datetime.fromisoformat(task_dict["due"].replace("Z", "+00:00"))
                        if due_date.replace(tzinfo=None) < now:
                            # Convert dict back to Task-like object for compatibility
                            task = type('Task', (), task_dict)()
                            task.due = due_date.replace(tzinfo=None)
                            overdue_tasks.append(task)
                
                return overdue_tasks
                
        except Exception as e:
            logger.error("Failed to get overdue tasks", error=str(e))
            return []
    
    async def _get_tasks_due_today(self, task_service: TaskService) -> List[Task]:
        """Get tasks that are due today"""
        try:
            async with async_session() as db:
                task_service_instance = TaskService(db)
                
                # Get all open tasks
                result = await task_service_instance.list_tasks(
                    status=[TaskStatus.OPEN],
                    size=1000  # Get all tasks
                )
                
                # Filter tasks due today
                today = datetime.utcnow().date()
                today_tasks = []
                
                for task_dict in result.get("items", []):
                    if task_dict.get("due"):
                        due_date = datetime.fromisoformat(task_dict["due"].replace("Z", "+00:00"))
                        if due_date.date() == today:
                            # Convert dict back to Task-like object for compatibility
                            task = type('Task', (), task_dict)()
                            task.due = due_date.replace(tzinfo=None)
                            today_tasks.append(task)
                
                return today_tasks
                
        except Exception as e:
            logger.error("Failed to get tasks due today", error=str(e))
            return []