"use client";

import {
  ArrowLeft,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  Gauge,
  Layers3,
  LoaderCircle,
  ShieldAlert,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { authFetch } from "@/lib/auth";
import { ReportDownloadDialog } from "@/components/report-download-dialog";
import { Riskometer } from "@/components/riskometer";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

const API_URL = process.env.NEXT_PUBLIC_API_URL
  ?? (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : "");
const colors = ["#172731", "#4eb6aa", "#d49b55", "#7896a7", "#9cb5ad", "#dce5e7"];

type Result = {
  summary: Record<string, string | number>;
  sector: Array<{ sector: string; allocation_percent: number }>;
  portfolio: Array<Record<string, string | number>>;
  risk: {
    overall_score: number;
    overall_level: string;
    results: Array<{ name: string; score: number; level: string; coverage: string }>;
  };
};

export function AnalysisView({ id }: { id: string }) {
  const [result, setResult] = useState<Result | null>(null);
  const [reportConfig, setReportConfig] = useState<{ title: string; subtitle: string; sections: Record<string, boolean> } | null>(null);
  const [error, setError] = useState("");
  const [reportDialogOpen, setReportDialogOpen] = useState(false);
  useEffect(() => {
    authFetch(`${API_URL}/api/analyses/${id}`)
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail ?? "Analysis not found");
        return data;
      })
      .then((data) => setResult(data.result))
      .catch((caught) => setError(caught instanceof Error ? caught.message : "Analysis not found"));
  }, [id]);
  useEffect(() => { authFetch("/api/report-configuration").then(response => response.json()).then(setReportConfig).catch(() => undefined); }, []);

  if (error) return <State message={error} error />;
  if (!result) return <State message="Loading portfolio analysis…" />;
  const summary = result.summary;
  return (
    <main className="analysis-page">
      <header className="analysis-topbar">
        <Link href="/dashboard-v2"><ArrowLeft size={17}/> Portfolio overview</Link>
        <span><CheckCircle2 size={15}/> Analysis complete</span>
        <button className="primary-button" onClick={() => setReportDialogOpen(true)}><Download size={16}/> Choose &amp; download report</button>
      </header>
      <div className="analysis-content">
        <div className="analysis-title"><div><p className="eyebrow">PORTFOLIO ANALYSIS · {id.slice(0, 8).toUpperCase()}</p><h1>{reportConfig?.title || "Investment health report"}</h1><p>{reportConfig?.subtitle || "Structure, risk, style, performance, and benchmark intelligence."}</p></div></div>
        <section className="analysis-kpis">
          <MiniKpi icon={<FileSpreadsheet size={18}/>} label="Portfolio value" value={new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(Number(summary.total_portfolio_value))} note={`${summary.total_holdings} holdings`} />
          <MiniKpi icon={<Gauge size={18}/>} label="Overall risk" value={`${result.risk.overall_score} / 100`} note={result.risk.overall_level} />
          <MiniKpi icon={<Layers3 size={18}/>} label="Diversification" value={String(summary.diversification)} note={`${summary.total_sectors} sectors`} />
          <MiniKpi icon={<ShieldAlert size={18}/>} label="Concentration" value={String(summary.concentration_risk)} note={`Top 5: ${summary.top5_weight}%`} />
        </section>
        <section className="analysis-layout">
          {reportConfig?.sections.sector !== false && <article className="panel analysis-sector">
            <div className="panel-header"><div><h2>Sector allocation</h2><p>Weight by invested value</p></div></div>
            <div className="analysis-chart">
              <ResponsiveContainer width="100%" height={300}><PieChart><Pie data={result.sector} dataKey="allocation_percent" nameKey="sector" innerRadius={76} outerRadius={118} paddingAngle={2} stroke="none">{result.sector.map((row, index) => <Cell key={row.sector} fill={colors[index % colors.length]}/>)}</Pie><Tooltip formatter={(value) => `${value}%`}/></PieChart></ResponsiveContainer>
              <div>{result.sector.map((row, index) => <p key={row.sector}><i style={{background: colors[index % colors.length]}}/><span>{row.sector}</span><strong>{row.allocation_percent}%</strong></p>)}</div>
            </div>
          </article>}
          {reportConfig?.sections.risk !== false && <article className="panel analysis-risk">
            <div className="panel-header"><div><h2>Risk factor breakdown</h2><p>Transparent scoring and data coverage</p></div></div>
            <Riskometer score={result.risk.overall_score} level={result.risk.overall_level} className="mx-auto max-w-[360px]" />
            <div className="factor-list">{result.risk.results.map((factor) => <div key={factor.name}><header><span>{factor.name.replaceAll("_", " ")}</span><strong>{factor.score.toFixed(2)} · {factor.level}</strong></header><div className="progress"><i style={{ width: `${factor.score}%` }}/></div><p>{factor.coverage}</p></div>)}</div>
          </article>}
        </section>
        {reportConfig?.sections.holdings !== false && <article className="panel holdings-panel">
          <div className="panel-header"><div><h2>Portfolio holdings</h2><p>Enriched holdings, allocation, sector, and market-cap classification</p></div><span>{result.portfolio.length} securities</span></div>
          <div className="table-scroll"><table><thead><tr><th>Security</th><th>ISIN</th><th>Sector</th><th>Market cap</th><th>Value</th><th>Weight</th></tr></thead><tbody>{result.portfolio.map((holding) => <tr key={String(holding.isin)}><td><strong>{holding.security_name}</strong></td><td>{holding.isin}</td><td>{holding.sector}</td><td><span className="table-badge">{holding.cap_category}</span></td><td>₹{Number(holding.value).toLocaleString("en-IN")}</td><td>{holding.weight_percent}%</td></tr>)}</tbody></table></div>
        </article>}
      </div>
      <ReportDownloadDialog runId={id} open={reportDialogOpen} onOpenChange={setReportDialogOpen} />
    </main>
  );
}

function MiniKpi({ icon, label, value, note }: { icon: React.ReactNode; label: string; value: string; note: string }) {
  return <article><div>{icon}</div><span>{label}</span><strong>{value}</strong><p>{note}</p></article>;
}

function State({ message, error }: { message: string; error?: boolean }) {
  return <div className="analysis-state">{error ? <ShieldAlert size={30}/> : <LoaderCircle className="spin" size={30}/>}<strong>{message}</strong><Link href="/dashboard-v2">Return to dashboard</Link></div>;
}
