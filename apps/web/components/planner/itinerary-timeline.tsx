"use client";

import type {
  Itinerary,
  ItineraryDay,
  ItineraryItem,
  TravelLeg,
} from "@agentic-travel-engine/shared-types";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useMemo, useState } from "react";

import { ProvenanceBadge } from "@/components/planner/provenance-badge";
import {
  formatActivityContext,
  formatDuration,
  formatMoney,
  formatProvenanceDetail,
  formatTime,
} from "@/lib/planner/format";
import { cn } from "@/lib/utils";

interface ItineraryTimelineProps {
  itinerary: Itinerary;
  affectedDays?: number[];
  changedItemIds?: string[];
  selectedDay?: number;
  selectedItemId?: string | null;
  onDayChange?: (day: number) => void;
  onSelectItem?: (itemId: string) => void;
  className?: string;
}

function dayThemeLabel(theme: string | null | undefined): string | null {
  if (!theme) {
    return null;
  }
  return theme.replaceAll("_", " ").trim();
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
      className="sticky top-0 z-10 -mx-1 bg-[var(--background)]/95 px-1 pb-4 pt-1 backdrop-blur-sm"
      role="tablist"
      aria-label="Select itinerary day"
    >
      <div className="flex gap-2 overflow-x-auto scrollbar-subtle">
        {days.map((day) => {
          const isSelected = day.day_number === selectedDay;
          const isAffected = affectedDays.includes(day.day_number);
          const theme = dayThemeLabel(day.day_theme);
          return (
            <button
              key={day.day_number}
              type="button"
              role="tab"
              aria-selected={isSelected}
              aria-label={`Day ${String(day.day_number).padStart(2, "0")}${theme ? ` ${theme}` : ""}`}
              className={cn(
                "min-w-[4rem] shrink-0 rounded-lg px-3 py-2.5 text-left transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]",
                isSelected
                  ? "bg-[var(--accent)]/10 text-[var(--foreground)]"
                  : "text-[var(--foreground-muted)] hover:bg-[var(--surface-hover)]/60 hover:text-[var(--foreground)]",
                isAffected && !isSelected && "text-[var(--accent)]",
              )}
              onClick={() => onSelect(day.day_number)}
            >
              <span
                className={cn(
                  "block font-display text-2xl leading-none",
                  isSelected && "text-[var(--accent)]",
                )}
              >
                {String(day.day_number).padStart(2, "0")}
              </span>
              {theme ? (
                <span className="mt-1.5 block max-w-[5.5rem] truncate text-[10px] font-medium uppercase tracking-[0.08em]">
                  {theme}
                </span>
              ) : (
                <span className="mt-1.5 block text-[10px] font-medium uppercase tracking-[0.08em]">
                  Day
                </span>
              )}
              {isAffected ? (
                <span className="mt-0.5 block text-[9px] font-medium text-[var(--accent)]">
                  Updated
                </span>
              ) : null}
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
    <div
      className="flex items-center gap-3 py-2 pl-[4rem] text-xs text-[var(--foreground-muted)]"
      title={`Estimated ${leg.travel_mode} · ${formatDuration(leg.duration_seconds)} · ${distanceKm} km`}
    >
      <span className="h-3 w-px bg-[var(--border)]" aria-hidden />
      <span className="tabular-nums">
        {formatDuration(leg.duration_seconds)} travel · {distanceKm} km
      </span>
    </div>
  );
}

function ActivityRow({
  item,
  leg,
  changed,
  selected,
  onSelect,
}: {
  item: ItineraryItem;
  leg?: TravelLeg;
  changed: boolean;
  selected?: boolean;
  onSelect?: (itemId: string) => void;
}) {
  const isFree =
    item.category === "free_time" ||
    item.data_status === "free" ||
    !item.cost.amount;
  const context = formatActivityContext(item);
  const provenanceDetail = formatProvenanceDetail(item);

  return (
    <>
      {leg ? <TravelLegRow leg={leg} /> : null}
      <motion.li
        layout
        role="button"
        tabIndex={0}
        aria-pressed={selected}
        className={cn(
          "grid cursor-pointer grid-cols-[4rem_minmax(0,1fr)_auto] items-start gap-x-4 rounded-lg py-3 transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]",
          selected ? "bg-[var(--accent)]/8" : "hover:bg-[var(--surface-hover)]/40",
          changed && "border-l-2 border-[var(--accent)] pl-3",
        )}
        data-changed={changed || undefined}
        onClick={() => onSelect?.(item.item_id)}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            onSelect?.(item.item_id);
          }
        }}
      >
        <time className="pt-0.5 text-sm tabular-nums text-[var(--foreground-muted)]">
          {formatTime(item.start_time)}
        </time>
        <div className="min-w-0">
          <p className="text-[1.05rem] font-medium leading-snug text-[var(--foreground)]">
            {item.title}
          </p>
          {context ? (
            <p className="mt-0.5 text-sm leading-snug text-[var(--foreground-secondary)]">
              {context}
            </p>
          ) : null}
          <div className="mt-1.5 flex flex-wrap items-center gap-x-2">
            <ProvenanceBadge
              dataKind={item.data_status}
              source={item.source}
              sourceId={item.source_id}
              minimal
              detail={provenanceDetail}
            />
            {changed ? (
              <span className="text-xs font-medium text-[var(--accent)]">Changed</span>
            ) : null}
          </div>
        </div>
        <div className="pt-0.5 text-right">
          {isFree ? (
            <span className="text-xs text-[var(--foreground-muted)]">Free</span>
          ) : (
            <span className="text-sm tabular-nums text-[var(--foreground)]">
              {formatMoney(item.cost.amount ?? 0, item.cost.currency)}
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
  selectedItemId,
  onSelectItem,
}: {
  day: ItineraryDay;
  affectedDays: number[];
  changedItemIds: string[];
  selectedItemId?: string | null;
  onSelectItem?: (itemId: string) => void;
}) {
  const reduceMotion = useReducedMotion();
  const isAffected = affectedDays.includes(day.day_number);
  const items = [...day.items].sort((a, b) => a.start_time.localeCompare(b.start_time));
  const legsByTo = new Map(day.travel_legs.map((leg) => [leg.to_item_id, leg]));
  const themeLabel = dayThemeLabel(day.day_theme);

  return (
    <motion.div
      key={day.day_number}
      initial={reduceMotion ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={reduceMotion ? undefined : { opacity: 0, y: -4 }}
      transition={{ duration: 0.22 }}
      role="tabpanel"
      aria-label={`Day ${day.day_number} itinerary`}
    >
      <div className="border-b border-[var(--border)]/50 pb-4">
        <h3 className="font-display text-[1.65rem] leading-tight tracking-tight text-[var(--foreground)] md:text-[1.85rem]">
          Day {String(day.day_number).padStart(2, "0")}
          {themeLabel ? (
            <>
              <span className="mx-2 text-[var(--foreground-muted)]">·</span>
              <span>{themeLabel}</span>
            </>
          ) : null}
          {isAffected ? (
            <span className="ml-2 align-middle text-xs font-sans font-medium text-[var(--accent)]">
              Updated
            </span>
          ) : null}
        </h3>
        {day.theme_subtitle ? (
          <p className="mt-1.5 text-sm leading-relaxed text-[var(--foreground-secondary)]">
            {day.theme_subtitle}
          </p>
        ) : null}
      </div>

      <ol className="mt-1 divide-y divide-[var(--border)]/40">
        {items.map((item) => (
          <ActivityRow
            key={item.item_id}
            item={item}
            leg={legsByTo.get(item.item_id)}
            changed={changedItemIds.includes(item.item_id)}
            selected={selectedItemId === item.item_id}
            onSelect={onSelectItem}
          />
        ))}
      </ol>
    </motion.div>
  );
}

export function ItineraryTimeline({
  itinerary,
  affectedDays = [],
  changedItemIds = [],
  selectedDay: selectedDayProp,
  selectedItemId,
  onDayChange,
  onSelectItem,
  className,
}: ItineraryTimelineProps) {
  const days = itinerary.days;
  const defaultDay = useMemo(() => {
    if (affectedDays.length > 0 && changedItemIds.length > 0) {
      return Math.min(...affectedDays);
    }
    return days[0]?.day_number ?? 1;
  }, [affectedDays, changedItemIds, days]);

  const [internalDay, setInternalDay] = useState(defaultDay);
  const selectedDay = selectedDayProp ?? internalDay;
  const setSelectedDay = onDayChange ?? setInternalDay;
  const resolvedDay = days.some((day) => day.day_number === selectedDay)
    ? selectedDay
    : defaultDay;

  const activeDay =
    days.find((day) => day.day_number === resolvedDay) ?? days[0];

  if (!activeDay) {
    return null;
  }

  return (
    <section className={cn("min-w-0", className)} aria-labelledby="itinerary-heading">
      <h2 id="itinerary-heading" className="sr-only">Itinerary</h2>

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
          selectedItemId={selectedItemId}
          onSelectItem={onSelectItem}
        />
      </AnimatePresence>
    </section>
  );
}
