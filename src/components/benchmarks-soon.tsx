import { ArrowLeft, BarChart3 } from "lucide-react";
import Link from "next/link";
import { Card } from "@/components/ui/card";

export function BenchmarksSoon() {
  return (
    <div className="mx-auto flex max-w-[640px] flex-col items-center px-4 py-16 text-center md:px-8">
      <Card className="w-full rounded-[13px] p-10">
        <div className="mx-auto grid size-14 place-items-center rounded-full bg-[#ecf4f3] text-[#2a655e]">
          <BarChart3 size={26} />
        </div>
        <h1 className="mt-5 text-[22px] font-bold text-[#173337]">Benchmark comparisons are coming</h1>
        <p className="mx-auto mt-2.5 max-w-sm text-[13px] leading-6 text-muted-text">
          We&apos;re building index-level tracking so you can compare your portfolio&apos;s performance against
          Nifty 50, Nifty 500, and sector benchmarks side by side. This page will go live once that&apos;s ready.
        </p>
        <Link
          href="/dashboard-v2"
          className="mt-6 inline-flex items-center gap-1.5 text-[12px] font-bold text-teal hover:text-teal-dark"
        >
          <ArrowLeft size={15} /> Back to overview
        </Link>
      </Card>
    </div>
  );
}
