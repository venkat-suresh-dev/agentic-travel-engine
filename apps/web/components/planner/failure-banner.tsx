import { AlertTriangle } from "lucide-react";

import { cn } from "@/lib/utils";

interface FailureBannerProps {
  title: string;
  message: string;
  preserved?: boolean;
  detail?: string;
  className?: string;
}

export function FailureBanner({
  title,
  message,
  preserved = false,
  detail,
  className,
}: FailureBannerProps) {
  return (
    <div
      role="alert"
      className={cn("border-l-2 border-[var(--budget-over-fg)] py-2 pl-3", className)}
    >
      <div className="flex gap-2">
        <AlertTriangle
          className="mt-0.5 h-4 w-4 shrink-0 text-[var(--budget-over-fg)]"
          aria-hidden
        />
        <div>
          <p className="font-medium text-[var(--budget-over-fg)]">{title}</p>
          <p className="mt-1 text-sm leading-relaxed text-[var(--foreground-secondary)]">
            {message}
          </p>
          {detail ? (
            <p className="mt-2 text-sm text-[var(--foreground)]">{detail}</p>
          ) : null}
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
