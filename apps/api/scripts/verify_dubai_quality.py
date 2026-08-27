"""Full verification pass for Dubai demo quality."""

from __future__ import annotations

import json
import sys
from collections import Counter

from app.api.deps import get_trip_planner_agent_service
from app.itinerary.builder import ItineraryBuilder
from app.itinerary.catalog import build_grounded_catalog
from app.itinerary.composer.fake import FakeItineraryComposer
from app.itinerary.diversity.geography import cluster_attractions, region_for_attraction
from app.itinerary.diversity.quality import assess_trip_diversity
from app.itinerary.from_state import build_itinerary_context_from_state
from app.itinerary.quality import filter_catalog_quality, score_attraction
from app.itinerary.reference.fusion import is_landmark_tier


def _composer_name(service) -> str:
    graph = service._graph
    # Inspect build_itinerary node binding
    return type(service._graph). __name__


def main() -> int:
    service = get_trip_planner_agent_service()
    composer = service._graph
    print("COMPOSER_PATH:", type(FakeItineraryComposer()).__name__)
    print("SERVICE_USES:", "FakeItineraryComposer (explicit in deps.py)")

    message = "Plan a 5-day trip to Dubai for 2 people under 150000 INR from Mumbai."
    result = service.start(message)
    thread_id = result.thread_id
    print("STATUS:", result.status.value)
    print("COMPOSER_PROVIDER:", result.itinerary_build_result.composer_provider if result.itinerary_build_result else None)

    ctx = build_itinerary_context_from_state(result.state)
    if ctx is None:
        print("ERROR: no context")
        return 1

    raw_catalog = build_grounded_catalog(ctx)
    filtered, qstats = filter_catalog_quality(raw_catalog)
    geoapify_count = sum(
        1 for item in raw_catalog.attractions.values() if item.source == "geoapify"
    )
    reference_count = sum(
        1 for item in raw_catalog.attractions.values() if item.source == "wikipedia"
    )
    landmark_pool = sum(1 for item in raw_catalog.attractions.values() if is_landmark_tier(item))
    print("FUSION_STATS:", json.dumps({
        "geoapify_candidates": geoapify_count,
        "reference_candidates": reference_count,
        "fused_candidates": len(raw_catalog.attractions),
        "landmark_tier_candidates": landmark_pool,
    }))
    print("QUALITY_STATS:", json.dumps({
        "attractions_retrieved": qstats.attractions_retrieved,
        "attractions_rejected_low_quality": qstats.attractions_rejected_low_quality,
        "attractions_rejected_duplicate_name": qstats.attractions_rejected_duplicate_name,
        "attractions_kept": qstats.attractions_kept,
        "landmark_tier_candidates": qstats.landmark_tier_candidates,
        "restaurants_retrieved": qstats.restaurants_retrieved,
        "restaurants_rejected_low_quality": qstats.restaurants_rejected_low_quality,
        "restaurants_kept": qstats.restaurants_kept,
        "rejection_reasons": qstats.rejection_reasons,
    }))

    print("\nTOP_ATTRACTION_CANDIDATES:")
    ranked = sorted(
        raw_catalog.attractions.values(),
        key=lambda a: score_attraction(a),
        reverse=True,
    )
    for attraction in ranked[:15]:
        print(
            f"  score={score_attraction(attraction):.2f} | {attraction.name[:50]} | "
            f"type={attraction.primary_type} | rating={attraction.rating}"
        )

    build = result.itinerary_build_result
    if not build or not build.itinerary:
        print("ERROR: no itinerary")
        return 1

    it = build.itinerary
    attr_sources: list[str] = []
    attr_titles: list[str] = []
    rest_sources: list[str] = []
    rest_titles: list[str] = []
    categories: set[str] = set()
    weak: list[str] = []

    landmark_selected = 0
    print("\nITINERARY:")
    for day in it.days:
        print(f"DAY {day.day_number}: {day.day_theme} | {day.theme_subtitle}")
        for item in day.items:
            if item.category.value == "attraction":
                attr_sources.append(item.source_id or "")
                attr_titles.append(item.title)
                if item.source_id and item.source_id in filtered.attractions:
                    att = filtered.attractions[item.source_id]
                    categories.add(att.primary_type or "unknown")
                    if score_attraction(att) < 0.45:
                        weak.append(item.title)
                    if is_landmark_tier(att):
                        landmark_selected += 1
                    tier = att.significance_tier.value
                    print(f"  A: {item.title} [{tier}]")
                else:
                    print(f"  A: {item.title}")
            elif item.category.value == "restaurant":
                rest_sources.append(item.source_id or "")
                rest_titles.append(item.title)
                print(f"  R: {item.title}")
        print(f"  travel_legs: {len(day.travel_legs)}")

    regions = cluster_attractions(filtered, num_regions=5)
    used_regions: set[int] = set()
    for sid in set(attr_sources):
        if sid in filtered.attractions:
            rid = region_for_attraction(sid, regions)
            if rid is not None:
                used_regions.add(rid)

    metrics = assess_trip_diversity(build.candidate, it, filtered)
    meaningful_per_day = [
        sum(1 for i in d.items if i.category.value == "attraction") for d in it.days
    ]

    print("\nMETRICS:")
    print(f"  unique_attraction_source_ids: {len(set(attr_sources))}")
    print(f"  unique_attraction_titles: {len(set(attr_titles))}")
    print(f"  unique_restaurant_source_ids: {len(set(rest_sources))}")
    print(f"  unique_restaurant_titles: {len(set(rest_titles))}")
    print(f"  unique_regions: {len(used_regions)}")
    print(f"  unique_categories: {len(categories)}")
    print(f"  repeated_source_ids: {metrics.repeated_source_ids}")
    print(f"  repeated_titles: {[t for t in set(attr_titles) if attr_titles.count(t)>1]}")
    print(f"  days_with_2plus: {sum(1 for c in meaningful_per_day if c >= 2)}")
    print(f"  days_with_3plus: {sum(1 for c in meaningful_per_day if c >= 3)}")
    print(f"  avg_meaningful_per_day: {sum(meaningful_per_day)/len(meaningful_per_day):.1f}")
    print(f"  landmark_tier_selected: {landmark_selected}")
    print(f"  weak_selected: {weak}")

    mods = [
        "Make day 2 more relaxed.",
        "Find a cheaper dinner on day 3.",
        "Make the trip more budget friendly.",
        "Add more culture and less shopping.",
        "Change the hotel.",
    ]
    print("\nMODIFICATIONS:")
    for mod in mods:
        mod_result = service.resume(thread_id, mod, operation_type="modification")
        prev_it = build.itinerary
        new_it = mod_result.itinerary_build_result.itinerary if mod_result.itinerary_build_result else None
        changed = False
        if new_it and prev_it:
            prev_ids = {i.source_id for d in prev_it.days for i in d.items if i.source_id}
            new_ids = {i.source_id for d in new_it.days for i in d.items if i.source_id}
            changed = prev_ids != new_ids or prev_it.budget_total_cost != new_it.budget_total_cost
        print(f"  MOD: {mod}")
        print(f"    status={mod_result.status.value} changed={changed}")
        if mod_result.critic_result:
            print(f"    critic_valid={mod_result.critic_result.valid} warnings={len(mod_result.critic_result.warnings)}")
        failure = mod_result.state.get("modification_failure")
        if failure:
            print(f"    failure={failure.get('message', '')[:120]}")
        if new_it:
            build.itinerary = new_it  # chain modifications

    return 0


if __name__ == "__main__":
    sys.exit(main())
