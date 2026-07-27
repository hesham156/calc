"use client";

import {
  type ColumnDef,
  type SortingState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { ArrowUpDown } from "lucide-react";
import { useMemo, useState } from "react";
import { DayFilters } from "@/components/day-filters";
import { StatusBadge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { countByFlag, type DayFlag, matchesFlags } from "@/lib/filters";
import type { AttendanceDay } from "@/lib/types";
import { fmtMinutes, fmtTime, WEEKDAYS_AR } from "@/lib/utils";

function sortableHeader(label: string) {
  // eslint-disable-next-line react/display-name
  return ({ column }: { column: { toggleSorting: (asc?: boolean) => void; getIsSorted: () => false | string } }) => (
    <button
      className="inline-flex items-center gap-1 font-semibold"
      onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
    >
      {label}
      <ArrowUpDown className="h-3 w-3 opacity-50" />
    </button>
  );
}

const columns: ColumnDef<AttendanceDay>[] = [
  { accessorKey: "date", header: sortableHeader("التاريخ"), cell: ({ row }) => row.original.date },
  {
    accessorKey: "weekday",
    header: "اليوم",
    cell: ({ row }) => WEEKDAYS_AR[row.original.weekday] ?? row.original.weekday,
  },
  {
    accessorKey: "work_start",
    header: "بداية الدوام",
    cell: ({ row }) => <span className="tabular-nums text-muted-foreground">{fmtTime(row.original.work_start)}</span>,
  },
  {
    accessorKey: "work_end",
    header: "نهاية الدوام",
    cell: ({ row }) => <span className="tabular-nums text-muted-foreground">{fmtTime(row.original.work_end)}</span>,
  },
  {
    accessorKey: "check_in",
    header: "الدخول",
    cell: ({ row }) => <span className="tabular-nums">{fmtTime(row.original.check_in)}</span>,
  },
  {
    accessorKey: "check_out",
    header: "الخروج",
    cell: ({ row }) => (
      <span className="tabular-nums">
        {row.original.check_out ? `${fmtTime(row.original.check_out)}${row.original.out_next_day ? "+1" : ""}` : "—"}
      </span>
    ),
  },
  {
    accessorKey: "worked_minutes",
    header: sortableHeader("مدة العمل"),
    cell: ({ row }) => <span className="tabular-nums">{fmtMinutes(row.original.worked_minutes)}</span>,
  },
  {
    accessorKey: "late_minutes",
    header: sortableHeader("التأخير"),
    cell: ({ row }) =>
      row.original.late_minutes > 0 ? (
        <span className="tabular-nums text-[#9c3c14]">{row.original.late_minutes} د</span>
      ) : (
        "—"
      ),
  },
  {
    accessorKey: "early_leave_minutes",
    header: "انصراف مبكر",
    cell: ({ row }) =>
      row.original.early_leave_minutes > 0 ? (
        <span className="tabular-nums">{row.original.early_leave_minutes} د</span>
      ) : (
        "—"
      ),
  },
  {
    accessorKey: "overtime_minutes",
    header: sortableHeader("أوفر تايم"),
    cell: ({ row }) =>
      row.original.overtime_minutes > 0 ? (
        <span className="tabular-nums text-[#006300]">{fmtMinutes(row.original.overtime_minutes)}</span>
      ) : (
        "—"
      ),
  },
  {
    accessorKey: "deduction_minutes",
    header: "الخصم",
    cell: ({ row }) => {
      const d = row.original;
      if (d.deduction_minutes <= 0) return "—";
      return (
        <span className="tabular-nums">
          {d.deduction_minutes} د{d.deduction_amount > 0 ? ` (${d.deduction_amount})` : ""}
        </span>
      );
    },
  },
  { accessorKey: "status", header: "الحالة", cell: ({ row }) => <StatusBadge status={row.original.status} /> },
];

/** Totals of whatever rows the table is currently showing. */
function sumDays(days: AttendanceDay[]) {
  return days.reduce(
    (acc, d) => ({
      count: acc.count + 1,
      worked: acc.worked + d.worked_minutes,
      late: acc.late + d.late_minutes,
      early: acc.early + d.early_leave_minutes,
      overtime: acc.overtime + d.overtime_minutes,
      deductionMinutes: acc.deductionMinutes + d.deduction_minutes,
      deductionAmount: acc.deductionAmount + d.deduction_amount,
    }),
    { count: 0, worked: 0, late: 0, early: 0, overtime: 0, deductionMinutes: 0, deductionAmount: 0 }
  );
}

export function AttendanceTable({ days }: { days: AttendanceDay[] }) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [filter, setFilter] = useState("");
  const [flags, setFlags] = useState<DayFlag[]>([]);

  const counts = useMemo(() => countByFlag(days), [days]);
  const rows = useMemo(() => days.filter((d) => matchesFlags(d, flags)), [days, flags]);

  const table = useReactTable({
    data: rows,
    columns,
    state: { sorting, globalFilter: filter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  const visible = table.getRowModel().rows;
  const totals = sumDays(visible.map((r) => r.original));

  return (
    <div className="space-y-3">
      <Input
        placeholder="بحث في السجل..."
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="max-w-xs"
      />
      <DayFilters value={flags} onChange={setFlags} counts={counts} />
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full min-w-[980px] text-sm">
          <thead className="bg-secondary/60">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((h) => (
                  <th key={h.id} className="whitespace-nowrap px-3 py-2.5 text-right font-semibold">
                    {h.isPlaceholder ? null : flexRender(h.column.columnDef.header, h.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} className="border-t hover:bg-accent/40">
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="whitespace-nowrap px-3 py-2">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
            {visible.length === 0 && (
              <tr>
                <td colSpan={columns.length} className="px-3 py-8 text-center text-muted-foreground">
                  لا توجد سجلات
                </td>
              </tr>
            )}
          </tbody>
          {visible.length > 0 && (
            <tfoot className="border-t-2 bg-secondary/60 font-semibold">
              <tr>
                <td className="whitespace-nowrap px-3 py-2.5">الإجمالي</td>
                <td className="whitespace-nowrap px-3 py-2.5 text-muted-foreground">{totals.count} يوم</td>
                <td colSpan={4} />
                <td className="whitespace-nowrap px-3 py-2.5 tabular-nums">{fmtMinutes(totals.worked)}</td>
                <td className="whitespace-nowrap px-3 py-2.5 tabular-nums text-[#9c3c14]">{totals.late} د</td>
                <td className="whitespace-nowrap px-3 py-2.5 tabular-nums">{totals.early} د</td>
                <td className="whitespace-nowrap px-3 py-2.5 tabular-nums text-[#006300]">
                  {fmtMinutes(totals.overtime)}
                </td>
                <td className="whitespace-nowrap px-3 py-2.5 tabular-nums">
                  {totals.deductionMinutes} د
                  {totals.deductionAmount > 0 && ` (${totals.deductionAmount.toFixed(2)})`}
                </td>
                <td />
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    </div>
  );
}
