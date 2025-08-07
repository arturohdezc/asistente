"""
Custom exception hierarchy for Personal Assistant Bot

This module defines a structured exception hierarchy that provides
better error handling and context preservation throughout the application.
"""

from typing import Optional, Dict, Any
import structlog

logger = structlog.get_logger()


class PersonalAssistantError(Exception):
    """Base exception for all Personal Assistant Bot errors"""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}
        self.original_error = original_error
        
        # Log the error when created
        logger.error(
            "PersonalAssistantError created",
            error_code=self.error_code,
            message=self.message,
            context=self.context,
            original_error=str(original_error) if original_error else None,
            exception_type=self.__class__.__name__
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context,
            "exception_type": self.__class__.__name__
        }


class ValidationError(PersonalAssistantError):
    """Raised when input validation fails"""
    pass


class AuthenticationError(PersonalAssistantError):
    """Raised when authentication fails"""
    pass


class AuthorizationError(PersonalAssistantError):
    """Raised when authorization fails"""
    pass


class RateLimitError(PersonalAssistantError):
    """Raised when rate limits are exceeded"""
    pass


class ExternalServiceError(PersonalAssistantError):
    """Base class for external service errors"""
    pass


class DatabaseError(PersonalAssistantError):
    """Raised when database operations fail"""
    pass


class ConfigurationError(PersonalAssistantError):
    """Raised when configuration is invalid or missing"""
    pass


# Service-specific exceptions
class TaskServiceError(PersonalAssistantError):
    """Raised when task service operations fail"""
    pass


class TelegramServiceError(ExternalServiceError):
    """Raised when Telegram API operations fail"""
    pass


class GeminiServiceError(ExternalServiceError):
    """Raised when Gemini AI API operations fail"""
    pass


class CalendarServiceError(ExternalServiceError):
    """Raised when Google Calendar API operations fail"""
    pass


class GmailServiceError(ExternalServiceError):
    """Raised when Gmail API operations fail"""
    pass


class SummaryServiceError(PersonalAssistantError):
    """Raised when summary service operations fail"""
    pass


class BackupServiceError(PersonalAssistantError):
    """Raised when backup service operations fail"""
    pass


# Circuit breaker exceptions
class CircuitBreakerError(PersonalAssistantError):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreakerOpenError(CircuitBreakerError):
    """Raised when circuit breaker is in open state"""
    pass


class CircuitBreakerTimeoutError(CircuitBreakerError):
    """Raised when circuit breaker operation times out"""
    pass


# Utility functions for error handling
def wrap_external_error(
    original_error: Exception,
    service_name: str,
    operation: str,
    context: Optional[Dict[str, Any]] = None
) -> ExternalServiceError:
    """
    Wrap external service errors with consistent context
    
    Args:
        original_error: The original exception
        service_name: Name of the external service
        operation: Operation that failed
        context: Additional context information
        
    Returns:
        Wrapped ExternalServiceError
    """
    error_context = {
        "service": service_name,
        "operation": operation,
        **(context or {})
    }
    
    return ExternalServiceError(
        message=f"{service_name} {operation} failed: {str(original_error)}",
        error_code=f"{service_name.upper()}_{operation.upper()}_ERROR",
        context=error_context,
        original_error=original_error
    )


def wrap_database_error(
    original_error: Exception,
    operation: str,
    table: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> DatabaseError:
    """
    Wrap database errors with consistent context
    
    Args:
        original_error: The original exception
        operation: Database operation that failed
        table: Database table involved
        context: Additional context information
        
    Returns:
        Wrapped DatabaseError
    """
    error_context = {
        "operation": operation,
        "table": table,
        **(context or {})
    }
    
    return DatabaseError(
        message=f"Database {operation} failed: {str(original_error)}",
        error_code=f"DATABASE_{operation.upper()}_ERROR",
        context=error_context,
        original_error=original_error
    )