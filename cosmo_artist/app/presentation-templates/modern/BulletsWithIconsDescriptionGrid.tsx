import React from "react";
import { RemoteSvgIcon } from "@/app/hooks/useRemoteSvgIcon";
import * as z from "zod";
import { IconSchema } from "../defaultSchemes";

export const layoutId = "bullet-with-icons-description-grid";
export const layoutName = "Bullet With Icons Description Grid";
export const layoutDescription =
  "A bullet with icons description grid slide layout";

const bulletWithIconsDescriptionGridSlideSchema = z.object({

  title: z.string().min(2).max(100).default("Businesses struggle").meta({
    description: "Main title of the slide",
  }),
  mainDescription: z
    .string()
    .min(20)
    .max(300)
    .default(
      "Show that we offer a solution that solves the problems previously described and identified. Make sure that the solutions we offer uphold the values of effectiveness, efficiency, and are highly relevant to the market situation and society is here and what is hsd sdksdf klfdslkf lkflkfsldkf.",
    )
    .meta({
      description: "Main content text describing the solution",
    }),
  sections: z
    .array(
      z.object({
        title: z.string().min(2).max(100).meta({
          description: "Section title",
        }),
        description: z.string().min(5).max(70).meta({
          description: "Section description",
        }),
        icon: IconSchema.optional().meta({
          description: "Icon for the section",
        }),
      }),
    )
    .min(2)
    .max(6)
    .default([
      {
        title: "Market",
        description:
          "Innovative and widely accepted. Innovative and widely accepted. Innovative and widely accepted.",
        icon: {
          __icon_query__: "market innovation",
          __icon_url__:
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/checks-bold.svg",
        },
      },
      {
        title: "Industry",
        description: "Based on sound market decisions.",
        icon: {
          __icon_query__: "industry building",
          __icon_url__:
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/fediverse-logo-bold.svg",
        },
      },
      {
        title: "SEM",
        description: "Driven by precise data and analysis.",
        icon: {
          __icon_query__: "SEM data analysis",
          __icon_url__:
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/video-bold.svg",
        },
      },
      {
        title: "End User",
        description: "Focused on real user impact.",
        icon: {
          __icon_query__: "end user impact",
          __icon_url__:
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/users-four-bold.svg",
        },
      },
      {
        title: "Industry",
        description: "Based on sound market decisions.",
        icon: {
          __icon_query__: "industry building",
          __icon_url__:
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/fediverse-logo-bold.svg",
        },
      },
      {
        title: "SEM",
        description: "Driven by precise data and analysis.",
        icon: {
          __icon_query__: "SEM data analysis",
          __icon_url__:
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/video-bold.svg",
        },
      },

    ])
    .meta({
      description:
        "List of solution sections with titles, descriptions, and optional icons",
    }),
});

export const Schema = bulletWithIconsDescriptionGridSlideSchema;

export type BulletWithIconsDescriptionGridSlideData = z.infer<typeof bulletWithIconsDescriptionGridSlideSchema>;

interface BulletWithIconsDescriptionGridSlideLayoutProps {
  data?: Partial<BulletWithIconsDescriptionGridSlideData>;
}

const BulletWithIconsDescriptionGridSlideLayout = ({
  data: slideData,
}: BulletWithIconsDescriptionGridSlideLayoutProps) => {
  const sections = slideData?.sections || [];
  
  return (
    <div
      className="w-full h-full aspect-video relative z-20 mx-auto overflow-hidden flex flex-col p-16 lg:p-20"
      style={{
        fontFamily: "var(--font-main, sans-serif)",
        backgroundColor: "var(--bg-primary, #000)",
        color: "var(--text-primary, #FFF)",
      }}
    >
      {/* Background Accent Glow */}
      <div 
        className="absolute top-0 right-0 w-1/2 h-1/2 bg-accent-primary opacity-5 blur-[120px] pointer-events-none"
        style={{ backgroundColor: 'var(--accent-primary)' }}
      ></div>

      {/* Editorial Watermark */}
      <div className="absolute -bottom-10 -left-10 text-[15rem] font-black opacity-[0.03] select-none pointer-events-none uppercase leading-none">
        {slideData?.title?.split(" ")[0]}
      </div>

      {/* Header / Brand */}
      <div className="flex items-center justify-between mb-12 relative z-10">
        <div className="flex items-center gap-3">
          {(slideData as any)?._logo_url__ && (
            <img src={(slideData as any)?._logo_url__} alt="logo" className="w-8 h-8 object-contain filter brightness-0 invert" />
          )}
          <span className="text-xl font-bold tracking-tighter opacity-80">
            {(slideData as any)?.__companyName__ || 'COSMO'}
          </span>
        </div>
        <div className="h-[1px] flex-grow mx-8 bg-current opacity-10"></div>
        <div className="text-sm font-mono opacity-40">SECTION 02 // ARCHIMEDES</div>
      </div>

      {/* Content Layout */}
      <div className="flex flex-1 gap-16 items-start relative z-10">
        {/* Left: Title and Main Description */}
        <div className="w-[45%] flex flex-col pt-4">
          <div className="inline-block px-3 py-1 rounded-full bg-accent-primary/10 text-accent-primary text-[10px] font-bold tracking-[0.2em] uppercase mb-6 w-fit">
            Strategy & Vision
          </div>
          <h1 className="text-5xl lg:text-6xl font-bold mb-8 leading-[0.95] tracking-tight uppercase hyphens-none">
            {slideData?.title}
          </h1>
          <div className="w-16 h-1 bg-accent-primary mb-10"></div>
          <p className="text-xl lg:text-2xl leading-snug opacity-80 font-medium text-balance">
            {slideData?.mainDescription}
          </p>
          
          <div className="mt-auto hidden lg:block">
             <div className="flex items-center gap-4 opacity-30">
                <span className="text-xs font-mono">EST. 2026</span>
                <div className="h-[1px] w-20 bg-current"></div>
                <span className="text-xs font-mono">CORE_ENGINE</span>
             </div>
          </div>
        </div>

        {/* Right: Bento Grid of Sections */}
        <div className="w-[55%] grid grid-cols-2 gap-4 h-full content-start">
          {sections.map((section, idx) => (
            <div
              key={idx}
              className="glass-card rounded-[2rem] p-8 flex flex-col gap-6 group hover:translate-y-[-4px] transition-all duration-700 ease-[cubic-bezier(0.23,1,0.32,1)]"
            >
              <div className="flex items-center justify-between">
                <div className="p-4 rounded-2xl bg-white/5 group-hover:bg-accent-primary group-hover:text-black transition-all duration-500">
                  {section?.icon?.__icon_url__ && (
                    <RemoteSvgIcon
                      url={section.icon.__icon_url__}
                      strokeColor={"currentColor"}
                      className="w-8 h-8"
                      color="currentColor"
                      title={section.icon.__icon_query__}
                    />
                  )}
                </div>
                <span className="text-[10px] font-mono opacity-30 group-hover:opacity-100 group-hover:text-accent-primary transition-all">/0{idx + 1}</span>
              </div>
              
              <div className="space-y-3">
                <h2 className="text-2xl font-bold tracking-tight uppercase">
                  {section.title}
                </h2>
                <p className="text-sm leading-relaxed opacity-40 group-hover:opacity-100 transition-opacity duration-500 line-clamp-4">
                  {section.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default BulletWithIconsDescriptionGridSlideLayout;
