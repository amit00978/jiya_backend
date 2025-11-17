"""
Intent Parser - Detects user intent and extracts entities
Uses rule-based matching with LLM fallback
"""
import re
import logging
from typing import Dict, Any, Optional
from openai import AsyncOpenAI

from app.core.config import settings
from app.models.schemas import Intent, IntentType

logger = logging.getLogger(__name__)


class IntentParser:
    """
    Parses user input to detect intent and extract slots
    
    Strategy:
    1. Rule-based pattern matching (fast, cheap)
    2. LLM fallback for complex queries (accurate)
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.intent_patterns = self._load_intent_patterns()
    
    def _load_intent_patterns(self) -> Dict[IntentType, list]:
        """Load rule-based patterns for each intent"""
        return {
            IntentType.SET_ALARM: [
                r"set (?:an? )?alarm (?:for|at) (\d{1,2}(?::\d{2})?\s*(?:am|pm)?)",
                r"wake me (?:up )?(?:at|by) (\d{1,2}(?::\d{2})?\s*(?:am|pm)?)",
                r"remind me (?:at|by) (\d{1,2}(?::\d{2})?\s*(?:am|pm)?)",
            ],
            IntentType.DELETE_ALARM: [
                r"delete (?:the )?alarm",
                r"cancel (?:the )?alarm",
                r"remove (?:the )?alarm",
            ],
            IntentType.SEARCH_FLIGHTS: [
                r"(?:find|search|show|get).{0,30}flights?",
                r"flights?.{0,30}(?:from|to)",
                r"(?:book|need).{0,30}(?:flight|ticket)",
            ],
            IntentType.GET_WEATHER: [
                r"(?:what'?s|how'?s) (?:the )?weather",
                r"weather (?:in|for|at)",
                r"temperature (?:in|for|at)",
            ],
        }
    
    async def parse(self, text: str) -> Intent:
        """
        Parse user input to extract intent and slots
        
        Args:
            text: User input text
            
        Returns:
            Intent object with detected intent, slots, and confidence
        """
        text_lower = text.lower().strip()
        
        # Try rule-based matching first
        rule_based_intent = self._rule_based_parse(text_lower)
        if rule_based_intent and rule_based_intent.confidence > 0.8:
            logger.info(f"✅ Rule-based match: {rule_based_intent.intent}")
            return rule_based_intent
        
        # Fallback to LLM for complex queries
        logger.info("🤖 Using LLM for intent parsing")
        llm_intent = await self._llm_parse(text)
        
        return llm_intent
    
    def _rule_based_parse(self, text: str) -> Optional[Intent]:
        """
        Rule-based intent detection using regex patterns
        
        Args:
            text: User input (lowercase)
            
        Returns:
            Intent or None if no match
        """
        for intent_type, patterns in self.intent_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    slots = self._extract_slots_from_pattern(text, intent_type, match)
                    return Intent(
                        intent=intent_type,
                        slots=slots,
                        confidence=0.9,
                        original_text=text
                    )
        
        return None
    
    def _extract_slots_from_pattern(
        self,
        text: str,
        intent: IntentType,
        match: re.Match
    ) -> Dict[str, Any]:
        """Extract slot values based on intent type"""
        slots = {}
        
        if intent == IntentType.SET_ALARM:
            # Extract time
            if match.groups():
                slots["time"] = match.group(1)
        
        elif intent == IntentType.SEARCH_FLIGHTS:
            # Extract locations and dates
            slots.update(self._extract_flight_slots(text))
        
        return slots
    
    def _extract_flight_slots(self, text: str) -> Dict[str, Any]:
        """Extract flight-specific slots"""
        slots = {}
        
        # Extract source and destination
        from_match = re.search(r"from\s+([a-z\s]+?)(?:\s+to|\s+for|\s+on|$)", text, re.IGNORECASE)
        to_match = re.search(r"to\s+([a-z\s]+?)(?:\s+on|\s+for|$)", text, re.IGNORECASE)
        
        if from_match:
            slots["source"] = from_match.group(1).strip()
        if to_match:
            slots["destination"] = to_match.group(1).strip()
        
        # Extract date
        date_match = re.search(
            r"(?:on\s+)?(\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4})",
            text,
            re.IGNORECASE
        )
        if date_match:
            slots["date"] = date_match.group(1)
        
        # Extract time window
        if "morning" in text:
            slots["time_window"] = "morning"
        elif "afternoon" in text:
            slots["time_window"] = "afternoon"
        elif "evening" in text:
            slots["time_window"] = "evening"
        elif "night" in text:
            slots["time_window"] = "night"
        
        return slots
    
    async def _llm_parse(self, text: str) -> Intent:
        """
        Use LLM to parse complex queries
        
        Args:
            text: User input
            
        Returns:
            Intent parsed by LLM
        """
        prompt = f"""You are an intent parser for a voice assistant. Analyze the user's request and extract:
1. Intent (one of: set_alarm, delete_alarm, search_flights, book_flight, get_weather, send_message, unknown)
2. Slots (key-value pairs of entities)

User request: "{text}"

Respond in JSON format:
{{
    "intent": "intent_name",
    "slots": {{"key": "value"}},
    "confidence": 0.95
}}"""

        try:
            response = await self.client.chat.completions.create(
                model=settings.DEFAULT_LLM_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert intent parser. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            # Map string to IntentType
            intent_str = result.get("intent", "unknown")
            try:
                intent_type = IntentType(intent_str)
            except ValueError:
                intent_type = IntentType.UNKNOWN
            
            return Intent(
                intent=intent_type,
                slots=result.get("slots", {}),
                confidence=result.get("confidence", 0.7),
                original_text=text
            )
            
        except Exception as e:
            logger.error(f"❌ LLM parsing error: {e}")
            return Intent(
                intent=IntentType.UNKNOWN,
                slots={},
                confidence=0.0,
                original_text=text
            )
