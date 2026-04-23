import React from "react";
import * as z from "zod";
import { ImageSchema } from "../defaultSchemes";

export const layoutId = "intro-pitchdeck-slide";
export const layoutName = "Intro Pitch Deck Slide";
export const layoutDescription =
  "A visually appealing introduction slide for a pitch deck, featuring a large title, company name, date, and contact information with a modern design. This Slide is always the first slide in a pitch deck, setting the tone for the presentation with a clean and professional look.";
const introPitchDeckSchema = z.object({
  title: z.string().min(2).max(15).default("Pitch Deck").meta({
    description: "Main title of the slide",
  }),
  description: z
    .string()
    .min(1)
    .max(200)
    .default("Add a short subtitle or description here. Add a short subtitle or description here. Add a short subtitle or description here. Add a short subtitle or description here.")
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
        backgroundColor: 'var(--bg-primary, #000)',
        color: 'var(--text-primary, #FFF)',
      }}
    >
      {/* Dynamic Background Glow */}
      <div 
        className="absolute -top-1/4 -right-1/4 w-full h-full rounded-full opacity-20 blur-[150px] animate-pulse" 
        style={{ backgroundColor: 'var(--accent-primary, #6366f1)' }}
      ></div>

      {/* Left Sidebar - Title & Brand */}
      <div className="relative z-20 w-[60%] h-full flex flex-col justify-between p-16 lg:p-24">
        {/* Brand/Logo Section */}
        <div className="flex items-center gap-4">
          {(slideData as any)?._logo_url__ && (
            <img 
              src={(slideData as any)?._logo_url__} 
              alt="logo" 
              className="w-10 h-10 object-contain filter brightness-0 invert" 
            />
          )}
          <span className="text-2xl font-black tracking-tighter premium-gradient-text">
            {(slideData as any)?.__companyName__ || 'COSMO'}
          </span>
        </div>

        {/* Hero Title - Aggressive Editorial Style */}
        <div className="flex flex-col gap-6">
          <div className="relative">
             <h1
              className="text-[8rem] lg:text-[10rem] font-black leading-[0.8] editorial-title select-none opacity-10 absolute -left-12 -top-12 pointer-events-none"
            >
              {slideData?.title?.split(" ")[0]}
            </h1>
            <h1
              className="text-8xl lg:text-9xl font-black leading-[0.85] editorial-title relative z-10"
              style={{ color: 'var(--text-primary)' }}
              id="pitchdeck-title"
            >
              {slideData?.title}
            </h1>
          </div>
          <p className="text-xl lg:text-2xl font-light leading-relaxed opacity-60 max-w-lg mt-4">
            {slideData?.description}
          </p>
        </div>

        {/* Contact/Date Card */}
        {slideData?.introCard?.enabled && (
          <div className="glass-card rounded-xl p-6 flex items-center gap-5 max-w-sm">
            <div 
              className="w-14 h-14 rounded-lg flex items-center justify-center text-xl font-bold shadow-lg" 
              style={{ backgroundColor: 'var(--accent-primary)', color: '#FFF' }}
            >
              {(slideData?.introCard?.name || "A").charAt(0).toUpperCase()}
            </div>
            <div className="flex flex-col">
              <span className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
                {slideData?.introCard?.name}
              </span>
              <span className="text-sm opacity-50" style={{ color: 'var(--text-primary)' }}>
                {slideData?.introCard?.date}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Right Section - Hero Visual */}
      <div className="relative w-[40%] h-full overflow-hidden">
        {/* Cinematic Gradient Mask */}
        <div 
          className="absolute inset-0 z-10" 
          style={{ 
            background: 'linear-gradient(to right, var(--bg-primary) 0%, rgba(0,0,0,0) 30%), linear-gradient(to top, var(--bg-primary) 0%, transparent 20%)' 
          }}
        ></div>
        
        {slideData?.image?.__image_url__ ? (
          <img
            src={slideData?.image?.__image_url__}
            alt={slideData?.image?.__image_prompt__ || "Hero"}
            className="w-full h-full object-cover scale-110 hover:scale-100 transition-transform duration-[3s] ease-out"
            crossOrigin="anonymous"
            referrerPolicy="no-referrer"
          />
        ) : (
          <div className="w-full h-full bg-neutral-900 flex items-center justify-center">
            <div className="w-24 h-24 rounded-full border-2 border-dashed border-neutral-700 animate-spin"></div>
          </div>
        )}
      </div>
    </div>
  );
};

export default IntroPitchDeckSlide;
