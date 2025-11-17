"""
Flights Service - Search and book flights using external APIs
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class FlightsService:
    """
    Service for searching flights using Skyscanner/Amadeus API
    """
    
    def __init__(self):
        self.skyscanner_api_key = settings.SKYSCANNER_API_KEY
        self.amadeus_api_key = settings.AMADEUS_API_KEY
        self.amadeus_api_secret = settings.AMADEUS_API_SECRET
    
    async def search_flights(
        self,
        source: str,
        destination: str,
        date: str,
        time_window: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search for flights
        
        Args:
            source: Source city
            destination: Destination city
            date: Travel date (YYYY-MM-DD or natural language)
            time_window: morning, afternoon, evening, night
            preferences: User preferences (airline, price, etc.)
            
        Returns:
            Dictionary with flight results
        """
        try:
            # Parse date
            parsed_date = self._parse_date(date)
            
            if not parsed_date:
                return {
                    "status": "error",
                    "message": "I couldn't understand that date format."
                }
            
            # Get IATA codes for cities
            source_code = await self._get_airport_code(source)
            dest_code = await self._get_airport_code(destination)
            
            # Search flights
            flights = await self._search_flights_api(
                source_code,
                dest_code,
                parsed_date,
                time_window,
                preferences or {}
            )
            
            return {
                "status": "success",
                "flights": flights,
                "count": len(flights),
                "source": source,
                "destination": destination,
                "date": parsed_date
            }
            
        except Exception as e:
            logger.error(f"❌ Flight search error: {e}", exc_info=True)
            return {
                "status": "error",
                "message": "Failed to search flights. Please try again."
            }
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """
        Parse date string to YYYY-MM-DD format
        
        Args:
            date_str: Date string (e.g., "25 Dec 2025", "2025-12-25")
            
        Returns:
            Date in YYYY-MM-DD format
        """
        try:
            from dateutil import parser
            parsed = parser.parse(date_str)
            return parsed.strftime("%Y-%m-%d")
        except Exception as e:
            logger.error(f"❌ Date parsing error: {e}")
            return None
    
    async def _get_airport_code(self, city: str) -> str:
        """
        Get IATA airport code for city
        
        Args:
            city: City name
            
        Returns:
            IATA code (e.g., DEL for Delhi)
        """
        # Simplified mapping - in production, use a proper API or database
        city_codes = {
            "delhi": "DEL",
            "bangalore": "BLR",
            "bengaluru": "BLR",
            "mumbai": "BOM",
            "chennai": "MAA",
            "kolkata": "CCU",
            "hyderabad": "HYD",
            "pune": "PNQ",
            "goa": "GOI",
            "jaipur": "JAI",
            "new york": "JFK",
            "london": "LHR",
            "dubai": "DXB",
            "singapore": "SIN"
        }
        
        return city_codes.get(city.lower(), city[:3].upper())
    
    async def _search_flights_api(
        self,
        source: str,
        destination: str,
        date: str,
        time_window: Optional[str],
        preferences: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Call flight search API (Skyscanner or Amadeus)
        
        This is a mock implementation. In production, integrate with:
        - Skyscanner Flight Search API
        - Amadeus Flight Offers Search API
        """
        
        # Mock flight data for demonstration
        mock_flights = self._get_mock_flights(
            source, destination, date, time_window, preferences
        )
        
        # In production, uncomment and use real API:
        # if self.amadeus_api_key:
        #     return await self._search_amadeus(source, destination, date)
        # elif self.skyscanner_api_key:
        #     return await self._search_skyscanner(source, destination, date)
        
        return mock_flights
    
    def _get_mock_flights(
        self,
        source: str,
        destination: str,
        date: str,
        time_window: Optional[str],
        preferences: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate mock flight data"""
        
        flights = [
            {
                "airline": "IndiGo",
                "flight_number": "6E-2045",
                "departure_time": "17:25",
                "arrival_time": "19:55",
                "duration": "2h 30m",
                "price": 7200,
                "currency": "INR",
                "direct": True,
                "stops": 0
            },
            {
                "airline": "Air India",
                "flight_number": "AI-512",
                "departure_time": "18:15",
                "arrival_time": "20:50",
                "duration": "2h 35m",
                "price": 8500,
                "currency": "INR",
                "direct": True,
                "stops": 0
            },
            {
                "airline": "SpiceJet",
                "flight_number": "SG-134",
                "departure_time": "19:00",
                "arrival_time": "21:35",
                "duration": "2h 35m",
                "price": 6800,
                "currency": "INR",
                "direct": True,
                "stops": 0
            }
        ]
        
        # Filter by time window
        if time_window:
            flights = self._filter_by_time_window(flights, time_window)
        
        # Filter by preferences
        if preferences.get("airline_pref"):
            flights = [f for f in flights if f["airline"] == preferences["airline_pref"]]
        
        if preferences.get("max_price"):
            flights = [f for f in flights if f["price"] <= preferences["max_price"]]
        
        if preferences.get("flight_type") == "direct":
            flights = [f for f in flights if f["direct"]]
        
        # Sort by price
        flights.sort(key=lambda x: x["price"])
        
        return flights[:5]
    
    def _filter_by_time_window(
        self,
        flights: List[Dict[str, Any]],
        time_window: str
    ) -> List[Dict[str, Any]]:
        """Filter flights by time of day"""
        time_ranges = {
            "morning": (6, 12),
            "afternoon": (12, 16),
            "evening": (16, 22),
            "night": (22, 6)
        }
        
        start_hour, end_hour = time_ranges.get(time_window.lower(), (0, 24))
        
        filtered = []
        for flight in flights:
            hour = int(flight["departure_time"].split(":")[0])
            if start_hour <= hour < end_hour:
                filtered.append(flight)
        
        return filtered
    
    async def _search_amadeus(
        self,
        source: str,
        destination: str,
        date: str
    ) -> List[Dict[str, Any]]:
        """
        Search flights using Amadeus API
        
        Documentation: https://developers.amadeus.com/self-service/category/air/api-doc/flight-offers-search
        """
        # Get access token
        token = await self._get_amadeus_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://test.api.amadeus.com/v2/shopping/flight-offers",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "originLocationCode": source,
                    "destinationLocationCode": destination,
                    "departureDate": date,
                    "adults": 1,
                    "max": 5
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_amadeus_response(data)
            else:
                logger.error(f"Amadeus API error: {response.status_code}")
                return []
    
    async def _get_amadeus_token(self) -> str:
        """Get Amadeus API access token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://test.api.amadeus.com/v1/security/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.amadeus_api_key,
                    "client_secret": self.amadeus_api_secret
                }
            )
            return response.json()["access_token"]
    
    def _parse_amadeus_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Amadeus API response"""
        flights = []
        for offer in data.get("data", []):
            # Parse flight details
            # Implementation details...
            pass
        return flights
