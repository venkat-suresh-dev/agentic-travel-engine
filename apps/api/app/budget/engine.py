"""Deterministic budget calculation engine."""

from __future__ import annotations

from decimal import Decimal

from mcp_tools.currency.schemas import quantize_money

from app.budget.exceptions import BudgetValidationError
from app.budget.schemas import (
    BudgetCategory,
    BudgetInputs,
    BudgetResult,
    CategoryInput,
    CategoryTotal,
    PriceDataKind,
)

_CATEGORY_ORDER: tuple[BudgetCategory, ...] = (
    BudgetCategory.FLIGHT,
    BudgetCategory.HOTEL,
    BudgetCategory.FOOD,
    BudgetCategory.ACTIVITY,
    BudgetCategory.TRANSPORT,
    BudgetCategory.OTHER,
)


class BudgetEngine:
    """Authoritative deterministic budget arithmetic. No LLM involvement."""

    def calculate(self, inputs: BudgetInputs) -> BudgetResult:
        if inputs.travelers < 1:
            raise BudgetValidationError("travelers must be at least 1")

        currency = inputs.budget_currency.upper()
        category_map = self._index_categories(inputs.categories)
        totals: list[CategoryTotal] = []
        unavailable: list[BudgetCategory] = []
        running_total = Decimal("0")

        for category in _CATEGORY_ORDER:
            category_input = category_map.get(category)
            if category_input is None:
                continue
            total = self._resolve_category_total(category_input, currency)
            totals.append(total)
            if total.data_kind == PriceDataKind.UNAVAILABLE:
                unavailable.append(category)
                continue
            if total.included_in_total and total.amount is not None:
                running_total += total.amount

        total_cost = quantize_money(running_total)
        remaining = quantize_money(inputs.budget_amount - total_cost)
        budget_exceeded = total_cost > inputs.budget_amount
        variance = quantize_money(max(Decimal("0"), total_cost - inputs.budget_amount))

        return BudgetResult(
            currency=currency,
            budget_amount=quantize_money(inputs.budget_amount),
            flight_cost=self._amount_for(totals, BudgetCategory.FLIGHT),
            hotel_cost=self._amount_for(totals, BudgetCategory.HOTEL),
            food_cost=self._amount_for(totals, BudgetCategory.FOOD),
            activity_cost=self._amount_for(totals, BudgetCategory.ACTIVITY),
            transport_cost=self._amount_for(totals, BudgetCategory.TRANSPORT),
            other_cost=self._amount_for(totals, BudgetCategory.OTHER),
            total_cost=total_cost,
            remaining=remaining,
            budget_exceeded=budget_exceeded,
            variance=variance,
            categories=totals,
            unavailable_categories=unavailable,
        )

    def _index_categories(
        self,
        categories: list[CategoryInput],
    ) -> dict[BudgetCategory, CategoryInput]:
        indexed: dict[BudgetCategory, CategoryInput] = {}
        for item in categories:
            indexed[item.category] = item
        return indexed

    def _resolve_category_total(
        self,
        category_input: CategoryInput,
        currency: str,
    ) -> CategoryTotal:
        if category_input.data_kind == PriceDataKind.UNAVAILABLE:
            return CategoryTotal(
                category=category_input.category,
                amount=None,
                currency=currency,
                source_amount=category_input.source_amount,
                source_currency=category_input.source_currency,
                is_estimate=category_input.is_estimate,
                basis=category_input.basis,
                assumption=category_input.assumption,
                data_kind=category_input.data_kind,
                source_offer_id=category_input.source_offer_id,
                conversion_note=category_input.conversion_note,
                included_in_total=False,
            )

        if category_input.data_kind == PriceDataKind.FREE:
            return CategoryTotal(
                category=category_input.category,
                amount=quantize_money(Decimal("0")),
                currency=currency,
                source_amount=Decimal("0"),
                source_currency=category_input.source_currency or currency,
                is_estimate=False,
                basis=category_input.basis,
                assumption=category_input.assumption,
                data_kind=category_input.data_kind,
                source_offer_id=category_input.source_offer_id,
                conversion_note=category_input.conversion_note,
                included_in_total=True,
            )

        amount = category_input.budget_amount
        if amount is None:
            return CategoryTotal(
                category=category_input.category,
                amount=None,
                currency=currency,
                source_amount=category_input.source_amount,
                source_currency=category_input.source_currency,
                is_estimate=category_input.is_estimate,
                basis=category_input.basis,
                assumption=category_input.assumption,
                data_kind=PriceDataKind.UNAVAILABLE,
                source_offer_id=category_input.source_offer_id,
                conversion_note=category_input.conversion_note,
                included_in_total=False,
            )

        return CategoryTotal(
            category=category_input.category,
            amount=quantize_money(amount),
            currency=currency,
            source_amount=category_input.source_amount,
            source_currency=category_input.source_currency,
            is_estimate=category_input.is_estimate,
            basis=category_input.basis,
            assumption=category_input.assumption,
            data_kind=category_input.data_kind,
            source_offer_id=category_input.source_offer_id,
            conversion_note=category_input.conversion_note,
            included_in_total=True,
        )

    def _amount_for(
        self,
        totals: list[CategoryTotal],
        category: BudgetCategory,
    ) -> Decimal | None:
        for total in totals:
            if total.category == category:
                return total.amount
        return None
