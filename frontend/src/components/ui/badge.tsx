import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium",
  {
    variants: {
      variant: {
        default: "bg-primary/10 text-primary",
        good: "bg-[#0ca30c]/10 text-[#006300]",
        warning: "bg-[#fab219]/15 text-[#8a5b00]",
        serious: "bg-[#ec835a]/15 text-[#9c3c14]",
        critical: "bg-[#d03b3b]/10 text-[#a02222]",
        muted: "bg-muted text-muted-foreground",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; variant: BadgeProps["variant"]; icon: string }> = {
    present: { label: "حاضر", variant: "good", icon: "✓" },
    absent: { label: "غائب", variant: "critical", icon: "✗" },
    leave: { label: "إجازة", variant: "default", icon: "◆" },
    weekend: { label: "عطلة", variant: "muted", icon: "○" },
    holiday: { label: "عطلة رسمية", variant: "muted", icon: "○" },
    incomplete: { label: "بصمة ناقصة", variant: "warning", icon: "!" },
  };
  const s = map[status] ?? { label: status, variant: "muted" as const, icon: "•" };
  return (
    <Badge variant={s.variant}>
      <span aria-hidden>{s.icon}</span>
      {s.label}
    </Badge>
  );
}
