"use client";

import { Check, Download, FileText, LoaderCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { downloadAuthorized } from "@/lib/auth";

export const REPORT_SECTIONS = [
  { key: "holdings", title: "Portfolio holdings", description: "Every security with ISIN, company name, market-cap category, sector, industry, quantity, current price, market value, and portfolio weight." },
  { key: "sector", title: "Sector allocation", description: "Sector-wise exposure table and visual allocation chart showing where the portfolio is concentrated." },
  { key: "industry", title: "Industry allocation", description: "Detailed industry-level exposure table and chart for a deeper diversification view." },
  { key: "market_cap", title: "Market-cap allocation", description: "Large-cap, mid-cap, small-cap, ETF, and other exposure with values, percentages, and chart." },
  { key: "top_holdings", title: "Top holdings", description: "The ten largest positions, their values and weights, plus a concentration bar chart." },
  { key: "benchmarks", title: "Benchmark comparisons", description: "Sector differences and top holdings versus NIFTY 50, NIFTY Midcap 150, and NIFTY 500, including comparison charts." },
  { key: "disparity", title: "Disparity impact analysis", description: "Since-inception return vs. NIFTY 50, NIFTY Midcap 150, and NIFTY 500, the resulting opportunity loss in rupees, and a Sharpe ratio / volatility statistics table." },
  { key: "risk", title: "Risk-O-Meter", description: "Overall portfolio risk score with concentration, sector, market-cap, quality, liquidity, volatility, and beta factor details." },
  { key: "style", title: "Stock style analysis", description: "Growth, value, momentum, and quality profiles, primary style allocation, holding classifications, score matrix, and definitions." },
] as const;

const defaultSelection = () => Object.fromEntries(REPORT_SECTIONS.map(section => [section.key, section.key !== "top_holdings"]));
const selectEverySection = () => Object.fromEntries(REPORT_SECTIONS.map(section => [section.key, true]));

export function ReportDownloadDialog({ runId, open, onOpenChange }: { runId: string | null; open: boolean; onOpenChange: (open: boolean) => void }) {
  const [selected, setSelected] = useState<Record<string, boolean>>(defaultSelection);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!open) return;
    Promise.resolve().then(() => { setSelected(defaultSelection()); setError(""); });
  }, [open]);
  const selectedKeys = useMemo(() => REPORT_SECTIONS.filter(section => selected[section.key]).map(section => section.key), [selected]);
  async function download() {
    if (!runId || !selectedKeys.length) return;
    setBusy(true); setError("");
    try {
      const query = new URLSearchParams({ sections: selectedKeys.join(",") });
      await downloadAuthorized(`/api/analyses/${runId}/report?${query}`, `portfolio-${runId.slice(0, 8)}.pdf`);
      onOpenChange(false);
    } catch { setError("The report could not be generated. Please try again."); }
    finally { setBusy(false); }
  }
  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent className="max-h-[92vh] overflow-hidden p-0 sm:max-w-4xl"><DialogHeader className="border-b border-line px-5 py-5 md:px-7"><div className="flex items-start gap-3"><span className="grid size-10 shrink-0 place-items-center rounded-xl bg-[#e8f4f1] text-teal"><FileText size={20}/></span><div><DialogTitle>Choose what to include in your report</DialogTitle><DialogDescription className="mt-1">Your PDF will use the Growth Avenues landscape presentation design. Recommended sections are selected by default; Top Holdings is optional.</DialogDescription></div></div></DialogHeader><div className="flex items-center justify-between border-b border-line bg-[#f8faf9] px-5 py-3 md:px-7"><p className="text-xs font-semibold text-[#173337]">{selectedKeys.length} of {REPORT_SECTIONS.length} sections selected</p><div className="flex gap-2"><button className="text-xs font-bold text-teal hover:text-teal-dark" onClick={() => setSelected(selectEverySection())}>Select all</button><span className="text-line">|</span><button className="text-xs font-bold text-muted-text hover:text-[#173337]" onClick={() => setSelected({})}>Clear all</button></div></div><div className="grid max-h-[58vh] gap-2 overflow-y-auto p-4 sm:grid-cols-2 md:p-6">{REPORT_SECTIONS.map(section => { const checked = selected[section.key] === true; return <label key={section.key} className={`flex cursor-pointer items-start gap-3 rounded-xl border p-4 transition ${checked ? "border-teal/40 bg-[#f2f8f6] shadow-sm" : "border-line bg-white hover:bg-[#fafcfb]"}`}><input type="checkbox" className="sr-only" checked={checked} onChange={() => setSelected(old => ({...old, [section.key]: !checked}))}/><span className={`mt-0.5 grid size-5 shrink-0 place-items-center rounded-md ${checked ? "bg-teal text-white" : "border border-[#b8c5c1] bg-white"}`}>{checked && <Check size={13} strokeWidth={3}/>}</span><span><b className="block text-xs text-[#173337]">{section.title}</b><small className="mt-1 block text-[11px] leading-[17px] text-muted-text">{section.description}</small></span></label>})}</div>{error && <p className="mx-6 mb-2 rounded-lg bg-red-50 p-3 text-xs font-semibold text-red-700">{error}</p>}<DialogFooter className="border-t border-line bg-white px-5 py-4 md:px-7"><Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button><Button className="gap-2 bg-teal text-white hover:bg-teal-dark" disabled={!selectedKeys.length || busy} onClick={download}>{busy ? <LoaderCircle size={16} className="animate-spin"/> : <Download size={16}/>} {busy ? "Preparing landscape PDF…" : `Download ${selectedKeys.length}-section report`}</Button></DialogFooter></DialogContent></Dialog>;
}
