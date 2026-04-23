import React, { useRef } from 'react'
import * as z from "zod";
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';
import { ImageSchema } from '../defaultSchemes';

export const layoutId = 'quote-slide'
export const layoutName = 'Quote'
export const layoutDescription = 'A high-impact slide layout for powerful quotes and mission statements.'

const quoteSlideSchema = z.object({
    heading: z.string().min(3).max(60).default('Core Philosophy').meta({
        description: "Main heading of the slide",
    }),
    quote: z.string().min(10).max(200).default('The best way to predict the future is to invent it. Innovation is the only way to stay ahead of the curve.').meta({
        description: "The main quote text content",
    }),
    author: z.string().min(2).max(50).default('Alan Kay').meta({
        description: "Author of the quote",
    }),
    backgroundImage: ImageSchema.default({
        __image_url__: 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=2000&q=80',
        __image_prompt__: 'Deep space nebula or high-tech data background'
    }).meta({
        description: "Background image for the slide",
    })
})

export const Schema = quoteSlideSchema

export type QuoteSlideData = z.infer<typeof quoteSlideSchema>

interface QuoteSlideLayoutProps {
    data?: Partial<QuoteSlideData>
}

const QuoteSlideLayout: React.FC<QuoteSlideLayoutProps> = ({ data: slideData }) => {
    const containerRef = useRef<HTMLDivElement>(null);

    useGSAP(() => {
        const tl = gsap.timeline();
        
        tl.from('.bg-image', {
            scale: 1.1,
            opacity: 0,
            duration: 2,
            ease: 'power2.out'
        });

        tl.from('.quote-content', {
            y: 40,
            opacity: 0,
            duration: 1.2,
            ease: 'power4.out'
        }, "-=1.5");

        tl.from('.quote-author', {
            x: -20,
            opacity: 0,
            duration: 1,
            ease: 'power3.out'
        }, "-=0.5");
    }, { scope: containerRef });

    return (
        <div
            ref={containerRef}
            className="w-full h-full aspect-video bg-black relative overflow-hidden flex flex-col items-center justify-center text-white"
            style={{
                fontFamily: "'Plus Jakarta Sans', sans-serif",
            }}
        >
            <style dangerouslySetInnerHTML={{ __html: `
                @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@600;800&family=Plus+Jakarta+Sans:wght@300;400;500;700&display=swap');
                
                .vignette {
                    background: radial-gradient(circle, transparent 20%, rgba(0,0,0,0.8) 100%);
                }

                .quote-mark {
                    font-family: 'Outfit';
                    line-height: 1;
                }
            ` }} />

            {/* Background Image with Overlay */}
            <div 
                className="bg-image absolute inset-0 w-full h-full bg-cover bg-center grayscale opacity-40"
                style={{ backgroundImage: `url('${slideData?.backgroundImage?.__image_url__}')` }}
            />
            <div className="absolute inset-0 vignette z-10" />
            <div className="absolute inset-0 bg-purple-900/10 z-0" />

            {/* Header / Logo */}
            <div className="absolute top-12 left-12 z-20 flex items-center gap-4">
                {(slideData as any)?._logo_url__ && (
                    <img src={(slideData as any)?._logo_url__} alt="logo" className="w-8 h-8 object-contain" />
                )}
                <div className="w-[1px] h-4 bg-white/20" />
                <span className="text-[10px] font-black uppercase tracking-[0.6em] text-white/40">
                    Proprietary
                </span>
            </div>

            {/* Main Content */}
            <div className="quote-content relative z-20 max-w-5xl px-16 text-center">
                <div className="quote-mark text-9xl text-purple-500/30 absolute -top-12 -left-8 select-none">
                    “
                </div>
                
                <h2 className="text-sm font-black uppercase tracking-[0.4em] text-purple-400 mb-12 opacity-80">
                    {slideData?.heading}
                </h2>

                <blockquote className="text-4xl lg:text-6xl font-extrabold leading-[1.1] mb-12 tracking-tight" style={{ fontFamily: 'Outfit' }}>
                    {slideData?.quote}
                </blockquote>

                <div className="quote-author flex items-center justify-center gap-6">
                    <div className="w-12 h-[1px] bg-white/30" />
                    <cite className="text-xl font-bold tracking-tight not-italic text-white/70">
                        {slideData?.author}
                    </cite>
                    <div className="w-12 h-[1px] bg-white/30" />
                </div>
            </div>

            {/* Footer decoration */}
            <div className="absolute bottom-12 left-0 right-0 z-20 flex justify-center">
                <div className="flex gap-2">
                    <div className="w-1 h-1 bg-white/20 rounded-full" />
                    <div className="w-1 h-1 bg-white/60 rounded-full" />
                    <div className="w-1 h-1 bg-white/20 rounded-full" />
                </div>
            </div>
        </div>
    )
}

export default QuoteSlideLayout