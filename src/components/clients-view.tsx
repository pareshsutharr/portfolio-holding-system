"use client";

import { LogIn, Plus, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { authFetch, useAuth, type Account } from "@/lib/auth";

type Client = Account & { portfolio_count: number; latest_portfolio?: { portfolio_value?: number; holdings?: number; risk_score?: number } };

export function ClientsView() {
  const auth = useAuth(); const router = useRouter();
  const [clients, setClients] = useState<Client[]>([]); const [error, setError] = useState(""); const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ full_name: "", email: "", password: "" });
  const load = () => authFetch("/api/admin/accounts").then(async r => { const d = await r.json(); if (!r.ok) throw new Error(d.detail); setClients(d.clients); }).catch(e => setError(e.message));
  useEffect(() => { if (auth.ready && auth.user?.role !== "admin") router.replace("/dashboard-v2"); else if (auth.user?.role === "admin") load(); }, [auth.ready, auth.user?.role, router]);
  async function create(event: React.FormEvent) { event.preventDefault(); const r = await authFetch("/api/admin/accounts", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(form) }); const d = await r.json(); if (!r.ok) return setError(d.detail); setOpen(false); setForm({ full_name: "", email: "", password: "" }); load(); }
  async function workAs(client: Client) { const r = await authFetch(`/api/admin/clients/${client.id}/impersonate`, { method: "POST" }); const d = await r.json(); if (!r.ok) return setError(d.detail); auth.setSession(d); router.push("/dashboard-v2"); }
  return <AppShell><div className="mx-auto max-w-6xl px-4 py-8 md:px-8">
    <header className="mb-7 flex items-end justify-between"><div><p className="text-[9px] font-extrabold uppercase tracking-[1.5px] text-[#89938f]">Administration</p><h1 className="mt-1 text-3xl font-bold text-[#173337]">Clients and holdings</h1><p className="mt-2 text-sm text-muted-text">See every client, their latest portfolio, history, and enter their workspace when they need help.</p></div><button className="primary-button" onClick={() => setOpen(true)}><Plus size={16}/> Add client</button></header>
    {error && <p className="mb-4 rounded-lg bg-red-50 p-3 text-xs text-red-700">{error}</p>}
    <section className="overflow-hidden rounded-xl border border-line bg-white">{clients.length === 0 ? <div className="grid place-items-center gap-2 p-14 text-center"><Users className="text-teal"/><strong>No clients yet</strong><span className="text-xs text-muted-text">Create a client or let them register.</span></div> : clients.map(client => <article key={client.id} className="grid grid-cols-[1.4fr_.8fr_1fr_auto] items-center gap-4 border-t border-line px-5 py-4 first:border-0"><div><strong className="block text-sm text-[#173337]">{client.full_name}</strong><span className="text-xs text-muted-text">{client.email}</span></div><div><strong className="block text-sm">{client.portfolio_count}</strong><span className="text-[10px] text-muted-text">analyses</span></div><div>{client.latest_portfolio ? <><strong className="block text-xs">₹{Number(client.latest_portfolio.portfolio_value ?? 0).toLocaleString("en-IN")} · {client.latest_portfolio.holdings} holdings</strong><span className="text-[10px] text-muted-text">Risk {client.latest_portfolio.risk_score ?? "—"}</span></> : <span className="text-xs text-muted-text">No portfolio yet</span>}</div><button className="secondary-button" onClick={() => workAs(client)}><LogIn size={15}/> Work as client</button></article>)}</section>
    {open && <div className="modal-backdrop"><form className="w-full max-w-md rounded-2xl bg-white p-7" onSubmit={create}><h2 className="text-xl font-bold">Create client account</h2><p className="mt-1 text-xs text-muted-text">The client can change their password later.</p><div className="mt-5 space-y-3">{(["full_name", "email", "password"] as const).map(key => <input key={key} className="h-11 w-full rounded-lg border border-line px-3 text-sm" type={key === "password" ? "password" : key === "email" ? "email" : "text"} required minLength={key === "password" ? 8 : 2} placeholder={key.replace("_", " ")} value={form[key]} onChange={e => setForm({ ...form, [key]: e.target.value })}/>)}</div><div className="mt-5 flex justify-end gap-2"><button type="button" className="secondary-button" onClick={() => setOpen(false)}>Cancel</button><button className="primary-button">Create account</button></div></form></div>}
  </div></AppShell>;
}
