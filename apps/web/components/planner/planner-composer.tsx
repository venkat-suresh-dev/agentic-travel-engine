"use client";

import { ArrowUpRight, Loader2 } from "lucide-react";
import { useId, useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

export interface ComposerDraft {
  text: string;
  key: number;
}

interface PlannerComposerProps {
  placeholder?: string;
  submitLabel?: string;
  disabled?: boolean;
  loading?: boolean;
  onSubmit: (message: string) => Promise<void> | void;
  suggestions?: string[];
  compact?: boolean;
  className?: string;
  title?: string;
  description?: string;
  supportingLine?: string;
  /** Initial message when this instance mounts (pair with remount key). */
  initialMessage?: string;
}

export function PlannerComposer({
  placeholder = "Describe what you want to change…",
  submitLabel = "Send",
  disabled = false,
  loading = false,
  onSubmit,
  suggestions = [],
  compact = false,
  className,
  title,
  description,
  supportingLine,
  initialMessage = "",
}: PlannerComposerProps) {
  const [message, setMessage] = useState(initialMessage);
  const labelId = useId();

  async function handleSubmit() {
    const trimmed = message.trim();
    if (!trimmed || disabled || loading) {
      return;
    }
    await onSubmit(trimmed);
    setMessage("");
  }

  return (
    <div className={cn(compact ? "space-y-3" : "space-y-4", className)}>
      {title ? (
        <div>
          <p className="text-sm font-medium text-[var(--foreground)]">{title}</p>
          {description ? (
            <p className="mt-0.5 text-sm text-[var(--foreground-secondary)]">
              {description}
            </p>
          ) : null}
          {supportingLine ? (
            <p className="mt-1 text-xs text-[var(--foreground-muted)]">{supportingLine}</p>
          ) : null}
        </div>
      ) : null}
      <label id={labelId} className="sr-only" htmlFor="planner-composer">
        Trip planning message
      </label>
      <div className={cn("flex items-end gap-2", !compact && "flex-col items-stretch")}>
        <Textarea
          id="planner-composer"
          aria-labelledby={labelId}
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder={placeholder}
          disabled={disabled || loading}
          rows={compact ? 1 : 4}
          className={cn(
            compact &&
              "!min-h-[2.75rem] flex-1 resize-none rounded-xl border-[var(--border)] bg-[var(--surface-elevated)] py-2.5 text-sm shadow-none",
          )}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void handleSubmit();
            }
          }}
        />
        <Button
          type="button"
          size={compact ? "sm" : "default"}
          onClick={() => void handleSubmit()}
          disabled={disabled || loading || !message.trim()}
          className={compact ? "h-10 shrink-0 rounded-xl" : undefined}
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              Working
            </>
          ) : (
            <>
              {submitLabel}
              <ArrowUpRight className="h-4 w-4" aria-hidden />
            </>
          )}
        </Button>
      </div>
      {suggestions.length > 0 ? (
        <div className="space-y-2">
          <p className="text-xs text-[var(--foreground-muted)]">Suggested</p>
          <div className="flex flex-wrap gap-2">
            {suggestions.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                className="rounded-full border border-[var(--border)] px-3 py-1.5 text-sm text-[var(--foreground-secondary)] transition-colors hover:border-[var(--border-strong)] hover:bg-[var(--surface-hover)]/50 hover:text-[var(--foreground)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
                onClick={() => setMessage(suggestion)}
                disabled={disabled || loading}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
