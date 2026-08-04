"use client";

import {
  ArrowRight,
  BarChart3,
  Check,
  ChevronRight,
  CircleHelp,
  Clock,
  Download,
  FileBarChart,
  FileSpreadsheet,
  Gauge,
  Plus,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  UploadCloud,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip as ChartTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { authFetch, downloadAuthorized } from "@/lib/auth";
import { Riskometer } from "@/components/riskometer";

const API_URL = process.env.NEXT_PUBLIC_API_URL
  ?? (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : "");
const PRIMARY_BENCHMARK = "Nifty 50";
const sectorColors = ["#172731", "#4eb6aa", "#d49b55", "#7896a7", "#9cb5ad", "#dce5e7", "#8c6d4f", "#5b7c99"];

function toneForScore(score: number) {
  if (score >= 70) return "bg-rose" as const;
  if (score >= 50) return "bg-amber" as const;
  if (score >= 30) return "bg-teal" as const;
  return "bg-green" as const;
}

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
  error?: string;
};

type DashboardResponse = {
  recent_analyses: AnalysisStatus[];
  total_analyses: number;
};

type AnalysisResult = {
  summary: {
    total_portfolio_value: number;
    total_holdings: number;
    diversification: string;
    total_sectors: number;
    total_industries?: number;
    concentration_risk: string;
    top5_weight: number;
  };
  sector: Array<{ sector: string; allocation_percent: number }>;
  risk: {
    overall_score: number;
    overall_level: string;
    results: Array<{ name: string; score: number; level: string; coverage: string }>;
  };
  returns?: {
    rows: Array<Record<string, string | number>>;
    benchmark_names: string[];
  };
};

type Preview = {
  upload_id: string;
  holding_count: number;
  portfolio_value: number;
  mapping: Record<string, string>;
  holdings: Array<Record<string, string | number>>;
};

type AnalysisResponse = {
  status: { id: string };
};

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);

const formatDate = (value: string) =>
  new Date(value).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });

