"use client";

import {
  AlarmClock,
  Banknote,
  CalendarX,
  Clock,
  Hourglass,
  TrendingUp,
  UserCheck,
  Users,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { MonthPicker, useMonths } from "@/components/month-picker";
import { Shell } from "@/components/shell";
import { StatCard } from "@/components/stat-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { Dashboard, MonthRef } from "@/lib/types";
import { fmtMinutes, MONTHS_AR } from "@/lib/utils";

export default function DashboardPage() {
  return (
    <Shell>
      <DashboardContent />
    </Shell>
  );
}

function DashboardContent() {
  const { months, loading: monthsLoading } = useMonths();
  const [month, setMonth] = useState<MonthRef | null>(null);
  const [data, setData] = useState<Dashboard | null>(null);

  useEffect(() => {
    if (months.length > 0 && !month) setMonth(months[0]);
  }, [months, month]);

  useEffect(() => {
    if (!month) return;
    api.get<Dashboard>(`/api/summary?year=${month.year}&month=${month.month}`).then(setData).catch(() => {});
  }, [month]);

  if (!monthsLoading && months.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-24 text-center">
        <Hourglass className="h-10 w-10 text-muted-foreground" />
        <h2 className="text-lg font-semibold">لا توجد بيانات بعد</h2>
        <p className="text-sm text-muted-foreground">ابدأ برفع ملف الحضور والانصراف الشهري</p>
        <Link
          href="/upload"
          className="inline-flex h-9 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          رفع ملف الآن
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">لوحة التحكم</h1>
          {month && (
            <p className="text-sm text-muted-foreground">
              ملخص شهر {MONTHS_AR[month.month - 1]} {month.year}
            </p>
          )}
        </div>
        <MonthPicker months={months} value={month} onChange={setMonth} />
      </div>

      {data && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard title="عدد الموظفين" value={data.employees} icon={Users} />
            <StatCard title="إجمالي ساعات العمل" value={fmtMinutes(data.worked_minutes)} icon={Clock} />
            <StatCard title="إجمالي الأوفر تايم" value={fmtMinutes(data.overtime_minutes)} icon={TrendingUp} tone="good" />
            <StatCard
              title="إجمالي التأخير"
              value={fmtMinutes(data.late_minutes)}
              sub={`${data.late_minutes} دقيقة`}
              icon={AlarmClock}
              tone="warn"
            />
            <StatCard title="أيام الحضور" value={data.present_days} icon={UserCheck} tone="good" />
            <StatCard title="إجمالي الغياب" value={`${data.absent_days} يوم`} icon={CalendarX} tone="bad" />
            <StatCard
              title="إجمالي الخصومات"
              value={fmtMinutes(data.deduction_minutes)}
              sub={data.deduction_amount > 0 ? `${data.deduction_amount} (قيمة)` : undefined}
              icon={Banknote}
              tone="bad"
            />
            <StatCard title="صافي ساعات العمل" value={fmtMinutes(data.net_minutes)} icon={Hourglass} />
          </div>

          <Card>
            <CardHeader>
              <CardTitle>روابط سريعة</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-3">
              <Link href="/employees" className="text-sm text-primary hover:underline">
                عرض تقارير الموظفين ←
              </Link>
              <Link href="/reports" className="text-sm text-primary hover:underline">
                جدول التقارير الكامل ←
              </Link>
              <Link href="/settings" className="text-sm text-primary hover:underline">
                تعديل إعدادات العمل ←
              </Link>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
