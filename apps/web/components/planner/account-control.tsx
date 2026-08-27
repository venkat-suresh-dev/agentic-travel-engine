"use client";

import { UserButton } from "@clerk/nextjs";

import { clerkAppearance } from "@/lib/clerk/appearance";
import { cn } from "@/lib/utils";

interface AccountControlProps {
  className?: string;
}

export function AccountControl({ className }: AccountControlProps) {
  return (
    <div
      className={cn("planner-account flex h-9 w-9 items-center justify-center", className)}
      aria-label="Account menu"
    >
      <UserButton
        afterSignOutUrl="/planner"
        appearance={{
          variables: {
            ...clerkAppearance.variables,
            colorPrimary: "#0d5c63",
            colorBackground: "#fbf8f2",
            colorText: "#1f2421",
            colorTextSecondary: "#8b8173",
            colorNeutral: "#8b8173",
          },
          elements: {
            userButtonBox: "h-9 w-9",
            userButtonTrigger:
              "flex h-9 w-9 items-center justify-center rounded-full border border-[var(--border)] bg-[var(--surface-elevated)] transition hover:border-[var(--accent)] focus:shadow-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]",
            userButtonAvatarBox:
              "h-8 w-8 rounded-full bg-[var(--accent)] text-[var(--accent-foreground)] shadow-none ring-0",
            avatarBox:
              "h-8 w-8 rounded-full bg-[var(--accent)] text-[var(--accent-foreground)]",
            userButtonPopoverCard:
              "rounded-xl border border-[var(--border)] bg-[var(--surface-elevated)] text-[var(--foreground)] shadow-[var(--shadow-soft)]",
            userButtonPopoverMain: "bg-[var(--surface-elevated)]",
            userButtonPopoverActionButton:
              "text-[var(--foreground)] hover:bg-[var(--surface-hover)]",
            userButtonPopoverActionButtonText: "text-[var(--foreground)]",
            userButtonPopoverActionButtonIconBox: "text-[var(--foreground-muted)]",
            userButtonPopoverFooter: "hidden",
            userPreviewMainIdentifier: "text-[var(--foreground)]",
            userPreviewSecondaryIdentifier: "text-[var(--foreground-secondary)]",
            userPreviewAvatarBox: "bg-[var(--accent)]",
          },
        }}
      />
    </div>
  );
}
