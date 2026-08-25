"use client";

import type { ConversationEntry } from "@/lib/planner/storage";
import { motion, useReducedMotion } from "framer-motion";
import { MessageSquareQuote, Sparkles } from "lucide-react";

import { cn } from "@/lib/utils";

interface ConversationPanelProps {
  history: ConversationEntry[];
  className?: string;
}

function entryIcon(kind: ConversationEntry["kind"]) {
  if (kind === "request") return MessageSquareQuote;
  return Sparkles;
}

export function ConversationPanel({ history, className }: ConversationPanelProps) {
  const reduceMotion = useReducedMotion();

  return (
    <section
      className={cn(
        "flex flex-col overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)]",
        className,
      )}
      aria-labelledby="conversation-heading"
    >
      <div className="border-b border-[var(--border)] px-3 py-2.5">
        <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
          Conversation
        </p>
        <h2 id="conversation-heading" className="font-display text-base text-[var(--foreground)]">
          Your requests
        </h2>
      </div>
      <div className="scrollbar-subtle max-h-[140px] space-y-2 overflow-y-auto px-3 py-2 lg:max-h-[160px]">
        {history.length === 0 ? (
          <p className="text-xs text-[var(--foreground-muted)]">
            Planning messages appear here as you refine the trip.
          </p>
        ) : (
          history.map((entry) => {
            const Icon = entryIcon(entry.kind);
            return (
              <motion.article
                key={entry.id}
                initial={reduceMotion ? false : { opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                className={cn(
                  "rounded-lg px-2.5 py-2",
                  entry.role === "user"
                    ? "bg-[var(--surface-elevated)] ring-1 ring-[var(--border)]"
                    : "bg-[var(--surface-muted)]",
                )}
              >
                <div className="mb-1 flex items-center gap-1.5 text-[10px] uppercase tracking-[0.12em] text-[var(--foreground-muted)]">
                  <Icon className="h-3 w-3" aria-hidden />
                  <span>{entry.role === "user" ? "You" : "Planner"}</span>
                </div>
                <p className="line-clamp-3 text-xs leading-relaxed text-[var(--foreground)]">
                  {entry.content}
                </p>
              </motion.article>
            );
          })
        )}
      </div>
    </section>
  );
}
