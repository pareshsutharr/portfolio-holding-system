"use client";

import {
  BarChart3,
  ChevronDown,
  Database,
  FileBarChart,
  FileSpreadsheet,
  Gauge,
  HardDrive,
  LayoutDashboard,
  LogOut,
  Menu,
  Settings,
  SlidersHorizontal,
  PieChart,
  Sparkles,
  TrendingUp,
  UserRound,
  Users,
  X,
} from "lucide-react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/lib/auth";

type NavLink = {
  label: string;
  icon: ReactNode;
  href?: string;
  badge?: string;
};

const primaryNav: NavLink[] = [
  { label: "Overview", icon: <LayoutDashboard size={18} />, href: "/dashboard-v2" },
  { label: "Portfolios", icon: <FileSpreadsheet size={18} />, href: "/reports" },
  { label: "Risk analysis", icon: <Gauge size={18} />, href: "/reports" },
  { label: "Benchmarks", icon: <BarChart3 size={18} />, href: "/benchmarks" },
  { label: "Reports", icon: <FileBarChart size={18} />, href: "/reports" },
  { label: "Compare", icon: <TrendingUp size={18} />, href: "/compare" },
];

const workspaceNav: NavLink[] = [
  { label: "Data center", icon: <HardDrive size={18} />, href: "/data-center" },
  { label: "Data health", icon: <Database size={18} />, href: "/data-health" },
  { label: "Settings", icon: <Settings size={18} />, href: "/settings" },
];

