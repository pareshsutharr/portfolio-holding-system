import { Globe, Info, ShieldCheck, UserRound } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Card } from "@/components/ui/card";

const API_URL = process.env.NEXT_PUBLIC_API_URL
  ?? (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : "");

export function SettingsView() {
  return (
    <div className="mx-auto max-w-[720px] px-4 py-8 md:px-8 md:py-9">
      <section className="mb-7">
        <p className="mb-1.5 text-[9px] font-extrabold tracking-[1.5px] text-[#89938f] uppercase">Workspace</p>
        <h1 className="text-[28px] font-bold leading-tight text-[#173337] md:text-[30px]">Settings</h1>
        <p className="mt-1.5 text-[13px] text-muted-text">Your profile and this workspace&apos;s configuration.</p>
      </section>

      <Card className="rounded-[13px] p-5">
        <div className="flex items-center gap-3">
          <Avatar size="lg">
            <AvatarFallback className="bg-[#dfc394] text-[13px] font-extrabold text-[#151f22]">PS</AvatarFallback>
          </Avatar>
          <div>
            <p className="text-[14px] font-bold text-[#173337]">Paresh Suthar</p>
            <p className="text-[11px] text-muted-text">Portfolio analyst</p>
          </div>
        </div>
      </Card>

      <Card className="mt-3.5 rounded-[13px] p-5">
        <div className="mb-3 flex items-center gap-2 text-[12px] font-bold text-[#173337]">
          <Info size={15} /> Environment
        </div>
        <div className="flex flex-col gap-2 text-[12px]">
          <Row icon={<Globe size={14} />} label="Analysis API" value={API_URL} />
          <Row icon={<UserRound size={14} />} label="Application" value="Northstar Portfolio Intelligence" />
        </div>
      </Card>

      <Card className="mt-3.5 flex items-start gap-2.5 rounded-[13px] p-5 text-[#4d7463]">
        <ShieldCheck size={17} className="mt-0.5 shrink-0" />
        <p className="m-0 text-[11px] leading-5">
          Account, notification, and export preferences aren&apos;t configurable yet — this page currently only
          reflects the active session and API connection.
        </p>
      </Card>
    </div>
  );
}

function Row({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-t border-[#edf0ed] py-2 first:border-t-0 first:pt-0">
      <span className="flex items-center gap-1.5 text-muted-text">
        {icon} {label}
      </span>
      <span className="truncate text-right font-medium text-[#173337]">{value}</span>
    </div>
  );
}
