"use client";

import type { ConversationEntry } from "@/lib/planner/storage";

import { cn } from "@/lib/utils";

interface ConversationPanelProps {
  history: ConversationEntry[];
  className?: string;
}

function recentChangeEntries(history: ConversationEntry[]): ConversationEntry[] {
  const entries: ConversationEntry[] = [];
  for (let index = 0; index < history.length; index += 1) {
    const entry = history[index]!;
    if (entry.kind !== "modification") {
      continue;
    }
    const previous = history[index - 1];
    if (previous && previous.role === "user") {
      entries.push(previous);
    }
    entries.push(entry);
  }
  return entries.slice(-4);
}

export function ConversationPanel({ history, className }: ConversationPanelProps) {
  const recent = recentChangeEntries(history);
  if (recent.length === 0) {
    return null;
  }

  return (
    <section
      className={cn("pt-3", className)}
      aria-labelledby="conversation-heading"
    >
      <h2
        id="conversation-heading"
        className="text-xs text-[var(--foreground-muted)]"
      >
        Recent changes
      </h2>
      <ol className="mt-2 max-h-[4.5rem] space-y-1.5 overflow-y-auto scrollbar-subtle">
        {recent.map((entry) => (
          <li key={entry.id} className="flex gap-3 text-xs leading-snug">
            <span className="w-12 shrink-0 text-[var(--foreground-muted)]">
              {entry.role === "user" ? "You" : "Planner"}
            </span>
            <span className="min-w-0 truncate text-[var(--foreground-secondary)]">
              {entry.content}
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}
