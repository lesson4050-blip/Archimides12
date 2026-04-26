import React, { useEffect, useRef } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
} from "recharts";
import * as z from "zod";
import { gsap } from "gsap";

export const layoutId = "chart-with-metrics";
export const layoutName = "Chart With Metrics Slide";
export const layoutDescription =
  "A high-end infographic dashboard featuring a chart or table with metrics, styled with obsidian glassmorphism.";

const growthStatsSchema = z
  .object({
    year: z.string(),
  })
  .catchall(z.number())
  .meta({
    description:
      "Growth statistics for a specific year, with any number of metrics as key-value pairs where keys are metric names and values are numbers.",
  });

const tractionSchema = z.object({
  title: z.string().default("Company Traction").meta({
    description: "Main title of the slide",
  }),
  description: z
    .string()
    .min(3)
    .max(200)
    .default(
      "Traction is a period where the company is feeling momentum during its development period. In general, companies will judge success by the amount of revenue and new customers they receive.",
    )
    .meta({
      description:
        "Main content text describing the company's traction and growth momentum.",
    }),
  tableMode: z.boolean().default(false),
  tableColumns: z.array(z.string().min(1).max(40)).min(2).max(10).default(["Metric", "Value"]),
  tableRows: z.array(z.array(z.string().min(0).max(200)).min(2).max(10)).min(1).max(30).default([["Users", "10K+"], ["Revenue", "$1.2M"], ["Satisfaction", "95%"]]),
  growthStats: z
    .array(growthStatsSchema)
    .min(1)
    .max(20)
    .default([
      growthStatsSchema.parse({ year: "2020", revenue: 5, growth: 10 }),
      growthStatsSchema.parse({ year: "2021", revenue: 15, growth: 25 }),
      growthStatsSchema.parse({ year: "2022", revenue: 45, growth: 50 }),
      growthStatsSchema.parse({ year: "2023", revenue: 120, growth: 80 }),
    ])
    .meta({
      description: "Growth statistics for chart visualization.",
    }),
});

export const Schema = tractionSchema;
export type CompanyTractionData = z.infer<typeof tractionSchema>;

interface Props {
  data?: Partial<CompanyTractionData>;
}

const defaultColors = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#ec4899"];

function getSeriesKeys(growthStats: Array<Record<string, string | number>>): string[] {
  if (!growthStats.length) return [];
  const first = growthStats[0];
  return Object.keys(first).filter((key) => key !== "year" && typeof first[key] === "number");
}

function computeStats(growthStats: Array<Record<string, string | number>>, seriesKeys: string[]) {
  if (!growthStats.length) return [];
  const first = growthStats[0];
  const last = growthStats[growthStats.length - 1];
  return seriesKeys.map((key) => {
    const start = typeof first[key] === "number" ? (first[key] as number) : 0;
    const end = typeof last[key] === "number" ? (last[key] as number) : 0;
    const growth = start === 0 ? 0 : ((end - start) / Math.abs(start)) * 100;
    return {
      label: key.replace(/([A-Z])/g, " $1").replace(/^./, (str) => str.toUpperCase()),
      value: `${growth >= 0 ? "+" : ""}${Math.round(growth)}%`,
      description: `Period growth rate`,
    };
  });
}

