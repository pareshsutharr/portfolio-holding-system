"use client";

import {
  Activity,
  ArrowRight,
  BarChart3,
  Bell,
  Check,
  ChevronRight,
  CircleHelp,
  Database,
  Download,
  FileBarChart,
  FileSpreadsheet,
  Gauge,
  HardDrive,
  LayoutDashboard,
  Menu,
  Plus,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  UploadCloud,
  X,
} from "lucide-react";
import Link from "next/link";
import { useMemo, useRef, useState } from "react";
import { authFetch, downloadAuthorized } from "@/lib/auth";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Riskometer } from "@/components/riskometer";

const API_URL = process.env.NEXT_PUBLIC_API_URL
  ?? (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : "");

const allocation = [
  { name: "Financial Services", value: 38.02, color: "#172731" },
  { name: "Information Technology", value: 37.84, color: "#4eb6aa" },
  { name: "Realty", value: 7.57, color: "#d49b55" },
  { name: "Metals & Mining", value: 6.13, color: "#7896a7" },
  { name: "Other", value: 10.44, color: "#dce5e7" },
];

const performance = [
  { month: "Feb", portfolio: 100, nifty: 100 },
  { month: "Mar", portfolio: 104, nifty: 102 },
  { month: "Apr", portfolio: 101, nifty: 103 },
  { month: "May", portfolio: 109, nifty: 105 },
  { month: "Jun", portfolio: 113, nifty: 108 },
  { month: "Jul", portfolio: 118, nifty: 111 },
];

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

