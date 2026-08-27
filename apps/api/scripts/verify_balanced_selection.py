"""Compare balanced selection on generic and preference-driven Dubai trips."""

from __future__ import annotations

import json
import sys

from app.api.deps import get_trip_planner_agent_service
from app.itinerary.catalog import build_grounded_catalog
from app.itinerary.diversity.geography import cluster_attractions, region_for_attraction
from app.itinerary.diversity.quality import assess_trip_diversity
from app.itinerary.diversity.significance import (
    ExperienceTheme,
    classify_experience_theme,
)
from app.itinerary.from_state import build_itinerary_context_from_state
from app.itinerary.quality import filter_catalog_quality
from app.itinerary.reference.fusion import is_landmark_tier


def _run(message: str) -> dict:
    service = get_trip_planner_agent_service()
    result = service.start(message)
    ctx = build_itinerary_context_from_state(result.state)
    if ctx is None or not result.itinerary_build_result or not result.itinerary_build_result.itinerary:
        return {"error": "no itinerary", "message": message}

    catalog = build_grounded_catalog(ctx)
    filtered, _ = filter_catalog_quality(catalog)
    it = result.itinerary_build_result.itinerary
    candidate = result.itinerary_build_result.candidate

    days_out = []
    landmark_count = 0
    themes: set[str] = set()
    categories: set[str] = set()
    regions: set[int] = set()
    region_list = cluster_attractions(filtered, num_regions=5)

    for day in it.days:
        attractions = []
        for item in day.items:
            if item.category.value != "attraction" or not item.source_id:
                continue
            att = filtered.attractions.get(item.source_id)
            if att is None:
                continue
            theme = classify_experience_theme(att).value
            themes.add(theme)
            categories.add(att.primary_type or "unknown")
            if is_landmark_tier(att):
                landmark_count += 1
            rid = region_for_attraction(item.source_id, region_list)
            if rid is not None:
                regions.add(rid)
            attractions.append(
                {
                    "title": item.title,
                    "theme": theme,
                    "tier": att.significance_tier.value,
                }
            )
        restaurant = next(
            (i.title for i in day.items if i.category.value == "restaurant"),
            "",
        )
        days_out.append(
            {
                "day": day.day_number,
                "day_theme": day.day_theme,
                "subtitle": day.theme_subtitle,
                "attractions": attractions,
                "restaurant": restaurant,
            }
        )

    metrics = assess_trip_diversity(candidate, it, filtered)
    return {
        "message": message,
        "landmark_count": landmark_count,
        "unique_regions": len(regions),
        "unique_categories": len(categories),
        "unique_themes": len(themes),
        "themes": sorted(themes),
        "repeated_source_ids": metrics.repeated_source_ids,
        "days": days_out,
    }


def main() -> int:
    scenarios = [
        "Plan a 5-day trip to Dubai for 2 people under 150000 INR from Mumbai.",
        "Plan a 5-day Dubai trip focused on heritage, local culture, and food.",
        "Plan a 5-day Dubai trip focused on modern attractions and waterfront experiences.",
    ]
    results = [_run(msg) for msg in scenarios]
    print(json.dumps(results, indent=2))

    service = get_trip_planner_agent_service()
    base = service.start(scenarios[0])
    thread_id = base.thread_id
    mods = [
        "Make day 2 more relaxed.",
        "Find a cheaper dinner on day 3.",
        "Make the trip more budget friendly.",
        "Add more culture and less shopping.",
    ]
    print("\nMODIFICATIONS:")
    for mod in mods:
        mod_result = service.resume(thread_id, mod, operation_type="modification")
        changed = mod_result.status.value == "complete"
        print(f"  {mod} -> {mod_result.status.value} changed={changed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
