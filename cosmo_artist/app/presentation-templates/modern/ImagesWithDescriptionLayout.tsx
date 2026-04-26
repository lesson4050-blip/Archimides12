import React from "react";
import * as z from "zod";
import { ImageSchema } from "../defaultSchemes";

export const layoutId = "images-with-description";
export const layoutName = "Images With Description";
export const layoutDescription =
  "Images with description slide layout";

const imagesWithDescriptionSlideSchema = z.object({
  name: z.string().min(2).max(50).meta({
    description: "Card title",
  }),
  description: z.string().min(20).max(120).meta({
    description: "Short description for the card",
  }),
  image: ImageSchema,
  linkedIn: z.string().optional().meta({
    description: "LinkedIn profile URL (optional)",
  }),
});

const imagesWithDescriptionSlideSchema2 = z.object({
  title: z.string().min(2).max(100).default("Our Team").meta({
    description: "Main title of the slide",
  }),
  subtitle: z.string().min(2).max(100).optional().meta({
    description: "Optional subtitle describing the team",
  }),
  teamMembers: z
    .array(imagesWithDescriptionSlideSchema)
    .min(2)
    .max(4)
    .default([
      {
        name: "Sarah Johnson",
        description:
          "Strategic leader with 15+ years experience in technology and business development. Former VP at Fortune 500 company.",
        image: {
          __image_url__:
            "https://plus.unsplash.com/premium_photo-1661589856899-6dd0871f9db6?fm=jpg&q=60&w=3000&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxzZWFyY2h8NXx8YnVzaW5lc3N3b21lbnxlbnwwfHwwfHx8MA%3D%3D",
          __image_prompt__: "Professional businesswoman CEO headshot",
        },
      },
      {
        name: "Michael Chen",
        description:
          "Technology expert specializing in scalable architecture and AI solutions. PhD in Computer Science from MIT.",
        image: {
          __image_url__:
            "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80",
          __image_prompt__: "Professional businessman CTO headshot",
        },
      },
      {
        name: "Emily Rodriguez",
        description:
          "Sales leader with proven track record of building high-performing teams and driving revenue growth in B2B markets.",
        image: {
          __image_url__:
            "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80",
          __image_prompt__: "Professional businesswoman VP headshot",
        },
      },
      {
        name: "David Kim",
        description:
          "Product strategist focused on user experience and market-driven solutions. Former product manager at leading tech companies.",
        image: {
          __image_url__:
            "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80",
          __image_prompt__: "Professional businessman product manager headshot",
        },
      },
    ])
    .meta({
      description: "List of team members with their information",
    }),


});

export const Schema = imagesWithDescriptionSlideSchema2;

export type ImagesWithDescriptionSlideData = z.infer<typeof imagesWithDescriptionSlideSchema2>;

interface ImagesWithDescriptionSlideLayoutProps {
  data?: Partial<ImagesWithDescriptionSlideData>;
}

const ImagesWithDescriptionSlideLayout: React.FC<ImagesWithDescriptionSlideLayoutProps> = ({
  data: slideData,
}) => {
  return (
    <>
      {/* Import Montserrat Font */}
      <link
        href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800&display=swap"
        rel="stylesheet"
      />

    <div
      className="w-full max-w-[1280px] h-full aspect-video mx-auto overflow-hidden relative z-20 flex flex-col p-16 lg:p-20"
      style={{
        fontFamily: "var(--font-main, sans-serif)",
        backgroundColor: "var(--bg-primary, #000)",
        color: "var(--text-primary, #FFF)",
      }}
    >
      {/* Editorial Background Elements */}
      <div className="absolute top-0 right-0 w-1/3 h-full bg-accent-primary/5 blur-[120px] pointer-events-none"></div>
      <div className="absolute -bottom-20 -right-20 text-[20rem] font-black opacity-[0.02] select-none pointer-events-none uppercase">
        CORE
      </div>

      {/* Header */}
      <div className="flex items-center justify-between mb-16 relative z-10">
        <div className="flex items-center gap-4">
          {(slideData as any)?._logo_url__ && (
            <img src={(slideData as any)?._logo_url__} alt="logo" className="w-8 h-8 object-contain" />
          )}
          <span className="text-xl font-bold tracking-tighter opacity-80 uppercase">
            {(slideData as any)?.__companyName__ || 'COSMO'}
          </span>
        </div>
        <div className="flex items-center gap-4">
           <div className="w-12 h-[1px] bg-white/20"></div>
           <span className="text-[10px] font-mono opacity-40 uppercase tracking-widest">Team Overview // 04</span>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex flex-col flex-1 relative z-10">
        {/* Title & Subtitle */}
        <div className="mb-12 max-w-2xl">
          <h1 className="text-7xl font-bold mb-6 leading-[0.95] tracking-tight uppercase">
            {slideData?.title}
          </h1>
          <p className="text-xl opacity-50 font-medium leading-relaxed">
            {slideData?.subtitle}
          </p>
        </div>

        {/* Team Grid */}
        <div className="grid grid-cols-4 gap-6 flex-1">
          {slideData?.teamMembers?.map((member, idx) => (
            <div
              key={idx}
              className="glass-card rounded-[2rem] p-6 flex flex-col gap-6 group hover:translate-y-[-8px] transition-all duration-700 ease-[cubic-bezier(0.23,1,0.32,1)]"
            >
              {/* Profile Image with frame */}
              <div className="relative aspect-[4/5] rounded-2xl overflow-hidden grayscale hover:grayscale-0 transition-all duration-700">
                <div className="absolute inset-0 z-10 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-60"></div>
                {member.image.__image_url__ && (
                  <img
                    src={member.image.__image_url__}
                    alt={member.image.__image_prompt__ || member.name}
                    className="w-full h-full object-cover transition-transform duration-1000 group-hover:scale-110"
                  />
                )}
                <div className="absolute bottom-4 left-4 z-20">
                   <span className="text-[10px] font-mono tracking-widest opacity-60 uppercase text-white">Member // 0{idx+1}</span>
                </div>
              </div>

              {/* Info */}
              <div className="space-y-3">
                <h2 className="text-2xl font-bold tracking-tight uppercase text-white">
                  {member.name}
                </h2>
                <p className="text-xs leading-relaxed opacity-40 group-hover:opacity-100 transition-opacity duration-500 line-clamp-3">
                  {member.description}
                </p>
                
                {member.linkedIn && (
                  <a
                    href={member.linkedIn}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center text-[10px] font-bold uppercase tracking-widest text-accent-primary hover:text-white transition-colors pt-2"
                  >
                    LinkedIn
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
    </>
  );
};

export default ImagesWithDescriptionSlideLayout;
