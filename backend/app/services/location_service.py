"""
Location Service
Handles reverse geocoding to identify cities from GPS coordinates
using OpenStreetMap (Nominatim) via geopy.
"""

from typing import Optional, Tuple
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from app.models import rates as rates_model

class LocationService:
    def __init__(self):
        # User agent is required by Nominatim policy
        self.geolocator = Nominatim(user_agent="petty_cash_system_v1")

    async def get_city_from_coordinates(self, lat: float, lon: float) -> Optional[str]:
        """
        Get city name from latitude and longitude.
        Returns the city or town name if found.
        """
        try:
            # Get address details
            # addressdetails=True to get raw address dict
            location = self.geolocator.reverse((lat, lon), exactly_one=True, language='en')
            
            if not location:
                return None
            
            address = location.raw.get('address', {})
            
            # Try to find the city in a specific order of preference
            city = (address.get('city') or 
                    address.get('town') or 
                    address.get('village') or 
                    address.get('suburb') or
                    address.get('county'))
            
            return city
            
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"⚠️ Geocoding error: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected geocoding error: {e}")
            return None

    async def find_nearest_business_location(self, detected_city: str) -> Optional[dict]:
        """
        Match detected city with our supported business locations.
        """
        if not detected_city:
            return None
            
        # Get all supported locations using existing logic
        return await rates_model.find_location(detected_city)

# Global instance
location_service = LocationService()
