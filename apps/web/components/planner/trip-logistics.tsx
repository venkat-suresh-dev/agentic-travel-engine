"use client";

import type { ReactNode } from "react";

import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { formatMoney, formatTime } from "@/lib/planner/format";
import type {
  FlightLogistics,
  GroundLogistics,
  StayLogistics,
  TripLogisticsModel,
} from "@/lib/planner/logistics";
import { cn } from "@/lib/utils";

interface TripLogisticsProps {
  logistics: TripLogisticsModel;
  className?: string;
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 text-sm">
      <dt className="text-[var(--foreground-muted)]">{label}</dt>
      <dd className="text-right text-[var(--foreground)]">{value}</dd>
    </div>
  );
}

function FlightDetails({ flight }: { flight: FlightLogistics }) {
  if (flight.status !== "available" || !flight.item) {
    return (
      <p className="text-sm leading-relaxed text-[var(--foreground-secondary)]">
        Currently unavailable. Other trip planning continues.
      </p>
    );
  }
  return (
    <dl className="space-y-2">
      {flight.carrier ? <DetailRow label="Carrier" value={flight.carrier} /> : null}
      {flight.stopsLabel ? <DetailRow label="Stops" value={flight.stopsLabel} /> : null}
      {flight.departureTime && flight.arrivalTime ? (
        <DetailRow
          label="Schedule"
          value={`${formatTime(flight.departureTime)} → ${formatTime(flight.arrivalTime)}`}
        />
      ) : null}
      {flight.durationLabel ? (
        <DetailRow label="Duration" value={flight.durationLabel} />
      ) : null}
      {flight.travelers ? (
        <DetailRow
          label="Travelers"
          value={`${flight.travelers} traveler${flight.travelers === 1 ? "" : "s"}`}
        />
      ) : null}
      {flight.priceAmount && flight.priceCurrency ? (
        <DetailRow
          label={flight.priceIsPartyTotal ? "Party total" : "Fare"}
          value={formatMoney(flight.priceAmount, flight.priceCurrency)}
        />
      ) : null}
      {flight.originalAmount &&
      flight.originalCurrency &&
      flight.originalCurrency.toUpperCase() !== (flight.priceCurrency ?? "").toUpperCase() ? (
        <DetailRow
          label="Original fare"
          value={formatMoney(flight.originalAmount, flight.originalCurrency)}
        />
      ) : null}
      {!flight.includedInBudget && flight.exclusionReason ? (
        <DetailRow label="Budget" value={flight.exclusionReason} />
      ) : null}
      <DetailRow label="Source" value={flight.provenanceLabel} />
    </dl>
  );
}

function StayDetails({ stay }: { stay: StayLogistics }) {
  if (stay.status !== "available" || !stay.item) {
    return (
      <p className="text-sm leading-relaxed text-[var(--foreground-secondary)]">
        Currently unavailable. Other trip planning continues.
      </p>
    );
  }
  const showOriginal =
    stay.originalAmount &&
    stay.originalCurrency &&
    stay.includedInBudget &&
    stay.originalCurrency.toUpperCase() !== (stay.priceCurrency ?? "").toUpperCase();
  return (
    <dl className="space-y-2">
      {stay.name ? <DetailRow label="Hotel" value={stay.name} /> : null}
      {stay.nights ? (
        <DetailRow
          label="Stay"
          value={`${stay.nights} night${stay.nights === 1 ? "" : "s"}`}
        />
      ) : null}
      {stay.priceAmount && stay.priceCurrency ? (
        <DetailRow
          label={stay.includedInBudget ? "Display amount" : "Original amount"}
          value={formatMoney(stay.priceAmount, stay.priceCurrency)}
        />
      ) : null}
      {showOriginal ? (
        <DetailRow
          label="Original amount"
          value={formatMoney(stay.originalAmount!, stay.originalCurrency!)}
        />
      ) : null}
      {!stay.includedInBudget && stay.exclusionReason ? (
        <DetailRow label="Budget" value={stay.exclusionReason} />
      ) : null}
      <DetailRow label="Source" value={stay.provenanceLabel} />
    </dl>
  );
}

function GroundDetails({ ground }: { ground: GroundLogistics }) {
  if (ground.legs.length === 0) {
    return (
      <p className="text-sm leading-relaxed text-[var(--foreground-secondary)]">
        Estimated ground travel is not available for this day.
      </p>
    );
  }
  return (
    <div className="space-y-3">
      <p className="font-mono text-[11px] text-[var(--foreground-muted)]">
        Estimated ground travel · {ground.modeLabel}
      </p>
      <ul className="space-y-2.5">
        {ground.legs.map((leg) => (
          <li key={leg.id} className="text-sm">
            <p className="text-[var(--foreground)]">
              {leg.fromLabel} → {leg.toLabel}
            </p>
            <p className="font-mono text-[11px] text-[var(--foreground-muted)]">
              {leg.durationLabel} · {leg.distanceLabel}
            </p>
          </li>
        ))}
      </ul>
      <p className="text-xs text-[var(--foreground-muted)]">
        Route planning only. No ride has been booked.
      </p>
    </div>
  );
}

