"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { RefreshCw } from "lucide-react";
import { authFetch, useAuth } from "@/lib/auth";

type IndexName = "NIFTY50" | "NIFTYMIDCAP150" | "NIFTY500";
type Allocation = { id: number; index_name: IndexName; sector: string; weight_percent: number; factsheet_date: string; updated_at: string };
type Run = { id: number; source: string; status: string; method_used: string | null; records_fetched: number; inserted: number; updated: number; duplicates_skipped: number; started_at: string; finished_at: string | null; error_message: string | null };
type Status = { running: boolean; latest_dates: Record<IndexName, string | null>; last_successful_ingestion: string | null; latest_status: string; runs: Run[] };
type History = { dates: string[]; snapshots: Record<string, Allocation[]> };

const INDEXES: { value: IndexName; label: string }[] = [
  { value: "NIFTY50", label: "NIFTY 50" },
  { value: "NIFTYMIDCAP150", label: "NIFTY Midcap 150" },
  { value: "NIFTY500", label: "NIFTY 500" },
];
const dateText = (value?: string | null) => value ? new Date(`${value.length === 10 ? value + "T00:00:00" : value}`).toLocaleString(undefined, value.length === 10 ? { dateStyle: "medium" } : { dateStyle: "medium", timeStyle: "short" }) : "Not available";
const badge = (status: string) => status.replaceAll("_", " ");

