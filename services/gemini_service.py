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

# GeminiServiceError is now imported from core.exceptions

class GeminiService:
    """Service for analyzing text using Gemini 1.5 Pro API"""
    
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.model = "gemini-1.5-pro-latest"
        self.max_retries = 3
        self.base_delay = 1  # Base delay for exponential backoff
    
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