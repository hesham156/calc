"use client";

import {
  BarChart3,
  FileSpreadsheet,
  LayoutDashboard,
  LogOut,
  Menu,
  Settings,
  Upload,
  Users,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getToken, setToken } from "@/lib/api";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "لوحة التحكم", icon: LayoutDashboard },
  { href: "/upload", label: "رفع ملف", icon: Upload },
  { href: "/employees", label: "الموظفون", icon: Users },
  { href: "/reports", label: "التقارير", icon: FileSpreadsheet },
  { href: "/settings", label: "الإعدادات", icon: Settings },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getToken()) router.replace("/login");
    else setReady(true);
  }, [router]);

  if (!ready) return null;

  return (
    <div className="flex min-h-screen">
      {/* sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 right-0 z-40 w-60 border-l bg-card transition-transform lg:static lg:translate-x-0",
          open ? "translate-x-0" : "translate-x-full"
        )}
      >
        <div className="flex h-14 items-center gap-2 border-b px-5">
          <BarChart3 className="h-5 w-5 text-primary" />
          <span className="font-bold">نظام الحضور</span>
        </div>
        <nav className="space-y-1 p-3">
          {NAV.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              onClick={() => setOpen(false)}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                pathname === href
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          ))}
        </nav>
        <div className="absolute bottom-0 w-full border-t p-3">
          <button
            onClick={() => {
              setToken(null);
              router.replace("/login");
            }}
            className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-accent"
          >
            <LogOut className="h-4 w-4" />
            تسجيل الخروج
          </button>
        </div>
      </aside>

      {open && <div className="fixed inset-0 z-30 bg-black/30 lg:hidden" onClick={() => setOpen(false)} />}

      {/* main */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center gap-3 border-b bg-card px-4 lg:hidden">
          <button onClick={() => setOpen(true)} aria-label="القائمة">
            <Menu className="h-5 w-5" />
          </button>
          <span className="font-bold">نظام الحضور</span>
        </header>
        <main className="flex-1 p-4 lg:p-6">{children}</main>
      </div>
    </div>
  );
}
