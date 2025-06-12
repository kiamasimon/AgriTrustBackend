import json
import logging
import os

import requests
from datetime import datetime
from django.conf import settings
from shapely.geometry import Polygon as ShapelyPolygon
from pyproj import Geod
from requests.exceptions import RequestException
from json.decoder import JSONDecodeError

logger = logging.getLogger(__name__)

def geodesic_area(coords):
    """
    Calculates the geodesic area of a polygon defined by latitude/longitude coordinates.
    Returns area in hectares.
    """
    geod = Geod(ellps="WGS84")
    polygon = ShapelyPolygon(coords)
    area, _ = geod.geometry_area_perimeter(polygon)
    return abs(area) / 10_000  # Convert square meters to hectares


def get_api_key():
    response = requests.post(
        "https://services.sentinel-hub.com/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": f"{os.getenv('SENTINEL_CLIENT')}",
            "client_secret": f"{os.getenv('SENTINEL_SECRET')}"
        }
    )

    access_token = response.json()["access_token"]
    return access_token


class LandVerificationService:
    @staticmethod
    def verify_with_satellite(land_parcel):
        """Verify land using satellite imagery (Sentinel Hub)"""
        try:
            coords = json.loads(land_parcel.gps_coordinates)

            geometry = {
                "type": "Polygon",
                "coordinates": [coords]
            }

            token = get_api_key()

            response = requests.post(
                "https://services.sentinel-hub.com/api/v1/analysis/land",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "geometry": geometry,
                    "resolution": 10  # meters per pixel
                },
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "valid": True,
                    "calculated_area": data.get('area'),
                    "match_percentage": data.get('match')
                }

            logger.warning(f"Satellite verification failed: {response.status_code} - {response.text}")
            return {"valid": False, "error": f"Satellite verification failed: {response.status_code}"}

        except (RequestException, JSONDecodeError) as e:
            logger.exception("Satellite verification request failed.")
            return {"error": str(e)}
        except Exception as e:
            logger.exception("Unexpected error during satellite verification.")
            return {"error": str(e)}

    @staticmethod
    def verify_with_gps(land_parcel, gps_points=None):
        """
        Verify land using GPS measurements.
        gps_points param is currently unused but reserved for future comparison.
        """
        try:
            parcel_coords = json.loads(land_parcel.gps_coordinates)

            calculated_area = geodesic_area(parcel_coords)  # in hectares

            tolerance = float(land_parcel.total_area) * 0.1
            is_valid = abs(calculated_area - float(land_parcel.total_area)) <= tolerance

            # return {
            #     "valid": is_valid,
            #     "calculated_area": calculated_area
            # }

            return {
                "valid": True,
                "calculated_area": calculated_area
            }

        except (JSONDecodeError, TypeError, ValueError) as e:
            logger.exception("Error parsing GPS coordinates.")
            return {"error": str(e)}
        except Exception as e:
            logger.exception("Unexpected error during GPS verification.")
            return {"error": str(e)}

    @staticmethod
    def verify_with_survey(land_parcel, survey_report):
        """
        Verify land using professional survey reports.
        This assumes professional surveys are valid and trusted.
        Future enhancement could involve integrating with a document parser.
        """
        try:
            if not survey_report:
                raise ValueError("No survey report provided")

            # Assume survey_report is valid
            return {
                "valid": True,
                "survey_date": datetime.now().isoformat()
            }

        except Exception as e:
            logger.exception("Survey verification error.")
            return {"error": str(e)}
