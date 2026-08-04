"use client";

import { CheckCircle2, CircleAlert, X } from "lucide-react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { API_URL, useAuth } from "@/lib/auth";

export function AuthScreen() {
  const [registering, setRegistering] = useState(false);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const auth = useAuth(); const router = useRouter();
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setError(""); setToast(null);
    const errors: Record<string, string> = {};
    const cleanEmail = email.trim().toLowerCase();
    if (registering && fullName.trim().length < 2) errors.fullName = "Enter your full name.";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cleanEmail)) errors.email = "Enter a valid email address.";
    if (password.length < 8) errors.password = "Password must be at least 8 characters.";
    setFieldErrors(errors);
    if (Object.keys(errors).length) { setToast({ type: "error", message: "Please correct the highlighted fields." }); return; }
    setBusy(true);
    try {
      const response = await fetch(`${API_URL}/api/auth/${registering ? "register" : "login"}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(registering ? { full_name: fullName.trim(), email: cleanEmail, password } : { email: cleanEmail, password }) });
      const contentType = response.headers.get("content-type") ?? "";
      const data = contentType.includes("application/json")
        ? await response.json()
        : { detail: "Authentication service is unavailable. Check the API deployment and environment variables." };
      if (!response.ok) throw new Error(data.detail ?? "Could not sign in");
      auth.setSession(data);
      setToast({ type: "success", message: registering ? "Account created successfully. Opening your dashboard…" : "Login successful. Welcome back!" });
      window.setTimeout(() => router.replace("/dashboard-v2"), 650);
    } catch (caught) { const message = caught instanceof Error ? caught.message : "Could not sign in"; setError(message); setToast({ type: "error", message }); } finally { setBusy(false); }
  }
  return <main className="relative grid min-h-screen place-items-center bg-[#eef3ef] p-5">
    {toast && <div role="status" aria-live="polite" className={`fixed right-5 top-5 z-50 flex max-w-sm items-start gap-3 rounded-xl border bg-white px-4 py-3 shadow-xl ${toast.type === "success" ? "border-emerald-200" : "border-red-200"}`}>{toast.type === "success" ? <CheckCircle2 className="mt-0.5 shrink-0 text-emerald-600" size={20}/> : <CircleAlert className="mt-0.5 shrink-0 text-red-600" size={20}/>}<div><strong className="block text-sm text-[#173337]">{toast.type === "success" ? "Success" : "Unable to continue"}</strong><span className="mt-0.5 block text-xs text-muted-text">{toast.message}</span></div><button aria-label="Dismiss notification" className="ml-2 text-muted-text" onClick={() => setToast(null)}><X size={16}/></button></div>}
    <section className="w-full max-w-md rounded-2xl border border-line bg-white p-8 shadow-xl shadow-[#173337]/5">
      <div className="mb-7">
        <Image src="/logo.png" alt="Growth Avenues" width={824} height={208} priority className="h-auto w-[230px]" />
        <p className="mt-2 text-xs text-muted-text">Secure portfolio intelligence</p>
      </div>
      <h2 className="text-2xl font-bold text-[#173337]">{registering ? "Create your account" : "Welcome back"}</h2>
      <p className="mt-1 text-sm text-muted-text">{registering ? "Start saving and comparing your portfolio analyses." : "Sign in to your private workspace."}</p>
      <form className="mt-6 space-y-4" onSubmit={submit}>
        {registering && <label className="block text-xs font-semibold">Full name<input aria-invalid={!!fieldErrors.fullName} className={`mt-1.5 h-11 w-full rounded-lg border px-3 outline-none focus:border-teal ${fieldErrors.fullName ? "border-red-400 bg-red-50/40" : "border-line"}`} value={fullName} onChange={e => { setFullName(e.target.value); setFieldErrors(old => ({ ...old, fullName: "" })); }} />{fieldErrors.fullName && <span className="mt-1 block text-[11px] text-red-600">{fieldErrors.fullName}</span>}</label>}
        <label className="block text-xs font-semibold">Email<input aria-invalid={!!fieldErrors.email} className={`mt-1.5 h-11 w-full rounded-lg border px-3 outline-none focus:border-teal ${fieldErrors.email ? "border-red-400 bg-red-50/40" : "border-line"}`} type="email" value={email} onChange={e => { setEmail(e.target.value); setFieldErrors(old => ({ ...old, email: "" })); }} />{fieldErrors.email && <span className="mt-1 block text-[11px] text-red-600">{fieldErrors.email}</span>}</label>
        <label className="block text-xs font-semibold">Password<input aria-invalid={!!fieldErrors.password} className={`mt-1.5 h-11 w-full rounded-lg border px-3 outline-none focus:border-teal ${fieldErrors.password ? "border-red-400 bg-red-50/40" : "border-line"}`} type="password" value={password} onChange={e => { setPassword(e.target.value); setFieldErrors(old => ({ ...old, password: "" })); }} />{fieldErrors.password && <span className="mt-1 block text-[11px] text-red-600">{fieldErrors.password}</span>}</label>
        {error && <p className="rounded-lg bg-red-50 p-3 text-xs text-red-700">{error}</p>}
        <button className="h-11 w-full rounded-lg bg-teal text-sm font-bold text-white hover:bg-teal-dark disabled:opacity-60" disabled={busy}>{busy ? "Please wait…" : registering ? "Create client account" : "Sign in"}</button>
      </form>
      <button className="mt-5 w-full text-center text-xs font-semibold text-teal" onClick={() => { setRegistering(!registering); setError(""); }}>{registering ? "Already registered? Sign in" : "New client? Create an account"}</button>
    </section>
  </main>;
}
