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
        "flex h-full flex-col rounded-[2rem] border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-soft)]",
        className,
      )}
      aria-labelledby="conversation-heading"
    >
      <div className="border-b border-[var(--border)] px-5 py-4">
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--foreground-muted)]">
          Planning conversation
        </p>
        <h2 id="conversation-heading" className="mt-1 font-display text-xl">
          Your requests
        </h2>
      </div>
      <div className="scrollbar-subtle flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {history.length === 0 ? (
          <p className="text-sm text-[var(--foreground-muted)]">
            Your planning conversation will appear here as you refine the trip.
          </p>
        ) : (
          history.map((entry) => {
            const Icon = entryIcon(entry.kind);
            return (
              <motion.article
                key={entry.id}
                initial={reduceMotion ? false : { opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className={cn(
                  "rounded-2xl px-4 py-3",
                  entry.role === "user"
                    ? "bg-[var(--surface-elevated)] ring-1 ring-[var(--border)]"
                    : "bg-[var(--surface-muted)]",
                )}
              >
                <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-[0.14em] text-[var(--foreground-muted)]">
                  <Icon className="h-3.5 w-3.5" aria-hidden />
                  <span>{entry.role === "user" ? "You" : "Planner"}</span>
                  <span aria-hidden>·</span>
                  <span>{entry.kind}</span>
                </div>
                <p className="text-sm leading-relaxed text-[var(--foreground)]">
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
