"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { CheckCircle2, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { Shell } from "@/components/shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { api } from "@/lib/api";
import type { WorkSettings } from "@/lib/types";

const schema = z.object({
  company_name: z.string(),
  work_start: z.string().regex(/^\d{2}:\d{2}/, "صيغة الوقت HH:MM"),
  work_end: z.string().regex(/^\d{2}:\d{2}/, "صيغة الوقت HH:MM"),
  daily_hours: z.coerce.number().positive().max(24),
  break_minutes: z.coerce.number().min(0).max(480),
  grace_minutes: z.coerce.number().min(0).max(240),
  overtime_after: z.string().regex(/^\d{2}:\d{2}/, "صيغة الوقت HH:MM"),
  hourly_rate: z.coerce.number().min(0).nullable(),
  overtime_hourly_rate: z.coerce.number().min(0).nullable(),
  deduction_policy: z.enum(["per_minute", "free_then_all", "round_hour", "none"]),
  deduction_free_minutes: z.coerce.number().min(0).max(240),
  count_early_leave: z.boolean(),
  weekend_days: z.array(z.string()),
});
type FormData = z.infer<typeof schema>;

const WEEKDAYS = [
  ["Friday", "الجمعة"], ["Saturday", "السبت"], ["Sunday", "الأحد"], ["Monday", "الاثنين"],
  ["Tuesday", "الثلاثاء"], ["Wednesday", "الأربعاء"], ["Thursday", "الخميس"],
] as const;

const POLICIES = [
  ["per_minute", "خصم كل دقيقة تأخير"],
  ["free_then_all", "سماحية مجانية ثم خصم الكل"],
  ["round_hour", "كل ساعة تأخير = خصم ساعة كاملة"],
  ["none", "بدون خصومات"],
] as const;

export default function SettingsPage() {
  return (
    <Shell>
      <SettingsContent />
    </Shell>
  );
}

function SettingsContent() {
  const [saved, setSaved] = useState(false);
  const [recomputing, setRecomputing] = useState(false);
  const [error, setError] = useState("");

  const {
    register,
    handleSubmit,
    control,
    reset,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  useEffect(() => {
    api.get<WorkSettings>("/api/settings").then((s) => {
      reset({
        ...s,
        work_start: s.work_start.slice(0, 5),
        work_end: s.work_end.slice(0, 5),
        overtime_after: s.overtime_after.slice(0, 5),
      });
    });
  }, [reset]);

  const onSubmit = async (data: FormData) => {
    setError("");
    setSaved(false);
    try {
      await api.put("/api/settings", data);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "فشل الحفظ");
    }
  };

  const recompute = async () => {
    setRecomputing(true);
    try {
      await api.post("/api/analyze", {});
    } finally {
      setRecomputing(false);
    }
  };

  const policy = watch("deduction_policy");

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">إعدادات العمل</h1>
        <p className="text-sm text-muted-foreground">
          جميع الحسابات (التأخير، الأوفر تايم، الخصومات) تُعاد تلقائياً حسب هذه القيم
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>الدوام</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="اسم الشركة (يظهر في التقارير)" error={errors.company_name?.message}>
              <Input {...register("company_name")} />
            </Field>
            <Field label="بداية الدوام" error={errors.work_start?.message}>
              <Input type="time" dir="ltr" {...register("work_start")} />
            </Field>
            <Field label="نهاية الدوام" error={errors.work_end?.message}>
              <Input type="time" dir="ltr" {...register("work_end")} />
            </Field>
            <Field label="ساعات العمل اليومية" error={errors.daily_hours?.message}>
              <Input type="number" step="0.5" dir="ltr" {...register("daily_hours")} />
            </Field>
            <Field label="وقت الراحة (دقائق)" error={errors.break_minutes?.message}>
              <Input type="number" dir="ltr" {...register("break_minutes")} />
            </Field>
            <Field label="سماحية التأخير (دقائق)" error={errors.grace_minutes?.message}>
              <Input type="number" dir="ltr" {...register("grace_minutes")} />
            </Field>
            <Field label="احتساب الأوفر تايم بعد" error={errors.overtime_after?.message}>
              <Input type="time" dir="ltr" {...register("overtime_after")} />
            </Field>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>الأجور والخصومات</CardTitle>
            <CardDescription>اترك سعر الساعة فارغاً (0) إذا لم ترغب باحتساب القيم المالية</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="سعر الساعة" error={errors.hourly_rate?.message}>
              <Input type="number" step="0.01" dir="ltr" {...register("hourly_rate")} />
            </Field>
            <Field label="سعر ساعة الأوفر تايم" error={errors.overtime_hourly_rate?.message}>
              <Input type="number" step="0.01" dir="ltr" {...register("overtime_hourly_rate")} />
            </Field>
            <Field label="طريقة حساب الخصومات" error={errors.deduction_policy?.message}>
              <Select {...register("deduction_policy")}>
                {POLICIES.map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </Select>
            </Field>
            {policy === "free_then_all" && (
              <Field label="الدقائق المجانية" error={errors.deduction_free_minutes?.message}>
                <Input type="number" dir="ltr" {...register("deduction_free_minutes")} />
              </Field>
            )}
            <div className="flex items-center gap-2 pt-6">
              <input id="cel" type="checkbox" className="h-4 w-4" {...register("count_early_leave")} />
              <Label htmlFor="cel">احتساب الانصراف المبكر ضمن الخصومات</Label>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>أيام العطلة الأسبوعية</CardTitle>
          </CardHeader>
          <CardContent>
            <Controller
              control={control}
              name="weekend_days"
              render={({ field }) => (
                <div className="flex flex-wrap gap-3">
                  {WEEKDAYS.map(([en, arText]) => (
                    <label key={en} className="flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm has-[:checked]:border-primary has-[:checked]:bg-primary/5">
                      <input
                        type="checkbox"
                        className="h-4 w-4"
                        checked={field.value?.includes(en) ?? false}
                        onChange={(e) => {
                          const cur = field.value ?? [];
                          field.onChange(e.target.checked ? [...cur, en] : cur.filter((d) => d !== en));
                        }}
                      />
                      {arText}
                    </label>
                  ))}
                </div>
              )}
            />
          </CardContent>
        </Card>

        {error && <p className="text-sm text-destructive">{error}</p>}

        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "جارٍ الحفظ..." : "حفظ الإعدادات"}
          </Button>
          <Button type="button" variant="outline" onClick={recompute} disabled={recomputing}>
            <RefreshCw className={recomputing ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
            إعادة احتساب جميع البيانات
          </Button>
          {saved && (
            <span className="flex items-center gap-1 text-sm text-[#006300]">
              <CheckCircle2 className="h-4 w-4" /> تم الحفظ
            </span>
          )}
        </div>
      </form>
    </div>
  );
}

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {children}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
