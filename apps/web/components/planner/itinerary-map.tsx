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
    if (dayNumber !== undefined && item.day_number !== dayNumber) {
      continue;
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
      className={cn(
        "overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)]",
        className,
      )}
      aria-label="Itinerary map"
    >
      <div className="flex items-center justify-between gap-2 border-b border-[var(--border)] px-3 py-2">
        <div>
          <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
            Map
          </p>
          <p className="text-xs text-[var(--foreground-secondary)]">
            Day {selectedDay} · {markers.length} location
            {markers.length === 1 ? "" : "s"}
          </p>
        </div>
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
      <div className="h-[180px] lg:h-[200px]">
        <ItineraryMapCanvas
          markers={markers}
          selectedItemId={selectedItemId}
          onSelectItem={onSelectItem}
        />
      </div>
    </section>
  );
}
