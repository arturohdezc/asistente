"""
Locust performance testing script for Personal Assistant Bot

This script defines load testing scenarios for the Personal Assistant Bot API
to validate performance under various load conditions.
"""

import json
import random
from locust import HttpUser, task, between, events
from datetime import datetime, timedelta


class PersonalAssistantUser(HttpUser):
    """
    Simulates a user interacting with the Personal Assistant Bot API
    """
    
    wait_time = between(1, 5)  # Wait 1-5 seconds between requests
    
    def on_start(self):
        """Called when a user starts"""
        self.task_ids = []  # Track created task IDs for cleanup
        
        # Simulate user authentication/setup
        response = self.client.get("/health")
        if response.status_code != 200:
            print(f"Health check failed: {response.status_code}")
    
    def on_stop(self):
        """Called when a user stops"""
        # Clean up created tasks
        for task_id in self.task_ids:
            try:
                self.client.delete(f"/api/v1/tasks/{task_id}")
            except Exception:
                pass  # Ignore cleanup errors
    
    @task(10)
    def health_check(self):
        """Health check endpoint - most frequent"""
        self.client.get("/health")
    
    @task(8)
    def api_health_check(self):
        """API health check"""
        self.client.get("/api/v1/health")
    
    @task(5)
    def list_tasks(self):
        """List tasks with various filters"""
        params = {}
        
        # Randomly add filters
        if random.choice([True, False]):
            params['priority'] = random.choice(['urgent', 'high', 'normal', 'low'])
        
        if random.choice([True, False]):
            params['status'] = random.choice(['open', 'done'])
        
        if random.choice([True, False]):
            params['page'] = random.randint(1, 3)
            params['size'] = random.choice([10, 20, 50])
        
        self.client.get("/api/v1/tasks", params=params)
    
    @task(3)
    def get_daily_summary(self):
        """Get daily task summary"""
        self.client.get("/api/v1/daily-summary")
    
    @task(2)
    def get_metrics(self):
        """Get Prometheus metrics"""
        with self.client.get("/api/v1/metrics", catch_response=True) as response:
            if response.status_code == 200:
                # Validate metrics format
                if "http_requests_total" in response.text or "# HELP" in response.text:
                    response.success()
                else:
                    response.failure("Invalid metrics format")
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(2)
    def get_circuit_breakers(self):
        """Get circuit breaker status"""
        self.client.get("/api/v1/circuit-breakers")
    
    @task(1)
    def create_task(self):
        """Create a new task"""
        task_titles = [
            "Review quarterly reports",
            "Prepare presentation for client meeting",
            "Update project documentation",
            "Schedule team standup",
            "Review code changes",
            "Plan sprint retrospective",
            "Update dependencies",
            "Write unit tests",
            "Deploy to staging",
            "Monitor system metrics"
        ]
        
        task_data = {
            "title": random.choice(task_titles),
            "priority": random.choice(["normal", "high", "urgent", "low"]),
            "status": "open"
        }
        
        # Randomly add due date
        if random.choice([True, False]):
            future_date = datetime.utcnow() + timedelta(
                days=random.randint(1, 30),
                hours=random.randint(0, 23)
            )
            task_data["due"] = future_date.isoformat()
        
        with self.client.post("/api/v1/tasks", json=task_data, catch_response=True) as response:
            if response.status_code == 201:
                try:
                    task = response.json()
                    self.task_ids.append(task["id"])
                    response.success()
                except (KeyError, json.JSONDecodeError):
                    response.failure("Invalid task creation response")
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(1)
    def get_task_details(self):
        """Get details of a specific task"""
        if self.task_ids:
            task_id = random.choice(self.task_ids)
            self.client.get(f"/api/v1/tasks/{task_id}")
        else:
            # Try a random task ID
            task_id = random.randint(1, 100)
            with self.client.get(f"/api/v1/tasks/{task_id}", catch_response=True) as response:
                if response.status_code in [200, 404]:
                    response.success()
                else:
                    response.failure(f"Unexpected status code: {response.status_code}")
    
    @task(1)
    def update_task(self):
        """Update an existing task"""
        if self.task_ids:
            task_id = random.choice(self.task_ids)
            
            update_data = {}
            
            # Randomly update different fields
            if random.choice([True, False]):
                update_data["title"] = f"Updated task {random.randint(1, 1000)}"
            
            if random.choice([True, False]):
                update_data["priority"] = random.choice(["normal", "high", "urgent", "low"])
            
            if random.choice([True, False]):
                update_data["status"] = random.choice(["open", "done"])
            
            if update_data:
                self.client.put(f"/api/v1/tasks/{task_id}", json=update_data)
    
    @task(1)
    def get_backup_stats(self):
        """Get backup statistics"""
        self.client.get("/api/v1/backup/stats")