export function SectorAllocationsAdmin() {
  const auth = useAuth(); const router = useRouter();
  const [indexName, setIndexName] = useState<IndexName>("NIFTY50");
  const [allocations, setAllocations] = useState<Allocation[]>([]);
  const [status, setStatus] = useState<Status | null>(null);
  const [history, setHistory] = useState<History>({ dates: [], snapshots: {} });
  const [older, setOlder] = useState(""); const [newer, setNewer] = useState("");
  const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const fetchJson = useCallback(async <T,>(path: string): Promise<T> => {
    const response = await authFetch(path); const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Request failed"); return data;
  }, []);
  const loadStatus = useCallback(() => fetchJson<Status>("/api/admin/sector-allocations/status").then(setStatus), [fetchJson]);
  const loadIndex = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [list, historyData] = await Promise.all([
        fetchJson<{ allocations: Allocation[] }>(`/api/admin/sector-allocations?indexName=${indexName}&latest=true`),
        fetchJson<History>(`/api/admin/sector-allocations/history?indexName=${indexName}`),
      ]);
      setAllocations(list.allocations); setHistory(historyData);
      setNewer(historyData.dates[0] || ""); setOlder(historyData.dates[1] || historyData.dates[0] || "");
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Could not load sector data"); }
    finally { setLoading(false); }
  }, [fetchJson, indexName]);

  useEffect(() => { if (auth.ready && auth.user?.role !== "admin") router.replace("/dashboard-v2"); }, [auth.ready, auth.user?.role, router]);
  useEffect(() => { if (auth.user?.role === "admin") Promise.resolve().then(() => Promise.all([loadIndex(), loadStatus()])).catch(() => undefined); }, [auth.user?.role, loadIndex, loadStatus]);
  useEffect(() => { if (!status?.running) return; const timer = window.setInterval(() => { loadStatus().then(loadIndex).catch(() => undefined); }, 3000); return () => window.clearInterval(timer); }, [status?.running, loadStatus, loadIndex]);

  async function refresh() {
    setMessage(""); setError("");
    try { const response = await authFetch("/api/admin/sector-allocations/refresh", { method: "POST" }); const data = await response.json(); if (!response.ok) throw new Error(data.detail); setMessage(data.message); await loadStatus(); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Refresh could not start"); }
  }
  const comparison = useMemo(() => {
    const before = new Map((history.snapshots[older] || []).map(row => [row.sector, row.weight_percent]));
    const after = new Map((history.snapshots[newer] || []).map(row => [row.sector, row.weight_percent]));
    return [...new Set([...before.keys(), ...after.keys()])].map(sector => ({ sector, previous: before.get(sector), current: after.get(sector) })).sort((a,b) => (b.current ?? 0) - (a.current ?? 0));
  }, [history, older, newer]);

  if (!auth.ready || auth.user?.role !== "admin") return <div className="p-8 text-sm text-muted-text">Checking administrator access…</div>;
  return <div className="mx-auto max-w-[1500px] space-y-6 p-4 md:p-8">
    <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-xs font-bold uppercase tracking-[1.5px] text-teal">Admin data operations</p><h1 className="mt-1 text-3xl font-bold text-[#173337]">Sector allocations</h1><p className="mt-1 text-sm text-muted-text">Official daily NIFTY factsheet snapshots and ingestion health.</p></div><button onClick={refresh} disabled={status?.running} className="flex h-10 items-center justify-center gap-2 rounded-lg bg-teal px-4 text-sm font-bold text-white disabled:opacity-50"><RefreshCw size={16} className={status?.running ? "animate-spin" : ""}/>{status?.running ? "Refreshing…" : "Refresh sector data"}</button></div>
    {message && <p className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{message}</p>}{error && <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">{INDEXES.map(item => <Summary key={item.value} label={`${item.label} factsheet`} value={dateText(status?.latest_dates[item.value])}/>)}<Summary label="Last successful ingestion" value={dateText(status?.last_successful_ingestion)}/><Summary label="Latest status" value={status?.latest_status ? badge(status.latest_status) : "Loading…"}/></div>
    <section className="rounded-xl border border-line bg-white p-4 md:p-6"><div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><h2 className="text-lg font-bold text-[#173337]">Latest allocation</h2><select value={indexName} onChange={event => setIndexName(event.target.value as IndexName)} className="h-10 rounded-lg border border-line bg-white px-3 text-sm font-semibold">{INDEXES.map(item => <option value={item.value} key={item.value}>{item.label}</option>)}</select></div>{loading ? <Empty text="Loading allocations…"/> : !allocations.length ? <Empty text="No validated snapshot yet. Use Refresh sector data."/> : <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(420px,0.9fr)]"><AllocationTable rows={allocations}/><div className="h-[460px] min-w-0"><ResponsiveContainer width="100%" height="100%"><BarChart data={allocations} layout="vertical" margin={{ left: 8, right: 24 }}><CartesianGrid strokeDasharray="3 3" horizontal={false}/><XAxis type="number" unit="%"/><YAxis dataKey="sector" type="category" width={145} tick={{fontSize:10}}/><Tooltip formatter={(value) => [`${Number(value).toFixed(2)}%`, "Weight"]}/><Bar dataKey="weight_percent" fill="#147d73" radius={[0,4,4,0]}/></BarChart></ResponsiveContainer></div></div>}</section>
    <section className="rounded-xl border border-line bg-white p-4 md:p-6"><h2 className="text-lg font-bold text-[#173337]">Historical comparison</h2><div className="my-4 flex flex-col gap-3 sm:flex-row"><DateSelect label="Previous" value={older} dates={history.dates} onChange={setOlder}/><DateSelect label="Current" value={newer} dates={history.dates} onChange={setNewer}/></div>{history.dates.length < 2 && <p className="mb-4 text-sm text-muted-text">A second published factsheet date is needed for a historical comparison.</p>}<div className="overflow-x-auto"><table className="w-full min-w-[650px] text-left text-sm"><thead><tr className="border-b border-line text-xs text-muted-text"><th className="py-3">Sector</th><th>Previous</th><th>Current</th><th>Change (pp)</th><th>Status</th></tr></thead><tbody>{comparison.map(row => <tr className="border-b border-line/70" key={row.sector}><td className="py-3 font-semibold">{row.sector}</td><td>{row.previous?.toFixed(2) ?? "—"}</td><td>{row.current?.toFixed(2) ?? "—"}</td><td className={(row.current ?? 0) - (row.previous ?? 0) >= 0 ? "text-emerald-700" : "text-red-600"}>{row.previous === undefined || row.current === undefined ? "—" : `${(row.current-row.previous).toFixed(2)}`}</td><td>{row.previous === undefined ? "Added" : row.current === undefined ? "Removed" : "Existing"}</td></tr>)}</tbody></table></div></section>
    <section className="rounded-xl border border-line bg-white p-4 md:p-6"><h2 className="mb-4 text-lg font-bold text-[#173337]">Ingestion monitoring</h2><div className="overflow-x-auto"><table className="w-full min-w-[1050px] text-left text-xs"><thead><tr className="border-b border-line text-muted-text">{["Source / index","Status","Method","Fetched","Inserted","Updated","Skipped","Started","Finished","Error"].map(value => <th className="px-2 py-3" key={value}>{value}</th>)}</tr></thead><tbody>{status?.runs.map(run => <tr className="border-b border-line/70" key={run.id}><td className="px-2 py-3 font-semibold">{run.source}</td><td className="capitalize">{badge(run.status)}</td><td>{run.method_used ?? "—"}</td><td>{run.records_fetched}</td><td>{run.inserted}</td><td>{run.updated}</td><td>{run.duplicates_skipped}</td><td>{dateText(run.started_at)}</td><td>{dateText(run.finished_at)}</td><td className="max-w-[220px] text-red-600">{run.error_message ?? "—"}</td></tr>)}{!status?.runs.length && <tr><td colSpan={10} className="py-8 text-center text-muted-text">No ingestion runs recorded.</td></tr>}</tbody></table></div></section>
  </div>;
}

function Summary({label,value}:{label:string;value:string}) { return <div className="rounded-xl border border-line bg-white p-4"><p className="text-[10px] font-bold uppercase tracking-wider text-muted-text">{label}</p><p className="mt-2 text-sm font-bold capitalize text-[#173337]">{value}</p></div>; }
function Empty({text}:{text:string}) { return <div className="grid h-48 place-items-center rounded-lg bg-canvas text-sm text-muted-text">{text}</div>; }
function DateSelect({label,value,dates,onChange}:{label:string;value:string;dates:string[];onChange:(value:string)=>void}) { return <label className="text-xs font-semibold">{label}<select value={value} onChange={e=>onChange(e.target.value)} className="mt-1 block h-10 min-w-52 rounded-lg border border-line bg-white px-3 text-sm">{dates.map(date=><option key={date}>{date}</option>)}</select></label>; }
function AllocationTable({rows}:{rows:Allocation[]}) { return <div className="overflow-x-auto"><table className="w-full min-w-[620px] text-left text-sm"><thead><tr className="border-b border-line text-xs text-muted-text"><th className="py-3">Rank</th><th>Sector</th><th>Weight (%)</th><th>Factsheet date</th><th>Last updated</th></tr></thead><tbody>{rows.map((row,index)=><tr className="border-b border-line/70" key={row.id}><td className="py-3">{index+1}</td><td className="font-semibold">{row.sector}</td><td>{row.weight_percent.toFixed(2)}</td><td>{dateText(row.factsheet_date)}</td><td>{dateText(row.updated_at)}</td></tr>)}</tbody></table></div>; }