export function Dashboard() {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [latest, setLatest] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  const [uploadOpen, setUploadOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [reportId, setReportId] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const step = useMemo(() => {
    if (reportId) return 3;
    if (preview) return 2;
    if (file) return 1;
    return 0;
  }, [file, preview, reportId]);

  const loadDashboard = useCallback(() => {
    setLoading(true);
    setLoadError("");
    authFetch(`${API_URL}/api/dashboard`)
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail ?? "Could not load your portfolios");
        return data as DashboardResponse;
      })
      .then(async (data) => {
        setDashboard(data);
        const latestComplete = data.recent_analyses.find((run) => run.status === "complete");
        if (!latestComplete) {
          setLatest(null);
          return;
        }
        const detail = await authFetch(`${API_URL}/api/analyses/${latestComplete.id}`).then((r) => r.json());
        setLatest(detail.result as AnalysisResult);
      })
      .catch((caught) => setLoadError(caught instanceof Error ? caught.message : "Could not load your portfolios"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    Promise.resolve().then(loadDashboard);
  }, [loadDashboard]);

  const latestCompleteRun = dashboard?.recent_analyses.find((run) => run.status === "complete");

  async function previewFile() {
    if (!file) return;
    setBusy(true);
    setError("");
    const body = new FormData();
    body.append("file", file);
    try {
      const response = await authFetch(`${API_URL}/api/analyses/preview`, { method: "POST", body });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Could not preview workbook");
      setPreview(data);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not preview workbook");
    } finally {
      setBusy(false);
    }
  }

  async function runAnalysis() {
    if (!preview) return;
    setBusy(true);
    setError("");
    try {
      const response = await authFetch(`${API_URL}/api/analyses`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ upload_id: preview.upload_id }),
      });
      const data: AnalysisResponse & { detail?: string } = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Analysis failed");
      setReportId(data.status.id);
      loadDashboard();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Analysis failed");
    } finally {
      setBusy(false);
    }
  }

  function resetUpload() {
    setFile(null);
    setPreview(null);
    setReportId("");
    setError("");
  }

  function openUpload() {
    resetUpload();
    setUploadOpen(true);
  }

  const periodRows = latest?.returns?.rows ?? [];
  const performanceData = periodRows.map((row) => ({
    period: String(row.period),
    portfolio: Number(row.portfolio_return ?? 0) * 100,
    benchmark: Number(row[`${PRIMARY_BENCHMARK}_return`] ?? 0) * 100,
  }));

  return (
    <div className="mx-auto max-w-[1500px] px-4 py-8 md:px-8 md:py-9">
      <section className="mb-7 flex flex-wrap items-end justify-between gap-6">
        <div>
          <p className="mb-1.5 text-[9px] font-extrabold tracking-[1.5px] text-[#89938f] uppercase">
            {new Date().toLocaleDateString("en-IN", { weekday: "long", day: "2-digit", month: "long" })}
          </p>
          <h1 className="text-[28px] font-bold leading-tight text-[#173337] md:text-[30px]">Portfolio overview</h1>
          <p className="mt-1.5 text-[13px] text-muted-text">A clear view of portfolio structure, risk, and performance.</p>
        </div>
        <div className="flex gap-2.5">
          <Button
            variant="outline"
            className="h-10 gap-2 rounded-lg border-[#cfd8d5] px-4 text-[12px] font-bold"
            disabled={!latestCompleteRun}
            onClick={() => latestCompleteRun && downloadAuthorized(`/api/analyses/${latestCompleteRun.id}/report`, `portfolio-${latestCompleteRun.id.slice(0, 8)}.pdf`)}
          >
            <Download size={16} /> Latest report
          </Button>
          <Button
            className="h-10 gap-2 rounded-lg bg-teal px-4 text-[12px] font-bold text-white shadow-[0_4px_12px_rgba(47,127,129,0.16)] hover:bg-teal-dark"
            onClick={openUpload}
          >
            <Plus size={17} /> Analyze portfolio
          </Button>
        </div>
      </section>

      {loading && (
        <Card className="flex min-h-40 items-center justify-center gap-2 rounded-[13px] p-12 text-sm text-muted-text">
          Loading your portfolios…
        </Card>
      )}

      {!loading && loadError && (
        <Card className="flex flex-col items-center gap-2 rounded-[13px] p-12 text-center">
          <ShieldAlert size={22} className="text-rose" />
          <p className="text-sm font-semibold text-[#173337]">Couldn&apos;t reach the analysis service</p>
          <p className="max-w-sm text-xs text-muted-text">{loadError}</p>
        </Card>
      )}

      {!loading && !loadError && dashboard && dashboard.total_analyses === 0 && (
        <Card className="flex flex-col items-center gap-3 rounded-[13px] p-14 text-center">
          <div className="grid size-12 place-items-center rounded-full bg-[#ecf4f3] text-[#2a655e]">
            <FileBarChart size={22} />
          </div>
          <p className="text-sm font-semibold text-[#173337]">No portfolios analyzed yet</p>
          <p className="max-w-sm text-xs text-muted-text">
            Upload a holdings workbook to see sector allocation, risk breakdown, and performance here.
          </p>
          <Button className="mt-2 gap-2 bg-teal text-white hover:bg-teal-dark" onClick={openUpload}>
            <Plus size={16} /> Analyze a portfolio
          </Button>
        </Card>
      )}

      {!loading && !loadError && dashboard && dashboard.total_analyses > 0 && (
        <>
          <section className="mb-4 grid grid-cols-1 gap-3.5 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard
              label="Portfolio value"
              value={latest ? formatCurrency(latest.summary.total_portfolio_value) : "—"}
              note={latest ? `${latest.summary.total_holdings} active holdings` : "Run an analysis to see this"}
              icon={<FileSpreadsheet size={19} />}
              iconClass="bg-[#ecf4f3] text-[#2a655e]"
              dotClass="bg-[#668b9d]"
            />
            <KpiCard
              label="Overall risk"
              value={latest ? latest.risk.overall_score.toFixed(2) : "—"}
              suffix={latest ? "/ 100" : undefined}
              note={latest ? `${latest.risk.overall_level} risk profile` : "Run an analysis to see this"}
              icon={<Gauge size={19} />}
              iconClass="bg-[#fbefdf] text-[#b5752d]"
              dotClass="bg-amber"
            />
            <KpiCard
              label="Top 5 concentration"
              value={latest ? `${Number(latest.summary.top5_weight).toFixed(2)}%` : "—"}
              note={latest ? latest.summary.concentration_risk : "Run an analysis to see this"}
              icon={<ShieldAlert size={19} />}
              iconClass="bg-[#f9e7e5] text-[#a34f4a]"
              dotClass="bg-rose"
            />
            <KpiCard
              label="Diversification"
              value={latest ? latest.summary.diversification : "—"}
              note={latest ? `${latest.summary.total_sectors} sectors` : "Run an analysis to see this"}
              icon={<ShieldCheck size={19} />}
              iconClass="bg-[#e5f0e9] text-[#3f7259]"
              dotClass="bg-green"
            />
          </section>

          <section className="grid grid-cols-1 gap-3.5 xl:grid-cols-[1.15fr_0.85fr]">
            <Card className="rounded-[13px] p-5">
              <PanelHeader title="Sector allocation" subtitle="Current portfolio weight" action={latestCompleteRun ? { label: "View details", href: `/analysis/${latestCompleteRun.id}` } : undefined} />
              {latest ? (
                <div className="mt-2 grid grid-cols-1 items-center gap-6 sm:grid-cols-[1.05fr_0.95fr]">
                  <div className="relative h-[250px]">
                    <ResponsiveContainer width="100%" height={250}>
                      <PieChart>
                        <Pie data={latest.sector} dataKey="allocation_percent" nameKey="sector" innerRadius={70} outerRadius={102} paddingAngle={2} stroke="none">
                          {latest.sector.map((item, index) => (
                            <Cell key={item.sector} fill={sectorColors[index % sectorColors.length]} />
                          ))}
                        </Pie>
                        <ChartTooltip formatter={(value) => `${value}%`} />
                      </PieChart>
                    </ResponsiveContainer>
                    <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                      <strong className="text-[26px] font-bold text-[#173337]">{latest.sector.length}</strong>
                      <span className="text-[10px] text-muted-text">sectors</span>
                    </div>
                  </div>
                  <div className="flex flex-col gap-3.5">
                    {latest.sector.slice(0, 6).map((item, index) => (
                      <div key={item.sector} className="grid grid-cols-[8px_1fr_auto] items-center gap-2.5">
                        <span className="size-1.5 rounded-full" style={{ background: sectorColors[index % sectorColors.length] }} />
                        <p className="m-0 truncate text-[10px] text-[#5d6d69]">{item.sector}</p>
                        <strong className="text-[10px] text-[#263c3a]">{item.allocation_percent}%</strong>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <EmptyPanel />
              )}
            </Card>

            <Card className="rounded-[13px] p-5">
              <PanelHeader title="Risk-O-Meter" subtitle="Weighted across seven factors" action={latestCompleteRun ? { label: "Full analysis", href: `/analysis/${latestCompleteRun.id}` } : undefined} />
              {latest ? (
                <div className="mt-2 grid grid-cols-1 gap-6 sm:grid-cols-[0.8fr_1.2fr]">
                  <div className="grid place-items-center py-2">
                    <Riskometer score={latest.risk.overall_score} level={latest.risk.overall_level} className="max-w-[260px]" />
                  </div>
                  <div className="flex flex-col justify-center gap-4">
                    {latest.risk.results.map((factor) => (
                      <div key={factor.name}>
                        <div className="mb-1.5 flex justify-between text-[10px]">
                          <span className="text-[#5f6e6b]">{factor.name.replaceAll("_", " ")}</span>
                          <strong className="text-[#263c3a]">{factor.score.toFixed(0)}</strong>
                        </div>
                        <Progress value={factor.score} className="h-[5px] bg-[#edf0ed]" indicatorClassName={toneForScore(factor.score)} />
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <EmptyPanel />
              )}
            </Card>

            <Card className="rounded-[13px] p-5 xl:col-span-1">
              <PanelHeader title="Portfolio performance" subtitle="Return by period vs. benchmark" action={{ label: "Compare benchmarks", href: "/compare" }} />
              {performanceData.length > 0 ? (
                <>
                  <div className="mt-3 flex justify-end gap-5 text-[9px] text-[#66736f]">
                    <span className="flex items-center gap-1.5">
                      <i className="inline-block h-0.5 w-3.5 bg-teal" /> Portfolio
                    </span>
                    <span className="flex items-center gap-1.5">
                      <i className="inline-block h-0.5 w-3.5 bg-[#a6b1ae]" /> {PRIMARY_BENCHMARK}
                    </span>
                  </div>
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={performanceData} margin={{ top: 15, right: 4, left: -15, bottom: 0 }}>
                      <CartesianGrid stroke="#e7eceb" vertical={false} />
                      <XAxis dataKey="period" axisLine={false} tickLine={false} tick={{ fill: "#74807d", fontSize: 12 }} />
                      <YAxis axisLine={false} tickLine={false} tick={{ fill: "#74807d", fontSize: 12 }} tickFormatter={(v) => `${v}%`} />
                      <ChartTooltip formatter={(value) => `${Number(value).toFixed(2)}%`} />
                      <Bar dataKey="portfolio" fill="#4eb6aa" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="benchmark" fill="#a6b1ae" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </>
              ) : (
                <EmptyPanel />
              )}
            </Card>

            <Card className="rounded-[13px] p-5">
              <PanelHeader title="Recent reports" subtitle="Generated portfolio analyses" action={{ label: "View all", href: "/reports" }} />
              <div className="mt-3">
                {dashboard.recent_analyses.length === 0 && <EmptyPanel />}
                {dashboard.recent_analyses.slice(0, 4).map((run, index) => (
                  <div
                    key={run.id}
                    className={cn(
                      "grid min-h-[63px] grid-cols-[35px_1.5fr_1fr_auto_38px] items-center gap-2.5 border-t border-[#edf0ed]",
                      index === 0 && "border-t-0"
                    )}
                  >
                    <div className="grid size-[34px] place-items-center rounded-lg bg-[#e9f0ef] text-teal">
                      <FileBarChart size={18} />
                    </div>
                    <div className="min-w-0">
                      <strong className="block truncate text-[10px] text-[#173337]">{run.filename}</strong>
                      <span className="mt-1 flex items-center gap-1 text-[9px] text-[#84908c]"><Clock size={10} /> {formatDate(run.created_at)}</span>
                    </div>
                    <p className="m-0 text-[9px] text-[#84908c]">
                      {run.status === "complete" && run.portfolio_value !== undefined
                        ? `${formatCurrency(run.portfolio_value)} · ${run.holdings} holdings`
                        : run.status === "processing"
                          ? "Processing…"
                          : "Failed"}
                    </p>
                    {run.status === "complete" ? (
                      <span className="flex w-fit items-center gap-1 rounded-full bg-[#e9f2ed] px-2 py-1 text-[9px] text-[#45775e]"><Check size={12} /> Complete</span>
                    ) : run.status === "processing" ? (
                      <span className="flex w-fit items-center gap-1 rounded-full bg-[#fbefdf] px-2 py-1 text-[9px] text-[#b5752d]">Processing</span>
                    ) : (
                      <span className="flex w-fit items-center gap-1 rounded-full bg-[#f9e7e5] px-2 py-1 text-[9px] text-[#a34f4a]">Failed</span>
                    )}
                    {run.status === "complete" ? (
                      <button
                        className="grid size-[31px] place-items-center rounded-md border border-line bg-white text-[#51615e] hover:bg-[#f5f7f4]"
                        aria-label="Download PDF report"
                        onClick={() => downloadAuthorized(`/api/analyses/${run.id}/report`, `portfolio-${run.id.slice(0, 8)}.pdf`)}
                      >
                        <Download size={15} />
                      </button>
                    ) : (
                      <span />
                    )}
                  </div>
                ))}
              </div>
            </Card>
          </section>
        </>
      )}

      <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
        <DialogContent className="max-w-full gap-0 p-0 sm:max-w-2xl" showCloseButton>
          <DialogHeader className="border-b border-line p-6 pb-5">
            <p className="mb-1.5 text-[9px] font-extrabold tracking-[1.5px] text-[#89938f] uppercase">New analysis</p>
            <DialogTitle className="text-[22px] font-bold">Analyze a portfolio</DialogTitle>
            <DialogDescription>Upload a broker holdings statement and verify its structure.</DialogDescription>
          </DialogHeader>

          <div className="grid grid-cols-4 gap-2 px-6 py-5">
            {["Upload", "Review", "Analyze", "Complete"].map((label, index) => (
              <div key={label} className={cn("relative flex items-center gap-2 text-[9px] font-bold", index <= step ? "text-teal" : "text-[#9ca6a2]")}>
                <span className={cn("grid size-[22px] shrink-0 place-items-center rounded-full bg-[#eef1ee] text-[#9ca6a2]", index <= step && "bg-teal text-white")}>
                  {index < step ? <Check size={12} /> : index + 1}
                </span>
                <p className="m-0 hidden sm:block">{label}</p>
              </div>
            ))}
          </div>

          {!preview && !reportId && (
            <div className="px-6">
              <button
                className={cn(
                  "flex min-h-[180px] w-full flex-col items-center justify-center rounded-xl border-[1.5px] border-dashed border-[#b7c8c3] bg-[#f9fbf8] text-center hover:border-teal hover:bg-[#f5faf7]",
                  file && "border-solid border-[#9bbdb2] bg-[#f4faf6]"
                )}
                onClick={() => inputRef.current?.click()}
              >
                <input ref={inputRef} type="file" accept=".xlsx,.xls" hidden onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
                <div className="mb-3 grid size-[50px] place-items-center rounded-2xl bg-[#e3efeb] text-teal">
                  {file ? <FileSpreadsheet size={25} /> : <UploadCloud size={25} />}
                </div>
                <strong className="text-[13px]">{file ? file.name : "Drop your holdings workbook here"}</strong>
                <p className="mt-1.5 text-[10px] text-[#87928e]">
                  {file ? `${(file.size / 1024).toFixed(1)} KB · Ready to review` : "or click to browse · Excel up to 20 MB"}
                </p>
              </button>
              <div className="my-5 flex gap-2.5 rounded-lg bg-[#f3f7f4] p-3 text-[#4d7463]">
                <ShieldCheck size={17} className="shrink-0" />
                <p className="m-0 text-[9px] leading-[15px]">
                  <strong>Private by design.</strong> Your workbook is processed locally and is never sent to a third-party AI when standard columns are detected.
                </p>
              </div>
            </div>
          )}

          {preview && !reportId && (
            <div className="px-6">
              <div className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="rounded-lg bg-[#f4f7f3] p-4">
                  <span className="text-[9px] text-muted-text">Holdings found</span>
                  <strong className="mt-1.5 block text-[18px] font-bold">{preview.holding_count}</strong>
                </div>
                <div className="rounded-lg bg-[#f4f7f3] p-4">
                  <span className="text-[9px] text-muted-text">Portfolio value</span>
                  <strong className="mt-1.5 block text-[18px] font-bold">{formatCurrency(preview.portfolio_value)}</strong>
                </div>
              </div>
              <h3 className="mb-2.5 text-[11px] font-semibold">Detected column mapping</h3>
              <div className="overflow-hidden rounded-lg border border-line">
                {Object.entries(preview.mapping).map(([field, column], index) => (
                  <div key={field} className={cn("grid grid-cols-[1fr_1.4fr_auto] items-center gap-2 border-t border-line px-3.5 py-2.5 text-[10px]", index === 0 && "border-t-0")}>
                    <span className="capitalize text-muted-text">{field.replace("_", " ")}</span>
                    <strong>{column}</strong>
                    <Check size={15} className="text-green" />
                  </div>
                ))}
              </div>
            </div>
          )}

          {reportId && (
            <div className="px-6 py-8 text-center">
              <div className="mx-auto mb-4 grid size-[56px] place-items-center rounded-full bg-[#e5f2ea] text-green">
                <Check size={28} />
              </div>
              <h3 className="text-[19px] font-bold">Analysis complete</h3>
              <p className="mt-1.5 mb-5 text-[11px] text-muted-text">Your interactive results and portfolio report are ready.</p>
              <div className="flex flex-col justify-center gap-2.5 sm:flex-row">
                <Button asChild className="gap-2 bg-teal text-white hover:bg-teal-dark">
                  <a href={`/analysis/${reportId}`}>
                    <BarChart3 size={16} /> Open analysis
                  </a>
                </Button>
                <Button variant="outline" className="gap-2" onClick={() => downloadAuthorized(`/api/analyses/${reportId}/report`, `portfolio-${reportId.slice(0, 8)}.pdf`)}>
                  <Download size={16} /> PDF report
                </Button>
              </div>
            </div>
          )}

          {error && <p className="mx-6 mt-4 rounded-lg bg-[#fff0ee] px-3.5 py-2.5 text-[10px] text-[#9b413c]">{error}</p>}

          <DialogFooter className="mt-6 flex-row justify-end gap-2.5 border-t border-line bg-transparent px-6 py-4">
            <Button
              variant="outline"
              onClick={() => {
                if (preview) setPreview(null);
                else setUploadOpen(false);
              }}
            >
              {preview && !reportId ? "Back" : "Cancel"}
            </Button>
            {!preview && !reportId && (
              <Button className="gap-2 bg-teal text-white hover:bg-teal-dark" disabled={!file || busy} onClick={previewFile}>
                {busy ? "Reading workbook…" : "Review workbook"} <ArrowRight size={16} />
              </Button>
            )}
            {preview && !reportId && (
              <Button className="gap-2 bg-teal text-white hover:bg-teal-dark" disabled={busy} onClick={runAnalysis}>
                {busy ? "Running full analysis…" : "Run analysis"} <Sparkles size={16} />
              </Button>
            )}
            {reportId && (
              <Button variant="outline" onClick={() => setUploadOpen(false)}>
                Close
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function EmptyPanel() {
  return <div className="grid min-h-[180px] place-items-center text-center text-[11px] text-muted-text">Not enough data yet.</div>;
}

function KpiCard({
  label,
  value,
  suffix,
  note,
  icon,
  iconClass,
  dotClass,
}: {
  label: string;
  value: string;
  suffix?: string;
  note: string;
  icon: React.ReactNode;
  iconClass: string;
  dotClass: string;
}) {
  return (
    <Card className="relative min-h-[148px] rounded-[13px] p-5">
      <div className={cn("absolute right-4 top-4 grid size-9 place-items-center rounded-[10px]", iconClass)}>{icon}</div>
      <div className="flex items-center gap-1.5 text-[11px] font-semibold text-muted-text">
        {label}
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="inline-flex cursor-help text-[#9aa6a2]">
              <CircleHelp size={13} />
            </span>
          </TooltipTrigger>
          <TooltipContent>Based on your latest analyzed portfolio</TooltipContent>
        </Tooltip>
      </div>
      <div className="mt-4 text-[24px] font-bold leading-8 text-[#173337]">
        {value} {suffix && <small className="font-sans text-[11px] font-medium text-[#89938f]">{suffix}</small>}
      </div>
      <p className="mt-2.5 flex items-center gap-1.5 text-[10px] text-[#697773]">
        <span className={cn("size-1.5 rounded-full", dotClass)} />
        {note}
      </p>
    </Card>
  );
}

function PanelHeader({ title, subtitle, action }: { title: string; subtitle: string; action?: { label: string; href: string } }) {
  return (
    <div className="flex items-start justify-between">
      <div>
        <h2 className="text-[16px] font-bold leading-[22px] text-[#173337]">{title}</h2>
        <p className="mt-0.5 text-[10px] text-[#89938f]">{subtitle}</p>
      </div>
      {action && (
        <Link href={action.href} className="flex items-center gap-0.5 text-[10px] font-bold text-teal hover:text-teal-dark">
          {action.label}
          <ChevronRight size={15} />
        </Link>
      )}
    </div>
  );
}
