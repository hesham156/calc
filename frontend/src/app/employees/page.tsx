"use client";

import { Search, User } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { MonthPicker, useMonths } from "@/components/month-picker";
import { Shell } from "@/components/shell";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import type { Employee, MonthRef } from "@/lib/types";
import { fmtMinutes } from "@/lib/utils";

export default function EmployeesPage() {
  return (
    <Shell>
      <EmployeesContent />
    </Shell>
  );
}

function EmployeesContent() {
  const { months } = useMonths();
  const [month, setMonth] = useState<MonthRef | null>(null);
  const [q, setQ] = useState("");
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (months.length > 0 && !month) setMonth(months[0]);
  }, [months, month]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (month) {
      params.set("year", String(month.year));
      params.set("month", String(month.month));
    }
    const t = setTimeout(() => {
      api
        .get<Employee[]>(`/api/employees?${params}`)
        .then(setEmployees)
        .catch(() => {})
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(t);
  }, [q, month]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">الموظفون</h1>
        <MonthPicker months={months} value={month} onChange={setMonth} />
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute right-3 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="بحث بالاسم أو رقم الموظف..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="pr-9"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {employees.map((e) => (
          <Link key={e.id} href={`/employees/${e.id}${month ? `?year=${month.year}&month=${month.month}` : ""}`}>
            <Card className="transition-shadow hover:shadow-md">
              <CardContent className="p-5">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                    <User className="h-5 w-5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-semibold">{e.name}</p>
                    <p className="text-xs text-muted-foreground">
                      #{e.code}
                      {e.department && ` · ${e.department}`}
                      {e.position && ` · ${e.position}`}
                    </p>
                  </div>
                </div>
                {e.summary && (
                  <div className="mt-4 grid grid-cols-3 gap-2 border-t pt-3 text-center text-xs">
                    <div>
                      <p className="font-bold tabular-nums">{fmtMinutes(e.summary.worked_minutes)}</p>
                      <p className="text-muted-foreground">ساعات العمل</p>
                    </div>
                    <div>
                      <p className="font-bold tabular-nums text-[#9c3c14]">{e.summary.late_minutes} د</p>
                      <p className="text-muted-foreground">التأخير</p>
                    </div>
                    <div>
                      <p className="font-bold tabular-nums text-[#a02222]">{e.summary.absent_days}</p>
                      <p className="text-muted-foreground">الغياب</p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      {!loading && employees.length === 0 && (
        <p className="py-12 text-center text-muted-foreground">لا يوجد موظفون — قم برفع ملف حضور أولاً</p>
      )}
    </div>
  );
}
