import React, { useEffect, useRef } from "react";
import * as z from "zod";
import { ImageSchema } from "../defaultSchemes";
import { gsap } from "gsap";

export const layoutId = "image-list-with-description";
export const layoutName = "Image List with Description";
export const layoutDescription =
  "An image list with description slide layout upgraded to Aggressive Editorial style with obsidian glassmorphism.";

const imageListWithDescriptionSlideSchema = z.object({
  title: z.string().min(2).max(100).default("Product Overview").meta({
    description: "Main title of the slide. Max 4 words",
  }),
  products: z
    .array(
      z.object({
        title: z.string().min(2).max(100).meta({
          description: "Product title",
        }),
        description: z.string().min(30).max(150).meta({
          description: "Product description",
        }),
        image: ImageSchema.meta({
          description: "Product image",
        }),
      }),
    )
    .min(1)
    .max(4)
    .default([
      {
        title: "Internet of Things",
        description:
          "Detail and explain each product. Our examination of community and market issues increases with additional products/services.",
        image: {
          __image_url__:
            "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=300&h=200&fit=crop",
          __image_prompt__: "Person working on electronics with headphones",
        },
      },
      {
        title: "Analytics Dashboard",
        description:
          "Our alternate product category is available. Our products must work together to solve social and economic issues.",
        image: {
          __image_url__: "https://images.unsplash.com/photo-1556157382-97eda2d62296?w=300&h=200&fit=crop",
          __image_prompt__: "Analytics dashboard on laptop screen",
        },
      },
    ])
    .meta({
      description: "List of products or services to showcase",
    }),
});

export const Schema = imageListWithDescriptionSlideSchema;
export type ImageListWithDescriptionSlideData = z.infer<
  typeof imageListWithDescriptionSlideSchema
>;

interface ImageListWithDescriptionSlideLayoutProps {
  data?: Partial<ImageListWithDescriptionSlideData>;
}

const ImageListWithDescriptionSlideLayout: React.FC<ImageListWithDescriptionSlideLayoutProps> = ({
  data: slideData,
}) => {
  const products = slideData?.products || [];
  const containerRef = useRef<HTMLDivElement>(null);
  const cardsRef = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    if (containerRef.current) {
      const tl = gsap.timeline({ defaults: { ease: "power4.out", duration: 1.2 } });
      
      tl.from(containerRef.current.querySelector(".editorial-title"), {
        y: 60,
        opacity: 0,
        skewY: 5,
      })
      .from(cardsRef.current, {
        y: 100,
        opacity: 0,
        stagger: 0.15,
      }, "-=0.8");
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
      {/* Editorial Grid Overlay */}
      <div className="absolute inset-0 grid grid-cols-12 gap-4 px-20 pointer-events-none opacity-[0.03]">
        {Array.from({ length: 12 }).map((_, i) => (
          <div key={i} className="border-x border-white h-full"></div>
        ))}
      </div>

      {/* Decorative Accent */}
      <div 
        className="absolute -bottom-1/4 -left-1/4 w-full h-full rounded-full opacity-10 blur-[150px] pointer-events-none" 
        style={{ backgroundColor: "var(--accent-primary, #ff4d00)" }}
      ></div>

      {/* Header */}
      <div className="flex items-center justify-between mb-12 relative z-10">
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
           <span className="text-[10px] font-mono opacity-40 uppercase tracking-widest">Solutions // 2026</span>
        </div>
      </div>

      {/* Main Content */}
      <div className="relative z-10 flex flex-col flex-1">
        <h1 className="editorial-title text-7xl lg:text-8xl uppercase mb-16 max-w-4xl leading-[0.9]">
          {slideData?.title}
        </h1>

        <div className="grid grid-cols-4 gap-6 flex-1 items-stretch">
          {products.slice(0, 4).map((prod, idx) => (
            <div
              key={idx}
              ref={(el) => (cardsRef.current[idx] = el)}
              className="obsidian-card rounded-[2rem] overflow-hidden flex flex-col group"
            >
              {/* Image Section */}
              <div className="relative h-48 overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent z-10"></div>
                {prod.image?.__image_url__ && (
                  <img 
                    src={prod.image.__image_url__} 
                    alt={prod.image.__image_prompt__ || prod.title} 
                    className="w-full h-full object-cover transition-transform duration-1000 group-hover:scale-110 grayscale-[0.3] group-hover:grayscale-0" 
                  />
                )}
                <div className="absolute bottom-4 left-6 z-20">
                  <span className="text-[10px] font-mono font-bold tracking-widest text-accent-primary uppercase">Feature {idx + 1}</span>
                </div>
              </div>

              {/* Text Section */}
              <div className="p-8 flex flex-col flex-1">
                <h2 className="text-2xl font-bold uppercase tracking-tight mb-4">{prod.title}</h2>
                <p className="text-sm leading-relaxed opacity-40 group-hover:opacity-100 transition-opacity duration-500">
                  {prod.description}
                </p>
                
                <div className="mt-auto pt-6 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
                   <div className="w-4 h-[1px] bg-accent-primary"></div>
                   <span className="text-[10px] font-bold uppercase tracking-widest text-accent-primary">Explore</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ImageListWithDescriptionSlideLayout;
