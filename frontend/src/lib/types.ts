export interface Employee {
  id: number;
  code: string;
  name: string;
  department: string;
  position: string;
  summary?: Summary | null;
}

export interface Summary {
  employee_id: number;
  year: number;
  month: number;
  work_days: number;
  present_days: number;
  absent_days: number;
  leave_days: number;
  weekend_days: number;
  worked_minutes: number;
  late_minutes: number;
  early_leave_minutes: number;
  overtime_minutes: number;
  break_minutes: number;
  deduction_minutes: number;
  deduction_amount: number;
  overtime_amount: number;
  net_minutes: number;
}

export interface AttendanceDay {
  id: number;
  date: string;
  weekday: string;
  shift: string;
  /** the shift window this row was judged against */
  work_start: string;
  work_end: string;
  check_in: string | null;
  check_out: string | null;
  out_next_day: boolean;
  break_minutes: number;
  worked_minutes: number;
  late_minutes: number;
  early_leave_minutes: number;
  overtime_minutes: number;
  deduction_minutes: number;
  deduction_amount: number;
  overtime_amount: number;
  status: string;
}

export interface ReportRow extends Omit<AttendanceDay, "shift" | "break_minutes" | "overtime_amount"> {
  employee_id: number;
  employee_name: string;
  employee_code: string;
}

export interface Dashboard {
  employees: number;
  worked_minutes: number;
  overtime_minutes: number;
  late_minutes: number;
  absent_days: number;
  present_days: number;
  leave_days: number;
  deduction_minutes: number;
  deduction_amount: number;
  overtime_amount: number;
  net_minutes: number;
}

export interface UploadInfo {
  id: number;
  filename: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  total_rows: number;
  processed_rows: number;
  template: string;
  error: string;
  created_at: string;
}

export interface WorkSettings {
  work_start: string;
  work_end: string;
  daily_hours: number;
  break_minutes: number;
  grace_minutes: number;
  overtime_after: string;
  hourly_rate: number | null;
  overtime_hourly_rate: number | null;
  deduction_policy: "per_minute" | "free_then_all" | "round_hour" | "none";
  deduction_free_minutes: number;
  count_early_leave: boolean;
  weekend_days: string[];
  company_name: string;
}

export interface MonthRef {
  year: number;
  month: number;
}
