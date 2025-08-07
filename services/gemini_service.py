import asyncio
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import httpx
import structlog
from pydantic import BaseModel, Field

from models.task import Priority
from config.settings import settings
from core.exceptions import GeminiServiceError, wrap_external_error
from core.circuit_breaker import get_gemini_circuit_breaker
from core.rate_limiter import gemini_rate_limiter

logger = structlog.get_logger()

class TaskData(BaseModel):
    """Task data extracted from text"""
    title: str = Field(..., min_length=1, max_length=500)
    due: Optional[datetime] = None
    priority: Priority = Priority.NORMAL

class AnalysisResult(BaseModel):
    """Result of text analysis"""
    tasks: List[TaskData] = Field(default_factory=list)
    context: str = Field(default="")
    priority: Priority = Priority.NORMAL

class CalendarEventData(BaseModel):
    """Calendar event data extracted from text"""
    title: str = Field(..., min_length=1, max_length=500)
    event_datetime: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(default=60, ge=1, le=1440)  # 1 minute to 24 hours
    description: Optional[str] = None

class CalendarAnalysisResult(BaseModel):
    """Result of calendar event analysis"""
    title: str = Field(..., min_length=1, max_length=500)
    event_datetime: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(default=60, ge=1, le=1440)
    description: Optional[str] = None

# GeminiServiceError is now imported from core.exceptions

