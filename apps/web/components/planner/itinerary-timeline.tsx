"use client";

import type { Itinerary, ItineraryDay, ItineraryItem, TravelLeg } from "@agentic-travel-engine/shared-types";
import { motion, useReducedMotion } from "framer-motion";
import { Car, Coffee, Landmark, Plane, Utensils } from "lucide-react";

import { ProvenanceBadge } from "@/components/planner/provenance-badge";
import {
  categoryLabel,
  formatDuration,
  formatMoney,
  formatTime,
} from "@/lib/planner/format";
import { cn } from "@/lib/utils";

interface ItineraryTimelineProps {
  itinerary: Itinerary;
  affectedDays?: number[];
  className?: string;
}

function categoryIcon(category: ItineraryItem["category"]) {
  switch (category) {
    case "flight":
      return Plane;
    case "restaurant":
      return Utensils;
    case "free_time":
      return Coffee;
    case "transport":
      return Car;
    default:
      return Landmark;
  }
}

function DaySection({
  day,
  affected,
}: {
  day: ItineraryDay;
  affected: boolean;
}) {
  const reduceMotion = useReducedMotion();
  const items = [...day.items].sort((a, b) => a.start_time.localeCompare(b.start_time));
  const legsByTo = new Map(day.travel_legs.map((leg) => [leg.to_item_id, leg]));

  return (
    <motion.section
      layout
      initial={reduceMotion ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "rounded-[2rem] border px-5 py-6 md:px-7",
        affected
          ? "border-[var(--accent)]/30 bg-[var(--surface-highlight)]"
          : "border-[var(--border)] bg-[var(--surface)]",
      )}
      aria-label={`Day ${day.day_number}`}
    >
      <div className="mb-6 flex items-end justify-between gap-4 border-b border-[var(--border)] pb-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.2em] text-[var(--foreground-muted)]">
            Day {day.day_number.toString().padStart(2, "0")}
          </p>
          <h3 className="mt-1 font-display text-2xl text-[var(--foreground)]">
            {items[0]?.location_name ?? `Day ${day.day_number}`}
          </h3>
        </div>
        <p className="text-sm text-[var(--foreground-secondary)]">
          {formatMoney(day.subtotal, day.currency)}
        </p>
      </div>

      <ol className="space-y-0">
        {items.map((item) => {
          const Icon = categoryIcon(item.category);
          const leg = legsByTo.get(item.item_id);
          return (
            <li key={item.item_id} className="relative pl-8">
              <span
                className="absolute left-0 top-2 h-full w-px bg-[var(--border)]"
                aria-hidden
              />
              <span
                className="absolute left-[-5px] top-2 h-2.5 w-2.5 rounded-full bg-[var(--accent)] ring-4 ring-[var(--surface)]"
                aria-hidden
              />
              {leg ? <TravelLegRow leg={leg} /> : null}
              <article className="pb-8">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 rounded-full bg-[var(--surface-elevated)] p-2 ring-1 ring-[var(--border)]">
                      <Icon className="h-4 w-4 text-[var(--accent)]" aria-hidden />
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
                        {formatTime(item.start_time)} · {categoryLabel(item.category)}
                      </p>
                      <h4 className="mt-1 text-lg font-medium text-[var(--foreground)]">
                        {item.title}
                      </h4>
                      {item.location_name ? (
                        <p className="mt-1 text-sm text-[var(--foreground-secondary)]">
                          {item.location_name}
                        </p>
                      ) : null}
                    </div>
                  </div>
                  <div className="text-right">
                    {item.cost.amount ? (
                      <p className="text-sm font-medium">
                        {formatMoney(item.cost.amount, item.cost.currency)}
                      </p>
                    ) : null}
                    <ProvenanceBadge
                      dataKind={item.data_status}
                      source={item.source}
                      sourceId={item.source_id}
                      className="mt-2"
                    />
                  </div>
                </div>
              </article>
            </li>
          );
        })}
      </ol>
    </motion.section>
  );
}

function TravelLegRow({ leg }: { leg: TravelLeg }) {
  return (
    <div className="mb-4 ml-1 flex items-center gap-2 text-xs text-[var(--foreground-muted)]">
      <Car className="h-3.5 w-3.5" aria-hidden />
      <span>
        {formatDuration(leg.duration_seconds)} · {leg.travel_mode}
      </span>
    </div>
  );
}

export function ItineraryTimeline({
  itinerary,
  affectedDays = [],
  className,
}: ItineraryTimelineProps) {
  return (
    <section
      className={cn("space-y-5", className)}
      aria-labelledby="itinerary-heading"
    >
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--foreground-muted)]">
            Itinerary
          </p>
          <h2 id="itinerary-heading" className="mt-2 font-display text-3xl">
            Your day-by-day plan
          </h2>
        </div>
        <p className="text-sm text-[var(--foreground-secondary)]">
          {formatMoney(itinerary.total_estimated_cost, itinerary.currency)} estimated
        </p>
      </div>
      <div className="space-y-5">
        {itinerary.days.map((day) => (
          <DaySection
            key={day.day_number}
            day={day}
            affected={affectedDays.includes(day.day_number)}
          />
        ))}
      </div>
    </section>
  );
}
