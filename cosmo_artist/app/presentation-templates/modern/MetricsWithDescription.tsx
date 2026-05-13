import React, { useEffect, useRef } from "react";
import * as z from "zod";
import { ImageSchema } from "../defaultSchemes";
import { gsap } from "gsap";

export const layoutId = "metrics-with-description-image";
export const layoutName = "Metrics With Description and Image Slide Layout";
export const layoutDescription =
  "A bold infographic layout featuring massive metrics, detailed descriptions, and a cinematic hero image, styled with obsidian glassmorphism.";

const marketSizeSlideSchema = z.object({
  title: z.string().min(2).max(100).default("Market Size").meta({
    description: "Main slide title",
  }),
  mapImage: ImageSchema.default({
    __image_url__:
      "https://upload.wikimedia.org/wikipedia/commons/8/80/World_map_-_low_resolution.svg",
    __image_prompt__: "World map with location pins or points",
  }),
  marketStats: z
    .array(
      z.object({
        label: z.string().min(3).max(30),
        value: z.string().min(3).max(30),
        description: z.string().min(3).max(130),
      }),
    )
    .min(1)
    .max(4)
    .default([
      {
        label: "Total Available Market (TAM)",
        value: "1.4 Billion",
        description:
          "The maximum potential revenue a business can earn by selling their offer to the entire market.",
      },
      {
        label: "Serviceable Available Market (SAM)",
        value: "194 Million",
        description:
          "The portion of the TAM that is targeted by your products and services within your geographical reach.",
      },
    ])
    .meta({
      description: "Market statistics with labels, values, and descriptions.",
    }),
  description: z
    .string()
    .default(
      "Market size analysis allows stakeholders to determine the potential of their business in the future, providing a clear roadmap for growth and investment strategy.",
    )
    .meta({
      description: "Main description text for the slide",
    }),
});

export const Schema = marketSizeSlideSchema;
export type MarketSizeSlideData = z.infer<typeof marketSizeSlideSchema>;

interface MarketSizeSlideProps {
  data?: Partial<MarketSizeSlideData>;
}

const MarketSizeSlideLayout: React.FC<MarketSizeSlideProps> = ({
  data: slideData,
}) => {
  const stats = slideData?.marketStats || [];
  const containerRef = useRef<HTMLDivElement>(null);
  const statsRef = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    if (containerRef.current) {
      const tl = gsap.timeline({ defaults: { ease: "power4.out", duration: 1 } });
      tl.from(containerRef.current.querySelector(".editorial-title"), { x: -50, opacity: 0 })
        .from(statsRef.current, { y: 30, opacity: 0, stagger: 0.1 }, "-=0.6")
        .from(containerRef.current.querySelector(".hero-image-container"), { scale: 1.1, opacity: 0, duration: 1.5 }, "-=1");
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
      {/* Background Gradients */}
      <div className="absolute top-0 left-0 w-1/3 h-full bg-accent-primary/5 blur-[120px] pointer-events-none"></div>

      {/* Header */}
      <div className="flex items-center justify-between mb-16 relative z-10">
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
           <span className="text-[10px] font-mono opacity-40 uppercase tracking-widest">Market Analysis // 05</span>
        </div>
      </div>

      <div className="flex flex-1 gap-16 relative z-10">
        {/* Left: Market Stats */}
        <div className="w-[55%] flex flex-col justify-center">
          <h1 className="editorial-title text-7xl lg:text-8xl uppercase mb-12 leading-[0.9]">
            {slideData?.title}
          </h1>
          
          <div className="grid grid-cols-2 gap-x-8 gap-y-12">
            {stats.map((stat, idx) => (
              <div 
                key={idx} 
                ref={(el) => { statsRef.current[idx] = el; }}
                className="flex flex-col gap-3 group"
              >
                <div className="flex items-center gap-2">
                   <div className="w-2 h-2 rounded-full bg-accent-primary"></div>
                   <span className="text-[10px] font-bold uppercase tracking-[0.2em] opacity-40">{stat.label}</span>
                </div>
                <div className="text-5xl lg:text-6xl font-black tracking-tighter text-white group-hover:text-accent-primary transition-colors duration-500">
                  {stat.value}
                </div>
                <p className="text-xs leading-relaxed opacity-30 group-hover:opacity-60 transition-opacity duration-500 max-w-[240px]">
                  {stat.description}
                </p>
              </div>
            ))}
          </div>

          <div className="mt-16 pt-8 border-t border-white/10 max-w-md">
             <p className="text-sm leading-relaxed opacity-40 italic">
               "{slideData?.description}"
             </p>
          </div>
        </div>

        {/* Right: Hero Image */}
        <div className="w-[45%] h-full relative hero-image-container">
           <div className="absolute inset-0 z-10 bg-gradient-to-l from-transparent via-black/20 to-black/80"></div>
           <div className="glass-card absolute inset-0 z-20 rounded-[3rem] border border-white/10 pointer-events-none"></div>
           
           <div className="w-full h-full rounded-[3rem] overflow-hidden">
             {slideData?.mapImage?.__image_url__ && (
               <img
                 src={slideData.mapImage.__image_url__}
                 alt={slideData.mapImage.__image_prompt__ || "Market Map"}
                 className="w-full h-full object-cover grayscale-[0.2] hover:grayscale-0 transition-all duration-1000"
               />
             )}
           </div>
           
           <div className="absolute -bottom-8 -right-8 w-48 h-48 bg-accent-primary/20 blur-[60px] rounded-full"></div>
        </div>
      </div>
    </div>
  );
};

export default MarketSizeSlideLayout;
