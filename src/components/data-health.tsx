"use client";

import { AlertTriangle, CheckCircle2, Database, LoaderCircle, RefreshCw, Server } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const API_URL = process.env.NEXT_PUBLIC_API_URL
  ?? (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : "");

type HealthResponse = {
  status: string;
  database: string;
  time: string;
};

type CheckState = "checking" | "ok" | "error";

export function DataHealth() {
  const [state, setState] = useState<CheckState>("checking");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState("");
  const [checkedAt, setCheckedAt] = useState<Date | null>(null);

  const runCheck = useCallback(() => {
    fetch(`${API_URL}/health`)
      .then(async (response) => {
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail ?? "Health check failed");
        return payload as HealthResponse;
      })
      .then((payload) => {
        setHealth(payload);
        setState("ok");
        setCheckedAt(new Date());
      })
      .catch((caught) => {
        setError(caught instanceof Error ? caught.message : "Could not reach the API");
        setState("error");
        setCheckedAt(new Date());
      });
  }, []);

  const recheck = useCallback(() => {
    setState("checking");
    setError("");
    runCheck();
  }, [runCheck]);

  useEffect(() => {
    runCheck();
  }, [runCheck]);

  return (
    <div className="mx-auto max-w-[820px] px-4 py-8 md:px-8 md:py-9">
      <section className="mb-7 flex flex-wrap items-end justify-between gap-6">
        <div>
          <p className="mb-1.5 text-[9px] font-extrabold tracking-[1.5px] text-[#89938f] uppercase">Workspace</p>
          <h1 className="text-[28px] font-bold leading-tight text-[#173337] md:text-[30px]">Data health</h1>
          <p className="mt-1.5 text-[13px] text-muted-text">
            Live connectivity check against the analysis API and its database.
          </p>
        </div>
        <Button variant="outline" className="h-10 gap-2 rounded-lg px-4 text-[12px] font-bold" onClick={recheck}>
          <RefreshCw size={15} className={state === "checking" ? "animate-spin" : ""} /> Recheck
        </Button>
      </section>

      <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2">
        <StatusCard
          icon={<Server size={19} />}
          label="API server"
          state={state}
          okText={health?.status === "ok" ? "Reachable" : health?.status ?? ""}
          errorText="Unreachable"
        />
        <StatusCard
          icon={<Database size={19} />}
          label="Database"
          state={state}
          okText={health?.database === "connected" ? "Connected" : health?.database ?? ""}
          errorText="Unreachable"
        />
      </div>

      <Card className="mt-3.5 rounded-[13px] p-5">
        <h2 className="text-[14px] font-bold text-[#173337]">Details</h2>
        <div className="mt-3 flex flex-col gap-2 text-[12px]">
          <Row label="API endpoint" value={API_URL} />
          <Row label="Server time" value={health?.time ? new Date(health.time).toLocaleString("en-IN") : "—"} />
          <Row label="Last checked" value={checkedAt ? checkedAt.toLocaleTimeString("en-IN") : "—"} />
          {state === "error" && <Row label="Error" value={error} tone="rose" />}
        </div>
      </Card>
    </div>
  );
}

function StatusCard({
  icon,
  label,
  state,
  okText,
  errorText,
}: {
  icon: React.ReactNode;
  label: string;
  state: CheckState;
  okText: string;
  errorText: string;
}) {
  const tone =
    state === "ok" ? "text-[#3f7259] bg-[#e5f0e9]" : state === "error" ? "text-[#a34f4a] bg-[#f9e7e5]" : "text-[#89938f] bg-[#f2f5f2]";
  return (
    <Card className="rounded-[13px] p-5">
      <div className="flex items-center gap-3">
        <div className={`grid size-9 place-items-center rounded-[10px] ${tone}`}>{icon}</div>
        <div>
          <p className="text-[11px] font-semibold text-muted-text">{label}</p>
          <p className="mt-1 flex items-center gap-1.5 text-[15px] font-bold text-[#173337]">
            {state === "checking" && <LoaderCircle size={15} className="animate-spin text-muted-text" />}
            {state === "ok" && <CheckCircle2 size={15} className="text-[#3f7259]" />}
            {state === "error" && <AlertTriangle size={15} className="text-[#a34f4a]" />}
            {state === "checking" ? "Checking…" : state === "ok" ? okText : errorText}
          </p>
        </div>
      </div>
    </Card>
  );
}

function Row({ label, value, tone }: { label: string; value: string; tone?: "rose" }) {
  return (
    <div className="flex items-center justify-between gap-4 border-t border-[#edf0ed] py-2 first:border-t-0 first:pt-0">
      <span className="text-muted-text">{label}</span>
      <span className={`truncate text-right font-medium ${tone === "rose" ? "text-[#a34f4a]" : "text-[#173337]"}`}>
        {value}
      </span>
    </div>
  );
}
