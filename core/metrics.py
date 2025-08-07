"""
Prometheus metrics collection for Personal Assistant Bot

This module provides metrics collection and exposition for monitoring
application performance and business metrics.
"""

import time
from typing import Dict, Any, Optional
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import structlog

from .circuit_breaker import circuit_breaker_manager

logger = structlog.get_logger()

# Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# Task metrics
tasks_total = Counter(
    'tasks_total',
    'Total tasks created',
    ['source', 'priority']
)

tasks_completed_total = Counter(
    'tasks_completed_total',
    'Total tasks completed',
    ['source', 'priority']
)

tasks_current = Gauge(
    'tasks_current',
    'Current number of open tasks',
    ['priority']
)

# External service metrics
external_api_requests_total = Counter(
    'external_api_requests_total',
    'Total external API requests',
    ['service', 'operation', 'status']
)

external_api_duration_seconds = Histogram(
    'external_api_duration_seconds',
    'External API request duration in seconds',
    ['service', 'operation']
)

# Circuit breaker metrics
circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=half-open, 2=open)',
    ['circuit_name']
)

circuit_breaker_failures_total = Counter(
    'circuit_breaker_failures_total',
    'Total circuit breaker failures',
    ['circuit_name']
)

# Webhook metrics
webhook_requests_total = Counter(
    'webhook_requests_total',
    'Total webhook requests',
    ['service', 'status']
)

# Database metrics
database_operations_total = Counter(
    'database_operations_total',
    'Total database operations',
    ['operation', 'table', 'status']
)

database_operation_duration_seconds = Histogram(
    'database_operation_duration_seconds',
    'Database operation duration in seconds',
    ['operation', 'table']
)

# Business metrics
daily_summaries_sent_total = Counter(
    'daily_summaries_sent_total',
    'Total daily summaries sent',
    ['status']
)

backups_created_total = Counter(
    'backups_created_total',
    'Total backups created',
    ['status']
)

gmail_notifications_processed_total = Counter(
    'gmail_notifications_processed_total',
    'Total Gmail notifications processed',
    ['status']
)

calendar_notifications_processed_total = Counter(
    'calendar_notifications_processed_total',
    'Total Calendar notifications processed',
    ['status']
)


class MetricsCollector:
    """
    Metrics collection and management
    """
    
    def __init__(self):
        self.start_time = time.time()
    
    def record_http_request(
        self, 
        method: str, 
        endpoint: str, 
        status_code: int, 
        duration: float
    ):
        """Record HTTP request metrics"""
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_task_created(self, source: str, priority: str):
        """Record task creation"""
        tasks_total.labels(source=source, priority=priority).inc()
    
    def record_task_completed(self, source: str, priority: str):
        """Record task completion"""
        tasks_completed_total.labels(source=source, priority=priority).inc()
    
    def update_current_tasks(self, priority_counts: Dict[str, int]):
        """Update current task counts by priority"""
        for priority, count in priority_counts.items():
            tasks_current.labels(priority=priority).set(count)
    
    def record_external_api_request(
        self,
        service: str,
        operation: str,
        status: str,
        duration: Optional[float] = None
    ):
        """Record external API request"""
        external_api_requests_total.labels(
            service=service,
            operation=operation,
            status=status
        ).inc()
        
        if duration is not None:
            external_api_duration_seconds.labels(
                service=service,
                operation=operation
            ).observe(duration)
    
    def record_webhook_request(self, service: str, status: str):
        """Record webhook request"""
        webhook_requests_total.labels(service=service, status=status).inc()
    
    def record_database_operation(
        self,
        operation: str,
        table: str,
        status: str,
        duration: Optional[float] = None
    ):
        """Record database operation"""
        database_operations_total.labels(
            operation=operation,
            table=table,
            status=status
        ).inc()
        
        if duration is not None:
            database_operation_duration_seconds.labels(
                operation=operation,
                table=table
            ).observe(duration)
    
    def update_circuit_breaker_metrics(self):
        """Update circuit breaker metrics"""
        stats = circuit_breaker_manager.get_all_stats()
        
        for circuit_name, circuit_stats in stats.items():
            # Map state to numeric value
            state_map = {"closed": 0, "half_open": 1, "open": 2}
            state_value = state_map.get(circuit_stats["state"], 0)
            
            circuit_breaker_state.labels(circuit_name=circuit_name).set(state_value)
    
    def record_daily_summary_sent(self, status: str):
        """Record daily summary sent"""
        daily_summaries_sent_total.labels(status=status).inc()
    
    def record_backup_created(self, status: str):
        """Record backup creation"""
        backups_created_total.labels(status=status).inc()
    
    def record_gmail_notification_processed(self, status: str):
        """Record Gmail notification processing"""
        gmail_notifications_processed_total.labels(status=status).inc()
    
    def record_calendar_notification_processed(self, status: str):
        """Record Calendar notification processing"""
        calendar_notifications_processed_total.labels(status=status).inc()
    
    def get_application_info(self) -> Dict[str, Any]:
        """Get application information for metrics"""
        uptime = time.time() - self.start_time
        
        return {
            "uptime_seconds": uptime,
            "start_time": self.start_time,
            "circuit_breakers": circuit_breaker_manager.get_all_stats()
        }


# Global metrics collector
metrics_collector = MetricsCollector()


def generate_metrics() -> str:
    """
    Generate Prometheus metrics in text format
    
    Returns:
        Prometheus metrics as string
    """
    try:
        # Update circuit breaker metrics before generating
        metrics_collector.update_circuit_breaker_metrics()
        
        # Generate Prometheus metrics
        return generate_latest().decode('utf-8')
        
    except Exception as e:
        logger.error("Failed to generate metrics", error=str(e), exc_info=True)
        return "# Error generating metrics\n"


def get_metrics_content_type() -> str:
    """Get the content type for Prometheus metrics"""
    return CONTENT_TYPE_LATEST