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
import { useState } from "react";
import { StatusBadge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import type { AttendanceDay } from "@/lib/types";
import { fmtMinutes, WEEKDAYS_AR } from "@/lib/utils";

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
  { accessorKey: "check_in", header: "الدخول", cell: ({ row }) => row.original.check_in ?? "—" },
  {
    accessorKey: "check_out",
    header: "الخروج",
    cell: ({ row }) =>
      row.original.check_out ? `${row.original.check_out}${row.original.out_next_day ? "+1" : ""}` : "—",
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

export function AttendanceTable({ days }: { days: AttendanceDay[] }) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [filter, setFilter] = useState("");

  const table = useReactTable({
    data: days,
    columns,
    state: { sorting, globalFilter: filter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  return (
    <div className="space-y-3">
      <Input
        placeholder="بحث في السجل..."
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="max-w-xs"
      />
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full min-w-[800px] text-sm">
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
            {table.getRowModel().rows.length === 0 && (
              <tr>
                <td colSpan={columns.length} className="px-3 py-8 text-center text-muted-foreground">
                  لا توجد سجلات
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
