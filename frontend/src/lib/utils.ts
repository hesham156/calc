import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** 495 -> "08:15" */
export function fmtMinutes(m: number): string {
  const sign = m < 0 ? "-" : "";
  const abs = Math.abs(m);
  return `${sign}${String(Math.floor(abs / 60)).padStart(2, "0")}:${String(abs % 60).padStart(2, "0")}`;
}

/** 495 -> "8.25 س" */
export function fmtHours(m: number): string {
  return `${(m / 60).toFixed(1)} س`;
}

/** "08:00:00" -> "08:00" */
export function fmtTime(t: string | null | undefined): string {
  return t ? t.slice(0, 5) : "—";
}

export const STATUS_AR: Record<string, string> = {
  present: "حاضر",
  absent: "غائب",
  leave: "إجازة",
  weekend: "عطلة",
  holiday: "عطلة رسمية",
  incomplete: "بصمة ناقصة",
};

export const MONTHS_AR = [
  "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
  "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
];

export const WEEKDAYS_AR: Record<string, string> = {
  Sunday: "الأحد", Monday: "الاثنين", Tuesday: "الثلاثاء", Wednesday: "الأربعاء",
  Thursday: "الخميس", Friday: "الجمعة", Saturday: "السبت",
};
