"use client";

/**
 * Lightweight skeleton placeholders that mirror the real component layout
 * while the data is loading. All skeletons use ``animate-pulse`` and no
 * text content so screen readers skip them (parent regions should keep
 * ``aria-busy="true"`` where appropriate).
 */

function Block({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded bg-zinc-200/70 dark:bg-zinc-800 ${className}`}
    />
  );
}

/** Placeholder for a single news card in ``NewsList``. */
export function NewsCardSkeleton() {
  return (
    <li className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-start justify-between gap-4">
        <Block className="h-5 w-3/4" />
        <Block className="h-5 w-20 shrink-0" />
      </div>
      <div className="mt-2 flex gap-2">
        <Block className="h-3 w-28" />
        <Block className="h-3 w-10" />
      </div>
      <div className="mt-3 flex gap-1.5">
        <Block className="h-4 w-16 rounded-full" />
        <Block className="h-4 w-20 rounded-full" />
      </div>
    </li>
  );
}

/** Full list skeleton (date section + N cards). */
export function NewsListSkeleton({ cards = 5 }: { cards?: number }) {
  return (
    <div aria-busy="true" aria-live="polite">
      <Block className="mb-3 h-3 w-24" />
      <section className="mb-6">
        <Block className="mb-2 h-3 w-40" />
        <ul className="space-y-3">
          {Array.from({ length: cards }).map((_, i) => (
            <NewsCardSkeleton key={i} />
          ))}
        </ul>
      </section>
    </div>
  );
}

/** Ticker placeholder that mimics the red-banner row. */
export function HotTickerSkeleton() {
  return (
    <section
      aria-busy="true"
      aria-hidden="true"
      className="mb-6 overflow-hidden rounded-lg border border-red-200 bg-red-50/60 dark:border-red-900/40 dark:bg-red-950/20"
    >
      <div className="flex items-stretch">
        <div className="flex shrink-0 items-center gap-2 border-r border-red-200/60 bg-red-300/50 px-3 py-2 dark:border-red-900/40 dark:bg-red-900/30">
          <Block className="h-3 w-16 !bg-red-200/80 dark:!bg-red-900/60" />
        </div>
        <div className="flex flex-1 gap-6 overflow-hidden px-3 py-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex shrink-0 items-center gap-2">
              <Block className="h-3 w-12" />
              <Block className="h-3 w-40" />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/** Placeholder chip row for the FilterBar source list while loading. */
export function ChipRowSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div aria-busy="true" className="flex flex-wrap gap-1.5">
      {Array.from({ length: count }).map((_, i) => (
        <Block key={i} className="h-6 w-20 rounded-full" />
      ))}
    </div>
  );
}
