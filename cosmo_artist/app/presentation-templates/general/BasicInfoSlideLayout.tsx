import React, { useEffect, useRef } from 'react'
import * as z from "zod";
import gsap from 'gsap';
import { ImageSchema } from '../defaultSchemes';

export const layoutId = 'basic-info-slide'
export const layoutName = 'Basic Info'
export const layoutDescription = 'A clean premium slide layout with title, description text, and a supporting image.'

const basicInfoSlideSchema = z.object({
    title: z.string().min(2).max(100).default('Product Overview').meta({
        description: "Main title of the slide",
    }),
    description: z.string().min(10).max(250).default('Our product offers customizable dashboards for real-time reporting and data-driven decisions. It integrates with third-party tools to enhance operations and scales with business growth for improved efficiency.').meta({
        description: "Main description text content",
    }),
    image: ImageSchema.default({
        __image_url__: 'https://images.unsplash.com/photo-1552664730-d307ca884978?auto=format&fit=crop&w=1000&q=80',
        __image_prompt__: 'Business team in meeting room discussing product features and solutions'
    }).meta({
        description: "Supporting image for the slide",
    })
})

export const Schema = basicInfoSlideSchema

export type BasicInfoSlideData = z.infer<typeof basicInfoSlideSchema>

interface BasicInfoSlideLayoutProps {
    data?: Partial<BasicInfoSlideData>
}

