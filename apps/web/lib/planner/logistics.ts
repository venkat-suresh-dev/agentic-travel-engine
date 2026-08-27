import type {
  AgentRunResponse,
  BudgetCategory,
  BudgetCategoryLine,
  BudgetSummary,
  Itinerary,
  ItineraryItem,
  ToolAvailability,
  TravelLeg,
  TripRequest,
} from "@agentic-travel-engine/shared-types";

import {
  formatDuration,
  formatProviderName,
  isSandboxSource,
  nightsBetween,
} from "@/lib/planner/format";

export type LogisticsStatus = "available" | "unavailable";

export interface FlightLogistics {
  status: LogisticsStatus;
  item: ItineraryItem | null;
  carrier: string | null;
  origin: string | null;
  destination: string | null;
  routeLabel: string | null;
  priceAmount: string | null;
  priceCurrency: string | null;
  originalAmount: string | null;
  originalCurrency: string | null;
  /** Party total from provider search (adults = travelers). */
  priceIsPartyTotal: boolean;
  departureTime: string | null;
  arrivalTime: string | null;
  durationLabel: string | null;
  stopsLabel: string | null;
  travelers: number | null;
  provenanceLabel: string;
  provider: string | null;
  includedInBudget: boolean;
  exclusionReason: string | null;
}

export interface StayLogistics {
  status: LogisticsStatus;
  item: ItineraryItem | null;
  name: string | null;
  nights: number | null;
  checkIn: string | null;
  checkOut: string | null;
  priceAmount: string | null;
  priceCurrency: string | null;
  originalAmount: string | null;
  originalCurrency: string | null;
  includedInBudget: boolean;
  exclusionReason: string | null;
  provenanceLabel: string;
  provider: string | null;
}

export interface GroundLegView {
  id: string;
  fromLabel: string;
  toLabel: string;
  durationLabel: string;
  distanceLabel: string;
  mode: string;
}

export interface GroundLogistics {
  status: LogisticsStatus;
  modeLabel: string;
  provenanceLabel: string;
  provider: string | null;
  legs: GroundLegView[];
  estimatedCost: BudgetCategoryLine | null;
}

export interface TripLogisticsModel {
  flight: FlightLogistics;
  stay: StayLogistics;
  ground: GroundLogistics;
}

export function buildTripLogistics(
  run: AgentRunResponse,
  selectedDay?: number,
): TripLogisticsModel | null {
  const itinerary = run.itinerary;
  if (!itinerary) {
    return null;
  }
  return {
    flight: buildFlightLogistics(
      itinerary,
      run.trip_request,
      run.tool_availability,
      run.budget,
    ),
    stay: buildStayLogistics(itinerary, run.tool_availability, run.budget),
    ground: buildGroundLogistics(itinerary, run.tool_availability, run.budget, selectedDay),
  };
}

export function budgetCategoryLabel(category: BudgetCategory): string {
  switch (category) {
    case "flight":
      return "Flights";
    case "hotel":
      return "Hotel";
    case "activity":
      return "Activities";
    case "food":
      return "Food";
    case "transport":
      return "Ground";
    default:
      return "Other";
  }
}

export function excludedBudgetCategories(budget: BudgetSummary | null | undefined): BudgetCategoryLine[] {
  if (!budget?.categories?.length) {
    return [];
  }
  return budget.categories.filter(
    (line) =>
      !line.included_in_total &&
      (line.data_kind === "unavailable" || line.assumption != null),
  );
}

export function budgetExclusionSummary(budget: BudgetSummary | null | undefined): string | null {
  const excluded = excludedBudgetCategories(budget);
  if (excluded.length === 0) {
    return null;
  }
  const labels = excluded.map((line) => budgetCategoryLabel(line.category));
  if (labels.length === 1) {
    return `${labels[0]} excluded — conversion unavailable`;
  }
  return `${labels.join(", ")} excluded — conversion unavailable`;
}

