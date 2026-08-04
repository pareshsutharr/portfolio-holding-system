import { cn } from "@/lib/utils";

const bands = [
  { label: "Low", color: "#57bf09" },
  { label: "Low to moderate", color: "#b4db1f" },
  { label: "Moderate", color: "#ffd20a" },
  { label: "Moderately high", color: "#ff9808" },
  { label: "High", color: "#ff5108" },
  { label: "Very high", color: "#e60000" },
] as const;

function point(angle: number, radius: number) {
  const radians = (angle * Math.PI) / 180;
  return { x: 160 + radius * Math.cos(radians), y: 160 + radius * Math.sin(radians) };
}

function wedge(start: number, end: number) {
  const outerStart = point(start, 140);
  const outerEnd = point(end, 140);
  const innerEnd = point(end, 68);
  const innerStart = point(start, 68);
  return `M ${outerStart.x} ${outerStart.y} A 140 140 0 0 1 ${outerEnd.x} ${outerEnd.y} L ${innerEnd.x} ${innerEnd.y} A 68 68 0 0 0 ${innerStart.x} ${innerStart.y} Z`;
}

export function riskLevel(score: number) {
  const index = Math.min(5, Math.floor(Math.max(0, score) / (100 / 6)));
  return bands[index].label;
}

export function Riskometer({
  score,
  level,
  className,
  showScore = true,
}: {
  score: number;
  level?: string;
  className?: string;
  showScore?: boolean;
}) {
  const safeScore = Math.min(100, Math.max(0, Number(score) || 0));
  const needle = point(180 + safeScore * 1.8, 57);
  const resolvedLevel = level || riskLevel(safeScore);

  return (
    <figure className={cn("m-0 w-full", className)} aria-label={`Riskometer: ${safeScore.toFixed(2)} out of 100, ${resolvedLevel}`}>
      <svg viewBox="0 0 320 205" role="img" className="h-auto w-full overflow-visible">
        <title>{`Riskometer — ${resolvedLevel}, score ${safeScore.toFixed(2)} out of 100`}</title>
        {bands.map((band, index) => {
          const start = 180 + index * 30 + 1.2;
          const end = 180 + (index + 1) * 30 - 1.2;
          const labelPoint = point(195 + index * 30, 108);
          const words = band.label.split(" ");
          const lines = band.label.length > 10 ? [words.slice(0, Math.ceil(words.length / 2)).join(" "), words.slice(Math.ceil(words.length / 2)).join(" ")] : [band.label];
          return (
            <g key={band.label}>
              <path d={wedge(start, end)} fill={band.color} />
              <text x={labelPoint.x} y={labelPoint.y - (lines.length - 1) * 5} textAnchor="middle" className="fill-[#172731] text-[8px] font-extrabold uppercase">
                {lines.map((line, lineIndex) => <tspan key={line} x={labelPoint.x} dy={lineIndex ? 10 : 0}>{line}</tspan>)}
              </text>
            </g>
          );
        })}
        <line x1="160" y1="160" x2={needle.x} y2={needle.y} stroke="#172731" strokeWidth="5" strokeLinecap="round" />
        <circle cx="160" cy="160" r="12" fill="#172731" />
        <circle cx="160" cy="160" r="5" fill="white" />
        {showScore && (
          <>
            <text x="160" y="184" textAnchor="middle" className="fill-[#173337] text-[14px] font-extrabold">{safeScore.toFixed(2)}</text>
            <text x="160" y="199" textAnchor="middle" className="fill-[#65736f] text-[9px] font-bold uppercase">{resolvedLevel} risk</text>
          </>
        )}
      </svg>
    </figure>
  );
}
