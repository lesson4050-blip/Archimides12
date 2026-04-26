import React from "react";
import * as z from "zod";
import { ImageSchema } from "../defaultSchemes";

export const layoutId = "intro-pitchdeck-slide";
export const layoutName = "Intro Pitch Deck Slide";
export const layoutDescription =
  "A visually appealing introduction slide for a pitch deck, featuring a large title, company name, date, and contact information with a modern design.";

const introPitchDeckSchema = z.object({
  title: z.string().min(2).max(100).default("Pitch Deck").meta({
    description: "Main title of the slide",
  }),
  description: z
    .string()
    .min(1)
    .max(200)
    .default("Add a short subtitle or description here.")
    .meta({
      description: "Description shown below the title",
    }),
  introCard: z
    .object({
      enabled: z.boolean().default(true),
      name: z.string().min(1).max(60).default("John Doe"),
      date: z.string().min(1).max(60).default("December 2025"),
    })
    .default({ enabled: true, name: "John Doe", date: "December 2025" })
    .meta({ description: "Optional intro card shown below description" }),
  image: ImageSchema.default({
    __image_url__:
      "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?q=80&w=1600&auto=format&fit=crop",
    __image_prompt__: "Abstract business background",
  }),
});

export const Schema = introPitchDeckSchema;
export type IntroPitchDeckData = z.infer<typeof introPitchDeckSchema>;

interface IntroSlideLayoutProps {
  data: Partial<IntroPitchDeckData>;
}

const IntroPitchDeckSlide: React.FC<IntroSlideLayoutProps> = ({
  data: slideData,
}) => {
  return (
    <div
      className="w-full h-full aspect-video relative overflow-hidden flex"
      style={{
        fontFamily: "var(--font-main, sans-serif)",
        backgroundColor: "var(--bg-primary, #000)",
        color: "var(--text-primary, #FFF)",
      }}
    >
      {/* Cinematic Ambient Light */}
      <div 
        className="absolute -top-1/4 -right-1/4 w-full h-full rounded-full opacity-30 blur-[180px] pointer-events-none" 
        style={{ backgroundColor: "var(--accent-primary, #ff4d00)" }}
      ></div>

      {/* Main Container */}
      <div className="relative z-20 w-full h-full flex">
        
        {/* Left Side: Brand & Content */}
        <div className="w-[60%] h-full flex flex-col justify-between p-20 lg:p-24 bg-gradient-to-r from-black via-black/80 to-transparent">
          
          {/* Header */}
          <div className="flex items-center gap-6">
            <div className="px-4 py-1.5 border border-white/10 rounded-full bg-white/5 backdrop-blur-md">
              <span className="text-xs font-bold tracking-[0.3em] uppercase opacity-70">Confidential // 2026</span>
            </div>
            {(slideData as any)?.__logo_url__ && (
              <img 
                src={(slideData as any)?.__logo_url__} 
                alt="logo" 
                className="w-8 h-8 object-contain" 
              />
            )}
          </div>

          {/* Hero Section */}
          <div className="space-y-10">
            <div className="space-y-2">
               <div className="flex items-center gap-3 text-accent-primary font-bold tracking-[0.2em] uppercase text-xs">
                 <div className="w-8 h-[2px] bg-accent-primary"></div>
                 <span>Presentation Engine v4.0</span>
               </div>
               <h1
                className="text-6xl lg:text-[7rem] font-bold leading-[0.85] tracking-tight uppercase"
                style={{ color: "var(--text-primary)" }}
              >
                {slideData?.title}
              </h1>
            </div>
            
            <p className="text-xl lg:text-2xl font-medium leading-snug opacity-40 max-w-xl text-balance">
              {slideData?.description}
            </p>
          </div>

          {/* Footer Info */}
          <div className="flex items-end justify-between">
            {slideData?.introCard?.enabled && (
              <div className="flex items-center gap-6 group">
                <div 
                  className="w-16 h-16 rounded-2xl flex items-center justify-center text-2xl font-bold bg-white text-black transition-transform group-hover:scale-110 duration-500 shadow-[0_0_40px_rgba(255,255,255,0.2)]" 
                >
                  {(slideData?.introCard?.name || "A").charAt(0).toUpperCase()}
                </div>
                <div className="flex flex-col">
                  <span className="text-xl font-bold uppercase tracking-tight">
                    {slideData?.introCard?.name}
                  </span>
                  <span className="text-xs font-mono opacity-30 uppercase tracking-widest">
                    {slideData?.introCard?.date}
                  </span>
                </div>
              </div>
            )}
            
            <div className="flex flex-col items-end opacity-20">
               <span className="text-[10px] font-mono tracking-widest">ENCRYPTED_ID</span>
               <span className="text-[10px] font-mono tracking-widest uppercase">{(slideData as any)?.__companyName__ || "COSMO"}_CORE</span>
            </div>
          </div>
        </div>

        {/* Right Side: Hero Visual */}
        <div className="w-[40%] h-full relative overflow-hidden">
          <div className="absolute inset-0 z-10 bg-gradient-to-r from-black to-transparent w-32"></div>
          
          <div className="absolute inset-4 z-20 border border-white/5 rounded-[2.5rem] pointer-events-none"></div>

          {slideData?.image?.__image_url__ ? (
            <img
              src={slideData?.image?.__image_url__}
              alt={slideData?.image?.__image_prompt__ || "Hero"}
              className="w-full h-full object-cover grayscale-[0.5] hover:grayscale-0 transition-all duration-1000"
              crossOrigin="anonymous"
              referrerPolicy="no-referrer"
            />
          ) : (
            <div className="w-full h-full bg-neutral-900 flex items-center justify-center">
              <div className="w-12 h-12 rounded-full border-2 border-white/10 border-t-white animate-spin"></div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default IntroPitchDeckSlide;