function buildFlightLogistics(
  itinerary: Itinerary,
  trip: TripRequest | null,
  tools: ToolAvailability | null,
  budget: BudgetSummary | null | undefined,
): FlightLogistics {
  const item = itinerary.infrastructure_items.find((entry) => entry.category === "flight") ?? null;
  const tool = findTool(tools, "search_flights");
  const parsed = item ? parseFlightTitle(item.title) : null;
  const originCity = trip?.departure_city ?? parsed?.origin ?? null;
  const destinationCity = trip?.destination ?? parsed?.destination ?? null;
  const routeLabel =
    originCity && destinationCity ? `${originCity} → ${destinationCity}` : parsed?.route ?? null;
  const provider = tool?.provider ?? item?.source ?? null;
  const budgetLine = budget?.categories?.find((line) => line.category === "flight") ?? null;
  const money = resolveDisplayMoney(item, budgetLine);
  const travelers = trip?.travelers ?? null;
  if (!item || item.data_status === "unavailable") {
    return {
      status: "unavailable",
      item,
      carrier: parsed?.carrier ?? null,
      origin: parsed?.origin ?? null,
      destination: parsed?.destination ?? null,
      routeLabel,
      priceAmount: money.amount,
      priceCurrency: money.currency,
      originalAmount: money.originalAmount,
      originalCurrency: money.originalCurrency,
      priceIsPartyTotal: (travelers ?? 1) > 1,
      departureTime: item?.start_time ?? null,
      arrivalTime: item?.end_time ?? null,
      durationLabel: durationFromDescription(item?.description) ?? durationFromTimes(item),
      stopsLabel: stopsFromDescription(item?.description),
      travelers,
      provenanceLabel: "Currently unavailable",
      provider,
      includedInBudget: false,
      exclusionReason: budgetLine?.assumption ?? null,
    };
  }

  return {
    status: "available",
    item,
    carrier: parsed?.carrier ?? item.title,
    origin: parsed?.origin ?? null,
    destination: parsed?.destination ?? null,
    routeLabel,
    priceAmount: money.amount,
    priceCurrency: money.currency,
    originalAmount: money.originalAmount,
    originalCurrency: money.originalCurrency,
    priceIsPartyTotal: (travelers ?? 1) > 1,
    departureTime: item.start_time,
    arrivalTime: item.end_time,
    durationLabel: durationFromDescription(item.description) ?? durationFromTimes(item),
    stopsLabel: stopsFromDescription(item.description),
    travelers,
    provenanceLabel: liveOrCachedLabel(item, provider, tool?.data_mode ?? item.data_status),
    provider,
    includedInBudget: money.includedInBudget,
    exclusionReason: money.exclusionReason,
  };
}

function buildStayLogistics(
  itinerary: Itinerary,
  tools: ToolAvailability | null,
  budget: BudgetSummary | null | undefined,
): StayLogistics {
  const hotels = itinerary.infrastructure_items.filter((entry) => entry.category === "hotel");
  const checkIn = hotels.find((entry) => /check-in/i.test(entry.title)) ?? hotels[0] ?? null;
  const checkOut = hotels.find((entry) => /check-out/i.test(entry.title)) ?? null;
  const tool = findTool(tools, "search_hotels");
  const provider = tool?.provider ?? checkIn?.source ?? null;
  const sandbox = tool?.data_mode === "sandbox" || isSandboxSource(checkIn?.source ?? provider);
  const unavailable = !checkIn;
  const budgetLine = budget?.categories?.find((line) => line.category === "hotel") ?? null;
  const money = resolveDisplayMoney(checkIn, budgetLine);

  const name = checkIn ? hotelDisplayName(checkIn.title) : null;
  const nights = nightsBetween(checkIn?.date ?? null, checkOut?.date ?? null);
  const provenanceLabel = unavailable
    ? "Currently unavailable"
    : sandbox
      ? `Sandbox · ${formatProviderName(provider)}`
      : liveOrCachedLabel(checkIn, provider, tool?.data_mode ?? checkIn.data_status);

  const defaultExclusion =
    !money.includedInBudget && money.amount
      ? "Hotel cost not included in trip budget because currency conversion is unavailable."
      : null;

  return {
    status: unavailable ? "unavailable" : "available",
    item: checkIn,
    name,
    nights,
    checkIn: checkIn?.date ?? null,
    checkOut: checkOut?.date ?? null,
    priceAmount: money.amount,
    priceCurrency: money.currency,
    originalAmount: money.originalAmount,
    originalCurrency: money.originalCurrency,
    includedInBudget: money.includedInBudget,
    exclusionReason: money.exclusionReason ?? defaultExclusion,
    provenanceLabel,
    provider,
  };
}

