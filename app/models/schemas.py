"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class ConversationRequest(BaseModel):
    """Request for conversation endpoint"""
    user_id: str
    audio: Optional[str] = None  # Base64 encoded audio
    text: Optional[str] = None   # Direct text input
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "text": "Set an alarm for 6 AM"
            }
        }


class ConversationResponse(BaseModel):
    """Response from conversation endpoint"""
    success: bool
    text_response: str
    audio_response: Optional[str] = None  # Base64 encoded audio
    intent: str
    confidence: float
    data: Optional[Dict[str, Any]] = None


class IntentType(str, Enum):
    """Supported intent types"""
    SET_ALARM = "set_alarm"
    DELETE_ALARM = "delete_alarm"
    SEARCH_FLIGHTS = "search_flights"
    BOOK_FLIGHT = "book_flight"
    GET_WEATHER = "get_weather"
    SEND_MESSAGE = "send_message"
    UNKNOWN = "unknown"


class Intent(BaseModel):
    """Parsed intent from user input"""
    intent: IntentType
    slots: Dict[str, Any] = Field(default_factory=dict)
    confidence: float
    original_text: str


class UserPreferences(BaseModel):
    """User preferences for personalization"""
    user_id: str
    timezone: str = "UTC"
    alarm_tone: str = "default"
    usual_wakeup: Optional[str] = None
    airline_pref: Optional[str] = None
    max_price: Optional[int] = None
    seat_pref: Optional[str] = None
    flight_type: str = "any"  # direct, any
    

class AlarmCreate(BaseModel):
    """Create alarm request"""
    user_id: str
    alarm_time: datetime
    repeat: bool = False
    label: Optional[str] = None
    tone: Optional[str] = None


class AlarmResponse(BaseModel):
    """Alarm response"""
    id: str
    user_id: str
    alarm_time: datetime
    repeat: bool
    label: Optional[str] = None
    active: bool = True
    created_at: datetime


class FlightSearchRequest(BaseModel):
    """Flight search request"""
    user_id: str
    source: str
    destination: str
    date: str  # YYYY-MM-DD
    time_window: Optional[str] = None  # morning, afternoon, evening, night
    max_results: int = 5


class FlightResult(BaseModel):
    """Single flight result"""
    airline: str
    flight_number: str
    departure_time: str
    arrival_time: str
    duration: str
    price: float
    currency: str = "INR"
    direct: bool
    stops: int = 0


class FlightSearchResponse(BaseModel):
    """Flight search response"""
    success: bool
    flights: List[FlightResult]
    count: int
