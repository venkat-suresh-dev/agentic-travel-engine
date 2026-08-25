"use client";

import { ArrowUpRight, Loader2 } from "lucide-react";
import { useId, useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

interface PlannerComposerProps {
  placeholder?: string;
  submitLabel?: string;
  disabled?: boolean;
  loading?: boolean;
  onSubmit: (message: string) => Promise<void> | void;
  suggestions?: string[];
  className?: string;
}

export function PlannerComposer({
  placeholder = "Describe what you want to change…",
  submitLabel = "Send",
  disabled = false,
  loading = false,
  onSubmit,
  suggestions = [],
  className,
}: PlannerComposerProps) {
  const [message, setMessage] = useState("");
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
    <div className={cn("space-y-3", className)}>
      <label id={labelId} className="sr-only" htmlFor="planner-composer">
        Trip planning message
      </label>
      <Textarea
        id="planner-composer"
        aria-labelledby={labelId}
        value={message}
        onChange={(event) => setMessage(event.target.value)}
        placeholder={placeholder}
        disabled={disabled || loading}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void handleSubmit();
          }
        }}
      />
      {suggestions.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {suggestions.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              className="rounded-full bg-[var(--surface-elevated)] px-3 py-1.5 text-xs text-[var(--foreground-secondary)] ring-1 ring-[var(--border)] transition-colors hover:bg-[var(--surface-hover)] hover:text-[var(--foreground)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
              onClick={() => setMessage(suggestion)}
              disabled={disabled || loading}
            >
              {suggestion}
            </button>
          ))}
        </div>
      ) : null}
      <div className="flex justify-end">
        <Button
          type="button"
          onClick={() => void handleSubmit()}
          disabled={disabled || loading || !message.trim()}
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
    </div>
  );
}
