import React, { useEffect, useRef } from "react";
import * as z from "zod";
import { IconSchema } from "../defaultSchemes";
import { RemoteSvgIcon } from "@/app/hooks/useRemoteSvgIcon";
import { gsap } from "gsap";

export const layoutId = "bullet-with-icons";
export const layoutName = "Bullet With Icons Slide Layout";
export const layoutDescription = "A clean and impactful layout featuring a main title and a list of key categories with icons, styled with obsidian glassmorphism.";

const bulletWithIconsSlideSchema = z.object({
  title: z.string().min(2).max(100).default("The Challenge").meta({
    description: "Main title of the slide",
  }),
  description: z
    .string()
    .min(50)
    .max(300)
    .default(
      "Defining the core challenges is essential for project success. Without a clear problem statement, development remains fragmented and less effective for stakeholders.",
    )
    .meta({
      description: "Main content text describing the context",
    }),
  problemCategories: z
    .array(
      z.object({
        title: z.string().min(2).max(100).meta({
          description: "Title of the category",
        }),
        description: z.string().min(20).max(150).meta({
          description: "Description of the category",
        }),
        icon: IconSchema.optional().meta({
          description: "Icon for the category",
        }),
      }),
    )
    .min(2)
    .max(4)
    .default([
      {
        title: "Inefficiency",
        description: "Businesses struggle with outdated tools and fragmented workflows.",
        icon: {
          __icon_url__: "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/checks-bold.svg",
          __icon_query__: "inefficiency alert",
        },
      },
    ])
    .meta({
      description: "List of categories with titles, descriptions, and icons",
    }),
});

export const Schema = bulletWithIconsSlideSchema;
export type BulletWithIconsSlideData = z.infer<typeof bulletWithIconsSlideSchema>;

interface BulletWithIconsSlideLayoutProps {
  data?: Partial<BulletWithIconsSlideData>;
}

const BulletWithIconsSlideLayout: React.FC<BulletWithIconsSlideLayoutProps> = ({
  data: slideData,
}) => {
  const problemCategories = slideData?.problemCategories || [];
  const containerRef = useRef<HTMLDivElement>(null);
  const itemsRef = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    if (containerRef.current) {
      const tl = gsap.timeline({ defaults: { ease: "power4.out", duration: 1.2 } });
      tl.from(containerRef.current.querySelector(".editorial-title"), { y: 60, opacity: 0 })
        .from(containerRef.current.querySelector(".main-description"), { opacity: 0 }, "-=0.8")
        .from(itemsRef.current, { x: 100, opacity: 0, stagger: 0.1 }, "-=1");
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
      {/* Editorial Watermark */}
      <div className="absolute top-0 right-0 text-[12rem] font-black opacity-[0.02] select-none pointer-events-none uppercase leading-none translate-x-1/4">
        {slideData?.title?.split(" ")[0]}
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
           <span className="text-[10px] font-mono opacity-40 uppercase tracking-widest">Problem Statement // 02</span>
        </div>
      </div>

      <div className="flex flex-1 gap-20 relative z-10 items-center">
        {/* Left: Main Content */}
        <div className="w-[45%] flex flex-col">
           <div className="inline-block px-3 py-1 rounded-full bg-accent-primary/10 text-accent-primary text-[10px] font-bold tracking-[0.3em] uppercase mb-8 w-fit">
              Core Conflict
           </div>
           <h1 className="editorial-title text-7xl lg:text-8xl uppercase mb-10 leading-[0.85]">
             {slideData?.title}
           </h1>
           <div className="w-20 h-1 bg-accent-primary mb-12"></div>
           <p className="main-description text-xl lg:text-2xl leading-relaxed opacity-40 font-medium text-balance">
             {slideData?.description}
           </p>
        </div>

        {/* Right: List Items */}
        <div className="w-[55%] flex flex-col gap-6">
           {problemCategories.map((category, idx) => (
             <div
               key={idx}
               ref={(el) => (itemsRef.current[idx] = el)}
               className="obsidian-card rounded-3xl p-8 flex items-center gap-8 group hover:translate-x-4 transition-all duration-700"
             >
                <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center group-hover:bg-accent-primary transition-colors duration-500">
                   {category.icon?.__icon_url__ && (
                     <RemoteSvgIcon
                       url={category.icon.__icon_url__}
                       strokeColor={"currentColor"}
                       className="w-8 h-8"
                       color="currentColor"
                       title={category.icon.__icon_query__}
                     />
                   )}
                </div>
                <div className="flex flex-col gap-1">
                   <h2 className="text-2xl font-bold uppercase tracking-tight group-hover:text-accent-primary transition-colors">{category.title}</h2>
                   <p className="text-sm opacity-40 group-hover:opacity-100 transition-opacity duration-500 max-w-sm">
                     {category.description}
                   </p>
                </div>
             </div>
           ))}
        </div>
      </div>
    </div>
  );
};

export default BulletWithIconsSlideLayout;