const BasicInfoSlideLayout: React.FC<BasicInfoSlideLayoutProps> = ({ data: slideData }) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const titleRef = useRef<HTMLHeadingElement>(null);
    const descriptionRef = useRef<HTMLParagraphElement>(null);
    const imageContainerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!containerRef.current) return;

        const ctx = gsap.context(() => {
            // Initial states
            gsap.set(titleRef.current, { y: 40, opacity: 0 });
            gsap.set(descriptionRef.current, { y: 30, opacity: 0 });
            gsap.set(imageContainerRef.current, { scale: 0.9, opacity: 0, rotate: 3 });
            gsap.set('.bg-accent-blob', { scale: 0, opacity: 0 });

            // Animation Timeline
            const tl = gsap.timeline({ defaults: { ease: 'power4.out', duration: 1.2 } });

            tl.to('.bg-accent-blob', { scale: 1, opacity: 0.25, stagger: 0.2, duration: 2 })
              .to(imageContainerRef.current, { scale: 1, opacity: 1, rotate: 0, duration: 1.5 }, '-=1.5')
              .to(titleRef.current, { y: 0, opacity: 1 }, '-=1')
              .to('.accent-bar', { width: '6rem', duration: 0.8 }, '-=0.8')
              .to(descriptionRef.current, { y: 0, opacity: 1 }, '-=0.6');

            // Floating animation for blobs
            gsap.to('.bg-accent-blob-1', {
                x: '+=30',
                y: '+=20',
                duration: 6,
                repeat: -1,
                yoyo: true,
                ease: 'sine.inOut'
            });
            gsap.to('.bg-accent-blob-2', {
                x: '-=35',
                y: '-=25',
                duration: 8,
                repeat: -1,
                yoyo: true,
                ease: 'sine.inOut'
            });
        }, containerRef);

        return () => ctx.revert();
    }, []);

    return (
        <>
            <link
                href="https://fonts.googleapis.com/css2?family=Outfit:wght@600;800&family=Plus+Jakarta+Sans:wght@300;400;500;700&display=swap"
                rel="stylesheet"
            />

            <div
                ref={containerRef}
                className="w-full rounded-sm max-w-[1280px] shadow-2xl max-h-[720px] aspect-video bg-[#080615] relative z-20 mx-auto overflow-hidden border border-white/5 p-12 flex flex-col justify-between text-white"
                style={{
                    fontFamily: "'Plus Jakarta Sans', sans-serif"
                }}
            >
                <style dangerouslySetInnerHTML={{ __html: `
                    .bg-grid {
                        background-image: linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px),
                                        linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
                        background-size: 50px 50px;
                    }
                ` }} />

                {/* Grid Overlay & Floating Blobs */}
                <div className="absolute inset-0 bg-grid opacity-30 pointer-events-none" />
                <div className="bg-accent-blob bg-accent-blob-1 absolute -top-20 -left-20 w-[450px] h-[450px] rounded-full blur-[110px] pointer-events-none" 
                     style={{ background: 'rgba(139, 92, 246, 0.25)' }}></div>
                <div className="bg-accent-blob bg-accent-blob-2 absolute -bottom-20 -right-20 w-[500px] h-[500px] rounded-full blur-[120px] pointer-events-none" 
                     style={{ background: 'rgba(236, 72, 153, 0.2)' }}></div>

                {/* Header / Logo */}
                <div className="relative z-10 flex justify-between items-center mb-6">
                    <div className="flex items-center gap-3">
                        {(slideData as any)?._logo_url__ && (
                            <img src={(slideData as any)?._logo_url__} alt="logo" className="w-9 h-9 object-contain" />
                        )}
                        {(slideData as any)?.__companyName__ && (
                            <span className="text-lg font-bold tracking-tight text-white/90 uppercase">
                                {(slideData as any)?.__companyName__}
                            </span>
                        )}
                    </div>
                    <div className="h-[1px] flex-1 mx-8 bg-white/10" />
                    <div className="text-xs font-bold uppercase tracking-widest text-white/40">
                        Information Overview
                    </div>
                </div>

                {/* Main Content Grid */}
                <div className="relative z-10 flex-1 grid grid-cols-12 gap-10 items-center">
                    
                    {/* Left Section - Supporting Image */}
                    <div className="col-span-5 flex items-center justify-center">
                        <div 
                            ref={imageContainerRef}
                            className="relative w-full aspect-[4/3] rounded-[2rem] overflow-hidden shadow-2xl border border-white/10 group"
                        >
                            <img
                                src={slideData?.image?.__image_url__ || ''}
                                alt={slideData?.image?.__image_prompt__ || slideData?.title || ''}
                                className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-115 pointer-events-none"
                            />
                            <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent pointer-events-none" />
                            
                            {/* Accent border overlay */}
                            <div className="absolute inset-0 border border-white/10 rounded-[2rem] pointer-events-none" />
                        </div>
                    </div>

                    {/* Right Section - Text Content */}
                    <div className="col-span-7 flex flex-col justify-center space-y-6 pl-4">
                        <div className="inline-block px-3 py-1 rounded-full text-[10px] font-extrabold uppercase tracking-[0.2em] bg-white/5 text-purple-300 self-start border border-white/10">
                            Key Details
                        </div>
                        
                        {/* Title */}
                        <h1 
                            ref={titleRef}
                            className="text-4xl lg:text-5xl font-extrabold tracking-tighter leading-[1.1] text-transparent bg-clip-text bg-gradient-to-r from-white via-white/90 to-white/70"
                            style={{ fontFamily: 'Outfit' }}
                        >
                            {slideData?.title || 'Product Overview'}
                        </h1>

                        {/* Neon accent bar */}
                        <div className="accent-bar w-0 h-1.5 bg-gradient-to-r from-[#FF5E97] to-[#DF66FF] rounded-full" />

                        {/* Description */}
                        <p 
                            ref={descriptionRef}
                            className="text-base lg:text-lg text-white/60 leading-relaxed font-medium max-w-xl"
                        >
                            {slideData?.description || 'Our product offers customizable dashboards for real-time reporting and data-driven decisions.'}
                        </p>
                    </div>

                </div>

                {/* Footer decoration */}
                <div className="relative z-10 flex justify-between items-center mt-6 text-white/30 text-[10px] uppercase tracking-[0.3em] font-bold">
                    <span>COSMO Artist Premium Deck</span>
                    <span>Confidential</span>
                </div>

            </div>
        </>
    )
}

export default BasicInfoSlideLayout
 
