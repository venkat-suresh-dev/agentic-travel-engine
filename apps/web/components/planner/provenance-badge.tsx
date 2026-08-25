import type { PriceDataKind } from "@agentic-travel-engine/shared-types";
import { Info } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { DATA_KIND_LABELS } from "@/lib/planner/format";
import { cn } from "@/lib/utils";

interface ProvenanceBadgeProps {
  dataKind: PriceDataKind;
  source: string;
  sourceId?: string | null;
  compact?: boolean;
  className?: string;
}

export function ProvenanceBadge({
  dataKind,
  source,
  sourceId,
  compact = false,
  className,
}: ProvenanceBadgeProps) {
  const meta = DATA_KIND_LABELS[dataKind];
  const provider = source.replace(/_/g, " ");

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          className={cn(
            "inline-flex items-center gap-1 rounded-full text-left transition-colors hover:opacity-80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]",
            className,
          )}
          aria-label={`Data provenance: ${meta.label} from ${provider}`}
        >
          <Badge variant={meta.tone} className={compact ? "text-[10px] px-1.5 py-0" : undefined}>
            {meta.label}
          </Badge>
          {!compact ? (
            <>
              <span className="text-[11px] text-[var(--foreground-muted)]">{provider}</span>
              <Info className="h-3 w-3 text-[var(--foreground-muted)]" aria-hidden />
            </>
          ) : null}
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-72">
        <p className="text-xs font-medium uppercase tracking-[0.12em] text-[var(--foreground-muted)]">
          Source provenance
        </p>
        <dl className="mt-3 space-y-2 text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-[var(--foreground-muted)]">Status</dt>
            <dd>{meta.label}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-[var(--foreground-muted)]">Provider</dt>
            <dd className="text-right">{provider}</dd>
          </div>
          {sourceId ? (
            <div className="flex justify-between gap-4">
              <dt className="text-[var(--foreground-muted)]">Reference</dt>
              <dd className="truncate text-right font-mono text-xs">{sourceId}</dd>
            </div>
          ) : null}
        </dl>
        <p className="mt-3 text-xs leading-relaxed text-[var(--foreground-muted)]">
          This plan is grounded in provider data where available. Estimated items
          are planning assumptions, not live quotes.
        </p>
      </PopoverContent>
    </Popover>
  );
}
