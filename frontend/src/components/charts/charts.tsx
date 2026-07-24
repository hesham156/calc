"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AttendanceDay } from "@/lib/types";
import { fmtMinutes, STATUS_AR } from "@/lib/utils";

// validated dataviz palette (see globals.css)
const SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"];
const STATUS_COLORS: Record<string, string> = {
  present: "#0ca30c",
  absent: "#d03b3b",
  leave: "#2a78d6",
  weekend: "#898781",
  holiday: "#898781",
  incomplete: "#fab219",
};
const GRID = "#e1e0d9";
const MUTED = "#898781";

const axisProps = {
  tick: { fill: MUTED, fontSize: 11 },
  axisLine: { stroke: "#c3c2b7" },
  tickLine: false as const,
};

function hoursTooltip(value: number | string) {
  return fmtMinutes(Number(value));
}

function dayLabel(d: string) {
  return d.slice(8); // "2026-07-20" -> "20"
}

export function WorkedHoursChart({ days }: { days: AttendanceDay[] }) {
  const data = days.map((d) => ({ day: dayLabel(d.date), قيمة: d.worked_minutes }));
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, left: 8, right: 8 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="day" {...axisProps} />
        <YAxis {...axisProps} tickFormatter={(v) => `${Math.round(v / 60)}س`} width={36} />
        <Tooltip formatter={hoursTooltip} labelFormatter={(l) => `يوم ${l}`} />
        <Bar dataKey="قيمة" name="ساعات العمل" fill={SERIES[0]} radius={[4, 4, 0, 0]} maxBarSize={18} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function LateChart({ days }: { days: AttendanceDay[] }) {
  const data = days.map((d) => ({
    day: dayLabel(d.date),
    تأخير: d.late_minutes,
    "انصراف مبكر": d.early_leave_minutes,
  }));
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, left: 8, right: 8 }} barGap={2}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="day" {...axisProps} />
        <YAxis {...axisProps} tickFormatter={(v) => `${v}د`} width={36} />
        <Tooltip formatter={(v: number | string) => `${v} دقيقة`} labelFormatter={(l) => `يوم ${l}`} />
        <Legend />
        <Bar dataKey="تأخير" fill={SERIES[1]} radius={[4, 4, 0, 0]} maxBarSize={12} />
        <Bar dataKey="انصراف مبكر" fill={SERIES[3]} radius={[4, 4, 0, 0]} maxBarSize={12} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function OvertimeChart({ days }: { days: AttendanceDay[] }) {
  const data = days.map((d) => ({ day: dayLabel(d.date), قيمة: d.overtime_minutes }));
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, left: 8, right: 8 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="day" {...axisProps} />
        <YAxis {...axisProps} tickFormatter={(v) => `${v}د`} width={36} />
        <Tooltip formatter={(v: number | string) => fmtMinutes(Number(v))} labelFormatter={(l) => `يوم ${l}`} />
        <Bar dataKey="قيمة" name="أوفر تايم" fill={SERIES[2]} radius={[4, 4, 0, 0]} maxBarSize={18} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function StatusPie({ days }: { days: AttendanceDay[] }) {
  const counts: Record<string, number> = {};
  for (const d of days) counts[d.status] = (counts[d.status] ?? 0) + 1;
  const data = Object.entries(counts).map(([status, value]) => ({
    name: STATUS_AR[status] ?? status,
    status,
    value,
  }));
  return (
    <ResponsiveContainer width="100%" height={240}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} paddingAngle={2} strokeWidth={2} stroke="#fcfcfb">
          {data.map((entry) => (
            <Cell key={entry.status} fill={STATUS_COLORS[entry.status] ?? MUTED} />
          ))}
        </Pie>
        <Tooltip formatter={(v: number | string) => `${v} يوم`} />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}

function timeToMinutes(t: string | null): number | null {
  if (!t) return null;
  const [h, m] = t.split(":").map(Number);
  return h * 60 + m;
}

export function InOutChart({ days }: { days: AttendanceDay[] }) {
  const data = days
    .filter((d) => d.check_in || d.check_out)
    .map((d) => ({
      day: dayLabel(d.date),
      دخول: timeToMinutes(d.check_in),
      خروج: timeToMinutes(d.check_out),
    }));
  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 8, left: 8, right: 8 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="day" {...axisProps} />
        <YAxis
          {...axisProps}
          domain={[0, 24 * 60]}
          ticks={[360, 600, 840, 1080, 1320]}
          tickFormatter={(v) => fmtMinutes(v)}
          width={44}
        />
        <Tooltip formatter={(v: number | string) => fmtMinutes(Number(v))} labelFormatter={(l) => `يوم ${l}`} />
        <Legend />
        <Line type="monotone" dataKey="دخول" stroke={SERIES[0]} strokeWidth={2} dot={{ r: 3 }} connectNulls />
        <Line type="monotone" dataKey="خروج" stroke={SERIES[1]} strokeWidth={2} dot={{ r: 3 }} connectNulls />
      </LineChart>
    </ResponsiveContainer>
  );
}
