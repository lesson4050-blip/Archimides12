import React, { useEffect, useRef } from 'react'
import * as z from "zod";
import { ImageSchema } from '../defaultSchemes';
import gsap from 'gsap';

export const layoutId = 'general-intro-slide'
export const layoutName = 'Intro Slide'
export const layoutDescription = 'A premium slide layout with animated title, glassmorphic presenter info, and a high-end visual style.'

const introSlideSchema = z.object({
    title: z.string().min(2).max(100).default('Product Overview').meta({
        description: "Main title of the slide",
    }),
    description: z.string().min(10).max(250).default('Our product offers customizable dashboards for real-time reporting and data-driven decisions.').meta({
        description: "Main description text content",
    }),
    presenterName: z.string().min(2).max(50).default('John Doe').meta({
        description: "Name of the presenter",
    }),
    presentationDate: z.string().min(2).max(50).default('December 2025').meta({
        description: "Date of the presentation",
    }),
    image: ImageSchema.default({
        __image_url__: 'https://images.unsplash.com/photo-1552664730-d307ca884978?auto=format&fit=crop&w=1000&q=80',
        __image_prompt__: 'Business team in meeting room discussing product features and solutions'
    }).meta({
        description: "Supporting image for the slide",
    })
})

export const Schema = introSlideSchema

export type IntroSlideData = z.infer<typeof introSlideSchema>

interface IntroSlideLayoutProps {
    data?: Partial<IntroSlideData>
}