function buildGroundLogistics(
  itinerary: Itinerary,
  tools: ToolAvailability | null,
  budget: AgentRunResponse["budget"],
  selectedDay?: number,
): GroundLogistics {
  const tool = findTool(tools, "get_distance_matrix");
  const provider = tool?.provider ?? null;
  const day =
    itinerary.days.find((entry) => entry.day_number === selectedDay) ?? itinerary.days[0];
  const itemsById = itemsIndex(itinerary);
  const sourceLegs = day?.travel_legs ?? [];
  const legs = sourceLegs
    .filter((leg) => leg.duration_seconds >= 120 || leg.distance_meters >= 400)
    .map((leg) => toGroundLegView(leg, itemsById));
  const fallbackLegs =
    legs.length > 0
      ? legs
      : sourceLegs.map((leg) => toGroundLegView(leg, itemsById));
  const mode = fallbackLegs[0]?.mode ?? sourceLegs[0]?.travel_mode ?? "driving";
  const estimatedCost =
    budget?.categories?.find(
      (line) =>
        line.category === "transport" &&
        line.included_in_total &&
        line.amount !== null,
    ) ?? null;
  const unavailable =
    fallbackLegs.length === 0 &&
    (tool?.status === "unavailable" || tool?.status === "error" || !tool);

  return {
    status: unavailable ? "unavailable" : "available",
    modeLabel: formatTravelMode(mode),
    provenanceLabel: unavailable
      ? "Currently unavailable"
      : `Estimated · ${formatProviderName(provider ?? sourceLegs[0]?.source)}`,
    provider,
    legs: fallbackLegs.slice(0, 6),
    estimatedCost,
  };
}

function resolveDisplayMoney(
  item: ItineraryItem | null,
  budgetLine: BudgetCategoryLine | null,
): {
  amount: string | null;
  currency: string | null;
  originalAmount: string | null;
  originalCurrency: string | null;
  includedInBudget: boolean;
  exclusionReason: string | null;
} {
  const included =
    budgetLine?.included_in_total === true && budgetLine.amount != null;

  if (included && budgetLine) {
    const originalAmount =
      budgetLine.source_amount ??
      item?.cost.source_amount ??
      null;
    const originalCurrency =
      budgetLine.source_currency ??
      item?.cost.source_currency ??
      null;
    const showOriginal =
      originalAmount != null &&
      originalCurrency != null &&
      originalCurrency.toUpperCase() !== budgetLine.currency.toUpperCase();
    return {
      amount: budgetLine.amount,
      currency: budgetLine.currency,
      originalAmount: showOriginal ? originalAmount : item?.cost.source_amount ?? null,
      originalCurrency: showOriginal
        ? originalCurrency
        : item?.cost.source_currency ?? null,
      includedInBudget: true,
      exclusionReason: null,
    };
  }

  const amount = item?.cost.amount ?? budgetLine?.source_amount ?? null;
  const currency = item?.cost.currency ?? budgetLine?.source_currency ?? null;
  return {
    amount,
    currency,
    originalAmount: amount,
    originalCurrency: currency,
    includedInBudget: false,
    exclusionReason: budgetLine?.assumption ?? null,
  };
}

