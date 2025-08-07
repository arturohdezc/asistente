import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import structlog
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from models.task import Task
from config.settings import settings

logger = structlog.get_logger()

class CalendarServiceError(Exception):
    """Calendar service specific errors"""
    pass

class CalendarService:
    """Service for Google Calendar integration"""
    
    def __init__(self):
        self.credentials = None
        self.service = None
        self.calendar_id = 'primary'  # Use primary calendar
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Calendar service"""
        try:
            # Parse credentials from settings
            credentials_data = settings.get_calendar_credentials()
            
            # Create credentials from service account info
            self.credentials = Credentials.from_service_account_info(
                credentials_data,
                scopes=['https://www.googleapis.com/auth/calendar']
            )
            
            # Build the service
            self.service = build('calendar', 'v3', credentials=self.credentials)
            
            logger.info("Calendar service initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize calendar service", error=str(e))
            raise CalendarServiceError(f"Failed to initialize calendar service: {str(e)}")
    
    async def create_event(
        self, 
        title: str, 
        start_time: datetime, 
        duration_minutes: int = 60,
        description: Optional[str] = None,
        attendees: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a calendar event
        
        Args:
            title: Event title
            start_time: Event start time
            duration_minutes: Event duration in minutes
            description: Optional event description
            attendees: Optional list of attendee emails
            
        Returns:
            Created event data
        """
        try:
            # Calculate end time
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            # Build event data
            event_data = {
                'summary': title,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': settings.timezone,
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': settings.timezone,
                },
            }
            
            if description:
                event_data['description'] = description
            
            if attendees:
                event_data['attendees'] = [{'email': email} for email in attendees]
            
            # Create event
            event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event_data
            ).execute()
            
            logger.info(
                "Calendar event created",
                event_id=event.get('id'),
                title=title,
                start_time=start_time.isoformat()
            )
            
            return event
            
        except HttpError as e:
            logger.error(
                "Google Calendar API error",
                error=str(e),
                title=title,
                start_time=start_time.isoformat()
            )
            raise CalendarServiceError(f"Calendar API error: {str(e)}")
        except Exception as e:
            logger.error(
                "Failed to create calendar event",
                error=str(e),
                title=title,
                start_time=start_time.isoformat()
            )
            raise CalendarServiceError(f"Failed to create calendar event: {str(e)}")
    
    async def get_upcoming_events(self, hours_ahead: int = 24) -> List[Dict[str, Any]]:
        """
        Get upcoming events within specified hours
        
        Args:
            hours_ahead: Number of hours to look ahead
            
        Returns:
            List of upcoming events
        """
        try:
            # Calculate time range
            now = datetime.utcnow()
            time_max = now + timedelta(hours=hours_ahead)
            
            # Get events
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=now.isoformat() + 'Z',
                timeMax=time_max.isoformat() + 'Z',
                maxResults=50,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            logger.info(
                "Retrieved upcoming events",
                count=len(events),
                hours_ahead=hours_ahead
            )
            
            return events
            
        except HttpError as e:
            logger.error("Google Calendar API error", error=str(e))
            raise CalendarServiceError(f"Calendar API error: {str(e)}")
        except Exception as e:
            logger.error("Failed to get upcoming events", error=str(e))
            raise CalendarServiceError(f"Failed to get upcoming events: {str(e)}")
    
    async def find_related_tasks_for_events(
        self, 
        events: List[Dict[str, Any]], 
        task_service: 'TaskService'
    ) -> Dict[str, List[Task]]:
        """
        Find tasks related to calendar events
        
        Args:
            events: List of calendar events
            task_service: Task service instance
            
        Returns:
            Dictionary mapping event IDs to related tasks
        """
        try:
            event_tasks = {}
            
            for event in events:
                event_id = event.get('id')
                summary = event.get('summary', '')
                description = event.get('description', '')
                attendees = [
                    attendee.get('email', '') 
                    for attendee in event.get('attendees', [])
                ]
                
                # Extract keywords from event
                keywords = self._extract_keywords(summary, description)
                
                # Find related tasks
                related_tasks = await task_service.find_related_tasks(
                    keywords=keywords,
                    attendees=attendees
                )
                
                if related_tasks:
                    event_tasks[event_id] = related_tasks
                    
                    logger.info(
                        "Found related tasks for event",
                        event_id=event_id,
                        event_summary=summary,
                        task_count=len(related_tasks)
                    )
            
            return event_tasks
            
        except Exception as e:
            logger.error("Failed to find related tasks for events", error=str(e))
            raise CalendarServiceError(f"Failed to find related tasks: {str(e)}")
    
    def _extract_keywords(self, summary: str, description: str) -> List[str]:
        """Extract keywords from event summary and description"""
        import re
        
        # Combine summary and description
        text = f"{summary} {description}".lower()
        
        # Extract meaningful words (3+ characters, not common words)
        common_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 
            'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 
            'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 
            'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use', 'with', 'have',
            'this', 'will', 'your', 'from', 'they', 'know', 'want', 'been', 'good',
            'much', 'some', 'time', 'very', 'when', 'come', 'here', 'just', 'like',
            'long', 'make', 'many', 'over', 'such', 'take', 'than', 'them', 'well',
            'were', 'what', 'where', 'would', 'there', 'could', 'other', 'after',
            'first', 'never', 'these', 'think', 'which', 'their', 'said', 'each',
            'about', 'again', 'before', 'great', 'right', 'should', 'those', 'under',
            'might', 'still', 'being', 'every', 'little', 'state', 'through', 'during'
        }
        
        # Find words that are 3+ characters and not common
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
        keywords = [word for word in words if word not in common_words]
        
        # Remove duplicates and limit to top 10
        return list(set(keywords))[:10]
    
    async def create_event_from_task(self, task: Task, duration_minutes: int = 60) -> Optional[Dict[str, Any]]:
        """
        Create calendar event from task
        
        Args:
            task: Task to create event for
            duration_minutes: Event duration in minutes
            
        Returns:
            Created event data or None if task has no due date
        """
        try:
            if not task.due:
                logger.info("Task has no due date, skipping calendar event creation", task_id=task.id)
                return None
            
            # Create event
            event = await self.create_event(
                title=f"Task: {task.title}",
                start_time=task.due,
                duration_minutes=duration_minutes,
                description=f"Task from {task.source}\nPriority: {task.priority}\nCreated: {task.created_at}"
            )
            
            logger.info(
                "Created calendar event from task",
                task_id=task.id,
                event_id=event.get('id')
            )
            
            return event
            
        except Exception as e:
            logger.error(
                "Failed to create calendar event from task",
                task_id=task.id,
                error=str(e)
            )
            raise CalendarServiceError(f"Failed to create event from task: {str(e)}")
    
    async def get_daily_schedule(self, date: datetime) -> List[Dict[str, Any]]:
        """
        Get daily schedule for a specific date
        
        Args:
            date: Date to get schedule for
            
        Returns:
            List of events for the day
        """
        try:
            # Calculate day boundaries
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            # Get events for the day
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_of_day.isoformat() + 'Z',
                timeMax=end_of_day.isoformat() + 'Z',
                maxResults=100,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            logger.info(
                "Retrieved daily schedule",
                date=date.strftime('%Y-%m-%d'),
                event_count=len(events)
            )
            
            return events
            
        except HttpError as e:
            logger.error("Google Calendar API error", error=str(e))
            raise CalendarServiceError(f"Calendar API error: {str(e)}")
        except Exception as e:
            logger.error("Failed to get daily schedule", error=str(e))
            raise CalendarServiceError(f"Failed to get daily schedule: {str(e)}")
    
    async def process_webhook_notification(
        self,
        notification_data: Dict[str, Any],
        task_service: 'TaskService',
        telegram_service: 'TelegramService'
    ) -> Dict[str, Any]:
        """
        Process Calendar webhook notification and send meeting context
        
        Args:
            notification_data: Webhook notification data
            task_service: Task service instance
            telegram_service: Telegram service instance
            
        Returns:
            Processing result
        """
        try:
            logger.info("Processing Calendar webhook notification", data=notification_data)
            
            # Extract notification details
            resource_id = notification_data.get('resourceId')
            resource_state = notification_data.get('resourceState')
            
            if resource_state != 'exists':
                return {"status": "ignored", "reason": f"Resource state: {resource_state}"}
            
            # Get upcoming events (next 2 hours)
            upcoming_events = await self.get_upcoming_events(hours_ahead=2)
            
            contexts_sent = []
            
            for event in upcoming_events:
                try:
                    # Extract event details
                    event_id = event.get('id')
                    summary = event.get('summary', 'No title')
                    start_time = event.get('start', {}).get('dateTime')
                    attendees = event.get('attendees', [])
                    
                    if not start_time:
                        continue
                    
                    # Parse start time
                    start_datetime = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    
                    # Check if event is starting soon (within 30 minutes)
                    now = datetime.utcnow().replace(tzinfo=start_datetime.tzinfo)
                    time_until_start = start_datetime - now
                    
                    if timedelta(minutes=0) <= time_until_start <= timedelta(minutes=30):
                        # Generate meeting context
                        context = await self._generate_meeting_context(
                            event, task_service
                        )
                        
                        if context:
                            # TODO: Get chat_id from user configuration
                            # For now, this would need to be configured per user
                            chat_id = None  # This should come from user settings
                            
                            if chat_id:
                                success = await telegram_service.send_meeting_context(
                                    context, chat_id
                                )
                                
                                if success:
                                    contexts_sent.append({
                                        "event_id": event_id,
                                        "summary": summary,
                                        "start_time": start_time,
                                        "context_sent": True
                                    })
                                    
                                    logger.info(
                                        "Meeting context sent",
                                        event_id=event_id,
                                        summary=summary
                                    )
                                else:
                                    logger.error(
                                        "Failed to send meeting context",
                                        event_id=event_id,
                                        summary=summary
                                    )
                            else:
                                logger.info(
                                    "No chat ID configured for meeting context",
                                    event_id=event_id
                                )
                
                except Exception as e:
                    logger.error(
                        "Failed to process individual event",
                        event_id=event.get('id'),
                        error=str(e)
                    )
                    continue
            
            return {
                "status": "processed",
                "contexts_sent": contexts_sent,
                "events_processed": len(upcoming_events)
            }
            
        except Exception as e:
            logger.error(
                "Failed to process Calendar webhook",
                error=str(e),
                exc_info=True
            )
            return {"status": "error", "error": str(e)}
    
    async def _generate_meeting_context(
        self,
        event: Dict[str, Any],
        task_service: 'TaskService'
    ) -> Optional[str]:
        """
        Generate meeting context by finding related tasks
        
        Args:
            event: Calendar event data
            task_service: Task service instance
            
        Returns:
            Formatted meeting context or None if no related tasks
        """
        try:
            # Extract event details
            summary = event.get('summary', '')
            description = event.get('description', '')
            attendees = [
                attendee.get('email', '') 
                for attendee in event.get('attendees', [])
            ]
            start_time = event.get('start', {}).get('dateTime', '')
            
            # Extract keywords from event
            keywords = self._extract_keywords(summary, description)
            
            # Find related tasks
            related_tasks = await task_service.find_related_tasks(
                keywords=keywords,
                attendees=attendees
            )
            
            if not related_tasks:
                return None
            
            # Format meeting context
            context_parts = [
                f"📅 **Meeting Context: {summary}**",
                f"🕐 **Time:** {self._format_datetime(start_time)}",
                ""
            ]
            
            if attendees:
                context_parts.extend([
                    "👥 **Attendees:**",
                    ", ".join(attendees),
                    ""
                ])
            
            context_parts.extend([
                f"📋 **Related Tasks ({len(related_tasks)}):**",
                ""
            ])
            
            # Group tasks by priority
            urgent_tasks = [t for t in related_tasks if t.priority == 'urgent']
            high_tasks = [t for t in related_tasks if t.priority == 'high']
            normal_tasks = [t for t in related_tasks if t.priority == 'normal']
            low_tasks = [t for t in related_tasks if t.priority == 'low']
            
            # Add tasks by priority
            for priority_name, tasks, emoji in [
                ("Urgent", urgent_tasks, "🔴"),
                ("High", high_tasks, "🟡"),
                ("Normal", normal_tasks, "🟢"),
                ("Low", low_tasks, "⚪")
            ]:
                if tasks:
                    context_parts.append(f"**{emoji} {priority_name}:**")
                    for task in tasks[:3]:  # Limit to 3 tasks per priority
                        due_text = ""
                        if task.due:
                            due_text = f" (Due: {task.due.strftime('%m-%d %H:%M')})"
                        context_parts.append(f"• [{task.id}] {task.title}{due_text}")
                    
                    if len(tasks) > 3:
                        context_parts.append(f"... and {len(tasks) - 3} more")
                    context_parts.append("")
            
            context_parts.extend([
                "💡 **Tip:** Use /done `<id>` to mark tasks as completed during the meeting.",
                ""
            ])
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(
                "Failed to generate meeting context",
                event_id=event.get('id'),
                error=str(e)
            )
            return None
    
    def _format_datetime(self, datetime_str: str) -> str:
        """Format datetime string for display"""
        try:
            if not datetime_str:
                return "No time specified"
            
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M')
        except Exception:
            return datetime_str