"use client";

import type {
  Itinerary,
  ItineraryDay,
  ItineraryItem,
  TravelLeg,
} from "@agentic-travel-engine/shared-types";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Car } from "lucide-react";
import { useMemo, useState } from "react";

import { ProvenanceBadge } from "@/components/planner/provenance-badge";
import {
  formatDuration,
  formatMoney,
  formatTime,
} from "@/lib/planner/format";
import { cn } from "@/lib/utils";

interface ItineraryTimelineProps {
  itinerary: Itinerary;
  affectedDays?: number[];
  changedItemIds?: string[];
  className?: string;
}

function DaySelector({
  days,
  selectedDay,
  affectedDays,
  onSelect,
}: {
  days: Itinerary["days"];
  selectedDay: number;
  affectedDays: number[];
  onSelect: (day: number) => void;
}) {
  return (
    <div
      className="sticky top-0 z-10 -mx-1 border-b border-[var(--border)] bg-[var(--background)]/95 px-1 pb-2 backdrop-blur-sm"
      role="tablist"
      aria-label="Select itinerary day"
    >
      <div className="flex gap-1.5 overflow-x-auto pb-0.5 scrollbar-thin">
        {days.map((day) => {
          const isSelected = day.day_number === selectedDay;
          const isAffected = affectedDays.includes(day.day_number);
          return (
            <button
              key={day.day_number}
              type="button"
              role="tab"
              aria-selected={isSelected}
              className={cn(
                "shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]",
                isSelected
                  ? "bg-[var(--accent)] text-[var(--accent-foreground)]"
                  : "bg-[var(--surface-elevated)] text-[var(--foreground-secondary)] ring-1 ring-[var(--border)] hover:bg-[var(--surface-hover)]",
                isAffected && !isSelected && "ring-[var(--accent)]/40",
              )}
              onClick={() => onSelect(day.day_number)}
            >
              Day {String(day.day_number).padStart(2, "0")}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function TravelLegRow({ leg }: { leg: TravelLeg }) {
  const distanceKm = (leg.distance_meters / 1000).toFixed(1);
  return (
    <div className="flex items-center gap-2 px-3 py-1 text-xs text-[var(--foreground-muted)]">
      <Car className="h-3 w-3 shrink-0" aria-hidden />
      <span>
        {formatDuration(leg.duration_seconds)} · {distanceKm} km ·{" "}
        {leg.travel_mode}
      </span>
    </div>
  );
}

function ActivityRow({
  item,
  leg,
  changed,
  showLocation,
}: {
  item: ItineraryItem;
  leg?: TravelLeg;
  changed: boolean;
  showLocation: boolean;
}) {
  return (
    <>
      {leg ? <TravelLegRow leg={leg} /> : null}
      <motion.li
        layout
        className={cn(
          "grid gap-2 rounded-lg border border-transparent px-3 py-2.5 transition-colors sm:grid-cols-[4.5rem_minmax(0,1fr)_auto]",
          changed
            ? "border-[var(--accent)]/30 bg-[var(--accent)]/5"
            : "hover:bg-[var(--surface-hover)]",
        )}
        data-changed={changed || undefined}
      >
        <div className="text-xs font-medium tabular-nums text-[var(--foreground-muted)]">
          {formatTime(item.start_time)}
        </div>
        <div className="min-w-0">
          <div className="flex flex-wrap items-start gap-x-2 gap-y-0.5">
            <p className="font-medium text-[var(--foreground)]">{item.title}</p>
            <ProvenanceBadge
              dataKind={item.data_status}
              source={item.source}
              sourceId={item.source_id}
              compact
            />
          </div>
          {showLocation && item.location_name ? (
            <p className="mt-0.5 text-xs text-[var(--foreground-muted)]">
              {item.location_name}
            </p>
          ) : null}
          {item.description ? (
            <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-[var(--foreground-secondary)]">
              {item.description}
            </p>
          ) : null}
        </div>
        <div className="flex items-start justify-end sm:flex-col sm:items-end">
          {item.cost.amount ? (
            <span className="text-sm font-medium tabular-nums text-[var(--foreground)]">
              {formatMoney(item.cost.amount, item.cost.currency)}
            </span>
          ) : (
            <span className="text-xs uppercase tracking-wide text-[var(--foreground-muted)]">
              Free
            </span>
          )}
        </div>
      </motion.li>
    </>
  );
}

function DayContent({
  day,
  affectedDays,
  changedItemIds,
}: {
  day: ItineraryDay;
  affectedDays: number[];
  changedItemIds: string[];
}) {
  const reduceMotion = useReducedMotion();
  const isAffected = affectedDays.includes(day.day_number);
  const items = [...day.items].sort((a, b) => a.start_time.localeCompare(b.start_time));
  const legsByTo = new Map(day.travel_legs.map((leg) => [leg.to_item_id, leg]));
  const dayLocation = items[0]?.location_name ?? null;

  return (
    <motion.div
      key={day.day_number}
      initial={reduceMotion ? false : { opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={reduceMotion ? undefined : { opacity: 0, y: -4 }}
      transition={{ duration: 0.2 }}
      role="tabpanel"
      aria-label={`Day ${day.day_number} itinerary`}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2 px-1 pt-3">
        <div>
          <h3 className="font-display text-xl text-[var(--foreground)]">
            Day {String(day.day_number).padStart(2, "0")}
            {dayLocation ? (
              <span className="ml-2 text-base font-normal text-[var(--foreground-secondary)]">
                {dayLocation}
              </span>
            ) : null}
          </h3>
        </div>
        <div className="flex items-center gap-3">
          {isAffected ? (
            <span className="rounded-full bg-[var(--accent)]/10 px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-[var(--accent)]">
              Updated
            </span>
          ) : null}
          <p className="text-sm text-[var(--foreground-secondary)]">
            {formatMoney(day.subtotal, day.currency)}
          </p>
        </div>
      </div>

      <ol className="mt-2 space-y-0.5 pb-3">
        {items.map((item) => {
          const changed = changedItemIds.includes(item.item_id);
          const showLocation = Boolean(
            item.location_name && item.location_name !== dayLocation,
          );
          return (
            <ActivityRow
              key={item.item_id}
              item={item}
              leg={legsByTo.get(item.item_id)}
              changed={changed}
              showLocation={showLocation}
            />
          );
        })}
      </ol>
    </motion.div>
  );
}

export function ItineraryTimeline({
  itinerary,
  affectedDays = [],
  changedItemIds = [],
  className,
}: ItineraryTimelineProps) {
  const days = itinerary.days;
  const defaultDay = useMemo(() => {
    if (affectedDays.length > 0 && changedItemIds.length > 0) {
      return Math.min(...affectedDays);
    }
    return days[0]?.day_number ?? 1;
  }, [affectedDays, changedItemIds, days]);

  const [selectedDay, setSelectedDay] = useState(defaultDay);
  const resolvedDay = days.some((day) => day.day_number === selectedDay)
    ? selectedDay
    : defaultDay;

  const activeDay =
    days.find((day) => day.day_number === resolvedDay) ?? days[0];

  if (!activeDay) {
    return null;
  }

  return (
    <section
      className={cn(
        "rounded-xl border border-[var(--border)] bg-[var(--surface)]",
        className,
      )}
      aria-labelledby="itinerary-heading"
    >
      <div className="flex items-end justify-between gap-3 border-b border-[var(--border)] px-4 py-3">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
            Itinerary
          </p>
          <h2 id="itinerary-heading" className="font-display text-lg text-[var(--foreground)]">
            Your day-by-day plan
          </h2>
        </div>
        <p className="shrink-0 text-xs text-[var(--foreground-secondary)]">
          {formatMoney(itinerary.total_estimated_cost, itinerary.currency)} est.
        </p>
      </div>

      <div className="px-4 pt-2">
        <DaySelector
          days={days}
          selectedDay={resolvedDay}
          affectedDays={affectedDays}
          onSelect={setSelectedDay}
        />
        <AnimatePresence mode="wait">
          <DayContent
            key={activeDay.day_number}
            day={activeDay}
            affectedDays={affectedDays}
            changedItemIds={changedItemIds}
          />
        </AnimatePresence>
      </div>
    </section>
  );
}