function toGroundLegView(
  leg: TravelLeg,
  itemsById: Map<string, ItineraryItem>,
): GroundLegView {
  return {
    id: leg.leg_id,
    fromLabel: shortPlaceLabel(itemsById.get(leg.from_item_id)),
    toLabel: shortPlaceLabel(itemsById.get(leg.to_item_id)),
    durationLabel: formatDuration(leg.duration_seconds),
    distanceLabel: `${(leg.distance_meters / 1000).toFixed(1)} km`,
    mode: leg.travel_mode,
  };
}

function itemsIndex(itinerary: Itinerary): Map<string, ItineraryItem> {
  const items = new Map<string, ItineraryItem>();
  for (const day of itinerary.days) {
    for (const item of day.items) {
      items.set(item.item_id, item);
    }
  }
  for (const item of itinerary.infrastructure_items) {
    items.set(item.item_id, item);
  }
  return items;
}

function shortPlaceLabel(item: ItineraryItem | undefined): string {
  if (!item) {
    return "Stop";
  }
  if (item.category === "hotel") {
    return hotelDisplayName(item.title);
  }
  const title = item.title.trim();
  return title.length > 28 ? `${title.slice(0, 26).trim()}…` : title;
}

function hotelDisplayName(title: string): string {
  return title.replace(/\s+check-in$/i, "").replace(/\s+check-out$/i, "").trim();
}

function parseFlightTitle(title: string): {
  carrier: string;
  origin: string | null;
  destination: string | null;
  route: string | null;
} {
  const match = title.match(/^(.*?)\s+([A-Z]{3})\s*(?:→|->|-)\s*([A-Z]{3})$/);
  if (match) {
    return {
      carrier: match[1]!.trim(),
      origin: match[2] ?? null,
      destination: match[3] ?? null,
      route: `${match[2]} → ${match[3]}`,
    };
  }
  return { carrier: title, origin: null, destination: null, route: null };
}

function durationFromDescription(description: string | null | undefined): string | null {
  if (!description) {
    return null;
  }
  const match = description.match(/(\d+h(?:\s+\d+m)?|\d+\s+min)/i);
  return match?.[1] ?? null;
}

function stopsFromDescription(description: string | null | undefined): string | null {
  if (!description) {
    return null;
  }
  if (/\bnonstop\b/i.test(description)) {
    return "Nonstop";
  }
  const match = description.match(/(\d+)\s+stops?/i);
  return match ? `${match[1]} stop${match[1] === "1" ? "" : "s"}` : null;
}

function durationFromTimes(item: ItineraryItem | null): string | null {
  if (!item) {
    return null;
  }
  const start = timeToMinutes(item.start_time);
  const end = timeToMinutes(item.end_time);
  if (start === null || end === null || end <= start) {
    return null;
  }
  return formatDuration((end - start) * 60);
}

function timeToMinutes(value: string): number | null {
  const [hours, minutes] = value.split(":");
  if (hours === undefined || minutes === undefined) {
    return null;
  }
  const hour = Number(hours);
  const minute = Number(minutes);
  if (Number.isNaN(hour) || Number.isNaN(minute)) {
    return null;
  }
  return hour * 60 + minute;
}

function liveOrCachedLabel(
  item: ItineraryItem | null,
  provider: string | null,
  dataMode: string,
): string {
  const name = formatProviderName(provider ?? item?.source);
  if (dataMode === "sandbox" || isSandboxSource(provider) || isSandboxSource(item?.source)) {
    return `Sandbox · ${name}`;
  }
  if (dataMode === "cached") {
    return `Cached · ${name}`;
  }
  return `Live · ${name}`;
}

function findTool(tools: ToolAvailability | null, name: string) {
  return tools?.tools.find((tool) => tool.tool_name === name) ?? null;
}

function formatTravelMode(mode: string): string {
  const normalized = mode.toLowerCase();
  if (normalized.includes("walk")) {
    return "Walking";
  }
  if (normalized.includes("transit") || normalized.includes("train")) {
    return "Transit";
  }
  return "Driving";
}