class GeminiService:
    """Service for analyzing text using Gemini 1.5 Pro API"""
    
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.model = "gemini-1.5-flash"
        self.max_retries = 3
        self.base_delay = 2  # Base delay for exponential backoff: 2s, 4s, 8s
    
    async def analyze_text(self, text: str, source: str) -> AnalysisResult:
        """
        Analyze text and extract tasks with context.
        
        Args:
            text: Text content to analyze
            source: Source of the text (email address, etc.)
            
        Returns:
            AnalysisResult with extracted tasks, context, and priority
        """
        try:
            logger.info(
                "Starting text analysis",
                source=source,
                text_length=len(text)
            )
            
            # Check rate limiter before making request
            if not await gemini_rate_limiter.acquire(user_id=source):
                logger.warning(
                    "Rate limited - falling back to simple task creation",
                    source=source
                )
                # Return empty result to trigger fallback
                return AnalysisResult(
                    tasks=[],
                    context="Rate limited - created simple task",
                    priority=Priority.NORMAL
                )
            
            # Create analysis prompt
            prompt = self._create_analysis_prompt(text, source)
            
            # Call Gemini API with circuit breaker and retry logic
            circuit_breaker = get_gemini_circuit_breaker()
            response = await circuit_breaker.call(self._call_gemini_with_retry, prompt)
            
            # Parse response
            result = self._parse_gemini_response(response)
            
            logger.info(
                "Text analysis completed",
                source=source,
                tasks_found=len(result.tasks),
                overall_priority=result.priority
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Failed to analyze text",
                source=source,
                error=str(e),
                exc_info=True
            )
            raise wrap_external_error(
                e, "Gemini", "analyze_text", 
                {"source": source, "text_length": len(text)}
            )
    
    def _create_analysis_prompt(self, text: str, source: str) -> str:
        """Create structured prompt for Gemini analysis"""
        current_time = datetime.utcnow().isoformat()
        
        prompt = f"""
You are an AI assistant that extracts actionable tasks from text content.

Current time: {current_time}
Source: {source}

Text to analyze:
{text}

Please analyze this text and extract any actionable tasks. For each task found, determine:
1. A clear, concise title (max 500 characters)
2. Due date if mentioned (ISO format)
3. Priority level based on urgency indicators

Priority classification rules:
- URGENT: Contains urgent indicators (🚨, ASAP, urgent, deadline today/tomorrow) OR due within 24 hours
- HIGH: Important keywords (important, priority, soon) OR due within 3 days
- NORMAL: Regular tasks without urgency indicators
- LOW: Optional tasks, suggestions, or future considerations

Also provide:
- Overall context summary of the content
- Overall priority level for the entire content

Respond with valid JSON in this exact format:
{{
  "tasks": [
    {{
      "title": "Task description",
      "due": "2024-01-15T10:00:00Z" or null,
      "priority": "urgent|high|normal|low"
    }}
  ],
  "context": "Brief summary of the content and its purpose",
  "priority": "urgent|high|normal|low"
}}

If no actionable tasks are found, return empty tasks array but still provide context and priority.
"""
        return prompt
    
    async def _call_gemini_with_retry(self, prompt: str) -> Dict[str, Any]:
        """Call Gemini API with exponential backoff retry logic"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                delay = self.base_delay * (2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                
                if attempt > 0:
                    logger.info(
                        "Retrying Gemini API call",
                        attempt=attempt + 1,
                        delay=delay
                    )
                    await asyncio.sleep(delay)
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.base_url}/models/{self.model}:generateContent",
                        params={"key": self.api_key},
                        json={
                            "contents": [{
                                "parts": [{
                                    "text": prompt
                                }]
                            }],
                            "generationConfig": {
                                "temperature": 0.1,
                                "topK": 1,
                                "topP": 0.8,
                                "maxOutputTokens": 2048,
                            },
                            "safetySettings": [
                                {
                                    "category": "HARM_CATEGORY_HARASSMENT",
                                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                                },
                                {
                                    "category": "HARM_CATEGORY_HATE_SPEECH",
                                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                                },
                                {
                                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                                },
                                {
                                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                                }
                            ]
                        },
                        headers={
                            "Content-Type": "application/json"
                        }
                    )
                    
                    response.raise_for_status()
                    return response.json()
                    
            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(
                    "Gemini API timeout",
                    attempt=attempt + 1,
                    error=str(e)
                )
            except httpx.HTTPStatusError as e:
                last_exception = e
                logger.warning(
                    "Gemini API HTTP error",
                    attempt=attempt + 1,
                    status_code=e.response.status_code,
                    error=str(e)
                )
                # Don't retry on 4xx errors (except rate limiting)
                if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                    break
            except Exception as e:
                last_exception = e
                logger.warning(
                    "Gemini API error",
                    attempt=attempt + 1,
                    error=str(e)
                )
        
        # All retries failed
        logger.error(
            "All Gemini API retries failed",
            max_retries=self.max_retries,
            last_error=str(last_exception)
        )
        raise GeminiServiceError(f"Gemini API failed after {self.max_retries} retries: {str(last_exception)}")
    
    def _parse_gemini_response(self, response: Dict[str, Any]) -> AnalysisResult:
        """Parse Gemini API response and extract structured data"""
        try:
            # Extract text from response
            candidates = response.get("candidates", [])
            if not candidates:
                raise GeminiServiceError("No candidates in Gemini response")
            
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if not parts:
                raise GeminiServiceError("No parts in Gemini response")
            
            text_response = parts[0].get("text", "")
            if not text_response:
                raise GeminiServiceError("Empty text in Gemini response")
            
            # Parse JSON from response
            try:
                # Clean up response text (remove markdown code blocks if present)
                clean_text = text_response.strip()
                if clean_text.startswith("```json"):
                    clean_text = clean_text[7:]
                if clean_text.endswith("```"):
                    clean_text = clean_text[:-3]
                clean_text = clean_text.strip()
                
                parsed_data = json.loads(clean_text)
            except json.JSONDecodeError as e:
                logger.error(
                    "Failed to parse Gemini JSON response",
                    response_text=text_response,
                    error=str(e)
                )
                # Return empty result if parsing fails
                return AnalysisResult(
                    tasks=[],
                    context="Failed to parse AI response",
                    priority=Priority.NORMAL
                )
            
            # Extract tasks
            tasks = []
            for task_data in parsed_data.get("tasks", []):
                try:
                    # Parse due date if present
                    due_date = None
                    if task_data.get("due"):
                        due_date = datetime.fromisoformat(task_data["due"].replace("Z", "+00:00"))
                    
                    # Parse priority
                    priority_str = task_data.get("priority", "normal").lower()
                    priority = Priority(priority_str) if priority_str in [p.value for p in Priority] else Priority.NORMAL
                    
                    task = TaskData(
                        title=task_data.get("title", "").strip(),
                        due=due_date,
                        priority=priority
                    )
                    tasks.append(task)
                    
                except Exception as e:
                    logger.warning(
                        "Failed to parse individual task",
                        task_data=task_data,
                        error=str(e)
                    )
                    continue
            
            # Extract context and overall priority
            context = parsed_data.get("context", "")
            priority_str = parsed_data.get("priority", "normal").lower()
            overall_priority = Priority(priority_str) if priority_str in [p.value for p in Priority] else Priority.NORMAL
            
            return AnalysisResult(
                tasks=tasks,
                context=context,
                priority=overall_priority
            )
            
        except Exception as e:
            logger.error(
                "Failed to parse Gemini response",
                response=response,
                error=str(e)
            )
            raise GeminiServiceError(f"Failed to parse Gemini response: {str(e)}")
    
    async def analyze_calendar_event(self, text: str, source: str) -> CalendarAnalysisResult:
        """
        Analyze text and extract calendar event information.
        
        Args:
            text: Text content to analyze for calendar event
            source: Source of the text (telegram user, etc.)
            
        Returns:
            CalendarAnalysisResult with extracted event details
        """
        try:
            logger.info(
                "Starting calendar event analysis",
                source=source,
                text_length=len(text)
            )
            
            # Check rate limiter before making request
            if not await gemini_rate_limiter.acquire(user_id=source):
                logger.warning(
                    "Rate limited - cannot analyze calendar event",
                    source=source
                )
                # Return result with no datetime to trigger error message
                return CalendarAnalysisResult(
                    title="Event",
                    event_datetime=None,
                    duration_minutes=60,
                    description="Rate limited - please try again later"
                )
            
            # Create calendar analysis prompt
            prompt = self._create_calendar_analysis_prompt(text, source)
            
            # Call Gemini API with circuit breaker and retry logic
            circuit_breaker = get_gemini_circuit_breaker()
            response = await circuit_breaker.call(self._call_gemini_with_retry, prompt)
            
            # Parse response
            result = self._parse_calendar_gemini_response(response)
            
            logger.info(
                "Calendar event analysis completed",
                source=source,
                title=result.title,
                has_datetime=result.event_datetime is not None
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Failed to analyze calendar event",
                source=source,
                error=str(e),
                exc_info=True
            )
            raise wrap_external_error(
                e, "Gemini", "analyze_calendar_event", 
                {"source": source, "text_length": len(text)}
            )
    
    def _create_calendar_analysis_prompt(self, text: str, source: str) -> str:
        """Create structured prompt for calendar event analysis"""
        current_time = datetime.utcnow().isoformat()
        
        prompt = f"""