function EssentialsRow({
  symbol,
  label,
  children,
  details,
  unavailable,
}: {
  symbol: string;
  label: string;
  children: ReactNode;
  details: ReactNode;
  unavailable?: boolean;
}) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          className={cn(
            "group min-w-0 flex-1 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-[var(--surface-hover)]/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]",
            unavailable && "opacity-80",
          )}
          aria-label={`${label} details`}
        >
          <p className="flex items-center gap-2 text-xs text-[var(--foreground-muted)]">
            <span className="text-sm leading-none" aria-hidden>{symbol}</span>
            <span>{label}</span>
          </p>
          <div className="mt-1.5 space-y-0.5">{children}</div>
        </button>
      </PopoverTrigger>
      <PopoverContent
        className="w-80 border-[var(--border)] bg-[var(--surface-elevated)] shadow-[var(--shadow-soft)]"
        align="start"
      >
        <p className="text-xs text-[var(--foreground-muted)]">{label}</p>
        <div className="mt-3">{details}</div>
      </PopoverContent>
    </Popover>
  );
}

export function TripLogistics({ logistics, className }: TripLogisticsProps) {
  const { flight, stay, ground } = logistics;
  const groundCost =
    ground.estimatedCost?.amount && ground.estimatedCost.currency
      ? formatMoney(ground.estimatedCost.amount, ground.estimatedCost.currency)
      : null;

  const flightPrice =
    flight.priceAmount && flight.priceCurrency
      ? formatMoney(flight.priceAmount, flight.priceCurrency)
      : null;
  const stayPrice =
    stay.priceAmount && stay.priceCurrency
      ? formatMoney(stay.priceAmount, stay.priceCurrency)
      : null;

  return (
    <section className={cn("py-1", className)} aria-label="Trip essentials">
      <p className="text-xs text-[var(--foreground-muted)]">Trip essentials</p>

      <div className="mt-2 flex flex-col gap-1 sm:flex-row sm:gap-0 sm:divide-x sm:divide-[var(--border)]/60">
        <EssentialsRow
          symbol="✈"
          label="Flight"
          unavailable={flight.status !== "available"}
          details={<FlightDetails flight={flight} />}
        >
          {flight.status === "available" ? (
            <>
              <p className="truncate text-sm font-medium text-[var(--foreground)]">
                {flight.routeLabel ?? flight.carrier}
              </p>
              <p className="truncate text-sm tabular-nums text-[var(--foreground-secondary)]">
                {flightPrice
                  ? `${flightPrice}${flight.priceIsPartyTotal ? " total" : ""}`
                  : (flight.carrier ?? "—")}
                <span className="text-[var(--foreground-muted)]">
                  {" "}
                  · {flight.provenanceLabel}
                </span>
              </p>
            </>
          ) : (
            <p className="text-sm text-[var(--foreground-secondary)]">Unavailable</p>
          )}
        </EssentialsRow>

        <EssentialsRow
          symbol="⌂"
          label="Stay"
          unavailable={stay.status !== "available"}
          details={<StayDetails stay={stay} />}
        >
          {stay.status === "available" ? (
            <>
              <p className="truncate text-sm font-medium text-[var(--foreground)]">
                {stay.name ?? "Selected hotel"}
              </p>
              <p className="truncate text-sm tabular-nums text-[var(--foreground-secondary)]">
                {stay.nights
                  ? `${stay.nights} night${stay.nights === 1 ? "" : "s"}`
                  : "—"}
                {stayPrice ? ` · ${stayPrice}` : ""}
                <span className="text-[var(--foreground-muted)]">
                  {" "}
                  · {stay.provenanceLabel}
                </span>
              </p>
            </>
          ) : (
            <p className="text-sm text-[var(--foreground-secondary)]">Unavailable</p>
          )}
        </EssentialsRow>

        <EssentialsRow
          symbol="⌁"
          label="Getting around"
          unavailable={ground.status !== "available"}
          details={<GroundDetails ground={ground} />}
        >
          {ground.status === "available" ? (
            <>
              <p className="truncate text-sm font-medium text-[var(--foreground)]">
                Estimated local travel
              </p>
              <p className="truncate text-sm tabular-nums text-[var(--foreground-secondary)]">
                {groundCost ?? ground.modeLabel}
                <span className="text-[var(--foreground-muted)]">
                  {" "}
                  · {ground.provenanceLabel}
                </span>
              </p>
            </>
          ) : (
            <p className="text-sm text-[var(--foreground-secondary)]">Unavailable</p>
          )}
        </EssentialsRow>
      </div>
    </section>
  );
}
