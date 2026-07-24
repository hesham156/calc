"use client";

import {
  AlarmClock,
  Banknote,
  CalendarCheck,
  CalendarX,
  Clock,
  Coffee,
  Download,
  Hourglass,
  Plane,
  TrendingUp,
} from "lucide-react";
import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
  InOutChart,
  LateChart,
  OvertimeChart,
  StatusPie,
  WorkedHoursChart,
} from "@/components/charts/charts";
import { AttendanceTable } from "@/components/attendance-table";
import { MonthPicker, useMonths } from "@/components/month-picker";
import { Shell } from "@/components/shell";
import { StatCard } from "@/components/stat-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { AttendanceDay, Employee, MonthRef, Summary } from "@/lib/types";
import { fmtMinutes, MONTHS_AR } from "@/lib/utils";

export default function EmployeeDetailPage() {
  return (
    <Shell>
      <EmployeeDetail />
    </Shell>
  );
}

function EmployeeDetail() {
  const { id } = useParams<{ id: string }>();
  const search = useSearchParams();
  const { months } = useMonths();
  const [month, setMonth] = useState<MonthRef | null>(() => {
    const y = Number(search.get("year"));
    const m = Number(search.get("month"));
    return y && m ? { year: y, month: m } : null;
  });
  const [employee, setEmployee] = useState<Employee | null>(null);
  const [days, setDays] = useState<AttendanceDay[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [exporting, setExporting] = useState("");

  useEffect(() => {
    if (months.length > 0 && !month) setMonth(months[0]);
  }, [months, month]);

  useEffect(() => {
    api.get<Employee>(`/api/employees/${id}`).then(setEmployee).catch(() => {});
  }, [id]);

  useEffect(() => {
    if (!month) return;
    const qs = `year=${month.year}&month=${month.month}`;
    api.get<AttendanceDay[]>(`/api/employees/${id}/attendance?${qs}`).then(setDays).catch(() => {});
    api.get<Summary | null>(`/api/employees/${id}/summary?${qs}`).then(setSummary).catch(() => {});
  }, [id, month]);

  const doExport = async (kind: "pdf" | "excel" | "csv") => {
    if (!month || !employee) return;
    setExporting(kind);
    const ext = kind === "excel" ? "xlsx" : kind;
    try {
      await api.download(
        `/api/export/${kind}?employee_id=${id}&year=${month.year}&month=${month.month}`,
        `attendance_${employee.code}_${month.year}-${String(month.month).padStart(2, "0")}.${ext}`
      );
    } finally {
      setExporting("");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">{employee?.name ?? "..."}</h1>
          <p className="text-sm text-muted-foreground">
            #{employee?.code}
            {employee?.department && ` · ${employee.department}`}
            {employee?.position && ` · ${employee.position}`}
            {month && ` — ${MONTHS_AR[month.month - 1]} ${month.year}`}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <MonthPicker months={months} value={month} onChange={setMonth} />
          {(["pdf", "excel", "csv"] as const).map((kind) => (
            <Button
              key={kind}
              variant="outline"
              size="sm"
              disabled={!!exporting}
              onClick={() => doExport(kind)}
            >
              <Download className="h-3.5 w-3.5" />
              {exporting === kind ? "..." : kind.toUpperCase()}
            </Button>
          ))}
        </div>
      </div>

      {summary && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-5">
          <StatCard title="أيام العمل" value={summary.work_days} icon={CalendarCheck} />
          <StatCard title="أيام الحضور" value={summary.present_days} icon={CalendarCheck} tone="good" />
          <StatCard title="الغياب" value={summary.absent_days} icon={CalendarX} tone="bad" />
          <StatCard title="الإجازات" value={summary.leave_days} icon={Plane} />
          <StatCard title="ساعات العمل" value={fmtMinutes(summary.worked_minutes)} icon={Clock} />
          <StatCard
            title="التأخير"
            value={fmtMinutes(summary.late_minutes)}
            sub={`${summary.late_minutes} دقيقة`}
            icon={AlarmClock}
            tone="warn"
          />
          <StatCard title="انصراف مبكر" value={fmtMinutes(summary.early_leave_minutes)} icon={AlarmClock} tone="warn" />
          <StatCard title="أوفر تايم" value={fmtMinutes(summary.overtime_minutes)} icon={TrendingUp} tone="good" />
          <StatCard title="الراحة" value={fmtMinutes(summary.break_minutes)} icon={Coffee} />
          <StatCard
            title="الخصومات"
            value={fmtMinutes(summary.deduction_minutes)}
            sub={summary.deduction_amount > 0 ? `القيمة: ${summary.deduction_amount}` : undefined}
            icon={Banknote}
            tone="bad"
          />
          <StatCard
            title="مستحقات الأوفر تايم"
            value={summary.overtime_amount > 0 ? summary.overtime_amount : "—"}
            icon={Banknote}
            tone="good"
          />
          <StatCard title="صافي ساعات العمل" value={fmtMinutes(summary.net_minutes)} icon={Hourglass} />
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <ChartCard title="ساعات العمل اليومية">
          <WorkedHoursChart days={days} />
        </ChartCard>
        <ChartCard title="التأخير والانصراف المبكر (دقائق)">
          <LateChart days={days} />
        </ChartCard>
        <ChartCard title="الأوفر تايم اليومي">
          <OvertimeChart days={days} />
        </ChartCard>
        <ChartCard title="توزيع أيام الشهر">
          <StatusPie days={days} />
        </ChartCard>
        <ChartCard title="أوقات الدخول والخروج" className="xl:col-span-2">
          <InOutChart days={days} />
        </ChartCard>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>السجل اليومي التفصيلي</CardTitle>
        </CardHeader>
        <CardContent>
          <AttendanceTable days={days} />
        </CardContent>
      </Card>
    </div>
  );
}

function ChartCard({
  title,
  children,
  className,
}: {
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-sm">{title}</CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}
