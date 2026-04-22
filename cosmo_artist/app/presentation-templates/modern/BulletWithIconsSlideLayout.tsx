import React from "react";
import * as z from "zod";
import { ImageSchema, IconSchema } from "../defaultSchemes";
import { RemoteSvgIcon } from "@/app/hooks/useRemoteSvgIcon";

export const layoutId = "bullet-with-icons";
export const layoutName = "Bullet With Icons Slide Layout";
export const layoutDescription = "Bullets with icons slide layout";
const bulletWithIconsSlideSchema = z.object({
  title: z.string().min(3).max(20).default("Problem").meta({
    description: "Main title of the problem statement slide",
  }),
  description: z
    .string()
    .min(50)
    .max(200)
    .default(
      "A problem needs to be discussed further and in detail because this problem is the main foundation in the initial development of a product, service, and decision making. Without a well-defined problem, it will have an impact on a job that is unfocused, unmanaged, and less relevant.",
    )
    .meta({
      description: "Main content text describing the problem statement",
    }),
  problemCategories: z
    .array(
      z.object({
        title: z.string().min(3).max(30).meta({
          description: "Title of the problem category",
        }),
        description: z.string().min(20).max(100).meta({
          description: "Description of the problem category",
        }),
        icon: IconSchema.optional().meta({
          description: "Optional icon for the problem category",
        }),
      }),
    )
    .min(2)
    .max(3)
    .default([
      {
        title: "Inefficiency",
        description:
          "Businesses struggle to find digital tools that meet their needs, causing operational slowdowns.",
        icon: {
          __icon_url__:
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/checks-bold.svg",
          __icon_query__: "warning alert inefficiency",
        },
      },
      {
        title: "High Costs",
        description:
          "Outdated systems increase expenses, while small businesses struggle to expand their market reach.",
        icon: {
          __icon_url__:
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/fediverse-logo-bold.svg",
          __icon_query__: "trending up costs chart",
        },
      },
      {
        title: "Inefficiency",
        description:
          "Businesses struggle to find digital tools that meet their needs, causing operational slowdowns.",
        icon: {
          __icon_url__:
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/video-bold.svg",
          __icon_query__: "warning alert inefficiency",
        },
      },
      {
        title: "Inefficiency",
        description:
          "Businesses struggle to find digital tools that meet their needs, causing operational slowdowns.",
        icon: {
          __icon_url__:
            "https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/users-four-bold.svg",
          __icon_query__: "warning alert inefficiency",
        },
      },
    ])
    .meta({
      description:
        "List of problem categories with titles, descriptions, and optional icons",
    }),


});

export const Schema = bulletWithIconsSlideSchema;

export type BulletWithIconsSlideData = z.infer<
  typeof bulletWithIconsSlideSchema
>;

interface BulletWithIconsSlideLayoutProps {
  data?: Partial<BulletWithIconsSlideData>;
}

const BulletWithIconsSlideLayout = ({
  data: slideData,
}: BulletWithIconsSlideLayoutProps) => {
  const problemCategories = slideData?.problemCategories || [];

  return (
    <>
      {/* Import fonts */}
      <link
        href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap"
        rel="stylesheet"
      />

      <div
        className="w-full max-w-[1280px] aspect-video relative z-20 mx-auto overflow-hidden"
        style={{
          fontFamily: "var(--font-main, sans-serif)",
          backgroundColor: "var(--bg-primary, #FFFFFF)",
          color: "var(--text-primary, #111827)",
        }}
      >
        {/* Background Decorative Element */}
        <div className="absolute bottom-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full opacity-5 blur-[100px]" style={{ backgroundColor: 'var(--accent-primary, #1E4CD9)' }}></div>

        {/* Top Header */}
        {((slideData as any)?.__companyName__ || (slideData as any)?._logo_url__) && (
          <div className="absolute top-0 left-0 right-0 px-16 pt-8 z-10">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                {(slideData as any)?._logo_url__ && <img src={(slideData as any)?._logo_url__} alt="logo" className="w-8 h-8 object-contain" />}
                {(slideData as any)?.__companyName__ && <span className="text-lg font-bold tracking-tight opacity-60">
                  {(slideData as any)?.__companyName__ || 'Company Name'}
                </span>}
              </div>
            </div>
          </div>
        )}

        {/* Main Content Area */}
        <div className="flex h-full px-20 pb-16 pt-24 items-center">
          {/* Left side - Main Problem */}
          <div className="flex-1 pr-12">
            <div className="flex flex-col items-start">
              <h2 className="text-6xl font-bold mb-10 leading-none editorial-title" style={{ color: 'var(--text-primary)' }}>
                {slideData?.title}
              </h2>
              <div className="w-20 h-1 mb-8" style={{ backgroundColor: 'var(--accent-primary)' }}></div>
              <div className="text-xl leading-relaxed opacity-80 max-w-lg" style={{ color: 'var(--text-primary)' }}>
                {slideData?.description}
              </div>
            </div>
          </div>

          {/* Right side - List with Glass Cards */}
          <div className="flex-1 pl-12">
            <div className="w-full max-w-xl mx-auto flex flex-col gap-6">
              {problemCategories.map((category, index) => (
                <div
                  key={index}
                  className="glass-card flex items-start gap-6 rounded-2xl p-6 shadow-lg border-l-4"
                  style={{ borderLeftColor: 'var(--accent-primary)' }}
                >
                  <div className="flex-shrink-0 w-14 h-14 flex items-center justify-center rounded-xl" style={{ backgroundColor: 'rgba(var(--accent-primary-rgb, 30, 76, 217), 0.1)' }}>
                    {category.icon?.__icon_url__ ? (
                      <RemoteSvgIcon
                        url={category.icon.__icon_url__}
                        strokeColor={"var(--accent-primary)"}
                        className="w-10 h-10"
                        color="var(--accent-primary)"
                        title={category.icon.__icon_query__}
                      />
                    ) : (
                      <div className="w-10 h-10 rounded-full opacity-20" style={{ backgroundColor: 'var(--accent-primary)' }} />
                    )}
                  </div>
                  <div>
                    <h3 className="text-2xl font-bold mb-2 leading-tight" style={{ color: 'var(--text-primary)' }}>
                      {category.title}
                    </h3>
                    <p className="text-lg leading-snug opacity-70" style={{ color: 'var(--text-primary)' }}>
                      {category.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default BulletWithIconsSlideLayout;
