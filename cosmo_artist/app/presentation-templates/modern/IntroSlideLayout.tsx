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
    <>
      {/* Montserrat Font */}
      <link
        href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap"
        rel="stylesheet"
      />
      <div
        className="w-full max-w-[1280px] aspect-video mx-auto relative overflow-hidden"
        style={{
          fontFamily: "var(--font-main, sans-serif)",
          backgroundColor: 'var(--bg-primary, #FFFFFF)',
          color: 'var(--text-primary, #111827)',
        }}
      >
        {/* Background Decorative Element */}
        <div className="absolute top-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full opacity-10 blur-[120px]" style={{ backgroundColor: 'var(--accent-primary, #1E4CD9)' }}></div>

        {/* Top Header */}
        {((slideData as any)?.__companyName__ || (slideData as any)?._logo_url__) && (
          <div className="absolute top-0 left-0 right-0 px-8 sm:px-12 lg:px-20 pt-8 z-10">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-3">
                {(slideData as any)?._logo_url__ && <img src={(slideData as any)?._logo_url__} alt="logo" className="w-8 h-8 object-contain" />}
                {(slideData as any)?.__companyName__ && <span className="text-lg font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
                  {(slideData as any)?.__companyName__ || 'Company Name'}
                </span>}
              </div>
            </div>
          </div>
        )}

        {/* Main Content Area */}
        <div
          className="absolute left-20 right-[45%] top-[55%] -translate-y-1/2 z-10"
        >
          {slideData?.title && (
            <div className="relative mb-8">
              <h1
                className="text-7xl font-bold editorial-title"
                style={{ color: 'var(--text-primary)' }}
                id="pitchdeck-title"
              >
                {slideData?.title}
              </h1>
              <div className="w-24 h-1 mt-4" style={{ backgroundColor: 'var(--accent-primary)' }}></div>
            </div>
          )}
          <p className="text-xl leading-relaxed opacity-80 max-w-xl" style={{ color: 'var(--text-primary)' }}>
            {slideData?.description}
          </p>
          
          {slideData?.introCard?.enabled && (
            <div className="mt-12 glass-card rounded-2xl p-6 shadow-xl flex items-center gap-6 max-w-md">
              <div className="w-14 h-14 rounded-xl flex items-center justify-center text-xl font-bold shadow-inner" style={{ backgroundColor: 'var(--accent-primary)', color: '#FFFFFF' }}>
                {(slideData?.introCard?.name || "").split(" ").map(p => p.charAt(0)).join("").slice(0, 2).toUpperCase()}
              </div>
              <div className="flex flex-col">
                <div className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>{slideData?.introCard?.name}</div>
                <div className="text-sm opacity-60" style={{ color: 'var(--text-primary)' }}>{slideData?.introCard?.date}</div>
              </div>
            </div>
          )}
        </div>

        {/* Right Hero Image Section */}
        {slideData?.image && slideData?.image?.__image_url__ && (
          <div className="absolute top-0 bottom-0 right-0 w-[42%] z-0">
            <div className="absolute inset-0 z-10" style={{ background: 'linear-gradient(to right, var(--bg-primary) 0%, transparent 40%)' }}></div>
            <img
              src={slideData?.image?.__image_url__}
              alt={slideData?.image?.__image_prompt__ || slideData?.title || "intro-image"}
              className="w-full h-full object-cover"
              crossOrigin="anonymous"
              referrerPolicy="no-referrer"
            />
          </div>
        )}
      </div>
    </>
  );
};

export default IntroPitchDeckSlide;
