import React, { useEffect, useRef } from "react";
import * as z from "zod";
import { ImageSchema } from "../defaultSchemes";
import { gsap } from "gsap";

export const layoutId = "image-and-description";
export const layoutName = "Image And Description";
export const layoutDescription =
  "A high-impact editorial layout featuring a large cinematic image, bold title, and structured description, styled with obsidian glassmorphism.";

const imageAndDescriptionSlideSchema = z.object({
  title: z.string().min(2).max(100).default("Innovating the Future").meta({
    description: "Main title of the slide",
  }),
  description: z.string().min(20).max(400).default("Detailing the next generation of solutions designed to transform the industry landscape with cutting-edge technology and human-centric design.").meta({
    description: "Detailed description of the content",
  }),
  image: ImageSchema.default({
    __image_url__: "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?q=80&w=1600&auto=format&fit=crop",
    __image_prompt__: "Futuristic robot hands or technology background",
  }),
});

export const Schema = imageAndDescriptionSlideSchema;
export type ImageAndDescriptionSlideData = z.infer<typeof imageAndDescriptionSlideSchema>;

interface ImageAndDescriptionSlideLayoutProps {
  data?: Partial<ImageAndDescriptionSlideData>;
}

const ImageAndDescriptionSlideLayout: React.FC<ImageAndDescriptionSlideLayoutProps> = ({
  data: slideData,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      const tl = gsap.timeline({ defaults: { ease: "power4.out", duration: 1.2 } });
      tl.from(containerRef.current.querySelector(".editorial-title"), { x: -60, opacity: 0 })
        .from(containerRef.current.querySelector(".description-text"), { y: 20, opacity: 0 }, "-=0.8")
        .from(containerRef.current.querySelector(".hero-image"), { clipPath: "inset(0 100% 0 0)", duration: 1.5 }, "-=1");
    }
  }, []);

  return (
    <div
      ref={containerRef}
      className="w-full h-full aspect-video relative overflow-hidden flex"
      style={{
        fontFamily: "var(--font-main, sans-serif)",
        backgroundColor: "var(--bg-primary, #000)",
        color: "var(--text-primary, #FFF)",
      }}
    >
      {/* Background Accent */}
      <div className="absolute top-0 right-0 w-1/2 h-full bg-accent-primary/5 blur-[150px] pointer-events-none"></div>

      {/* Header */}
      <div className="absolute top-16 left-20 right-20 flex items-center justify-between z-30">
        <div className="flex items-center gap-4">
          {(slideData as any)?._logo_url__ && (
            <img src={(slideData as any)?._logo_url__} alt="logo" className="w-8 h-8 object-contain" />
          )}
          <span className="text-xl font-bold tracking-tighter opacity-80 uppercase">
            {(slideData as any)?.__companyName__ || "COSMO"}
          </span>
        </div>
        <div className="flex items-center gap-4">
           <span className="text-[10px] font-mono opacity-40 uppercase tracking-widest">Vision Strategy // 03</span>
        </div>
      </div>

      {/* Main Content Split */}
      <div className="flex w-full h-full relative z-20">
        {/* Left: Content */}
        <div className="w-[50%] h-full flex flex-col justify-center pl-24 pr-16 bg-gradient-to-r from-black via-black/90 to-transparent">
           <div className="inline-block px-3 py-1 rounded-full bg-accent-primary/10 text-accent-primary text-[10px] font-bold tracking-[0.3em] uppercase mb-8 w-fit">
              Strategic Insight
           </div>
           <h1 className="editorial-title text-7xl lg:text-8xl uppercase mb-10 leading-[0.85]">
             {slideData?.title}
           </h1>
           <div className="w-20 h-1 bg-accent-primary mb-12"></div>
           <p className="description-text text-xl lg:text-2xl leading-relaxed opacity-50 font-medium text-balance max-w-xl">
             {slideData?.description}
           </p>
           
           <div className="mt-20 flex items-center gap-8 opacity-20">
              <div className="flex flex-col">
                 <span className="text-[10px] font-mono">LATITUDE</span>
                 <span className="text-[10px] font-mono">40.7128° N</span>
              </div>
              <div className="flex flex-col">
                 <span className="text-[10px] font-mono">LONGITUDE</span>
                 <span className="text-[10px] font-mono">74.0060° W</span>
              </div>
           </div>
        </div>

        {/* Right: Cinematic Visual */}
        <div className="w-[50%] h-full relative overflow-hidden">
           <div className="absolute inset-0 z-10 bg-gradient-to-r from-black to-transparent w-24"></div>
           <div className="hero-image w-full h-full">
             {slideData?.image?.__image_url__ && (
               <img
                 src={slideData.image.__image_url__}
                 alt={slideData.image.__image_prompt__ || "Hero"}
                 className="w-full h-full object-cover grayscale-[0.3] hover:grayscale-0 transition-all duration-1000 scale-105"
               />
             )}
           </div>
           
           {/* Glass Frame Overlay */}
           <div className="absolute inset-10 z-20 border border-white/5 rounded-[3rem] pointer-events-none"></div>
        </div>
      </div>
    </div>
  );
};

export default ImageAndDescriptionSlideLayout;
