"use client";
import { useId, useState } from "react";

interface TrendPoint {
  date: string;
  sst_celsius: number;
}

interface SstTrendChartProps {
  trend: TrendPoint[];
}

const WIDTH = 240;
const HEIGHT = 64;
const PADDING = 8;

export function SstTrendChart({ trend }: SstTrendChartProps) {
  const gradientId = useId();
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  if (trend.length < 2) {
    return null;
  }

  const values = trend.map((p) => p.sst_celsius);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const points = trend.map((p, i) => {
    const x = PADDING + (i / (trend.length - 1)) * (WIDTH - PADDING * 2);
    const y = PADDING + (1 - (p.sst_celsius - min) / range) * (HEIGHT - PADDING * 2);
    return { x, y, ...p };
  });

  const linePath = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
  const areaPath = `${linePath} L${points[points.length - 1].x},${HEIGHT - PADDING} L${points[0].x},${HEIGHT - PADDING} Z`;

  const hovered = hoverIndex != null ? points[hoverIndex] : null;

  return (
    <div className="mt-2">
      <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">
        SST trend ({trend.length} days, °C)
      </div>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="w-full h-16"
        role="img"
        aria-label={`Sea surface temperature over the last ${trend.length} days, ranging from ${min.toFixed(1)} to ${max.toFixed(1)} degrees Celsius`}
        onMouseLeave={() => setHoverIndex(null)}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2563eb" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#2563eb" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={areaPath} fill={`url(#${gradientId})`} stroke="none" />
        <path
          d={linePath}
          fill="none"
          stroke="#2563eb"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {points.map((p, i) => (
          <circle
            key={p.date}
            cx={p.x}
            cy={p.y}
            r={i === hoverIndex ? 3 : 2}
            fill="#2563eb"
            className="dark:fill-blue-400"
          />
        ))}
        {points.map((p, i) => (
          <rect
            key={`hit-${p.date}`}
            x={p.x - (WIDTH / trend.length) / 2}
            y={0}
            width={WIDTH / trend.length}
            height={HEIGHT}
            fill="transparent"
            onMouseEnter={() => setHoverIndex(i)}
          />
        ))}
      </svg>
      {hovered && (
        <div className="text-xs text-slate-600 dark:text-slate-300">
          {new Date(hovered.date).toLocaleDateString(undefined, { month: "short", day: "numeric" })}:{" "}
          {hovered.sst_celsius.toFixed(2)}°C
        </div>
      )}
    </div>
  );
}
