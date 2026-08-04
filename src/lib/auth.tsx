"use client";

import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export const API_URL = process.env.NEXT_PUBLIC_API_URL
  ?? (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : "");

export type Account = { id: string; email: string; full_name: string; role: "admin" | "client"; is_active: boolean };
type Session = { user: Account; workspace_owner: Account; is_impersonating: boolean };
type AuthContextValue = Session & { ready: boolean; setSession: (session: Session & { access_token?: string }) => void; logout: () => void; stopImpersonating: () => Promise<void> };

const empty = { user: null as unknown as Account, workspace_owner: null as unknown as Account, is_impersonating: false, ready: false };
const AuthContext = createContext<AuthContextValue>({ ...empty, setSession: () => undefined, logout: () => undefined, stopImpersonating: async () => undefined });

export function token() { return typeof window === "undefined" ? null : localStorage.getItem("northstar_token"); }

export async function authFetch(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  const accessToken = token();
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  return fetch(path.startsWith("http") ? path : `${API_URL}${path}`, { ...init, headers });
}

export async function downloadAuthorized(path: string, filename: string) {
  const response = await authFetch(path);
  if (!response.ok) throw new Error("Download failed");
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url; anchor.download = filename; anchor.click();
  URL.revokeObjectURL(url);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setState] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);
  const pathname = usePathname();
  const router = useRouter();

  const setSession = (value: Session & { access_token?: string }) => {
    if (value.access_token) localStorage.setItem("northstar_token", value.access_token);
    setState(value);
  };
  const logout = () => { localStorage.removeItem("northstar_token"); setState(null); router.replace("/login"); };

  useEffect(() => {
    const accessToken = token();
    if (!accessToken) { Promise.resolve().then(() => setReady(true)); if (pathname !== "/login") router.replace("/login"); return; }
    authFetch("/api/auth/me").then(async (response) => {
      if (!response.ok) throw new Error();
      setState(await response.json());
    }).catch(() => { localStorage.removeItem("northstar_token"); if (pathname !== "/login") router.replace("/login"); }).finally(() => setReady(true));
  }, [pathname, router]);

  const stopImpersonating = async () => {
    const response = await authFetch("/api/auth/stop-impersonating", { method: "POST" });
    if (!response.ok) throw new Error("Could not return to admin account");
    setSession(await response.json()); router.push("/clients");
  };
  const value = { ...(session ?? empty), ready, setSession, logout, stopImpersonating };
  if (!ready && pathname !== "/login") return <div className="grid min-h-screen place-items-center text-sm text-muted-text">Loading secure workspace…</div>;
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() { return useContext(AuthContext); }