export function PortfolioDashboard() {
  const [mobileNav, setMobileNav] = useState(false);
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

  async function previewFile() {
    if (!file) return;
    setBusy(true);
    setError("");
    const body = new FormData();
    body.append("file", file);
    try {
      const response = await authFetch(`${API_URL}/api/analyses/preview`, {
        method: "POST",
        body,
      });
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

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileNav ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark"><TrendingUp size={19} /></div>
          <div><strong>Northstar</strong><span>Portfolio intelligence</span></div>
          <button className="icon-button mobile-only" onClick={() => setMobileNav(false)} aria-label="Close navigation"><X size={18} /></button>
        </div>
        <nav className="nav-list" aria-label="Primary navigation">
          <NavItem icon={<LayoutDashboard size={18} />} label="Overview" active />
          <NavItem icon={<FileSpreadsheet size={18} />} label="Portfolios" href="/reports" />
          <NavItem icon={<Gauge size={18} />} label="Risk analysis" badge="7" href="/reports" />
          <NavItem icon={<BarChart3 size={18} />} label="Benchmarks" href="/benchmarks" />
          <NavItem icon={<FileBarChart size={18} />} label="Reports" href="/reports" />
          <div className="nav-divider" />
          <p className="nav-caption">Workspace</p>
          <NavItem icon={<HardDrive size={18} />} label="Data center" href="/data-center" />
          <NavItem icon={<Database size={18} />} label="Data health" href="/data-health" />
          <NavItem icon={<Settings size={18} />} label="Settings" href="/settings" />
        </nav>
        <div className="sidebar-card">
          <div className="sidebar-card-icon"><Sparkles size={17} /></div>
          <strong>Data is current</strong>
          <p>Market data updated today at 09:42</p>
          <Link href="/data-health">View data health <ArrowRight size={14} /></Link>
        </div>
        <div className="profile">
          <div className="avatar">PS</div>
          <div><strong>Paresh Suthar</strong><span>Portfolio analyst</span></div>
          <ChevronRight size={17} />
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <button className="icon-button mobile-only" onClick={() => setMobileNav(true)} aria-label="Open navigation"><Menu size={20} /></button>
          <div className="search"><Search size={17} /><input aria-label="Search" placeholder="Search portfolios or reports…" /><kbd>⌘ K</kbd></div>
          <div className="topbar-actions">
            <button className="icon-button"><CircleHelp size={19} /></button>
            <button className="icon-button notification"><Bell size={19} /><span /></button>
            <button className="primary-button" onClick={() => { resetUpload(); setUploadOpen(true); }}><Plus size={17} /> New analysis</button>
          </div>
        </header>

        <div className="content">
          <section className="welcome">
            <div><p className="eyebrow">MONDAY, 28 JULY</p><h1>Portfolio overview</h1><p>A clear view of portfolio structure, risk, and performance.</p></div>
            <div className="welcome-actions"><button className="secondary-button"><Download size={16} /> Latest report</button><button className="primary-button" onClick={() => setUploadOpen(true)}><Plus size={17} /> Analyze portfolio</button></div>
          </section>

          <section className="kpi-grid">
            <KpiCard label="Portfolio value" value="₹1,93,167" note="15 active holdings" icon={<FileSpreadsheet size={19} />} />
            <KpiCard label="Overall risk" value="63.76" suffix="/ 100" note="High risk profile" tone="amber" icon={<Gauge size={19} />} />
            <KpiCard label="Top 5 concentration" value="73.93%" note="Above preferred range" tone="rose" icon={<Activity size={19} />} />
            <KpiCard label="Diversification" value="Good" note="7 sectors · 9 industries" tone="green" icon={<ShieldCheck size={19} />} />
          </section>

          <section className="dashboard-grid">
            <article className="panel allocation-panel">
              <PanelHeader title="Sector allocation" subtitle="Current portfolio weight" action="View details" />
              <div className="allocation-body">
                <div className="donut-wrap">
                  <ResponsiveContainer width="100%" height={250}>
                    <PieChart>
                      <Pie data={allocation} dataKey="value" innerRadius={70} outerRadius={102} paddingAngle={2} stroke="none">
                        {allocation.map((item) => <Cell key={item.name} fill={item.color} />)}
                      </Pie>
                      <Tooltip formatter={(value) => `${value}%`} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="donut-label"><strong>7</strong><span>sectors</span></div>
                </div>
                <div className="legend">
                  {allocation.map((item) => <div key={item.name}><span className="legend-dot" style={{ background: item.color }} /><p>{item.name}</p><strong>{item.value}%</strong></div>)}
                </div>
              </div>
            </article>

            <article className="panel risk-panel">
              <PanelHeader title="Risk-O-Meter" subtitle="Weighted across seven factors" action="Full analysis" />
              <div className="risk-score"><Riskometer score={63.76} level="High" className="max-w-[270px]" /></div>
              <div className="risk-factors">
                <RiskFactor label="Concentration" value={78} tone="high" />
                <RiskFactor label="Sector exposure" value={69} tone="high" />
                <RiskFactor label="Market cap" value={37} tone="low" />
                <RiskFactor label="Quality" value={16} tone="very-low" />
              </div>
            </article>

            <article className="panel performance-panel">
              <PanelHeader title="Portfolio performance" subtitle="Six-month indexed growth" action="Compare benchmarks" />
              <div className="chart-key"><span><i className="portfolio-key" /> Portfolio +18.0%</span><span><i className="nifty-key" /> Nifty 50 +11.0%</span></div>
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={performance} margin={{ top: 15, right: 4, left: -25, bottom: 0 }}>
                  <defs><linearGradient id="portfolioFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#4eb6aa" stopOpacity={0.25}/><stop offset="100%" stopColor="#4eb6aa" stopOpacity={0}/></linearGradient></defs>
                  <CartesianGrid stroke="#e7eceb" vertical={false} />
                  <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fill: "#74807d", fontSize: 12 }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: "#74807d", fontSize: 12 }} domain={[96, 120]} />
                  <Tooltip />
                  <Area type="monotone" dataKey="portfolio" stroke="#4eb6aa" strokeWidth={2.5} fill="url(#portfolioFill)" />
                  <Area type="monotone" dataKey="nifty" stroke="#a6b1ae" strokeWidth={2} fill="transparent" strokeDasharray="5 5" />
                </AreaChart>
              </ResponsiveContainer>
            </article>

            <article className="panel reports-panel">
              <PanelHeader title="Recent reports" subtitle="Generated portfolio analyses" action="View all" />
              <div className="report-list">
                <ReportRow name="Portfolio analysis" date="Today, 09:48" meta="15 holdings · ₹1.93L" status="Complete" />
                <ReportRow name="Risk methodology" date="24 Jul, 16:20" meta="Calculation guide" status="Complete" />
                <ReportRow name="Stock style report" date="18 Jul, 11:05" meta="14 holdings · ₹1.84L" status="Complete" />
              </div>
            </article>
          </section>
        </div>
      </main>

      {uploadOpen && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal" role="dialog" aria-modal="true" aria-labelledby="upload-title">
            <header><div><p className="eyebrow">NEW ANALYSIS</p><h2 id="upload-title">Analyze a portfolio</h2><p>Upload a broker holdings statement and verify its structure.</p></div><button className="icon-button" onClick={() => setUploadOpen(false)}><X size={19} /></button></header>
            <div className="steps">
              {["Upload", "Review", "Analyze", "Complete"].map((label, index) => <div className={index <= step ? "active" : ""} key={label}><span>{index < step ? <Check size={13}/> : index + 1}</span><p>{label}</p></div>)}
            </div>
            {!preview && !reportId && (
              <>
                <button className={`dropzone ${file ? "has-file" : ""}`} onClick={() => inputRef.current?.click()}>
                  <input ref={inputRef} type="file" accept=".xlsx,.xls" hidden onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
                  <div className="upload-icon">{file ? <FileSpreadsheet size={27}/> : <UploadCloud size={27}/>}</div>
                  <strong>{file ? file.name : "Drop your holdings workbook here"}</strong>
                  <p>{file ? `${(file.size / 1024).toFixed(1)} KB · Ready to review` : "or click to browse · Excel up to 20 MB"}</p>
                </button>
                <div className="privacy-note"><ShieldCheck size={17}/><p><strong>Private by design.</strong> Your workbook is processed locally and is never sent to a third-party AI when standard columns are detected.</p></div>
              </>
            )}
            {preview && !reportId && (
              <div className="preview-card">
                <div className="preview-summary"><div><span>Holdings found</span><strong>{preview.holding_count}</strong></div><div><span>Portfolio value</span><strong>{formatCurrency(preview.portfolio_value)}</strong></div></div>
                <h3>Detected column mapping</h3>
                <div className="mapping-grid">{Object.entries(preview.mapping).map(([field, column]) => <div key={field}><span>{field.replace("_", " ")}</span><strong>{column}</strong><Check size={15}/></div>)}</div>
              </div>
            )}
            {reportId && (
              <div className="success-state"><div><Check size={30}/></div><h3>Analysis complete</h3><p>Your interactive results and portfolio report are ready.</p><span className="success-actions"><a className="primary-button" href={`/analysis/${reportId}`}><BarChart3 size={17}/> Open analysis</a><button className="secondary-button" onClick={() => downloadAuthorized(`/api/analyses/${reportId}/report`, `portfolio-${reportId.slice(0, 8)}.pdf`)}><Download size={17}/> PDF report</button></span></div>
            )}
            {error && <p className="form-error">{error}</p>}
            <footer>
              <button className="secondary-button" onClick={() => { if (preview) setPreview(null); else setUploadOpen(false); }}>{preview && !reportId ? "Back" : "Cancel"}</button>
              {!preview && !reportId && <button className="primary-button" disabled={!file || busy} onClick={previewFile}>{busy ? "Reading workbook…" : "Review workbook"} <ArrowRight size={16}/></button>}
              {preview && !reportId && <button className="primary-button" disabled={busy} onClick={runAnalysis}>{busy ? "Running full analysis…" : "Run analysis"} <Sparkles size={16}/></button>}
              {reportId && <button className="secondary-button" onClick={() => setUploadOpen(false)}>Close</button>}
            </footer>
          </section>
        </div>
      )}
    </div>
  );
}

