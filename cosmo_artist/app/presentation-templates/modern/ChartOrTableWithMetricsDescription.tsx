import React, { useEffect, useRef } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import * as z from "zod";
import { gsap } from "gsap";

export const layoutId = "chart-with-metrics-description";
export const layoutName = "Chart Or Table With Metrics Description";
export const layoutDescription =
  "A detailed infographic dashboard featuring a main chart or table, supported by specific metric cards and editorial descriptions.";

const metricsWithDescriptionSchema = z.object({
  title: z.string().min(2).max(100).default("Growth Analysis").meta({
    description: "Main title of the slide",
  }),
  description: z
    .string()
    .min(3)
    .max(250)
    .default(
      "Our multi-dimensional growth analysis highlights the core drivers of performance across key market segments, demonstrating consistent upward momentum.",
    )
    .meta({
      description: "Detailed description of the chart or table data.",
    }),
  tableMode: z.boolean().default(false),
  tableColumns: z.array(z.string()).default(["Category", "Q1", "Q2", "Q3", "Growth"]),
  tableRows: z.array(z.array(z.string())).default([
    ["Platform", "120K", "150K", "190K", "+26%"],
    ["Enterprise", "$2.4M", "$2.9M", "$3.5M", "+21%"],
    ["Consumer", "$1.1M", "$1.4M", "$1.8M", "+32%"],
  ]),
  chartData: z
    .array(
      z.object({
        label: z.string(),
        value: z.number(),
      }),
    )
    .min(2)
    .max(8)
    .default([
      { label: "Q1", value: 400 },
      { label: "Q2", value: 600 },
      { label: "Q3", value: 850 },
      { label: "Q4", value: 1200 },
    ]),
  metricCards: z
    .array(
      z.object({
        label: z.string().min(3).max(20),
        value: z.string().min(2).max(15),
        trend: z.string().optional(),
      }),
    )
    .min(1)
    .max(3)
    .default([
      { label: "Active Users", value: "2.4M", trend: "+14%" },
      { label: "Retention", value: "92%", trend: "+5%" },
      { label: "CAC", value: "$45", trend: "-12%" },
    ]),
});

export const Schema = metricsWithDescriptionSchema;
export type MetricsWithDescriptionData = z.infer<typeof metricsWithDescriptionSchema>;

interface Props {
  data?: Partial<MetricsWithDescriptionData>;
}

const defaultColors = ["#6366f1", "#818cf8", "#a5b4fc", "#c7d2fe"];

const MetricsWithDescriptionLayout: React.FC<Props> = ({ data }) => {
  const chartData = data?.chartData || [];
  const metricCards = data?.metricCards || [];
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      const tl = gsap.timeline({ defaults: { ease: "power4.out", duration: 1 } });
      tl.from(containerRef.current.querySelector(".editorial-title"), { x: -50, opacity: 0 })
        .from(containerRef.current.querySelectorAll(".metric-card"), { y: 30, opacity: 0, stagger: 0.1 }, "-=0.6")
        .from(containerRef.current.querySelector(".main-viz"), { scale: 0.95, opacity: 0 }, "-=0.8");
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
      <div className="absolute -top-24 -left-24 w-96 h-96 bg-accent-primary/10 blur-[120px] rounded-full pointer-events-none"></div>

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
           <span className="text-[10px] font-mono opacity-40 uppercase tracking-widest">Performance Matrix // 2026</span>
        </div>
      </div>

      <div className="flex flex-1 gap-12 relative z-10">
        {/* Left: Info & Metrics */}
        <div className="w-[35%] flex flex-col">
          <h1 className="editorial-title text-6xl uppercase mb-8 leading-none">
            {data?.title}
          </h1>
          <p className="text-lg opacity-40 mb-12 font-medium leading-relaxed">
            {data?.description}
          </p>

          <div className="flex flex-col gap-4">
            {metricCards.map((card, idx) => (
              <div key={idx} className="metric-card glass-card rounded-3xl p-6 flex justify-between items-center group">
                 <div className="flex flex-col">
                    <span className="text-[10px] font-mono opacity-30 uppercase tracking-widest mb-1">{card.label}</span>
                    <span className="text-3xl font-bold">{card.value}</span>
                 </div>
                 {card.trend && (
                   <div className={`px-3 py-1 rounded-full text-[10px] font-bold ${card.trend.startsWith("+") ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
                     {card.trend}
                   </div>
                 )}
              </div>
            ))}
          </div>
        </div>

        {/* Right: Visualization */}
        <div className="w-[65%] flex flex-col">
          <div className="main-viz flex-1 obsidian-card rounded-[3rem] p-10 overflow-hidden relative">
            {data?.tableMode ? (
              <div className="w-full h-full overflow-auto custom_scrollbar">
                 <table className="w-full text-left border-separate border-spacing-y-4">
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
                           <td key={cIdx} className="bg-white/5 group-hover:bg-white/10 transition-colors px-6 py-5 rounded-2xl text-sm font-bold">
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
                  <BarChart data={chartData} margin={{ top: 20, right: 20, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.03)" />
                    <XAxis 
                      dataKey="label" 
                      axisLine={false} 
                      tickLine={false} 
                      tick={{ fill: "rgba(255,255,255,0.2)", fontSize: 10, fontWeight: 700 }}
                      dy={10}
                    />
                    <YAxis 
                      axisLine={false} 
                      tickLine={false} 
                      tick={{ fill: "rgba(255,255,255,0.2)", fontSize: 10, fontWeight: 700 }}
                    />
                    <Tooltip 
                      cursor={{ fill: "rgba(255,255,255,0.05)" }}
                      contentStyle={{ backgroundColor: "#111", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "1.5rem" }}
                    />
                    <Bar 
                      dataKey="value" 
                      radius={[10, 10, 0, 0]}
                      animationDuration={1500}
                    >
                      {chartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={defaultColors[index % defaultColors.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
            
            {/* Aesthetic Detail */}
            <div className="absolute top-10 right-10 flex gap-2 opacity-10">
               <div className="w-1 h-1 rounded-full bg-white"></div>
               <div className="w-1 h-1 rounded-full bg-white"></div>
               <div className="w-1 h-1 rounded-full bg-white"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MetricsWithDescriptionLayout;