export function AppShell({ children }: { children: ReactNode }) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const pathname = usePathname();
  const auth = useAuth();
  const initials = auth.workspace_owner?.full_name?.split(" ").map(part => part[0]).slice(0, 2).join("").toUpperCase() || "NS";

  const isActive = (href?: string) =>
    !!href && (href === "/dashboard-v2" ? pathname === href : pathname?.startsWith(href));

  return (
    <div className="min-h-screen bg-canvas">
      {mobileNavOpen && (
        <button
          aria-label="Close navigation overlay"
          className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm md:hidden"
          onClick={() => setMobileNavOpen(false)}
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-navy px-4 py-6 text-white transition-transform duration-200 md:translate-x-0 ${
          mobileNavOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-12 items-center px-2">
          <Link href="/dashboard-v2" aria-label="Growth Avenues home" className="block">
            <Image
              src="/logo.png"
              alt="Growth Avenues"
              width={824}
              height={208}
              priority
              className="h-auto w-[182px] rounded-md"
            />
          </Link>
          <button
            className="ml-auto grid size-8 place-items-center rounded-md text-[#a3a3a3] hover:bg-white/10 md:hidden"
            onClick={() => setMobileNavOpen(false)}
            aria-label="Close navigation"
          >
            <X size={18} />
          </button>
        </div>

        <nav aria-label="Primary navigation" className="mt-7 flex flex-1 flex-col gap-1 overflow-y-auto">
          {primaryNav.map((item) => (
            <NavItem key={item.label} item={item} active={!!isActive(item.href)} />
          ))}

          <Collapsible defaultOpen className="mt-2">
            <Separator className="mx-2 my-3 bg-[#262626]" />
            <CollapsibleTrigger className="group flex w-full items-center gap-1 px-3 pb-2 text-left text-[9px] font-bold tracking-[1.4px] text-[#737373] uppercase">
              Workspace
              <ChevronDown size={12} className="ml-auto transition-transform group-data-open:rotate-180" />
            </CollapsibleTrigger>
            <CollapsibleContent className="flex flex-col gap-1">
              {auth.user?.role === "admin" && <NavItem item={{ label: "Clients", icon: <Users size={18} />, href: "/clients" }} active={!!isActive("/clients")} />}
              {auth.user?.role === "admin" && <NavItem item={{ label: "Report customizer", icon: <SlidersHorizontal size={18} />, href: "/report-customizer" }} active={!!isActive("/report-customizer")} />}
              {auth.user?.role === "admin" && <NavItem item={{ label: "Sector allocations", icon: <PieChart size={18} />, href: "/admin/sector-allocations" }} active={!!isActive("/admin/sector-allocations")} />}
              {workspaceNav.filter(item => auth.user?.role === "admin" || !["Data center", "Data health"].includes(item.label)).map((item) => (
                <NavItem key={item.label} item={item} active={!!isActive(item.href)} />
              ))}
            </CollapsibleContent>
          </Collapsible>
        </nav>

        <div className="mx-1 mb-4 rounded-xl border border-[#2a2a2a] bg-[#141414] p-4">
          <div className="mb-3 grid size-8 place-items-center rounded-lg bg-[#262626] text-white">
            <Sparkles size={16} />
          </div>
          <p className="text-xs font-semibold">Data is current</p>
          <p className="mt-1.5 text-[10px] leading-4 text-[#a3a3a3]">
            Market data updated today at 09:42
          </p>
          <Link
            href="/data-health"
            className="flex items-center gap-1.5 text-[10px] font-semibold text-[#d4d4d4] hover:text-white"
          >
            View data health
          </Link>
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex items-center gap-2.5 border-t border-[#262626] px-1 pt-4 text-left hover:opacity-90">
              <Avatar>
                <AvatarFallback className="bg-white text-[11px] font-extrabold text-[#0a0a0a]">
                  {initials}
                </AvatarFallback>
              </Avatar>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[11px] font-semibold">{auth.workspace_owner?.full_name}</p>
                <p className="truncate text-[9px] text-[#a3a3a3]">{auth.is_impersonating ? "Admin working as client" : auth.user?.role}</p>
              </div>
              <ChevronDown size={15} className="text-[#a3a3a3]" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" side="top" className="w-56">
            <DropdownMenuLabel>My account</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link href="/settings">
                <UserRound /> Profile
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href="/settings">
                <Settings /> Settings
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem variant="destructive" onClick={auth.logout}>
              <LogOut /> Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </aside>

      <div className="min-w-0 md:ml-64">
        {auth.is_impersonating && <div className="flex min-h-10 items-center justify-center gap-3 bg-amber px-4 py-2 text-xs font-semibold text-white">Working as {auth.workspace_owner.full_name}<button className="rounded-md border border-white/50 px-2 py-1 hover:bg-white/10" onClick={auth.stopImpersonating}>Return to admin</button></div>}
        <header className="sticky top-0 z-30 flex h-[68px] items-center gap-3 border-b border-line bg-white/95 px-4 backdrop-blur-md md:px-8">
          <button
            className="grid size-9 place-items-center rounded-md border border-line text-[#51615e] hover:bg-[#f5f7f4] md:hidden"
            onClick={() => setMobileNavOpen(true)}
            aria-label="Open navigation"
          >
            <Menu size={19} />
          </button>

          <div className="ml-auto flex items-center gap-2">
            <Badge variant="outline" className="hidden gap-1.5 rounded-full border-line px-2.5 py-1 text-[10px] sm:flex">
              <span className="size-1.5 rounded-full bg-green" /> Live data
            </Badge>
          </div>
        </header>

        <main>{children}</main>
      </div>
    </div>
  );
}

function NavItem({ item, active }: { item: NavLink; active: boolean }) {
  const className = `flex h-[42px] w-full items-center gap-3 rounded-lg px-3 text-left text-[13px] font-semibold transition-colors ${
    active
      ? "bg-white text-[#0a0a0a]"
      : "text-[#a3a3a3] hover:bg-[#1a1a1a] hover:text-white"
  }`;
  const content = (
    <>
      {item.icon}
      <span className="truncate">{item.label}</span>
      {item.badge && (
        <b className="ml-auto rounded-full bg-[#2a2a2a] px-1.5 py-0.5 text-[10px] font-bold text-white">
          {item.badge}
        </b>
      )}
    </>
  );

  return item.href ? (
    <Link href={item.href} className={className}>
      {content}
    </Link>
  ) : (
    <button type="button" className={className}>
      {content}
    </button>
  );
}
