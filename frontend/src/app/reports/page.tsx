"use client";

import { Search } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { DayFilters } from "@/components/day-filters";
import { MonthPicker, useMonths } from "@/components/month-picker";
import { Shell } from "@/components/shell";
import { StatusBadge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { api } from "@/lib/api";
import type { DayFlag } from "@/lib/filters";
import type { MonthRef, ReportRow } from "@/lib/types";
import { fmtMinutes, STATUS_AR } from "@/lib/utils";

export default function ReportsPage() {
  return (
    <Shell>
      <ReportsContent />
    </Shell>
  );
}

function ReportsContent() {
  const { months } = useMonths();
  const [month, setMonth] = useState<MonthRef | null>(null);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [flags, setFlags] = useState<DayFlag[]>([]);
  const [rows, setRows] = useState<ReportRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (months.length > 0 && !month) setMonth(months[0]);
  }, [months, month]);

  useEffect(() => {
    if (!month) return;
    const params = new URLSearchParams({
      year: String(month.year),
      month: String(month.month),
      page_size: "1000",
    });
    if (q) params.set("q", q);
    if (status) params.set("status", status);
    for (const f of flags) params.append("flags", f);
    const t = setTimeout(() => {
      api
        .get<ReportRow[]>(`/api/reports?${params}`)
        .then(setRows)
        .catch(() => {})
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(t);
  }, [month, q, status, flags]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">التقارير</h1>
        <MonthPicker months={months} value={month} onChange={setMonth} />
      </div>

      <div className="flex flex-wrap gap-3">
        <div className="relative w-full max-w-sm">
          <Search className="absolute right-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="بحث باسم أو رقم الموظف..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="pr-9"
          />
        </div>
        <Select className="w-40" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">كل الحالات</option>
          {Object.entries(STATUS_AR).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </Select>
      </div>

      <DayFilters value={flags} onChange={setFlags} />

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-sm">
              <thead className="bg-secondary/60">
                <tr>
                  {["الموظف", "التاريخ", "الدخول", "الخروج", "مدة العمل", "التأخير", "انصراف مبكر", "أوفر تايم", "الخصم", "الحالة"].map((h) => (
                    <th key={h} className="whitespace-nowrap px-3 py-2.5 text-right font-semibold">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id} className="border-t hover:bg-accent/40">
                    <td className="whitespace-nowrap px-3 py-2">
                      <Link href={`/employees/${r.employee_id}${month ? `?year=${month.year}&month=${month.month}` : ""}`} className="text-primary hover:underline">
                        {r.employee_name}
                      </Link>
                      <span className="mr-1 text-xs text-muted-foreground">#{r.employee_code}</span>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 tabular-nums">{r.date}</td>
                    <td className="px-3 py-2 tabular-nums">{r.check_in ?? "—"}</td>
                    <td className="px-3 py-2 tabular-nums">{r.check_out ? `${r.check_out}${r.out_next_day ? "+1" : ""}` : "—"}</td>
                    <td className="px-3 py-2 tabular-nums">{fmtMinutes(r.worked_minutes)}</td>
                    <td className="px-3 py-2 tabular-nums">{r.late_minutes > 0 ? `${r.late_minutes} د` : "—"}</td>
                    <td className="px-3 py-2 tabular-nums">{r.early_leave_minutes > 0 ? `${r.early_leave_minutes} د` : "—"}</td>
                    <td className="px-3 py-2 tabular-nums">{r.overtime_minutes > 0 ? fmtMinutes(r.overtime_minutes) : "—"}</td>
                    <td className="px-3 py-2 tabular-nums">
                      {r.deduction_minutes > 0 ? `${r.deduction_minutes} د${r.deduction_amount > 0 ? ` (${r.deduction_amount})` : ""}` : "—"}
                    </td>
                    <td className="px-3 py-2"><StatusBadge status={r.status} /></td>
                  </tr>
                ))}
                {!loading && rows.length === 0 && (
                  <tr>
                    <td colSpan={10} className="px-3 py-10 text-center text-muted-foreground">لا توجد سجلات</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
