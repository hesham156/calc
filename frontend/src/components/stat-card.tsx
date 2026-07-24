import type { LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function StatCard({
  title,
  value,
  sub,
  icon: Icon,
  tone = "default",
}: {
  title: string;
  value: string | number;
  sub?: string;
  icon: LucideIcon;
  tone?: "default" | "good" | "bad" | "warn";
}) {
  const tones = {
    default: "text-primary bg-primary/10",
    good: "text-[#006300] bg-[#0ca30c]/10",
    bad: "text-[#a02222] bg-[#d03b3b]/10",
    warn: "text-[#8a5b00] bg-[#fab219]/15",
  };
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-5">
        <div className={cn("flex h-11 w-11 shrink-0 items-center justify-center rounded-lg", tones[tone])}>
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm text-muted-foreground">{title}</p>
          <p className="text-xl font-bold tabular-nums">{value}</p>
          {sub && <p className="text-xs text-muted-foreground">{sub}</p>}
        </div>
      </CardContent>
    </Card>
  );
}
