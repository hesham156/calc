"use client";

import { useEffect, useState } from "react";
import { Select } from "@/components/ui/select";
import { api } from "@/lib/api";
import type { MonthRef } from "@/lib/types";
import { MONTHS_AR } from "@/lib/utils";

export function useMonths(): { months: MonthRef[]; loading: boolean } {
  const [months, setMonths] = useState<MonthRef[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api
      .get<MonthRef[]>("/api/months")
      .then(setMonths)
      .catch(() => setMonths([]))
      .finally(() => setLoading(false));
  }, []);
  return { months, loading };
}

export function MonthPicker({
  months,
  value,
  onChange,
}: {
  months: MonthRef[];
  value: MonthRef | null;
  onChange: (m: MonthRef) => void;
}) {
  if (months.length === 0) return null;
  return (
    <Select
      className="w-44"
      value={value ? `${value.year}-${value.month}` : ""}
      onChange={(e) => {
        const [y, m] = e.target.value.split("-").map(Number);
        onChange({ year: y, month: m });
      }}
    >
      {months.map((m) => (
        <option key={`${m.year}-${m.month}`} value={`${m.year}-${m.month}`}>
          {MONTHS_AR[m.month - 1]} {m.year}
        </option>
      ))}
    </Select>
  );
}
