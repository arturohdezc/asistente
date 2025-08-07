import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import re
import httpx
import structlog
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.constants import ParseMode

from models.task import Task, TaskStatus, Priority
from services.task_service import TaskService
from services.calendar_service import CalendarService
from services.gemini_service import GeminiService
from config.settings import settings

logger = structlog.get_logger()

class TelegramServiceError(Exception):
    """Telegram service specific errors"""
    pass

class TelegramService:
    """Service for handling Telegram bot interactions"""
    
    def __init__(self, task_service: TaskService, calendar_service: Optional['CalendarService'] = None, gemini_service: Optional[GeminiService] = None):
        self.task_service = task_service
        self.calendar_service = calendar_service
        self.gemini_service = gemini_service or GeminiService()
        self.bot_token = settings.telegram_token
        self.webhook_secret = settings.telegram_webhook_secret
        self.bot = Bot(token=self.bot_token)
    
    async def validate_webhook_token(self, token: Optional[str]) -> bool:
        """Validate Telegram webhook secret token"""
        if not token:
            logger.warning("Missing Telegram webhook secret token")
            return False
        
        if token != self.webhook_secret:
            logger.warning("Invalid Telegram webhook secret token")
            return False
        
        return True
    
    async def process_update(self, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Telegram webhook update"""
        try:
            logger.info("Processing Telegram update", update_data=update_data)
            
            # Parse update
            if "message" not in update_data:
                return {"status": "ignored", "reason": "No message in update"}
            
            message = update_data["message"]
            text = message.get("text", "")
            chat_id = message.get("chat", {}).get("id")
            user_id = message.get("from", {}).get("id")
            
            if not chat_id or not text:
                return {"status": "ignored", "reason": "Missing chat_id or text"}
            
            # Handle commands
            if text.startswith("/"):
                response = await self._handle_command(text, chat_id, user_id)
            else:
                response = await self._handle_text_message(text, chat_id, user_id)
            
            return {"status": "processed", "response": response}
            
        except Exception as e:
            logger.error(
                "Failed to process Telegram update",
                update_data=update_data,
                error=str(e),
                exc_info=True
            )
            raise TelegramServiceError(f"Failed to process update: {str(e)}")
    
    async def _handle_command(self, text: str, chat_id: int, user_id: int) -> str:
        """Handle Telegram commands"""
        parts = text.split(" ", 1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        try:
            if command == "/start":
                response = await self._handle_start_command()
            elif command == "/help":
                response = await self._handle_help_command()
            elif command == "/add":
                response = await self._handle_add_command(args, user_id)
            elif command == "/done":
                response = await self._handle_done_command(args, user_id)
            elif command == "/list":
                response = await self._handle_list_command(user_id)
            elif command == "/calendar":
                response = await self._handle_calendar_command(args, user_id)
            else:
                response = f"Unknown command: {command}. Use /help for available commands."
            
            # Send response to user
            await self._send_message(chat_id, response)
            return response
            
        except Exception as e:
            error_msg = f"Error processing command {command}: {str(e)}"
            logger.error("Command processing failed", command=command, error=str(e))
            await self._send_message(chat_id, f"❌ {error_msg}")
            return error_msg
    
    async def _handle_text_message(self, text: str, chat_id: int, user_id: int) -> str:
        """Handle non-command text messages"""
        response = "I received your message. Use /help to see available commands."
        await self._send_message(chat_id, response)
        return response
    
    async def _handle_start_command(self) -> str:
        """Handle /start command"""
        return (
            "🤖 Welcome to Personal Assistant Bot!\n\n"
            "I can help you manage tasks and calendar events.\n\n"
            "Use /help to see all available commands."
        )
    
    async def _handle_help_command(self) -> str:
        """Handle /help command"""
        return (
            "📋 **Available Commands:**\n\n"
            "/add `<text>` - Create a new task\n"
            "/done `<id>` - Mark task as completed\n"
            "/list - List all tasks grouped by priority\n"
            "/calendar `<event description with date/time>` - Create calendar event\n"
            "/help - Show this help message\n\n"
            "**Priority Indicators:**\n"
            "🔴 Urgent - Due within 24 hours\n"
            "🟡 High - Important tasks\n"
            "🟢 Normal - Regular tasks\n"
            "⚪ Low - Optional tasks"
        )
    
    async def _handle_add_command(self, text: str, user_id: int) -> str:
        """Handle /add command to create new task"""
        if not text.strip():
            return "❌ Please provide task description. Usage: /add `<task description>`"
        
        try:
            # Use Gemini to analyze the text and extract structured task information
            analysis_result = await self.gemini_service.analyze_text(
                text=text.strip(),
                source=f"telegram_user_{user_id}"
            )
            
            # Create tasks from Gemini analysis
            created_tasks = []
            for task_data in analysis_result.tasks:
                task = await self.task_service.create_task(
                    title=task_data.title,
                    due=task_data.due,
                    source=f"telegram_user_{user_id}",
                    priority=task_data.priority
                )
                created_tasks.append(task)
            
            # If no tasks were extracted, create a simple task
            if not created_tasks:
                task = await self.task_service.create_task(
                    title=text.strip(),
                    source=f"telegram_user_{user_id}",
                    priority=Priority.NORMAL
                )
                created_tasks.append(task)
            
            # Format response
            if len(created_tasks) == 1:
                task = created_tasks[0]
                priority_emoji = self._get_priority_emoji(Priority(task.priority))
                
                response = (
                    f"✅ Task created successfully!\n\n"
                    f"**ID:** {task.id}\n"
                    f"**Title:** {task.title}\n"
                    f"**Priority:** {priority_emoji} {task.priority.title()}\n"
                    f"**Status:** {task.status.title()}"
                )
                
                if task.due:
                    response += f"\n**Due:** {task.due.strftime('%Y-%m-%d %H:%M')}"
                
                return response
            else:
                # Multiple tasks created
                response = f"✅ Created {len(created_tasks)} tasks from your message:\n\n"
                for task in created_tasks:
                    priority_emoji = self._get_priority_emoji(Priority(task.priority))
                    response += f"**{task.id}.** {task.title} {priority_emoji}\n"
                
                return response
            
        except Exception as e:
            logger.error("Failed to create task", text=text, user_id=user_id, error=str(e))
            return f"❌ Failed to create task: {str(e)}"
    
    async def _handle_done_command(self, args: str, user_id: int) -> str:
        """Handle /done command to mark task as completed"""
        if not args.strip():
            return "❌ Please provide task ID. Usage: /done `<task_id>`"
        
        try:
            task_id = int(args.strip())
        except ValueError:
            return "❌ Invalid task ID. Please provide a numeric ID."
        
        try:
            # Get task
            task = await self.task_service.get_task(task_id)
            if not task:
                return f"❌ Task {task_id} not found."
            
            # Check if already completed
            if task.status == TaskStatus.DONE.value:
                return f"✅ Task {task_id} was already completed: {task.title}"
            
            # Update task status
            updated_task = await self.task_service.update_task(
                task_id, 
                {"status": TaskStatus.DONE.value}
            )
            
            if updated_task:
                return f"✅ Task completed: {updated_task.title}"
            else:
                return f"❌ Failed to update task {task_id}"
                
        except Exception as e:
            logger.error("Failed to complete task", task_id=args, user_id=user_id, error=str(e))
            return f"❌ Failed to complete task: {str(e)}"
    
    async def _handle_list_command(self, user_id: int) -> str:
        """Handle /list command to show tasks grouped by priority"""
        try:
            # Get tasks grouped by priority
            tasks_by_priority = await self.task_service.get_tasks_for_summary()
            
            # Build response
            response_parts = ["📋 **Your Tasks:**\n"]
            
            total_tasks = 0
            for priority_name, priority_emoji in [
                (Priority.URGENT.value, "🔴"),
                (Priority.HIGH.value, "🟡"),
                (Priority.NORMAL.value, "🟢"),
                (Priority.LOW.value, "⚪")
            ]:
                tasks = tasks_by_priority.get(priority_name, [])
                if tasks:
                    response_parts.append(f"\n**{priority_emoji} {priority_name.title()} ({len(tasks)}):**")
                    for task in tasks[:5]:  # Limit to 5 tasks per priority
                        due_text = ""
                        if task.due:
                            due_text = f" (Due: {task.due.strftime('%Y-%m-%d %H:%M')})"
                        response_parts.append(f"• [{task.id}] {task.title}{due_text}")
                    
                    if len(tasks) > 5:
                        response_parts.append(f"... and {len(tasks) - 5} more")
                    
                    total_tasks += len(tasks)
            
            if total_tasks == 0:
                return "📋 No open tasks found. Use /add to create a new task!"
            
            response_parts.append(f"\n**Total open tasks:** {total_tasks}")
            response_parts.append("\nUse /done `<id>` to mark tasks as completed.")
            
            return "\n".join(response_parts)
            
        except Exception as e:
            logger.error("Failed to list tasks", user_id=user_id, error=str(e))
            return f"❌ Failed to list tasks: {str(e)}"
    
    async def _handle_calendar_command(self, args: str, user_id: int) -> str:
        """Handle /calendar command to create calendar event"""
        if not self.calendar_service:
            return "❌ Calendar service not available."
        
        if not args.strip():
            return (
                "❌ Please provide event details.\n"
                "Usage: /calendar `<event description with date/time>`\n"
                "Examples:\n"
                "• /calendar Meeting tomorrow at 2pm\n"
                "• /calendar Team standup Monday 9:30am\n"
                "• /calendar 2024-01-15 14:30 Project review"
            )
        
        try:
            # Use Gemini to analyze the text and extract event information
            analysis_result = await self.gemini_service.analyze_calendar_event(
                text=args.strip(),
                source=f"telegram_user_{user_id}"
            )
            
            if not analysis_result.event_datetime:
                return (
                    "❌ Could not extract date/time from your message.\n"
                    "Please include when the event should happen.\n"
                    "Examples:\n"
                    "• /calendar Meeting tomorrow at 2pm\n"
                    "• /calendar Team standup Monday 9:30am\n"
                    "• /calendar 2024-01-15 14:30 Project review"
                )
            
            # Create calendar event
            event = await self.calendar_service.create_event(
                title=analysis_result.title,
                start_time=analysis_result.event_datetime,
                duration_minutes=analysis_result.duration_minutes or 60,
                description=analysis_result.description
            )
            
            response = (
                f"📅 Calendar event created successfully!\n\n"
                f"**Title:** {analysis_result.title}\n"
                f"**Date:** {analysis_result.event_datetime.strftime('%Y-%m-%d %H:%M')}\n"
                f"**Duration:** {analysis_result.duration_minutes or 60} minutes"
            )
            
            if analysis_result.description:
                response += f"\n**Description:** {analysis_result.description}"
            
            if event.get('id'):
                response += f"\n**Event ID:** {event.get('id')}"
            
            return response
            
        except Exception as e:
            logger.error("Failed to create calendar event", args=args, user_id=user_id, error=str(e))
            return f"❌ Failed to create calendar event: {str(e)}"
    
    async def _send_message(self, chat_id: int, text: str) -> bool:
        """Send message to Telegram chat"""
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN
            )
            return True
        except Exception as e:
            logger.error(
                "Failed to send Telegram message",
                chat_id=chat_id,
                error=str(e)
            )
            return False
    
    def _get_priority_emoji(self, priority: Priority) -> str:
        """Get emoji for task priority"""
        emoji_map = {
            Priority.URGENT: "🔴",
            Priority.HIGH: "🟡", 
            Priority.NORMAL: "🟢",
            Priority.LOW: "⚪"
        }
        return emoji_map.get(priority, "🟢")
    
    async def send_daily_summary(self, chat_id: int, tasks_by_priority: Dict[str, List[Task]]) -> bool:
        """Send daily task summary to Telegram chat"""
        try:
            # Build summary message
            message_parts = ["🌅 **Daily Task Summary**\n"]
            
            total_tasks = 0
            for priority_name, priority_emoji in [
                (Priority.URGENT.value, "🔴"),
                (Priority.HIGH.value, "🟡"),
                (Priority.NORMAL.value, "🟢"),
                (Priority.LOW.value, "⚪")
            ]:
                tasks = tasks_by_priority.get(priority_name, [])
                if tasks:
                    message_parts.append(f"\n**{priority_emoji} {priority_name.title()} ({len(tasks)}):**")
                    for task in tasks[:3]:  # Limit to 3 tasks per priority for summary
                        due_text = ""
                        if task.due:
                            due_text = f" (Due: {task.due.strftime('%m-%d %H:%M')})"
                        message_parts.append(f"• {task.title}{due_text}")
                    
                    if len(tasks) > 3:
                        message_parts.append(f"... and {len(tasks) - 3} more")
                    
                    total_tasks += len(tasks)
            
            if total_tasks == 0:
                message_parts = ["🌅 **Daily Task Summary**\n\n✅ No open tasks! Great job!"]
            else:
                message_parts.append(f"\n**Total open tasks:** {total_tasks}")
                message_parts.append("\nUse /list to see all tasks or /add to create new ones.")
            
            message = "\n".join(message_parts)
            return await self._send_message(chat_id, message)
            
        except Exception as e:
            logger.error(
                "Failed to send daily summary",
                chat_id=chat_id,
                error=str(e)
            )
            return False
    
    async def send_task_notification(self, chat_id: int, task: Task, notification_type: str = "created") -> bool:
        """Send task notification to Telegram chat"""
        try:
            priority_emoji = self._get_priority_emoji(Priority(task.priority))
            
            if notification_type == "created":
                message = (
                    f"📝 **New Task Created**\n\n"
                    f"**Title:** {task.title}\n"
                    f"**Priority:** {priority_emoji} {task.priority.title()}\n"
                    f"**Source:** {task.source}"
                )
                if task.due:
                    message += f"\n**Due:** {task.due.strftime('%Y-%m-%d %H:%M')}"
            
            elif notification_type == "urgent":
                message = (
                    f"🚨 **Urgent Task Alert**\n\n"
                    f"**Title:** {task.title}\n"
                    f"**Due:** {task.due.strftime('%Y-%m-%d %H:%M') if task.due else 'No due date'}\n"
                    f"**Source:** {task.source}\n\n"
                    f"This task is due within 24 hours!"
                )
            
            else:
                message = f"📋 Task update: {task.title}"
            
            return await self._send_message(chat_id, message)
            
        except Exception as e:
            logger.error(
                "Failed to send task notification",
                chat_id=chat_id,
                task_id=task.id,
                error=str(e)
            )
            return False
    
    async def send_meeting_context(self, context_text: str, chat_id: int) -> bool:
        """Send meeting context to Telegram chat"""
        try:
            return await self._send_message(chat_id, context_text)
            
        except Exception as e:
            logger.error(
                "Failed to send meeting context",
                chat_id=chat_id,
                error=str(e)
            )
            return False