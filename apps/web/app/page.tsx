import { APP_NAME } from "@agentic-travel-engine/shared-types";

export default function Home() {
  return (
    <main className="flex min-h-full flex-col items-center justify-center bg-zinc-50 px-6 py-16 font-sans dark:bg-black">
      <div className="w-full max-w-2xl space-y-4 text-center">
        <p className="text-sm font-medium uppercase tracking-wide text-zinc-500">
          Foundation
        </p>
        <h1 className="text-4xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
          {APP_NAME}
        </h1>
        <p className="text-lg text-zinc-600 dark:text-zinc-400">
          Monorepo scaffold for the AI Trip Planner. Trip-planning features will
          be added in later phases.
        </p>
      </div>
    </main>
  );
}
