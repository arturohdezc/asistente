import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import structlog
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from models.gmail_channel import GmailChannel
from models.task import Task
from services.task_service import TaskService
from services.gemini_service import GeminiService
from config.settings import settings
from database import async_session

logger = structlog.get_logger()

class GmailWatcherServiceError(Exception):
    """Gmail watcher service specific errors"""
    pass

class GmailWatcherService:
    """Service for managing Gmail watch channels and processing notifications"""
    
    def __init__(self):
        self.accounts = settings.get_gmail_accounts()
        self.webhook_url = "https://us-central1-YOUR_PROJECT.cloudfunctions.net/gmail-webhook-proxy"  # Update with actual URL
        self.renewal_interval = timedelta(hours=2)  # Renew channels every 2 hours
        self.channel_duration = timedelta(hours=24)  # Channels last 24 hours
    
    async def start_watching_all_accounts(self) -> Dict[str, Any]:
        """
        Start watching all configured Gmail accounts
        
        Returns:
            Dictionary with results for each account
        """
        results = {}
        
        for account in self.accounts:
            email = account.get("email")
            credentials_path = account.get("credentials")
            
            try:
                result = await self.start_watching_account(email, credentials_path)
                results[email] = {"status": "success", "data": result}
                
                logger.info(
                    "Started watching Gmail account",
                    email=email,
                    channel_id=result.get("channel_id")
                )
                
            except Exception as e:
                results[email] = {"status": "error", "error": str(e)}
                logger.error(
                    "Failed to start watching Gmail account",
                    email=email,
                    error=str(e),
                    exc_info=True
                )
        
        return results
    
    async def start_watching_account(self, email: str, credentials_path: str) -> Dict[str, Any]:
        """
        Start watching a specific Gmail account
        
        Args:
            email: Gmail account email
            credentials_path: Path to OAuth2 credentials file
            
        Returns:
            Watch response data
        """
        try:
            # Load credentials
            credentials = self._load_credentials(credentials_path)
            
            # Build Gmail service
            service = build('gmail', 'v1', credentials=credentials)
            
            # Generate unique channel ID
            channel_id = f"gmail-{email.replace('@', '-').replace('.', '-')}-{int(datetime.utcnow().timestamp())}"
            
            # Calculate expiration (24 hours from now)
            expiration = datetime.utcnow() + self.channel_duration
            expiration_ms = int(expiration.timestamp() * 1000)
            
            # Create watch request
            watch_request = {
                'labelIds': ['INBOX'],  # Watch only inbox
                'topicName': f'projects/YOUR_PROJECT/topics/gmail-notifications',  # Update with actual topic
                'labelFilterAction': 'include'
            }
            
            # Alternative: Use webhook URL directly if not using Pub/Sub
            # watch_request = {
            #     'labelIds': ['INBOX'],
            #     'webhook': {
            #         'url': self.webhook_url,
            #         'expiration': expiration_ms
            #     }
            # }
            
            # Execute watch request
            watch_response = service.users().watch(
                userId='me',
                body=watch_request
            ).execute()
            
            # Store channel information in database
            await self._store_channel_info(
                email=email,
                channel_id=channel_id,
                history_id=watch_response.get('historyId'),
                expiration=expiration
            )
            
            logger.info(
                "Gmail watch started",
                email=email,
                channel_id=channel_id,
                history_id=watch_response.get('historyId'),
                expiration=expiration.isoformat()
            )
            
            return {
                "email": email,
                "channel_id": channel_id,
                "history_id": watch_response.get('historyId'),
                "expiration": expiration.isoformat(),
                "watch_response": watch_response
            }
            
        except HttpError as e:
            logger.error(
                "Gmail API error",
                email=email,
                error=str(e)
            )
            raise GmailWatcherServiceError(f"Gmail API error for {email}: {str(e)}")
        except Exception as e:
            logger.error(
                "Failed to start watching Gmail account",
                email=email,
                error=str(e)
            )
            raise GmailWatcherServiceError(f"Failed to start watching {email}: {str(e)}")
    
    async def renew_all_channels(self) -> Dict[str, Any]:
        """
        Renew all Gmail watch channels that are expiring soon
        
        Returns:
            Dictionary with renewal results
        """
        results = {}
        
        try:
            async with async_session() as db:
                # Get channels that need renewal (expiring within 2 hours)
                renewal_threshold = datetime.utcnow() + self.renewal_interval
                
                result = await db.execute(
                    select(GmailChannel).where(
                        GmailChannel.expiration <= renewal_threshold
                    )
                )
                channels_to_renew = result.scalars().all()
                
                logger.info(
                    "Found channels to renew",
                    count=len(channels_to_renew)
                )
                
                for channel in channels_to_renew:
                    try:
                        # Find account credentials for this email
                        account = next(
                            (acc for acc in self.accounts if acc.get("email") == channel.email),
                            None
                        )
                        
                        if not account:
                            logger.warning(
                                "No account configuration found for channel",
                                email=channel.email,
                                channel_id=channel.channel_id
                            )
                            continue
                        
                        # Stop old channel
                        await self.stop_watching_account(channel.email, account.get("credentials"))
                        
                        # Start new channel
                        new_channel = await self.start_watching_account(
                            channel.email,
                            account.get("credentials")
                        )
                        
                        results[channel.email] = {"status": "renewed", "data": new_channel}
                        
                        logger.info(
                            "Renewed Gmail channel",
                            email=channel.email,
                            old_channel_id=channel.channel_id,
                            new_channel_id=new_channel.get("channel_id")
                        )
                        
                    except Exception as e:
                        results[channel.email] = {"status": "error", "error": str(e)}
                        logger.error(
                            "Failed to renew Gmail channel",
                            email=channel.email,
                            channel_id=channel.channel_id,
                            error=str(e)
                        )
                
                return results
                
        except Exception as e:
            logger.error("Failed to renew channels", error=str(e), exc_info=True)
            raise GmailWatcherServiceError(f"Failed to renew channels: {str(e)}")
    
    async def stop_watching_account(self, email: str, credentials_path: str) -> bool:
        """
        Stop watching a specific Gmail account
        
        Args:
            email: Gmail account email
            credentials_path: Path to OAuth2 credentials file
            
        Returns:
            True if stopped successfully
        """
        try:
            # Load credentials
            credentials = self._load_credentials(credentials_path)
            
            # Build Gmail service
            service = build('gmail', 'v1', credentials=credentials)
            
            # Stop watching
            service.users().stop(userId='me').execute()
            
            # Remove channel from database
            async with async_session() as db:
                await db.execute(
                    delete(GmailChannel).where(GmailChannel.email == email)
                )
                await db.commit()
            
            logger.info("Stopped watching Gmail account", email=email)
            return True
            
        except Exception as e:
            logger.error(
                "Failed to stop watching Gmail account",
                email=email,
                error=str(e)
            )
            return False
    
    async def process_notification(
        self,
        notification_data: Dict[str, Any],
        task_service: TaskService,
        gemini_service: GeminiService
    ) -> Dict[str, Any]:
        """
        Process Gmail push notification and create tasks
        
        Args:
            notification_data: Notification payload from Gmail
            task_service: Task service instance
            gemini_service: Gemini service instance
            
        Returns:
            Processing result
        """
        try:
            logger.info("Processing Gmail notification", data=notification_data)
            
            # Extract notification details
            message = notification_data.get('message', {})
            data = message.get('data', '')
            
            if not data:
                return {"status": "ignored", "reason": "No data in notification"}
            
            # Decode base64 data
            import base64
            decoded_data = json.loads(base64.b64decode(data).decode('utf-8'))
            
            email_address = decoded_data.get('emailAddress')
            history_id = decoded_data.get('historyId')
            
            if not email_address or not history_id:
                return {"status": "ignored", "reason": "Missing email or history ID"}
            
            # Get account credentials
            account = next(
                (acc for acc in self.accounts if acc.get("email") == email_address),
                None
            )
            
            if not account:
                return {"status": "error", "reason": f"No credentials for {email_address}"}
            
            # Load credentials and build service
            credentials = self._load_credentials(account.get("credentials"))
            service = build('gmail', 'v1', credentials=credentials)
            
            # Get channel info from database
            async with async_session() as db:
                result = await db.execute(
                    select(GmailChannel).where(GmailChannel.email == email_address)
                )
                channel = result.scalar_one_or_none()
                
                if not channel:
                    return {"status": "error", "reason": f"No channel found for {email_address}"}
                
                # Get history since last known history ID
                history_response = service.users().history().list(
                    userId='me',
                    startHistoryId=channel.history_id,
                    historyTypes=['messageAdded']
                ).execute()
                
                history_items = history_response.get('history', [])
                tasks_created = []
                
                for history_item in history_items:
                    messages_added = history_item.get('messagesAdded', [])
                    
                    for message_added in messages_added:
                        message_id = message_added.get('message', {}).get('id')
                        
                        if message_id:
                            # Get full message
                            message = service.users().messages().get(
                                userId='me',
                                id=message_id,
                                format='full'
                            ).execute()
                            
                            # Extract email content
                            email_content = self._extract_email_content(message)
                            
                            if email_content:
                                # Analyze with Gemini
                                analysis = await gemini_service.analyze_text(
                                    email_content['body'],
                                    email_address
                                )
                                
                                # Create tasks from analysis
                                for task_data in analysis.tasks:
                                    task = await task_service.create_task(
                                        title=task_data.title,
                                        source=email_address,
                                        due=task_data.due,
                                        priority=task_data.priority
                                    )
                                    tasks_created.append(task.to_dict())
                
                # Update channel history ID
                channel.history_id = history_id
                await db.commit()
                
                logger.info(
                    "Gmail notification processed",
                    email=email_address,
                    tasks_created=len(tasks_created),
                    history_items=len(history_items)
                )
                
                return {
                    "status": "processed",
                    "email": email_address,
                    "tasks_created": tasks_created,
                    "history_items_processed": len(history_items)
                }
                
        except Exception as e:
            logger.error(
                "Failed to process Gmail notification",
                error=str(e),
                exc_info=True
            )
            return {"status": "error", "error": str(e)}
    
    async def run_renewal_scheduler(self):
        """
        Background task to periodically renew Gmail watch channels
        """
        logger.info("Starting Gmail channel renewal scheduler")
        
        while True:
            try:
                await asyncio.sleep(self.renewal_interval.total_seconds())
                
                logger.info("Running scheduled channel renewal")
                results = await self.renew_all_channels()
                
                logger.info(
                    "Scheduled channel renewal completed",
                    results=results
                )
                
            except Exception as e:
                logger.error(
                    "Error in renewal scheduler",
                    error=str(e),
                    exc_info=True
                )
                # Continue running even if renewal fails
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
    
    def _load_credentials(self, credentials_path: str) -> Credentials:
        """Load OAuth2 credentials from file"""
        try:
            with open(credentials_path, 'r') as f:
                creds_data = json.load(f)
            
            credentials = Credentials.from_authorized_user_info(creds_data)
            
            # Refresh if expired
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            
            return credentials
            
        except Exception as e:
            raise GmailWatcherServiceError(f"Failed to load credentials: {str(e)}")
    
    async def _store_channel_info(
        self,
        email: str,
        channel_id: str,
        history_id: str,
        expiration: datetime
    ):
        """Store Gmail channel information in database"""
        try:
            async with async_session() as db:
                # Remove existing channel for this email
                await db.execute(
                    delete(GmailChannel).where(GmailChannel.email == email)
                )
                
                # Create new channel record
                channel = GmailChannel(
                    email=email,
                    channel_id=channel_id,
                    history_id=history_id,
                    expiration=expiration
                )
                
                db.add(channel)
                await db.commit()
                
        except Exception as e:
            logger.error(
                "Failed to store channel info",
                email=email,
                channel_id=channel_id,
                error=str(e)
            )
            raise
    
    def _extract_email_content(self, message: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Extract subject and body from Gmail message"""
        try:
            headers = message.get('payload', {}).get('headers', [])
            
            # Extract subject
            subject = ""
            for header in headers:
                if header.get('name') == 'Subject':
                    subject = header.get('value', '')
                    break
            
            # Extract body
            body = ""
            payload = message.get('payload', {})
            
            # Handle multipart messages
            if 'parts' in payload:
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/plain':
                        body_data = part.get('body', {}).get('data', '')
                        if body_data:
                            import base64
                            body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                            break
            else:
                # Handle single part messages
                if payload.get('mimeType') == 'text/plain':
                    body_data = payload.get('body', {}).get('data', '')
                    if body_data:
                        import base64
                        body = base64.urlsafe_b64decode(body_data).decode('utf-8')
            
            if subject or body:
                return {
                    "subject": subject,
                    "body": f"{subject}\n\n{body}".strip()
                }
            
            return None
            
        except Exception as e:
            logger.error("Failed to extract email content", error=str(e))
            return None