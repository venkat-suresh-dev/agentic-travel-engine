"use client";

import type { Itinerary, ItineraryItem } from "@agentic-travel-engine/shared-types";
import dynamic from "next/dynamic";
import { MapPin } from "lucide-react";
import { useMemo } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface MapMarker {
  id: string;
  itemId: string;
  dayNumber: number;
  title: string;
  category: ItineraryItem["category"];
  latitude: number;
  longitude: number;
}

const ItineraryMapCanvas = dynamic(
  () =>
    import("@/components/planner/itinerary-map-canvas").then(
      (mod) => mod.ItineraryMapCanvas,
    ),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full min-h-[180px] items-center justify-center rounded-lg bg-[var(--surface-elevated)] text-xs text-[var(--foreground-muted)]">
        Loading map…
      </div>
    ),
  },
);

export interface MapLeg {
  id: string;
  from: [number, number];
  to: [number, number];
}

export function extractMapMarkers(
  itinerary: Itinerary,
  dayNumber?: number,
): MapMarker[] {
  const markers: MapMarker[] = [];
  const days =
    dayNumber !== undefined
      ? itinerary.days.filter((day) => day.day_number === dayNumber)
      : itinerary.days;

  for (const day of days) {
    for (const item of day.items) {
      if (item.latitude === null || item.longitude === null) {
        continue;
      }
      markers.push({
        id: `${day.day_number}-${item.item_id}`,
        itemId: item.item_id,
        dayNumber: day.day_number,
        title: item.title,
        category: item.category,
        latitude: item.latitude,
        longitude: item.longitude,
      });
    }
  }

  for (const item of itinerary.infrastructure_items) {
    if (item.latitude === null || item.longitude === null) {
      continue;
    }
    if (/check-out/i.test(item.title)) {
      continue;
    }
    if (item.category !== "hotel") {
      if (dayNumber !== undefined && item.day_number !== dayNumber) {
        continue;
      }
    } else if (dayNumber !== undefined) {
      const dayPoints = markers.filter((marker) => marker.dayNumber === dayNumber);
      if (dayPoints.length > 0) {
        const nearby = dayPoints.some((marker) => {
          const latDelta = Math.abs(marker.latitude - item.latitude!);
          const lngDelta = Math.abs(marker.longitude - item.longitude!);
          return latDelta < 0.18 && lngDelta < 0.18;
        });
        if (!nearby) {
          continue;
        }
      }
    }
    markers.push({
      id: `infra-${item.item_id}`,
      itemId: item.item_id,
      dayNumber: item.day_number ?? 0,
      title: item.title,
      category: item.category,
      latitude: item.latitude,
      longitude: item.longitude,
    });
  }

  return markers;
}

export function extractMapLegs(itinerary: Itinerary, dayNumber: number): MapLeg[] {
  const day = itinerary.days.find((entry) => entry.day_number === dayNumber);
  if (!day) {
    return [];
  }
  const itemsById = new Map(day.items.map((item) => [item.item_id, item]));
  const legs: MapLeg[] = [];
  for (const leg of day.travel_legs) {
    const from = itemsById.get(leg.from_item_id);
    const to = itemsById.get(leg.to_item_id);
    if (
      from?.latitude == null ||
      from.longitude == null ||
      to?.latitude == null ||
      to.longitude == null
    ) {
      continue;
    }
    legs.push({
      id: leg.leg_id,
      from: [from.latitude, from.longitude],
      to: [to.latitude, to.longitude],
    });
  }
  return legs;
}

interface ItineraryMapProps {
  itinerary: Itinerary;
  selectedDay: number;
  selectedItemId?: string | null;
  onSelectItem?: (itemId: string) => void;
  className?: string;
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
}

export function ItineraryMap({
  itinerary,
  selectedDay,
  selectedItemId,
  onSelectItem,
  className,
  collapsed = false,
  onToggleCollapsed,
}: ItineraryMapProps) {
  const markers = useMemo(
    () => extractMapMarkers(itinerary, selectedDay),
    [itinerary, selectedDay],
  );
  const legs = useMemo(
    () => extractMapLegs(itinerary, selectedDay),
    [itinerary, selectedDay],
  );

  if (markers.length === 0) {
    return null;
  }

  if (collapsed) {
    return (
      <div className={cn("flex justify-end", className)}>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          className="h-8 rounded-lg px-3 text-xs lg:hidden"
          onClick={onToggleCollapsed}
        >
          <MapPin className="h-3.5 w-3.5" />
          Show map
        </Button>
      </div>
    );
  }

  return (
    <section
      className={cn("min-w-0", className)}
      aria-label="Itinerary map"
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-xs text-[var(--foreground-muted)]">Map</p>
        {onToggleCollapsed ? (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs lg:hidden"
            onClick={onToggleCollapsed}
          >
            Hide
          </Button>
        ) : null}
      </div>
      <div className="h-[200px] overflow-hidden rounded-xl bg-[var(--surface)] shadow-[var(--shadow-soft)] lg:h-[240px]">
        <ItineraryMapCanvas
          markers={markers}
          legs={legs}
          selectedItemId={selectedItemId}
          onSelectItem={onSelectItem}
        />
      </div>
    </section>
  );
}