const CompanyTractionSlideLayout: React.FC<Props> = ({ data }) => {
  const growthStats = data?.growthStats || [];
  const seriesKeys = getSeriesKeys(growthStats);
  const stats = computeStats(growthStats, seriesKeys);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      gsap.from(containerRef.current.querySelectorAll(".stat-card"), {
        y: 40,
        opacity: 0,
        stagger: 0.1,
        duration: 1,
        ease: "power3.out",
      });
    }
  }, []);

  return (
    <div
      ref={containerRef}
      className="w-full h-full aspect-video relative overflow-hidden flex flex-col p-16 lg:p-20"
      style={{
        fontFamily: "var(--font-main, sans-serif)",
        backgroundColor: "var(--bg-primary, #000)",
        color: "var(--text-primary, #FFF)",
      }}
    >
      {/* Background elements */}
      <div className="absolute top-0 right-0 w-1/2 h-full bg-accent-primary/5 blur-[150px] pointer-events-none"></div>
      
      {/* Header */}
      <div className="flex items-center justify-between mb-12 relative z-10">
        <div className="flex items-center gap-4">
          {(data as any)?._logo_url__ && (
            <img src={(data as any)?._logo_url__} alt="logo" className="w-8 h-8 object-contain" />
          )}
          <span className="text-xl font-bold tracking-tighter opacity-80 uppercase">
            {(data as any)?.__companyName__ || "COSMO"}
          </span>
        </div>
        <div className="flex items-center gap-4">
           <div className="w-12 h-[1px] bg-white/20"></div>
           <span className="text-[10px] font-mono opacity-40 uppercase tracking-widest">Traction Report // 2026</span>
        </div>
      </div>

      <div className="flex flex-1 gap-12 relative z-10">
        {/* Left: Info & Stats */}
        <div className="w-[40%] flex flex-col">
          <h1 className="editorial-title text-6xl uppercase mb-8 leading-none">
            {data?.title}
          </h1>
          <p className="text-lg opacity-40 mb-12 max-w-md font-medium">
            {data?.description}
          </p>

          <div className="grid grid-cols-2 gap-4">
            {stats.slice(0, 4).map((stat, idx) => (
              <div key={idx} className="stat-card glass-card rounded-3xl p-6 flex flex-col gap-2">
                <span className="text-[10px] font-mono opacity-30 uppercase tracking-widest">{stat.label}</span>
                <span className="text-4xl font-bold text-accent-primary">{stat.value}</span>
                <span className="text-[10px] opacity-20 uppercase font-bold">{stat.description}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Chart or Table */}
        <div className="w-[60%] flex flex-col">
          <div className="flex-1 glass-card rounded-[2.5rem] p-10 overflow-hidden relative">
            {data?.tableMode ? (
              <div className="w-full h-full overflow-auto custom_scrollbar">
                 <table className="w-full text-left border-separate border-spacing-y-3">
                   <thead>
                     <tr>
                       {data.tableColumns?.map((col, idx) => (
                         <th key={idx} className="pb-4 px-6 text-[10px] font-mono uppercase tracking-widest opacity-30">{col}</th>
                       ))}
                     </tr>
                   </thead>
                   <tbody>
                     {data.tableRows?.map((row, rIdx) => (
                       <tr key={rIdx} className="group">
                         {row.map((cell, cIdx) => (
                           <td key={cIdx} className="bg-white/5 group-hover:bg-white/10 transition-colors px-6 py-4 rounded-2xl text-sm font-medium">
                             {cell}
                           </td>
                         ))}
                       </tr>
                     ))}
                   </tbody>
                 </table>
              </div>
            ) : (
              <div className="w-full h-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={growthStats} margin={{ top: 20, right: 20, left: 0, bottom: 0 }}>
                    <defs>
                      {seriesKeys.map((key, idx) => (
                        <linearGradient key={key} id={`gradient-${idx}`} x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={defaultColors[idx % defaultColors.length]} stopOpacity={0.3}/>
                          <stop offset="95%" stopColor={defaultColors[idx % defaultColors.length]} stopOpacity={0}/>
                        </linearGradient>
                      ))}
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                    <XAxis 
                      dataKey="year" 
                      axisLine={false} 
                      tickLine={false} 
                      tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10, fontWeight: 700 }}
                      dy={10}
                    />
                    <YAxis 
                      axisLine={false} 
                      tickLine={false} 
                      tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10, fontWeight: 700 }}
                    />
                    <Tooltip 
                      contentStyle={{ backgroundColor: "#111", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "1rem" }}
                      itemStyle={{ fontSize: "12px", fontWeight: "bold" }}
                    />
                    <Legend iconType="circle" wrapperStyle={{ paddingTop: "20px", opacity: 0.6 }} />
                    {seriesKeys.map((key, idx) => (
                      <Area
                        key={key}
                        type="monotone"
                        dataKey={key}
                        stroke={defaultColors[idx % defaultColors.length]}
                        strokeWidth={4}
                        fillOpacity={1}
                        fill={`url(#gradient-${idx})`}
                        animationDuration={2000}
                      />
                    ))}
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CompanyTractionSlideLayout;
