import React, { useEffect, useRef } from "react";
import * as z from "zod";
import { gsap } from "gsap";

export const layoutId = "table-of-contents";
export const layoutName = "Table Of Contents";
export const layoutDescription =
  "A high-end editorial table of contents layout with numbered sections and structured descriptions, styled with obsidian glassmorphism.";

const tableOfContentsSchema = z.object({
  title: z.string().min(2).max(100).default("Table of Contents").meta({
    description: "Main title of the slide",
  }),
  items: z
    .array(
      z.object({
        title: z.string().min(2).max(100).meta({
          description: "Section title",
        }),
        description: z.string().min(10).max(100).meta({
          description: "Brief section description",
        }),
      }),
    )
    .min(2)
    .max(8)
    .default([
      {
        title: "Introduction",
        description: "Overview of the project goals and vision.",
      },
      {
        title: "Market Analysis",
        description: "Deep dive into the target audience and TAM.",
      },
      {
        title: "Product Roadmap",
        description: "Key milestones and development phases.",
      },
      {
        title: "Financial Outlook",
        description: "Revenue projections and funding strategy.",
      },
    ])
    .meta({
      description: "List of presentation sections",
    }),
});

export const Schema = tableOfContentsSchema;
export type TableOfContentsData = z.infer<typeof tableOfContentsSchema>;

interface TableOfContentsLayoutProps {
  data?: Partial<TableOfContentsData>;
}

const TableOfContentsLayout: React.FC<TableOfContentsLayoutProps> = ({
  data: slideData,
}) => {
  const items = slideData?.items || [];
  const containerRef = useRef<HTMLDivElement>(null);
  const itemsRef = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    if (containerRef.current) {
      const tl = gsap.timeline({ defaults: { ease: "power4.out", duration: 1 } });
      tl.from(containerRef.current.querySelector(".editorial-title"), { x: -100, opacity: 0 })
        .from(itemsRef.current, { x: 50, opacity: 0, stagger: 0.1 }, "-=0.6");
    }
  }, []);

  return (
    <div
      ref={containerRef}
      className="w-full h-full aspect-video relative overflow-hidden flex flex-col p-16 lg:p-24"
      style={{
        fontFamily: "var(--font-main, sans-serif)",
        backgroundColor: "var(--bg-primary, #000)",
        color: "var(--text-primary, #FFF)",
      }}
    >
      {/* Decorative Grid */}
      <div className="absolute inset-0 opacity-[0.02] pointer-events-none">
        <div className="w-full h-full border-l border-white ml-[25%]"></div>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between mb-20 relative z-10">
        <div className="flex items-center gap-4">
          {(slideData as any)?._logo_url__ && (
            <img src={(slideData as any)?._logo_url__} alt="logo" className="w-8 h-8 object-contain" />
          )}
          <span className="text-xl font-bold tracking-tighter opacity-80 uppercase">
            {(slideData as any)?.__companyName__ || "COSMO"}
          </span>
        </div>
        <div className="flex items-center gap-4">
           <div className="w-12 h-[1px] bg-white/20"></div>
           <span className="text-[10px] font-mono opacity-40 uppercase tracking-widest">Outline // 2026</span>
        </div>
      </div>

      <div className="flex flex-1 gap-20 relative z-10">
        {/* Left: Title */}
        <div className="w-[30%] flex flex-col justify-start">
          <h1 className="editorial-title text-7xl lg:text-8xl uppercase leading-[0.85] mb-8">
            {slideData?.title}
          </h1>
          <div className="w-24 h-1 bg-accent-primary"></div>
        </div>

        {/* Right: Items */}
        <div className="w-[70%] grid grid-cols-2 gap-x-12 gap-y-10 content-start">
          {items.map((item, idx) => (
            <div
              key={idx}
              ref={(el) => { itemsRef.current[idx] = el; }}
              className="group flex gap-8 items-start hover:translate-x-4 transition-transform duration-700"
            >
              <div className="flex flex-col items-center">
                 <span className="text-3xl font-black text-accent-primary opacity-20 group-hover:opacity-100 transition-opacity">
                   0{idx + 1}
                 </span>
                 <div className="w-[1px] h-12 bg-white/10 group-hover:bg-accent-primary transition-colors"></div>
              </div>
              <div className="flex flex-col gap-2 pt-1">
                 <h2 className="text-2xl font-bold uppercase tracking-tight group-hover:text-accent-primary transition-colors">
                   {item.title}
                 </h2>
                 <p className="text-sm leading-relaxed opacity-40 group-hover:opacity-100 transition-opacity duration-500 max-w-sm">
                   {item.description}
                 </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Footer Decoration */}
      <div className="absolute bottom-12 left-24 flex items-center gap-4 opacity-10">
         <span className="text-[10px] font-mono tracking-widest uppercase">System Initialization Complete</span>
         <div className="w-8 h-[1px] bg-white"></div>
         <span className="text-[10px] font-mono tracking-widest uppercase">Ready to Present</span>
      </div>
    </div>
  );
};

export default TableOfContentsLayout;