const IntroSlideLayout: React.FC<IntroSlideLayoutProps> = ({ data: slideData }) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const titleRef = useRef<HTMLHeadingElement>(null);
    const imageRef = useRef<HTMLDivElement>(null);
    const cardRef = useRef<HTMLDivElement>(null);
    const bgElementRef = useRef<HTMLDivElement>(null);

    const getInitials = (name: string) => {
        return name.split(' ').map(word => word.charAt(0).toUpperCase()).join('');
    };

    const presenterInitials = getInitials(slideData?.presenterName || 'John Doe');

    useEffect(() => {
        if (!containerRef.current) return;

        const ctx = gsap.context(() => {
            // Initial states
            gsap.set(titleRef.current, { y: 100, opacity: 0 });
            gsap.set(imageRef.current, { scale: 0.8, opacity: 0, rotate: -5 });
            gsap.set(cardRef.current, { y: 50, opacity: 0 });
            gsap.set('.bg-accent-blob', { scale: 0, opacity: 0 });

            // Animation Timeline
            const tl = gsap.timeline({ defaults: { ease: 'power4.out', duration: 1.2 } });

            tl.to('.bg-accent-blob', { scale: 1, opacity: 0.15, stagger: 0.2, duration: 2 })
              .to(titleRef.current, { y: 0, opacity: 1 }, '-=1.5')
              .to(imageRef.current, { scale: 1, opacity: 1, rotate: 0 }, '-=1')
              .to(cardRef.current, { y: 0, opacity: 1 }, '-=0.8');

            // Floating animation for blobs
            gsap.to('.bg-accent-blob-1', {
                x: '+=30',
                y: '+=20',
                duration: 5,
                repeat: -1,
                yoyo: true,
                ease: 'sine.inOut'
            });
            gsap.to('.bg-accent-blob-2', {
                x: '-=40',
                y: '-=30',
                duration: 7,
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
                href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap"
                rel="stylesheet"
            />
            <div
                ref={containerRef}
                className="w-full rounded-sm max-w-[1280px] shadow-2xl max-h-[720px] aspect-video bg-white relative z-20 mx-auto overflow-hidden border border-gray-100"
                style={{
                    background: "var(--background-color, #FAFAFA)",
                    fontFamily: "'Plus Jakarta Sans', sans-serif"
                }}
            >
                {/* Decorative Background Elements */}
                <div className="absolute inset-0 overflow-hidden pointer-events-none">
                    <div className="bg-accent-blob bg-accent-blob-1 absolute -top-20 -left-20 w-96 h-96 rounded-full blur-[100px]" 
                         style={{ background: 'var(--primary-color, #6366f1)' }}></div>
                    <div className="bg-accent-blob bg-accent-blob-2 absolute -bottom-20 -right-20 w-[500px] h-[500px] rounded-full blur-[120px]" 
                         style={{ background: 'var(--secondary-color, #a855f7)' }}></div>
                </div>

                {/* Header / Logo */}
                <div className="absolute top-0 left-0 right-0 px-12 pt-8 z-30">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            {(slideData as any)?._logo_url__ && (
                                <img src={(slideData as any)?._logo_url__} alt="logo" className="w-10 h-10 object-contain" />
                            )}
                            {(slideData as any)?.__companyName__ && (
                                <span className="text-xl font-bold tracking-tight" style={{ color: 'var(--background-text, #0f172a)' }}>
                                    {(slideData as any)?.__companyName__}
                                </span>
                            )}
                        </div>
                        <div className="h-px flex-1 mx-8 bg-gray-200/50"></div>
                        <div className="text-xs font-bold uppercase tracking-widest text-gray-400">
                            Confidential / {slideData?.presentationDate || '2025'}
                        </div>
                    </div>
                </div>

                {/* Main Content Grid */}
                <div className="relative z-10 grid grid-cols-12 h-full px-12 pt-24 pb-12 items-center gap-8">
                    
                    {/* Left Content */}
                    <div className="col-span-7 flex flex-col justify-center space-y-8">
                        <div className="space-y-4">
                            <div className="inline-block px-3 py-1 rounded-full text-[10px] font-extrabold uppercase tracking-[0.2em] bg-gray-100 text-gray-500 mb-2 border border-gray-200">
                                Presentation Insight
                            </div>
                            <h1 
                                ref={titleRef}
                                className="text-6xl lg:text-7xl font-extrabold tracking-tighter leading-[0.95]"
                                style={{ 
                                    color: "var(--background-text, #0f172a)",
                                    fontFamily: "'Outfit', sans-serif"
                                }}
                            >
                                {slideData?.title || 'Product Overview'}
                            </h1>
                        </div>

                        <div className="w-24 h-1.5 rounded-full" style={{ background: 'linear-gradient(90deg, var(--primary-color, #6366f1), var(--secondary-color, #a855f7))' }}></div>

                        <p className="text-xl text-gray-500 max-w-xl leading-relaxed font-medium">
                            {slideData?.description || 'Strategic overview and detailed roadmap for excellence.'}
                        </p>

                        {/* Glassmorphic Presenter Card */}
                        <div 
                            ref={cardRef}
                            className="inline-flex items-center gap-4 p-5 rounded-2xl border border-white/40 shadow-xl backdrop-blur-xl bg-white/60"
                            style={{ maxWidth: 'fit-content' }}
                        >
                            <div className="relative">
                                <div className="w-14 h-14 rounded-xl flex items-center justify-center font-bold text-lg shadow-inner"
                                     style={{ 
                                         background: 'linear-gradient(135deg, var(--primary-color, #6366f1), var(--secondary-color, #a855f7))',
                                         color: 'white'
                                     }}>
                                    {presenterInitials}
                                </div>
                                <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-green-500 border-2 border-white rounded-full"></div>
                            </div>
                            <div className="flex flex-col pr-4">
                                <span className="text-sm font-bold text-gray-400 uppercase tracking-tighter">Presented By</span>
                                <span className="text-xl font-extrabold text-gray-900 tracking-tight">
                                    {slideData?.presenterName || 'John Doe'}
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Right Image Section */}
                    <div className="col-span-5 relative h-full flex items-center justify-center">
                        <div 
                            ref={imageRef}
                            className="relative w-full aspect-[4/5] rounded-[2.5rem] overflow-hidden shadow-2xl group"
                        >
                            <img
                                src={slideData?.image?.__image_url__ || ''}
                                alt={slideData?.image?.__image_prompt__ || ''}
                                className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
                            />
                            <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent"></div>
                            
                            {/* Floating stat inside image */}
                            <div className="absolute bottom-6 left-6 right-6 p-4 rounded-xl bg-white/10 backdrop-blur-md border border-white/20 text-white">
                                <div className="text-[10px] font-bold uppercase tracking-widest opacity-70">Focus Objective</div>
                                <div className="text-sm font-semibold truncate">{slideData?.image?.__image_prompt__?.split(' ').slice(0, 5).join(' ') || 'Innovation'}</div>
                            </div>
                        </div>
                        
                        {/* Decorative ring */}
                        <div className="absolute -top-4 -right-4 w-24 h-24 rounded-full border-4 border-gray-100 opacity-50 -z-10"></div>
                        <div className="absolute -bottom-10 -left-10 w-40 h-40 rounded-full border-[12px] border-gray-50 -z-10"></div>
                    </div>

                </div>
            </div>
        </>
    )
}

export default IntroSlideLayout 
