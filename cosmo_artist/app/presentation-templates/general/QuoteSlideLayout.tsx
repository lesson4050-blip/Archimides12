import React, { useEffect, useRef } from 'react'
import * as z from "zod";
import gsap from 'gsap';
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
    const cardRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!containerRef.current) return;

        const ctx = gsap.context(() => {
            // Initial states
            gsap.set(cardRef.current, { scale: 0.9, y: 40, opacity: 0 });
            gsap.set('.bg-image', { scale: 1.15, opacity: 0 });
            gsap.set('.bg-accent-blob', { scale: 0, opacity: 0 });
            gsap.set('.quote-mark', { scale: 0, opacity: 0 });

            // Animation Timeline
            const tl = gsap.timeline({ defaults: { ease: 'power4.out', duration: 1.2 } });

            tl.to('.bg-image', { scale: 1, opacity: 0.25, duration: 2.5 })
              .to('.bg-accent-blob', { scale: 1, opacity: 0.2, stagger: 0.2, duration: 2 }, '-=2')
              .to(cardRef.current, { scale: 1, y: 0, opacity: 1, duration: 1.5 }, '-=1.2')
              .to('.quote-mark', { scale: 1, opacity: 0.3, stagger: 0.3, ease: 'back.out(1.5)', duration: 1 }, '-=0.8');

            // Floating animation for blobs
            gsap.to('.bg-accent-blob-1', {
                x: '+=30',
                y: '+=25',
                duration: 7,
                repeat: -1,
                yoyo: true,
                ease: 'sine.inOut'
            });
            gsap.to('.bg-accent-blob-2', {
                x: '-=40',
                y: '-=30',
                duration: 9,
                repeat: -1,
                yoyo: true,
                ease: 'sine.inOut'
            });
        }, containerRef);

        return () => ctx.revert();
    }, []);

    return (
        <div
            ref={containerRef}
            className="w-full h-full aspect-video bg-[#080615] relative overflow-hidden flex flex-col items-center justify-center text-white border border-white/5"
            style={{
                fontFamily: "'Plus Jakarta Sans', sans-serif",
            }}
        >
            <style dangerouslySetInnerHTML={{ __html: `
                @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@600;800&family=Plus+Jakarta+Sans:wght@300;400;500;700&display=swap');
                
                .vignette {
                    background: radial-gradient(circle, transparent 30%, rgba(8, 6, 21, 0.9) 100%);
                }

                .glass-quote-card {
                    background: rgba(255, 255, 255, 0.02);
                    backdrop-filter: blur(20px);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    box-shadow: 0 20px 50px -10px rgba(0, 0, 0, 0.6);
                }

                .glow-text {
                    text-shadow: 0 0 40px rgba(223, 102, 255, 0.3);
                }

                .bg-grid {
                    background-image: linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px),
                                    linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
                    background-size: 50px 50px;
                }
            ` }} />

            {/* Grid overlay */}
            <div className="absolute inset-0 bg-grid opacity-30 pointer-events-none" />

            {/* Background Image with Overlay */}
            <div 
                className="bg-image absolute inset-0 w-full h-full bg-cover bg-center grayscale pointer-events-none"
                style={{ backgroundImage: `url('${slideData?.backgroundImage?.__image_url__}')` }}
            />
            <div className="absolute inset-0 vignette z-10 pointer-events-none" />

            {/* Background floating accent blobs */}
            <div className="bg-accent-blob bg-accent-blob-1 absolute -top-20 -left-20 w-[450px] h-[450px] rounded-full blur-[110px] pointer-events-none" 
                 style={{ background: 'rgba(139, 92, 246, 0.2)' }}></div>
            <div className="bg-accent-blob bg-accent-blob-2 absolute -bottom-25 -right-20 w-[550px] h-[550px] rounded-full blur-[130px] pointer-events-none" 
                 style={{ background: 'rgba(236, 72, 153, 0.15)' }}></div>

            {/* Header / Logo */}
            <div className="absolute top-12 left-12 z-20 flex items-center gap-4">
                {(slideData as any)?._logo_url__ && (
                    <img src={(slideData as any)?._logo_url__} alt="logo" className="w-8 h-8 object-contain" />
                )}
                <div className="w-[1px] h-4 bg-white/20" />
                <span className="text-[10px] font-black uppercase tracking-[0.6em] text-white/40">
                    {(slideData as any)?.__companyName__ || 'COSMO'}
                </span>
            </div>

            {/* Main Content Quote Card */}
            <div 
                ref={cardRef}
                className="glass-quote-card relative z-20 max-w-4xl w-full mx-6 p-12 lg:p-16 rounded-[2.5rem] text-center overflow-hidden"
            >
                {/* Neon glow dots inside card */}
                <div className="absolute -top-12 -left-12 w-24 h-24 bg-[#FF5E97]/10 rounded-full blur-xl pointer-events-none" />
                <div className="absolute -bottom-12 -right-12 w-24 h-24 bg-[#DF66FF]/10 rounded-full blur-xl pointer-events-none" />

                {/* Decorative Quotation Marks */}
                <div className="quote-mark text-8xl lg:text-9xl absolute top-4 left-6 select-none text-transparent bg-clip-text bg-gradient-to-r from-[#FF5E97] to-[#DF66FF] font-serif leading-none" style={{ fontFamily: 'Outfit' }}>
                    “
                </div>
                <div className="quote-mark text-8xl lg:text-9xl absolute bottom-0 right-6 select-none text-transparent bg-clip-text bg-gradient-to-r from-[#DF66FF] to-white font-serif leading-none" style={{ fontFamily: 'Outfit' }}>
                    ”
                </div>
                
                {/* Heading Category */}
                <h2 className="text-xs font-extrabold uppercase tracking-[0.35em] text-[#FF5E97] mb-8">
                    {slideData?.heading}
                </h2>

                {/* The Quote Block */}
                <blockquote 
                    className="text-2xl lg:text-4xl font-extrabold leading-[1.3] mb-8 tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-white via-white/90 to-white/70 glow-text" 
                    style={{ fontFamily: 'Outfit' }}
                >
                    "{slideData?.quote}"
                </blockquote>

                {/* Author Info */}
                <div className="quote-author flex items-center justify-center gap-6 mt-10">
                    <div className="w-8 h-[1px] bg-gradient-to-r from-transparent to-white/30" />
                    <cite className="text-base lg:text-lg font-bold tracking-wider not-italic text-transparent bg-clip-text bg-gradient-to-r from-[#FF5E97] via-[#DF66FF] to-white">
                        {slideData?.author}
                    </cite>
                    <div className="w-8 h-[1px] bg-gradient-to-l from-transparent to-white/30" />
                </div>
            </div>

            {/* Footer decoration */}
            <div className="absolute bottom-12 left-0 right-0 z-20 flex justify-center opacity-30">
                <div className="flex gap-2">
                    <div className="w-1.5 h-1.5 bg-white/20 rounded-full" />
                    <div className="w-4 h-1.5 bg-gradient-to-r from-[#FF5E97] to-[#DF66FF] rounded-full" />
                    <div className="w-1.5 h-1.5 bg-white/20 rounded-full" />
                </div>
            </div>
        </div>
    )
}

export default QuoteSlideLayout

