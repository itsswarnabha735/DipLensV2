from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime
import logging
from app.alerts.models import AlertEvent, Priority

logger = logging.getLogger(__name__)

class NotificationProvider(ABC):
    @abstractmethod
    async def send(self, event: AlertEvent) -> bool:
        pass

class ConsoleNotificationProvider(NotificationProvider):
    """Default provider that logs to console/stdout"""
    async def send(self, event: AlertEvent) -> bool:
        print(f"\n[ALERT PUSH] {event.priority.value.upper()} - {event.symbol}: {event.message}")
        print(f"Chips: {', '.join(event.chips)}")
        print(f"Payload: {event.payload}\n")
        return True

class MockFCMProvider(NotificationProvider):
    """Mock FCM provider for testing push logic"""
    async def send(self, event: AlertEvent) -> bool:
        # Simulate FCM payload construction
        fcm_message = {
            "token": "device_token",
            "notification": {
                "title": f"Potential window: {event.symbol}",
                "body": event.message
            },
            "data": {
                "symbol": event.symbol,
                "rule_id": event.rule_id,
                "chips": str(event.chips),
                "priority": event.priority.value
            },
            "android": {
                "priority": "high" if event.priority == Priority.HIGH else "normal",
                "collapse_key": f"{event.rule_id}_{event.symbol}" # ALRT-19
            },
            "apns": {
                "headers": {
                    "apns-collapse-id": f"{event.rule_id}_{event.symbol}" # ALRT-18
                }
            }
        }
        logger.info(f"FCM Mock Send: {fcm_message}")
        return True

class NotificationService:
    def __init__(self):
        self.providers: List[NotificationProvider] = [
            ConsoleNotificationProvider(),
            MockFCMProvider()
        ]
    
    async def dispatch(self, event: AlertEvent) -> bool:
        """Dispatch event to all configured providers"""
        success = True
        for provider in self.providers:
            try:
                if not await provider.send(event):
                    success = False
            except Exception as e:
                logger.error(f"Provider {provider.__class__.__name__} failed: {e}")
                success = False
        return success
