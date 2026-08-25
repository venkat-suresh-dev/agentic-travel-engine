"""Static IATA airport code resolver for common destinations."""

from __future__ import annotations

import re

from mcp_tools.flights.exceptions import FlightValidationError

_IATA_PATTERN = re.compile(r"^[A-Za-z]{3}$")

_COMMON_AIRPORT_CODES: dict[str, str] = {
    "mumbai": "BOM",
    "bombay": "BOM",
    "dubai": "DXB",
    "delhi": "DEL",
    "new delhi": "DEL",
    "bangalore": "BLR",
    "bengaluru": "BLR",
    "chennai": "MAA",
    "madras": "MAA",
    "kolkata": "CCU",
    "calcutta": "CCU",
    "hyderabad": "HYD",
    "pune": "PNQ",
    "goa": "GOI",
    "london": "LHR",
    "paris": "CDG",
    "new york": "JFK",
    "nyc": "JFK",
    "singapore": "SIN",
    "bangkok": "BKK",
    "tokyo": "NRT",
    "sydney": "SYD",
    "melbourne": "MEL",
    "san francisco": "SFO",
    "los angeles": "LAX",
    "chicago": "ORD",
    "toronto": "YYZ",
    "vancouver": "YVR",
    "hong kong": "HKG",
    "abu dhabi": "AUH",
    "doha": "DOH",
    "istanbul": "IST",
    "rome": "FCO",
    "barcelona": "BCN",
    "madrid": "MAD",
    "amsterdam": "AMS",
    "frankfurt": "FRA",
    "zurich": "ZRH",
    "cairo": "CAI",
    "johannesburg": "JNB",
    "cape town": "CPT",
    "bali": "DPS",
    "phuket": "HKT",
    "kuala lumpur": "KUL",
    "seoul": "ICN",
    "beijing": "PEK",
    "shanghai": "PVG",
}


class StaticAirportCodeResolver:
    """Resolve common city names to IATA airport codes without external APIs."""

    def resolve(self, location: str) -> str:
        normalized = location.strip()
        if not normalized:
            raise FlightValidationError("location is required for airport resolution")
        if _IATA_PATTERN.fullmatch(normalized):
            return normalized.upper()
        key = normalized.lower()
        if key in _COMMON_AIRPORT_CODES:
            return _COMMON_AIRPORT_CODES[key]
        for alias, code in _COMMON_AIRPORT_CODES.items():
            if alias in key or key in alias:
                return code
        msg = f"unable to resolve airport code for location: {location}"
        raise FlightValidationError(msg)
