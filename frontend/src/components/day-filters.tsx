"use client";

import { DAY_FLAGS, type DayFlag } from "@/lib/filters";
import { cn } from "@/lib/utils";

const chip =
  "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors";

export function DayFilters({
  value,
  onChange,
  counts,
  className,
}: {
  value: DayFlag[];
  onChange: (flags: DayFlag[]) => void;
  /** optional per-flag row counts, shown on the chip */
  counts?: Record<DayFlag, number>;
  className?: string;
}) {
  const toggle = (key: DayFlag) =>
    onChange(value.includes(key) ? value.filter((f) => f !== key) : [...value, key]);

  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      <button
        type="button"
        onClick={() => onChange([])}
        aria-pressed={value.length === 0}
        className={cn(
          chip,
          value.length === 0
            ? "border-primary bg-primary/10 text-primary"
            : "border-input text-muted-foreground hover:bg-accent"
        )}
      >
        كل الأيام
      </button>
      {DAY_FLAGS.map(({ key, label }) => {
        const active = value.includes(key);
        return (
          <button
            key={key}
            type="button"
            onClick={() => toggle(key)}
            aria-pressed={active}
            className={cn(
              chip,
              active
                ? "border-primary bg-primary/10 text-primary"
                : "border-input text-muted-foreground hover:bg-accent"
            )}
          >
            {label}
            {counts && (
              <span className={cn("tabular-nums", active ? "opacity-80" : "opacity-60")}>
                {counts[key]}
              </span>
            )}
          </button>
        );
      })}
      {value.length > 1 && (
        <span className="text-xs text-muted-foreground">(أي فلتر من المحددة)</span>
      )}
    </div>
  );
}