You are an AI assistant that extracts calendar event information from natural language text.

Current time: {current_time}
Source: {source}

Text to analyze:
{text}

Please analyze this text and extract calendar event information. Determine:
1. Event title (clear, concise, max 500 characters)
2. Date and time when the event should occur (ISO format with timezone)
3. Duration in minutes (default 60 if not specified)
4. Additional description if provided

Date/time parsing rules:
- "tomorrow" = next day at specified time or 9:00 AM if no time given
- "Monday", "Tuesday", etc. = next occurrence of that weekday
- "next week" = same day next week
- "2pm", "14:30", "2:30 PM" = convert to 24-hour format
- If only date given, default to 9:00 AM
- If only time given, assume today if time hasn't passed, otherwise tomorrow
- Always output in ISO format: "2024-01-15T14:30:00Z"

Duration parsing rules:
- "30 minutes", "1 hour", "2 hours" = convert to minutes
- Default to 60 minutes if not specified
- Maximum 1440 minutes (24 hours)

Respond with valid JSON in this exact format:
{{
  "title": "Event title",
  "event_datetime": "2024-01-15T14:30:00Z" or null,
  "duration_minutes": 60,
  "description": "Additional details" or null
}}

If you cannot extract a clear date/time, set event_datetime to null.
Always provide a meaningful title even if date/time is unclear.
"""
        return prompt
    
    def _parse_calendar_gemini_response(self, response: Dict[str, Any]) -> CalendarAnalysisResult:
        """Parse Gemini API response for calendar event data"""
        try:
            # Extract text from response
            candidates = response.get("candidates", [])
            if not candidates:
                raise GeminiServiceError("No candidates in Gemini response")
            
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if not parts:
                raise GeminiServiceError("No parts in Gemini response")
            
            text_response = parts[0].get("text", "")
            if not text_response:
                raise GeminiServiceError("Empty text in Gemini response")
            
            # Parse JSON from response
            try:
                # Clean up response text (remove markdown code blocks if present)
                clean_text = text_response.strip()
                if clean_text.startswith("```json"):
                    clean_text = clean_text[7:]
                if clean_text.endswith("```"):
                    clean_text = clean_text[:-3]
                clean_text = clean_text.strip()
                
                parsed_data = json.loads(clean_text)
            except json.JSONDecodeError as e:
                logger.error(
                    "Failed to parse calendar Gemini JSON response",
                    response_text=text_response,
                    error=str(e)
                )
                # Return basic result if parsing fails
                return CalendarAnalysisResult(
                    title="Event",
                    event_datetime=None,
                    duration_minutes=60,
                    description=None
                )
            
            # Parse event datetime if present
            event_datetime = None
            if parsed_data.get("event_datetime"):
                try:
                    event_datetime = datetime.fromisoformat(
                        parsed_data["event_datetime"].replace("Z", "+00:00")
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to parse event datetime",
                        datetime_str=parsed_data.get("event_datetime"),
                        error=str(e)
                    )
            
            # Extract other fields with defaults
            title = parsed_data.get("title", "Event").strip()
            duration_minutes = parsed_data.get("duration_minutes", 60)
            description = parsed_data.get("description")
            
            # Validate duration
            if not isinstance(duration_minutes, int) or duration_minutes < 1 or duration_minutes > 1440:
                duration_minutes = 60
            
            return CalendarAnalysisResult(
                title=title,
                event_datetime=event_datetime,
                duration_minutes=duration_minutes,
                description=description
            )
            
        except Exception as e:
            logger.error(
                "Failed to parse calendar Gemini response",
                response=response,
                error=str(e)
            )
            raise GeminiServiceError(f"Failed to parse calendar Gemini response: {str(e)}")