"""Static city code resolver for common destinations."""

from __future__ import annotations

import re

from mcp_tools.hotels.exceptions import HotelValidationError

_IATA_PATTERN = re.compile(r"^[A-Za-z]{3}$")

_COMMON_CITY_CODES: dict[str, str] = {
    "mumbai": "BOM",
    "bombay": "BOM",
    "dubai": "DXB",
    "delhi": "DEL",
    "new delhi": "DEL",
    "bangalore": "BLR",
    "bengaluru": "BLR",
    "chennai": "MAA",
    "kolkata": "CCU",
    "hyderabad": "HYD",
    "pune": "PNQ",
    "goa": "GOI",
    "london": "LON",
    "paris": "PAR",
    "new york": "NYC",
    "singapore": "SIN",
    "bangkok": "BKK",
    "tokyo": "TYO",
    "sydney": "SYD",
    "melbourne": "MEL",
    "san francisco": "SFO",
    "los angeles": "LAX",
    "abu dhabi": "AUH",
    "doha": "DOH",
}


class StaticCityCodeResolver:
    """Resolve common city names to IATA city codes without external APIs."""

    def resolve(self, location: str) -> str:
        normalized = location.strip()
        if not normalized:
            raise HotelValidationError("location is required for city resolution")
        if _IATA_PATTERN.fullmatch(normalized):
            return normalized.upper()
        key = normalized.lower()
        if key in _COMMON_CITY_CODES:
            return _COMMON_CITY_CODES[key]
        for alias, code in _COMMON_CITY_CODES.items():
            if alias in key or key in alias:
                return code
        msg = f"unable to resolve city code for location: {location}"
        raise HotelValidationError(msg)
