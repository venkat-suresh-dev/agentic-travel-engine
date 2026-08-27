import { describe, expect, it } from "vitest";

import { completeRunFixture } from "@/test/fixtures/planner";
import { initialLiveExecutionState } from "@/lib/planner/execution-state";
import {
  buildTraceSummaryChips,
  formatToolTraceDetail,
  resolveTraceExecution,
  toolRecordsToExecutionItems,
} from "@/lib/planner/tool-trace";

describe("tool trace mapping", () => {
  const records = completeRunFixture.tool_availability?.tools ?? [];

  it("maps successful completed run tools to success statuses", () => {
    const items = toolRecordsToExecutionItems(records);
    expect(items).toHaveLength(7);
    expect(items.every((item) => item.status === "success")).toBe(true);
    expect(formatToolTraceDetail(items[0]!)).toContain("Live");
    expect(formatToolTraceDetail(items[1]!)).toContain("Sandbox");
  });

  it("labels cached tool as cached", () => {
    const cached = toolRecordsToExecutionItems([
      {
        tool_name: "search_flights",
        status: "success",
        data_mode: "cached",
        provider: "serpapi-google-flights",
        duration_ms: 12,
      },
    ]);
    expect(formatToolTraceDetail(cached[0]!)).toBe("Cached · serpapi");
  });

  it("labels unavailable tool as unavailable", () => {
    const unavailable = toolRecordsToExecutionItems([
      {
        tool_name: "search_hotels",
        status: "unavailable",
        data_mode: "unavailable",
        provider: "stayingapi-sandbox",
        duration_ms: null,
      },
    ]);
    expect(unavailable[0]?.status).toBe("unavailable");
    expect(formatToolTraceDetail(unavailable[0]!)).toBe("Unavailable");
  });

  it("marks only failed tools unavailable in partial aggregate", () => {
    const partialRun = {
      ...completeRunFixture,
      tool_availability: {
        aggregate_status: "partial",
        unavailable_tools: ["search_hotels"],
        duration_ms: 1500,
        tools: records.map((record) =>
          record.tool_name === "search_hotels"
            ? {
                ...record,
                status: "unavailable" as const,
                data_mode: "unavailable" as const,
              }
            : record,
        ),
      },
    };
    const resolved = resolveTraceExecution(
      partialRun,
      initialLiveExecutionState,
      false,
    );
    expect(resolved.tools.filter((tool) => tool.status === "unavailable")).toHaveLength(
      1,
    );
    expect(resolved.tools.filter((tool) => tool.status === "success")).toHaveLength(
      6,
    );
    const chips = buildTraceSummaryChips(partialRun, resolved);
    expect(chips.some((chip) => chip.includes("unavailable"))).toBe(true);
    expect(chips.some((chip) => chip.includes("partial"))).toBe(true);
    expect(chips.some((chip) => chip.includes("7 partial"))).toBe(false);
  });

  it("uses authoritative API tools instead of unavailable fallback", () => {
    const resolved = resolveTraceExecution(
      completeRunFixture,
      {
        ...initialLiveExecutionState,
        tools: completeRunFixture.tool_availability!.unavailable_tools.map(
          (tool) => ({
            id: tool,
            kind: "tool" as const,
            name: tool,
            label: tool,
            status: "unavailable" as const,
            durationMs: null,
          }),
        ),
      },
      false,
    );
    expect(resolved.tools.every((tool) => tool.status === "success")).toBe(true);
    const chips = buildTraceSummaryChips(completeRunFixture, resolved);
    expect(chips).toContain("7 sources");
    expect(chips.some((chip) => chip.toLowerCase().includes("partial"))).toBe(
      false,
    );
  });
});
