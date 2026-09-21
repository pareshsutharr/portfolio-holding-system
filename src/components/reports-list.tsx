"use client";

import {
  AlertTriangle,
  ArrowRight,
  Check,
  Clock,
  Download,
  FileBarChart,
  LoaderCircle,
  Plus,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { authFetch } from "@/lib/auth";
import { ReportDownloadDialog } from "@/components/report-download-dialog";

const API_URL = process.env.NEXT_PUBLIC_API_URL
  ?? (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : "");

type AnalysisStatus = {
  id: string;
  status: "processing" | "complete" | "failed";
  created_at: string;
  completed_at?: string;
  filename: string;
  portfolio_value?: number;
  holdings?: number;
  risk_score?: number;
  risk_level?: string;
  report_number?: string | null;
  error?: string;
};

type DashboardResponse = {
  recent_analyses: AnalysisStatus[];
  total_analyses: number;
};

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);

const formatDate = (value: string) =>
  new Date(value).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });

export function ReportsList() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [downloadRunId, setDownloadRunId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    authFetch(`${API_URL}/api/dashboard`)
      .then(async (response) => {
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail ?? "Could not load reports");
        return payload as DashboardResponse;
      })
      .then((payload) => {
        if (!cancelled) setData(payload);
      })
      .catch((caught) => {
        if (!cancelled) setError(caught instanceof Error ? caught.message : "Could not load reports");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="mx-auto max-w-[1100px] px-4 py-8 md:px-8 md:py-9">
      <section className="mb-7 flex flex-wrap items-end justify-between gap-6">
        <div>
          <p className="mb-1.5 text-[9px] font-extrabold tracking-[1.5px] text-[#89938f] uppercase">
            Portfolios &amp; Reports
          </p>
          <h1 className="text-[28px] font-bold leading-tight text-[#173337] md:text-[30px]">
            Your analyzed portfolios
          </h1>
          <p className="mt-1.5 text-[13px] text-muted-text">
            Every portfolio you&apos;ve uploaded and analyzed, with risk scores and downloadable reports.
          </p>
        </div>
        <Button asChild className="h-10 gap-2 rounded-lg bg-teal px-4 text-[12px] font-bold text-white hover:bg-teal-dark">
          <Link href="/dashboard-v2">
            <Plus size={17} /> New analysis
          </Link>
        </Button>
      </section>

      {loading && (
        <Card className="flex items-center justify-center gap-2 rounded-[13px] p-12 text-sm text-muted-text">
          <LoaderCircle size={16} className="animate-spin" /> Loading your reports…
        </Card>
      )}

      {!loading && error && (
        <Card className="flex flex-col items-center gap-2 rounded-[13px] p-12 text-center">
          <AlertTriangle size={22} className="text-rose" />
          <p className="text-sm font-semibold text-[#173337]">Couldn&apos;t reach the analysis service</p>
          <p className="max-w-sm text-xs text-muted-text">{error}</p>
        </Card>
      )}

      {!loading && !error && data && data.recent_analyses.length === 0 && (
        <Card className="flex flex-col items-center gap-3 rounded-[13px] p-12 text-center">
          <div className="grid size-12 place-items-center rounded-full bg-[#ecf4f3] text-[#2a655e]">
            <FileBarChart size={22} />
          </div>
          <p className="text-sm font-semibold text-[#173337]">No portfolios analyzed yet</p>
          <p className="max-w-sm text-xs text-muted-text">
            Upload a holdings workbook from the overview page to see it here, with a full risk breakdown and a
            downloadable report.
          </p>
          <Button asChild className="mt-2 gap-2 bg-teal text-white hover:bg-teal-dark">
            <Link href="/dashboard-v2">
              <Plus size={16} /> Analyze a portfolio
            </Link>
          </Button>
        </Card>
      )}

      {!loading && !error && data && data.recent_analyses.length > 0 && (
        <Card className="overflow-hidden rounded-[13px] p-0">
          {data.recent_analyses.map((run, index) => (
            <div
              key={run.id}
              className={`grid grid-cols-[35px_1.5fr_1fr_auto_auto] items-center gap-3 border-t border-[#edf0ed] px-5 py-4 ${
                index === 0 ? "border-t-0" : ""
              }`}
            >
              <div className="grid size-[34px] place-items-center rounded-lg bg-[#ecf4f3] text-[#2a655e]">
                <FileBarChart size={18} />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <strong className="truncate text-[12px] text-[#173337]">{run.filename}</strong>
                  {run.report_number && (
                    <span className="shrink-0 rounded-full bg-[#ecf4f3] px-2 py-0.5 font-mono text-[9px] font-bold tracking-wide text-[#2a655e]">
                      {run.report_number}
                    </span>
                  )}
                </div>
                <span className="mt-1 flex items-center gap-1 text-[10px] text-[#84908c]">
                  <Clock size={11} /> {formatDate(run.created_at)}
                </span>
              </div>
              <p className="m-0 text-[11px] text-[#65736f]">
                {run.status === "complete" && run.portfolio_value !== undefined
                  ? `${formatCurrency(run.portfolio_value)} · ${run.holdings} holdings`
                  : run.status === "processing"
                    ? "Processing…"
                    : "Failed"}
                {run.status === "complete" && run.risk_score !== undefined && (
                  <span className="ml-2 text-[#89938f]">
                    Risk {run.risk_score} ({run.risk_level})
                  </span>
                )}
              </p>
              <StatusBadge status={run.status} />
              <div className="flex items-center gap-1.5">
                {run.status === "complete" && (
                  <>
                    <Button asChild size="sm" variant="outline" className="gap-1.5">
                      <Link href={`/analysis/${run.id}`}>
                        View <ArrowRight size={14} />
                      </Link>
                    </Button>
                    <Button size="icon-sm" variant="outline" aria-label="Choose and download PDF report" onClick={() => setDownloadRunId(run.id)}>
                        <Download size={15} />
                    </Button>
                  </>
                )}
              </div>
            </div>
          ))}
        </Card>
      )}

      {!loading && !error && data && data.total_analyses > data.recent_analyses.length && (
        <p className="mt-4 text-center text-[11px] text-muted-text">
          Showing {data.recent_analyses.length} most recent of {data.total_analyses} total analyses.
        </p>
      )}
      <ReportDownloadDialog runId={downloadRunId} open={!!downloadRunId} onOpenChange={open => { if (!open) setDownloadRunId(null); }} />
    </div>
  );
}

function StatusBadge({ status }: { status: AnalysisStatus["status"] }) {
  if (status === "complete") {
    return (
      <Badge variant="outline" className="gap-1 rounded-full border-transparent bg-[#e9f2ed] text-[#45775e]">
        <Check size={12} /> Complete
      </Badge>
    );
  }
  if (status === "processing") {
    return (
      <Badge variant="outline" className="gap-1 rounded-full border-transparent bg-[#fbefdf] text-[#b5752d]">
        <LoaderCircle size={12} className="animate-spin" /> Processing
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className="gap-1 rounded-full border-transparent bg-[#f9e7e5] text-[#a34f4a]">
      <AlertTriangle size={12} /> Failed
    </Badge>
  );
}
