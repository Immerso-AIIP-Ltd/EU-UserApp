from typing import Optional

import requests
from loguru import logger

from app.core.constants import HeaderKeys, HeaderValues, HTTPStatus

GEO_API_URL = "https://dev-apigateway.erosuniverse.com/api/geo/v1/location"


class GeoService:
    """Service to handle Geo API operations."""

    @staticmethod
    def get_country_code_by_ip(ip_address: str) -> Optional[str]:
        """Fetch country code from Geo API using IP address."""
        if not ip_address:
            return None

        try:
            headers = {
                HeaderKeys.CONTENT_TYPE: HeaderValues.APPLICATION_JSON,
                "x-platform": "web",
                "x-version": "1.0",
                "x-appname": "geo_app",
            }
            params = {"ip_address": ip_address}

            logger.info(f"Fetching location for IP: {ip_address}")
            response = requests.get(
                GEO_API_URL,
                params=params,
                headers=headers,
                timeout=5,
            )

            if response.status_code == HTTPStatus.OK:
                data = response.json()
                # Assuming the response structure based on typical Geo APIs
                # Adjusting based on user request if they provided sample response?
                # User didn't provide sample response, but typically it
                # returns a JSON with country info.
                # I will assumed it returns something like
                # {"data": {"country_code": "IN"}} or directly at root.
                # Let's log the response to be safe and try to retrieve it safely.
                logger.debug(f"Geo API Response: {data}")

                # Handling common patterns.
                # Pattern 1: { "data": { "country_code": "IN" } }
                # Pattern 2: { "country_code": "IN" }

                if "data" in data and isinstance(data["data"], dict):
                    return data["data"].get("country_code") or data["data"].get(
                        "countryCode",
                    )

                return data.get("country_code") or data.get("countryCode")

            logger.error(
                f"Geo API failed with status {response.status_code}: {response.text}",
            )
            return None

        except requests.RequestException as e:
            logger.error(f"Error fetching country code for IP {ip_address}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in GeoService: {e}")
            return None
