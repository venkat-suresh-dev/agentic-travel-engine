"""Provider-independent currency conversion schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

MONEY_SCALE = Decimal("0.01")
ROUNDING_POLICY = ROUND_HALF_UP

REFERENCE_RATE_DISCLAIMER = (
    "Reference/planning exchange rate only. This is not a payment authorization, "
    "bank settlement, or card-charge rate guarantee."
)


class CurrencyDataStatus(StrEnum):
    LIVE = "live"
    CACHED = "cached"
    UNAVAILABLE = "unavailable"


class RateKind(StrEnum):
    REFERENCE = "reference"


def quantize_money(amount: Decimal) -> Decimal:
    """Apply the canonical money rounding policy for converted amounts."""
    return amount.quantize(MONEY_SCALE, rounding=ROUNDING_POLICY)


class CurrencyConversionRequest(BaseModel):
    """Narrow currency conversion tool request contract."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    base_currency: str = Field(min_length=3, max_length=3)
    quote_currency: str = Field(min_length=3, max_length=3)
    amount: Decimal = Field(gt=0)
    rate_date: date | None = None

    @field_validator("base_currency", "quote_currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized.isalpha():
            msg = f"invalid currency code: {value}"
            raise ValueError(msg)
        return normalized


class CurrencyConversionResult(BaseModel):
    """Normalized currency conversion response with provenance metadata."""

    model_config = ConfigDict(extra="forbid")

    base_currency: str
    quote_currency: str
    rate: Decimal
    input_amount: Decimal
    converted_amount: Decimal
    rate_date: date
    retrieved_at: datetime
    source: str
    data_status: CurrencyDataStatus
    rate_kind: RateKind = RateKind.REFERENCE
    source_context: str | None = None
    source_offer_id: str | None = None
    error_message: str | None = None
    disclaimer: str = REFERENCE_RATE_DISCLAIMER

    @classmethod
    def unavailable(
        cls,
        *,
        base_currency: str,
        quote_currency: str,
        input_amount: Decimal,
        source: str,
        retrieved_at: datetime,
        error_message: str,
    ) -> CurrencyConversionResult:
        return cls(
            base_currency=base_currency,
            quote_currency=quote_currency,
            rate=Decimal("0"),
            input_amount=input_amount,
            converted_amount=Decimal("0"),
            rate_date=retrieved_at.date(),
            retrieved_at=retrieved_at,
            source=source,
            data_status=CurrencyDataStatus.UNAVAILABLE,
            error_message=error_message,
        )


class CurrencyToolMetadata(BaseModel):
    """Observability metadata for a currency tool invocation."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    provider: str
    request_args: dict[str, object]
    response_status: CurrencyDataStatus
    latency_ms: float
    retrieved_at: datetime
    cache_status: str
