"""
Flights Router
"""
from fastapi import APIRouter, HTTPException
import logging

from app.models.schemas import FlightSearchRequest
from app.services.flights import FlightsService

logger = logging.getLogger(__name__)

router = APIRouter()
flights_service = FlightsService()


@router.post("/search")
async def search_flights(request: FlightSearchRequest):
    """Search for flights"""
    try:
        result = await flights_service.search_flights(
            source=request.source,
            destination=request.destination,
            date=request.date,
            time_window=request.time_window
        )
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error searching flights: {e}")
        raise HTTPException(status_code=500, detail=str(e))
