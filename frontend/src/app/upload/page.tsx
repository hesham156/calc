"use client";

import { CheckCircle2, FileSpreadsheet, UploadCloud, XCircle } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { useDropzone, type FileRejection } from "react-dropzone";
import { Shell } from "@/components/shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { api } from "@/lib/api";
import type { UploadInfo } from "@/lib/types";
import { cn } from "@/lib/utils";

const MAX_MB = 50;
const ACCEPTED = {
  "text/csv": [".csv"],
  "application/vnd.ms-excel": [".xls"],
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
};

export default function UploadPage() {
  return (
    <Shell>
      <UploadContent />
    </Shell>
  );
}

function UploadContent() {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [upload, setUpload] = useState<UploadInfo | null>(null);
  const [history, setHistory] = useState<UploadInfo[]>([]);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refreshHistory = useCallback(() => {
    api.get<UploadInfo[]>("/api/uploads").then(setHistory).catch(() => {});
  }, []);
  useEffect(refreshHistory, [refreshHistory]);
  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  const onDrop = useCallback((accepted: File[], rejected: FileRejection[]) => {
    setError("");
    setUpload(null);
    if (rejected.length > 0) {
      const code = rejected[0].errors[0]?.code;
      setError(code === "file-too-large" ? `الملف أكبر من ${MAX_MB} ميجابايت` : "نوع الملف غير مدعوم — المسموح: CSV / XLS / XLSX");
      return;
    }
    if (accepted[0]) setFile(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    maxSize: MAX_MB * 1024 * 1024,
    multiple: false,
  });

  const startUpload = async () => {
    if (!file) return;
    setError("");
    try {
      const info = await api.upload<UploadInfo>("/api/upload", file);
      setUpload(info);
      pollRef.current = setInterval(async () => {
        const status = await api.get<UploadInfo>(`/api/uploads/${info.id}`);
        setUpload(status);
        if (status.status === "completed" || status.status === "failed") {
          if (pollRef.current) clearInterval(pollRef.current);
          refreshHistory();
        }
      }, 700);
    } catch (e) {
      setError(e instanceof Error ? e.message : "فشل الرفع");
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">رفع ملف الحضور</h1>
        <p className="text-sm text-muted-foreground">
          يدعم النظام ملفات CSV / XLS / XLSX من أجهزة البصمة (ZKTeco BioTime، Suprema، وغيرها) — يتم اكتشاف الأعمدة تلقائياً
        </p>
      </div>

      <Card>
        <CardContent className="p-5">
          <div
            {...getRootProps()}
            className={cn(
              "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-10 text-center transition-colors",
              isDragActive ? "border-primary bg-primary/5" : "border-input hover:border-primary/50"
            )}
          >
            <input {...getInputProps()} />
            <UploadCloud className="h-10 w-10 text-muted-foreground" />
            {file ? (
              <div className="flex items-center gap-2 text-sm font-medium">
                <FileSpreadsheet className="h-4 w-4 text-primary" />
                {file.name}
                <span className="text-muted-foreground">({(file.size / 1024).toFixed(1)} KB)</span>
              </div>
            ) : (
              <>
                <p className="font-medium">اسحب الملف هنا أو اضغط للاختيار</p>
                <p className="text-xs text-muted-foreground">CSV, XLS, XLSX — حتى {MAX_MB} ميجابايت</p>
              </>
            )}
          </div>

          {error && (
            <p className="mt-3 flex items-center gap-2 text-sm text-destructive">
              <XCircle className="h-4 w-4" /> {error}
            </p>
          )}

          <div className="mt-4 flex items-center gap-3">
            <Button onClick={startUpload} disabled={!file || upload?.status === "processing"}>
              رفع وتحليل
            </Button>
            {file && (
              <Button variant="ghost" onClick={() => { setFile(null); setUpload(null); }}>
                إلغاء
              </Button>
            )}
          </div>

          {upload && (
            <div className="mt-5 space-y-2 rounded-lg border bg-secondary/40 p-4">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">
                  {upload.status === "processing" || upload.status === "pending"
                    ? "جارٍ التحليل..."
                    : upload.status === "completed"
                      ? "اكتمل التحليل"
                      : "فشل التحليل"}
                </span>
                <span className="tabular-nums text-muted-foreground">{upload.progress}%</span>
              </div>
              <Progress value={upload.progress} />
              {upload.status === "completed" && (
                <div className="flex flex-wrap items-center gap-2 pt-1 text-sm text-[#006300]">
                  <CheckCircle2 className="h-4 w-4" />
                  تمت معالجة {upload.processed_rows} سجل
                  {upload.template && <span className="text-muted-foreground">(القالب: {upload.template})</span>}
                  <Link href="/employees" className="text-primary hover:underline">عرض النتائج ←</Link>
                </div>
              )}
              {upload.status === "failed" && (
                <p className="text-sm text-destructive">{upload.error}</p>
              )}
              {upload.status === "completed" && upload.error && (
                <p className="text-xs text-muted-foreground">ملاحظات: {upload.error}</p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {history.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>آخر الملفات المرفوعة</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="divide-y text-sm">
              {history.slice(0, 8).map((u) => (
                <div key={u.id} className="flex items-center justify-between gap-3 py-2">
                  <span className="truncate">{u.filename}</span>
                  <span
                    className={cn(
                      "shrink-0 text-xs",
                      u.status === "completed" ? "text-[#006300]" : u.status === "failed" ? "text-destructive" : "text-muted-foreground"
                    )}
                  >
                    {u.status === "completed" ? `✓ ${u.processed_rows} سجل` : u.status === "failed" ? "✗ فشل" : "..."}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
