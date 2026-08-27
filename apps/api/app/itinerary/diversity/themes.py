"""Day theme derivation from grounded candidates."""

from __future__ import annotations

from dataclasses import dataclass

from app.itinerary.catalog import GroundedCatalog

CATEGORY_THEMES: dict[str, tuple[str, str]] = {
    "museum": ("Culture", "Museums & galleries"),
    "art_gallery": ("Culture", "Art & exhibitions"),
    "historical_landmark": ("Heritage", "Landmarks & history"),
    "place_of_worship": ("Heritage", "Sacred sites & tradition"),
    "park": ("Outdoors", "Parks & open air"),
    "zoo": ("Family", "Wildlife & nature"),
    "amusement_park": ("Family", "Thrills & entertainment"),
    "shopping_mall": ("Shopping", "Markets & retail"),
    "tourist_attraction": ("Highlights", "Iconic sights"),
}


@dataclass(frozen=True, slots=True)
class DayTheme:
    title: str
    subtitle: str


def derive_day_theme(
    attraction_ids: list[str],
    catalog: GroundedCatalog,
    *,
    region_label: str | None = None,
    used_titles: set[str] | None = None,
) -> DayTheme:
    """Derive a day theme from selected attraction categories.

    Prefers experience identity (Heritage, Culture, Outdoors) over repeating
    geographic bucket labels.
    """
    taken = used_titles or set()
    if not attraction_ids:
        if region_label:
            return DayTheme(
                title=_unused_or_same(_title_case(region_label), taken),
                subtitle="Unscheduled day",
            )
        return DayTheme(title=_unused_or_same("Leisure", taken), subtitle="Open day")

    theme_counts: dict[str, int] = {}
    subtitle_parts: list[str] = []
    for attraction_id in attraction_ids:
        attraction = catalog.attractions.get(attraction_id)
        if attraction is None:
            continue
        primary = attraction.primary_type or "tourist_attraction"
        theme_pair = CATEGORY_THEMES.get(primary, ("Highlights", "Local sights"))
        theme_counts[theme_pair[0]] = theme_counts.get(theme_pair[0], 0) + 1
        if theme_pair[1] not in subtitle_parts:
            subtitle_parts.append(theme_pair[1])

    ranked = sorted(theme_counts, key=lambda key: theme_counts[key], reverse=True)
    title = next((name for name in ranked if name not in taken), None)
    if title is None:
        regional = _title_case(region_label) if region_label else None
        if regional and regional not in taken:
            title = regional
        elif ranked:
            title = ranked[0]
        else:
            title = "Leisure"

    subtitle = " & ".join(subtitle_parts[:2]) if subtitle_parts else "Local exploration"
    return DayTheme(title=title, subtitle=subtitle)


def _title_case(value: str) -> str:
    return " ".join(part.capitalize() for part in value.replace("_", " ").split())


def _unused_or_same(title: str, taken: set[str]) -> str:
    if title not in taken:
        return title
    fallback = "Leisure"
    return fallback if fallback not in taken else title
