"""
Response Builder - Creates natural language responses using LLM
"""
import logging
from typing import Dict, Any
from openai import AsyncOpenAI

from app.core.config import settings
from app.models.schemas import Intent, IntentType

logger = logging.getLogger(__name__)


class ResponseBuilder:
    """
    Builds natural, Jarvis-style responses using LLM
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def build_response(
        self,
        intent: Intent,
        action_result: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> str:
        """
        Build natural language response
        
        Args:
            intent: Parsed intent
            action_result: Result from action service
            user_context: User preferences and context
            
        Returns:
            Natural language response text
        """
        try:
            # Check if action was successful
            status = action_result.get("status")
            
            if status == "error":
                return self._build_error_response(action_result)
            
            if status == "missing_slots":
                return action_result.get("message", "I need more information.")
            
            # Build context-aware response
            if intent.intent == IntentType.SET_ALARM:
                return self._build_alarm_response(action_result)
            
            elif intent.intent == IntentType.DELETE_ALARM:
                return self._build_delete_alarm_response(action_result)
            
            elif intent.intent == IntentType.SEARCH_FLIGHTS:
                return await self._build_flight_response(action_result, user_context)
            
            else:
                return "I've processed your request."
                
        except Exception as e:
            logger.error(f"❌ Response building error: {e}")
            return "I've completed that task for you."
    
    def _build_alarm_response(self, result: Dict[str, Any]) -> str:
        """Build response for alarm setting"""
        if result.get("status") == "success":
            return result.get("message", "Your alarm has been set.")
        return "I couldn't set the alarm. Please try again."
    
    def _build_delete_alarm_response(self, result: Dict[str, Any]) -> str:
        """Build response for alarm deletion"""
        return result.get("message", "Alarm deleted.")
    
    async def _build_flight_response(
        self,
        result: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> str:
        """Build detailed flight search response"""
        if result.get("status") != "success":
            return result.get("message", "I couldn't find any flights.")
        
        flights = result.get("flights", [])
        
        if not flights:
            return f"I couldn't find any flights from {result.get('source')} to {result.get('destination')} on {result.get('date')}."
        
        # Build natural response using LLM
        prompt = f"""You are Jarvis, an AI assistant. Present these flight options in a natural, conversational way.

Flight search: {result.get('source')} to {result.get('destination')} on {result.get('date')}

Available flights:
{self._format_flights_for_llm(flights)}

Create a brief, helpful response (2-3 sentences) highlighting the best option."""

        try:
            response = await self.client.chat.completions.create(
                model=settings.DEFAULT_LLM_MODEL,
                messages=[
                    {"role": "system", "content": "You are Jarvis, a helpful and concise AI assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"❌ LLM response error: {e}")
            # Fallback to template
            best_flight = flights[0]
            return f"I found {len(flights)} flights. The best option is {best_flight['airline']} at {best_flight['departure_time']} for ₹{best_flight['price']:,}, {best_flight['duration']} duration."
    
    def _format_flights_for_llm(self, flights: list) -> str:
        """Format flight data for LLM"""
        lines = []
        for i, flight in enumerate(flights[:3], 1):
            stops_text = 'non-stop' if flight['direct'] else f"{flight['stops']} stop(s)"
            lines.append(
                f"{i}. {flight['airline']} {flight['flight_number']}: "
                f"Departs {flight['departure_time']}, "
                f"arrives {flight['arrival_time']}, "
                f"₹{flight['price']:,}, "
                f"{flight['duration']}, "
                f"{stops_text}"
            )
        return "\n".join(lines)
    
    def _build_error_response(self, result: Dict[str, Any]) -> str:
        """Build error response"""
        return result.get("message", "I encountered an error. Please try again.")
