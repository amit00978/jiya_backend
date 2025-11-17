"""
Command Router - Routes intents to appropriate action services
"""
import logging
from typing import Dict, Any

from app.models.schemas import Intent, IntentType
from app.services.reminders import RemindersService
from app.services.flights import FlightsService

logger = logging.getLogger(__name__)


class CommandRouter:
    """
    Routes commands to appropriate action services
    """
    
    def __init__(self):
        self.reminders_service = RemindersService()
        self.flights_service = FlightsService()
    
    async def route(
        self,
        intent: Intent,
        user_id: str,
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Route intent to appropriate service
        
        Args:
            intent: Parsed intent with slots
            user_id: User identifier
            user_context: User preferences and context
            
        Returns:
            Result from action service
        """
        try:
            if intent.intent == IntentType.SET_ALARM:
                return await self._handle_set_alarm(intent, user_id, user_context)
            
            elif intent.intent == IntentType.DELETE_ALARM:
                return await self._handle_delete_alarm(intent, user_id)
            
            elif intent.intent == IntentType.SEARCH_FLIGHTS:
                return await self._handle_search_flights(intent, user_id, user_context)
            
            elif intent.intent == IntentType.GET_WEATHER:
                return await self._handle_get_weather(intent, user_id)
            
            else:
                return {
                    "status": "unknown_intent",
                    "message": "I'm not sure how to help with that yet."
                }
                
        except Exception as e:
            logger.error(f"❌ Routing error: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def _handle_set_alarm(
        self,
        intent: Intent,
        user_id: str,
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle set alarm command"""
        time = intent.slots.get("time")
        
        if not time:
            return {
                "status": "missing_slots",
                "message": "I need a time to set the alarm. When would you like to wake up?"
            }
        
        # Get timezone from user context
        timezone = user_context.get("preferences", {}).get("timezone", "UTC")
        
        result = await self.reminders_service.set_alarm(
            user_id=user_id,
            time=time,
            timezone=timezone
        )
        
        return result
    
    async def _handle_delete_alarm(
        self,
        intent: Intent,
        user_id: str
    ) -> Dict[str, Any]:
        """Handle delete alarm command"""
        result = await self.reminders_service.delete_recent_alarm(user_id)
        return result
    
    async def _handle_search_flights(
        self,
        intent: Intent,
        user_id: str,
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle flight search command"""
        source = intent.slots.get("source")
        destination = intent.slots.get("destination")
        date = intent.slots.get("date")
        time_window = intent.slots.get("time_window")
        
        # Validate required slots
        missing = []
        if not source:
            missing.append("source city")
        if not destination:
            missing.append("destination city")
        if not date:
            missing.append("travel date")
        
        if missing:
            return {
                "status": "missing_slots",
                "message": f"I need the following information: {', '.join(missing)}"
            }
        
        # Get user preferences
        preferences = user_context.get("intent_specific", {})
        
        result = await self.flights_service.search_flights(
            source=source,
            destination=destination,
            date=date,
            time_window=time_window,
            preferences=preferences
        )
        
        return result
    
    async def _handle_get_weather(
        self,
        intent: Intent,
        user_id: str
    ) -> Dict[str, Any]:
        """Handle weather query"""
        # TODO: Implement weather service
        return {
            "status": "not_implemented",
            "message": "Weather service coming soon!"
        }
