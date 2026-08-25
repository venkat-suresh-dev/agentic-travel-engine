import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.08em]",
  {
    variants: {
      variant: {
        default: "bg-[var(--surface-elevated)] text-[var(--foreground-secondary)] ring-1 ring-[var(--border)]",
        live: "bg-[var(--status-live-bg)] text-[var(--status-live-fg)]",
        cached: "bg-[var(--status-cached-bg)] text-[var(--status-cached-fg)]",
        estimated: "bg-[var(--status-estimated-bg)] text-[var(--status-estimated-fg)]",
        free: "bg-[var(--status-free-bg)] text-[var(--status-free-fg)]",
        unavailable: "bg-[var(--status-unavailable-bg)] text-[var(--status-unavailable-fg)]",
        success: "bg-[var(--budget-under-bg)] text-[var(--budget-under-fg)]",
        warning: "bg-[var(--budget-near-bg)] text-[var(--budget-near-fg)]",
        danger: "bg-[var(--budget-over-bg)] text-[var(--budget-over-fg)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
