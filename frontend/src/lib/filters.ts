import type { AttendanceDay } from "@/lib/types";

/** Quick day filters — keys must match DAY_FLAGS in backend/app/api/routes/reports.py */
export type DayFlag = "absent" | "single_punch" | "late" | "early_leave" | "overtime";

type DayLike = Pick<
  AttendanceDay,
  "status" | "late_minutes" | "early_leave_minutes" | "overtime_minutes"
>;

export const DAY_FLAGS: {
  key: DayFlag;
  label: string;
  match: (day: DayLike) => boolean;
}[] = [
  { key: "absent", label: "أيام الغياب", match: (d) => d.status === "absent" },
  { key: "single_punch", label: "بصمة واحدة", match: (d) => d.status === "incomplete" },
  { key: "late", label: "أيام التأخير", match: (d) => d.late_minutes > 0 },
  { key: "early_leave", label: "انصراف مبكر", match: (d) => d.early_leave_minutes > 0 },
  { key: "overtime", label: "أوفر تايم", match: (d) => d.overtime_minutes > 0 },
];

/** Several selected flags are OR-combined — same semantics as the API. */
export function matchesFlags(day: DayLike, flags: DayFlag[]): boolean {
  if (flags.length === 0) return true;
  return DAY_FLAGS.some((f) => flags.includes(f.key) && f.match(day));
}

export function countByFlag<T extends DayLike>(days: T[]): Record<DayFlag, number> {
  const counts = {} as Record<DayFlag, number>;
  for (const { key, match } of DAY_FLAGS) counts[key] = days.filter(match).length;
  return counts;
}