class WebhookUser(HttpUser):
    """
    Simulates webhook requests from external services
    """
    
    wait_time = between(5, 15)  # Webhooks are less frequent
    weight = 1  # Lower weight compared to regular users
    
    @task(3)
    def telegram_webhook(self):
        """Simulate Telegram webhook"""
        webhook_data = {
            "message": {
                "message_id": random.randint(1, 10000),
                "from": {
                    "id": random.randint(100000, 999999),
                    "first_name": "Test",
                    "username": "testuser"
                },
                "chat": {
                    "id": random.randint(100000, 999999),
                    "type": "private"
                },
                "date": int(datetime.utcnow().timestamp()),
                "text": random.choice([
                    "/start",
                    "/help",
                    "/list",
                    "/add Test task from webhook",
                    "/done 123"
                ])
            }
        }
        
        headers = {
            "X-Telegram-Bot-Api-Secret-Token": "test_secret_token",
            "Content-Type": "application/json"
        }
        
        with self.client.post(
            "/api/v1/webhook/telegram", 
            json=webhook_data, 
            headers=headers,
            catch_response=True
        ) as response:
            # Webhook should return 401 for invalid token in load testing
            if response.status_code in [200, 401]:
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")
    
    @task(2)
    def gmail_webhook(self):
        """Simulate Gmail webhook"""
        webhook_data = {
            "message": {
                "data": "eyJlbWFpbEFkZHJlc3MiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiaGlzdG9yeUlkIjoiMTIzNDU2In0=",
                "messageId": f"msg_{random.randint(1, 10000)}",
                "publishTime": datetime.utcnow().isoformat() + "Z"
            }
        }
        
        with self.client.post(
            "/api/v1/webhook/gmail", 
            json=webhook_data,
            catch_response=True
        ) as response:
            if response.status_code in [200, 500]:  # May fail due to missing credentials
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")
    
    @task(1)
    def calendar_webhook(self):
        """Simulate Calendar webhook"""
        headers = {
            "X-Goog-Channel-ID": f"channel_{random.randint(1, 1000)}",
            "X-Goog-Resource-State": "exists",
            "X-Goog-Resource-URI": "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            "X-Goog-Message-Number": str(random.randint(1, 10000))
        }
        
        with self.client.post(
            "/api/v1/webhook/calendar",
            headers=headers,
            catch_response=True
        ) as response:
            if response.status_code in [200, 500]:  # May fail due to missing credentials
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")


class AdminUser(HttpUser):
    """
    Simulates administrative operations
    """
    
    wait_time = between(10, 30)  # Admin operations are less frequent
    weight = 1  # Much lower weight
    
    @task(3)
    def create_backup(self):
        """Create manual backup"""
        with self.client.post("/api/v1/backup/create", catch_response=True) as response:
            if response.status_code in [200, 500]:  # May fail in test environment
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")
    
    @task(2)
    def list_backups(self):
        """List available backups"""
        self.client.get("/api/v1/backup/list")
    
    @task(1)
    def daily_summary_cron(self):
        """Simulate cron job for daily summary"""
        headers = {
            "Authorization": "Bearer test_cron_token"
        }
        
        with self.client.post(
            "/api/v1/cron/daily-summary",
            headers=headers,
            catch_response=True
        ) as response:
            # Should return 401 for invalid token
            if response.status_code in [200, 401]:
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")


# Event handlers for custom metrics
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, context, **kwargs):
    """Custom request handler for additional metrics"""
    if exception:
        print(f"Request failed: {request_type} {name} - {exception}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    print("🚀 Starting Personal Assistant Bot load test")
    print(f"Target host: {environment.host}")
    print(f"Users: {environment.runner.target_user_count}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops"""
    print("🏁 Load test completed")
    
    # Print summary statistics
    stats = environment.runner.stats
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Failed requests: {stats.total.num_failures}")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"Max response time: {stats.total.max_response_time:.2f}ms")
    print(f"Requests per second: {stats.total.current_rps:.2f}")
    
    # Check if performance criteria are met
    if stats.total.avg_response_time > 1000:  # 1 second
        print("⚠️  WARNING: Average response time exceeds 1 second")
    
    if stats.total.num_failures / max(stats.total.num_requests, 1) > 0.05:  # 5% error rate
        print("⚠️  WARNING: Error rate exceeds 5%")
    
    print("📊 Detailed results available in Locust web UI")


# Custom user classes for different load patterns
class BurstUser(PersonalAssistantUser):
    """User that creates burst traffic"""
    wait_time = between(0.1, 0.5)  # Very short wait times
    weight = 1


class SlowUser(PersonalAssistantUser):
    """User that simulates slow connections"""
    wait_time = between(10, 30)  # Longer wait times
    weight = 2


if __name__ == "__main__":
    # Example of running Locust programmatically
    import subprocess
    import sys
    
    print("🧪 Personal Assistant Bot Load Testing")
    print("=" * 50)
    
    # Default Locust command
    cmd = [
        "locust",
        "-f", "locustfile.py",
        "--host", "http://localhost:8080",
        "--users", "50",
        "--spawn-rate", "5",
        "--run-time", "5m",
        "--html", "locust-report.html"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print("Open http://localhost:8089 to view real-time results")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n🛑 Load test interrupted by user")
    except Exception as e:
        print(f"❌ Load test failed: {e}")
        sys.exit(1)