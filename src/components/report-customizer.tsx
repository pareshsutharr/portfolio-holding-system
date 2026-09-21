"use client";

import { Check, FileText, LoaderCircle, RotateCcw, Save, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { authFetch, type Account, useAuth } from "@/lib/auth";

const sectionLabels: Record<string, { title: string; description: string }> = {
  holdings: { title: "Portfolio holdings", description: "Detailed security-level positions, values, and weights" },
  sector: { title: "Sector allocation", description: "Sector exposure table and chart" },
  industry: { title: "Industry allocation", description: "Industry exposure table and chart" },
  market_cap: { title: "Market-cap allocation", description: "Large, mid, small-cap, and other exposure" },
  top_holdings: { title: "Top holdings", description: "Largest positions and concentration view" },
  benchmarks: { title: "Benchmark comparison", description: "Benchmark summaries and constituent comparisons" },
  disparity: { title: "Disparity impact analysis", description: "Since-inception return vs. benchmarks, opportunity loss, and key statistics" },
  risk: { title: "Risk-O-Meter", description: "Overall risk score and factor breakdown" },
  style: { title: "Investment style", description: "Growth, value, and quality classification" },
};

const BENCHMARK_NAMES = ["Nifty 50", "Nifty Midcap 150", "Nifty 500"];

type Client = Account & { portfolio_count: number };
type Configuration = { title: string; subtitle: string; sections: Record<string, boolean>; benchmarks: Record<string, boolean>; exists?: boolean };

export function ReportCustomizer() {
  const auth = useAuth();
  const router = useRouter();
  const [clients, setClients] = useState<Client[]>([]);
  const [target, setTarget] = useState("global");
  const [config, setConfig] = useState<Configuration | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (auth.ready && auth.user?.role !== "admin") router.replace("/dashboard-v2");
    if (auth.user?.role === "admin") authFetch("/api/admin/accounts").then(r => r.json()).then(data => setClients(data.clients || []));
  }, [auth.ready, auth.user?.role, router]);

  useEffect(() => {
    if (auth.user?.role !== "admin") return;
    Promise.resolve().then(() => { setBusy(true); setError(""); setMessage(""); return authFetch(`/api/admin/report-configurations/${target}`); }).then(async response => {
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not load template");
      setConfig(data);
    }).catch(caught => setError(caught instanceof Error ? caught.message : "Could not load template")).finally(() => setBusy(false));
  }, [target, auth.user?.role]);

  async function save() {
    if (!config) return;
    setBusy(true); setError(""); setMessage("");
    const response = await authFetch(`/api/admin/report-configurations/${target}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(config) });
    const data = await response.json();
    if (!response.ok) setError(data.detail || "Could not save template");
    else { setConfig(data); setMessage(target === "global" ? "Default report updated for all customers." : "Personal report override saved."); }
    setBusy(false);
  }

  async function resetOverride() {
    if (target === "global") return;
    setBusy(true);
    const response = await authFetch(`/api/admin/report-configurations/${target}`, { method: "DELETE" });
    const data = await response.json();
    if (!response.ok) setError(data.detail || "Could not reset template");
    else { setConfig(data.effective); setMessage("Personal override removed. This customer now uses the global template."); }
    setBusy(false);
  }

  return <main className="mx-auto w-full max-w-6xl p-5 md:p-8">
    <header className="mb-7 flex flex-col justify-between gap-4 md:flex-row md:items-end"><div><p className="text-[9px] font-extrabold uppercase tracking-[1.5px] text-[#89938f]">Administration</p><h1 className="mt-1 text-3xl font-bold text-[#173337]">Report customizer</h1><p className="mt-2 max-w-2xl text-sm text-muted-text">Control what customers see in downloaded reports. Set one default for everyone, then create personal overrides where needed.</p></div><button className="primary-button" disabled={busy || !config} onClick={save}>{busy ? <LoaderCircle size={16} className="animate-spin"/> : <Save size={16}/>} Save report template</button></header>

    <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
      <aside className="h-fit rounded-xl border border-line bg-white p-3"><p className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-text">Apply template to</p><button onClick={() => setTarget("global")} className={`flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left text-sm font-semibold ${target === "global" ? "bg-[#e9f3f1] text-teal-dark" : "hover:bg-[#f6f8f6]"}`}><Users size={17}/><span><b className="block">All customers</b><small className="font-normal text-muted-text">Global default</small></span></button><div className="my-2 border-t border-line"/>{clients.map(client => <button key={client.id} onClick={() => setTarget(client.id)} className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm ${target === client.id ? "bg-[#e9f3f1] text-teal-dark" : "hover:bg-[#f6f8f6]"}`}><span className="grid size-8 shrink-0 place-items-center rounded-full bg-[#edf1ef] text-[10px] font-bold">{client.full_name.split(" ").map(p => p[0]).slice(0,2).join("")}</span><span className="min-w-0"><b className="block truncate">{client.full_name}</b><small className="block truncate font-normal text-muted-text">{client.email}</small></span></button>)}</aside>

      <section className="rounded-xl border border-line bg-white p-5 md:p-7">{busy && !config ? <div className="grid min-h-80 place-items-center"><LoaderCircle className="animate-spin text-teal"/></div> : config && <><div className="mb-6 flex items-start justify-between gap-3"><div><div className="flex items-center gap-2"><FileText className="text-teal" size={20}/><h2 className="text-lg font-bold text-[#173337]">{target === "global" ? "Default customer report" : clients.find(c => c.id === target)?.full_name}</h2></div><p className="mt-1 text-xs text-muted-text">Changes apply to both existing and future report downloads.</p></div>{target !== "global" && <button className="secondary-button" onClick={resetOverride}><RotateCcw size={14}/> Use global default</button>}</div>
        <div className="grid gap-4"><label className="text-xs font-semibold">Report title<input className="mt-1.5 h-11 w-full rounded-lg border border-line px-3 text-sm outline-none focus:border-teal" value={config.title} onChange={e => setConfig({...config, title: e.target.value})}/></label><label className="text-xs font-semibold">Introduction<textarea className="mt-1.5 min-h-20 w-full resize-y rounded-lg border border-line p-3 text-sm outline-none focus:border-teal" value={config.subtitle} onChange={e => setConfig({...config, subtitle: e.target.value})}/></label></div>
        <h3 className="mb-3 mt-7 text-sm font-bold text-[#173337]">Included report sections</h3><div className="grid gap-2 sm:grid-cols-2">{Object.entries(sectionLabels).map(([key, item]) => { const enabled = config.sections[key] !== false; return <button key={key} type="button" aria-pressed={enabled} onClick={() => setConfig({...config, sections: {...config.sections, [key]: !enabled}})} className={`flex items-start gap-3 rounded-xl border p-4 text-left transition ${enabled ? "border-teal/40 bg-[#f3f9f7]" : "border-line bg-white opacity-65"}`}><span className={`mt-0.5 grid size-5 shrink-0 place-items-center rounded ${enabled ? "bg-teal text-white" : "border border-line"}`}>{enabled && <Check size={13}/>}</span><span><b className="block text-xs text-[#173337]">{item.title}</b><small className="mt-1 block leading-4 text-muted-text">{item.description}</small></span></button>})}</div>
        <h3 className="mb-1 mt-7 text-sm font-bold text-[#173337]">Benchmarks to compare against</h3><p className="mb-3 text-xs text-muted-text">Controls which indices appear on the benchmark comparison and growth-of-investment pages.</p><div className="flex flex-wrap gap-2">{BENCHMARK_NAMES.map(name => { const enabled = (config.benchmarks ?? {})[name] !== false; return <button key={name} type="button" aria-pressed={enabled} onClick={() => setConfig({...config, benchmarks: {...config.benchmarks, [name]: !enabled}})} className={`flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-semibold transition ${enabled ? "border-teal/40 bg-[#f3f9f7] text-teal-dark" : "border-line bg-white text-muted-text opacity-65"}`}><span className={`grid size-4 shrink-0 place-items-center rounded-full ${enabled ? "bg-teal text-white" : "border border-line"}`}>{enabled && <Check size={10}/>}</span>{name}</button>})}</div></>}
        {message && <p className="mt-5 rounded-lg bg-emerald-50 p-3 text-xs font-semibold text-emerald-700">{message}</p>}{error && <p className="mt-5 rounded-lg bg-red-50 p-3 text-xs font-semibold text-red-700">{error}</p>}</section>
    </div>
  </main>;
}