function NavItem({ icon, label, active, badge, href }: { icon: React.ReactNode; label: string; active?: boolean; badge?: string; href?: string }) {
  const content = <>{icon}<span>{label}</span>{badge && <b>{badge}</b>}</>;
  return href
    ? <Link className={`nav-item ${active ? "active" : ""}`} href={href}>{content}</Link>
    : <button className={`nav-item ${active ? "active" : ""}`}>{content}</button>;
}

function KpiCard({ label, value, suffix, note, icon, tone = "blue" }: { label: string; value: string; suffix?: string; note: string; icon: React.ReactNode; tone?: string }) {
  return <article className="kpi-card"><div className={`kpi-icon ${tone}`}>{icon}</div><div className="kpi-label">{label}<CircleHelp size={13}/></div><div className="kpi-value">{value} <small>{suffix}</small></div><p><span className={`status-dot ${tone}`} />{note}</p></article>;
}

function PanelHeader({ title, subtitle, action }: { title: string; subtitle: string; action: string }) {
  return <header className="panel-header"><div><h2>{title}</h2><p>{subtitle}</p></div><button>{action}<ChevronRight size={15}/></button></header>;
}

function RiskFactor({ label, value, tone }: { label: string; value: number; tone: string }) {
  return <div className="risk-factor"><div><span>{label}</span><strong>{value}</strong></div><div className="progress"><i className={tone} style={{ width: `${value}%` }} /></div></div>;
}

function ReportRow({ name, date, meta, status }: { name: string; date: string; meta: string; status: string }) {
  return <div className="report-row"><div className="file-icon"><FileBarChart size={18}/></div><div className="report-name"><strong>{name}</strong><span>{date}</span></div><p>{meta}</p><span className="complete-badge"><Check size={12}/>{status}</span><button className="icon-button"><Download size={17}/></button></div>;
}
