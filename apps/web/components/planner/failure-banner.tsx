import { AlertTriangle } from "lucide-react";

import { cn } from "@/lib/utils";

interface FailureBannerProps {
  title: string;
  message: string;
  preserved?: boolean;
  className?: string;
}

export function FailureBanner({
  title,
  message,
  preserved = false,
  className,
}: FailureBannerProps) {
  return (
    <div
      role="alert"
      className={cn(
        "rounded-2xl border border-[var(--budget-over-fg)]/20 bg-[var(--budget-over-bg)] px-5 py-4",
        className,
      )}
    >
      <div className="flex gap-3">
        <AlertTriangle
          className="mt-0.5 h-5 w-5 shrink-0 text-[var(--budget-over-fg)]"
          aria-hidden
        />
        <div>
          <p className="font-medium text-[var(--budget-over-fg)]">{title}</p>
          <p className="mt-1 text-sm leading-relaxed text-[var(--foreground-secondary)]">
            {message}
          </p>
          {preserved ? (
            <p className="mt-2 text-sm font-medium text-[var(--foreground)]">
              Your previous itinerary is still intact.
            </p>
          ) : null}
        </div>
      </div>
    </div>
  );
}
