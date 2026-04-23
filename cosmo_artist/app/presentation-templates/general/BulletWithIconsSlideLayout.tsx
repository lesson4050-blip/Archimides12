import React, { useEffect, useRef } from 'react'
import * as z from "zod";
import { ImageSchema, IconSchema } from '../defaultSchemes';
import { RemoteSvgIcon } from '@/app/hooks/useRemoteSvgIcon';
import gsap from 'gsap';

export const layoutId = 'bullet-with-icons-slide'
export const layoutName = 'Bullet with Icons'
export const layoutDescription = 'A premium bullets style slide with staggered animations, glassmorphic cards, and a high-end visual style.'

const bulletWithIconsSlideSchema = z.object({
    title: z.string().min(3).max(60).default('Strategic Challenges').meta({
        description: "Main title of the slide",
    }),
    description: z.string().max(250).default('Navigating complex market dynamics requires precision and advanced operational agility.').meta({
        description: "Main description text content",
    }),
    image: ImageSchema.default({
        __image_url__: 'https://images.unsplash.com/photo-1552664730-d307ca884978?auto=format&fit=crop&w=1000&q=80',
        __image_prompt__: 'Business people analyzing documents and charts in office'
    }).meta({
        description: "Supporting image for the slide",
    }),
    bulletPoints: z.array(z.object({
        title: z.string().min(2).max(60).meta({
            description: "Bullet point title",
        }),
        description: z.string().min(10).max(150).meta({
            description: "Bullet point description",
        }),
        icon: IconSchema,
    })).min(1).max(3).default([
        {
            title: 'Operational Inefficiency',
            description: 'Manual processes and fragmented workflows hinder rapid decision-making and productivity.',
            icon: {
                __icon_url__: 'https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/checks-bold.svg',
                __icon_query__: 'warning alert inefficiency'
            }
        },
        {
            title: 'Scalability Constraints',
            description: 'Legacy infrastructure prevents seamless expansion into emerging global markets.',
            icon: {
                __icon_url__: 'https://presenton-public.s3.ap-southeast-1.amazonaws.com/static/icons/bold/fediverse-logo-bold.svg',
                __icon_query__: 'trending up costs chart'
            }
        }
    ]).meta({
        description: "List of bullet points with icons and descriptions",
    })
})

export const Schema = bulletWithIconsSlideSchema

export type BulletWithIconsSlideData = z.infer<typeof bulletWithIconsSlideSchema>

interface BulletWithIconsSlideLayoutProps {
    data?: Partial<BulletWithIconsSlideData>
}

const BulletWithIconsSlideLayout: React.FC<BulletWithIconsSlideLayoutProps> = ({ data: slideData }) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const titleRef = useRef<HTMLHeadingElement>(null);
    const contentRef = useRef<HTMLDivElement>(null);
    const bulletRef = useRef<HTMLDivElement>(null);
    const bulletPoints = slideData?.bulletPoints || []

    useEffect(() => {
        if (!containerRef.current) return;

        const ctx = gsap.context(() => {
            gsap.set('.bullet-card', { x: 50, opacity: 0 });
            gsap.set(titleRef.current, { y: -50, opacity: 0 });
            gsap.set('.image-container', { scale: 0.9, opacity: 0 });

            const tl = gsap.timeline({ defaults: { ease: 'power3.out', duration: 1 } });

            tl.to(titleRef.current, { y: 0, opacity: 1 })
              .to('.image-container', { scale: 1, opacity: 1 }, '-=0.5')
              .to('.bullet-card', { 
                  x: 0, 
                  opacity: 1, 
                  stagger: 0.2,
                  duration: 0.8,
                  ease: 'back.out(1.7)'
              }, '-=0.3');
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
                className="w-full rounded-sm max-w-[1280px] shadow-2xl max-h-[720px] aspect-video relative z-20 mx-auto overflow-hidden border border-gray-100"
                style={{
                    fontFamily: "'Plus Jakarta Sans', sans-serif",
                    background: "var(--background-color, #FAFAFA)"
                }}
            >
                {/* Subtle Grid Background */}
                <div className="absolute inset-0 opacity-[0.03] pointer-events-none">
                    <svg width="100%" height="100%">
                        <pattern id="grid-pattern" width="40" height="40" patternUnits="userSpaceOnUse">
                            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" strokeWidth="1" />
                        </pattern>
                        <rect width="100%" height="100%" fill="url(#grid-pattern)" />
                    </svg>
                </div>

                {/* Company Logo / Header */}
                <div className="absolute top-0 left-0 right-0 px-12 pt-8 z-30">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            {(slideData as any)?._logo_url__ && (
                                <img src={(slideData as any)?._logo_url__} alt="logo" className="w-8 h-8 object-contain" />
                            )}
                            {(slideData as any)?.__companyName__ && (
                                <span className="text-lg font-bold tracking-tight text-gray-800">
                                    {(slideData as any)?.__companyName__}
                                </span>
                            )}
                        </div>
                        <div className="text-[10px] font-bold uppercase tracking-widest text-gray-400 border-l border-gray-300 pl-4">
                            Strategic Brief / Page 04
                        </div>
                    </div>
                </div>

                {/* Main Content */}
                <div className="flex flex-col h-full px-12 pt-28 pb-12">
                    {/* Title Section */}
                    <div className="mb-12 relative">
                        <div className="absolute -left-4 top-0 w-1 h-full rounded-full" style={{ background: 'var(--primary-color, #6366f1)' }}></div>
                        <h1 
                            ref={titleRef}
                            className="text-5xl lg:text-6xl font-extrabold tracking-tight text-gray-900"
                            style={{ fontFamily: "'Outfit', sans-serif" }}
                        >
                            {slideData?.title || 'Strategic Challenges'}
                        </h1>
                    </div>

                    {/* Content Grid */}
                    <div className="grid grid-cols-12 gap-12 flex-1 items-center">
                        
                        {/* Left: Image */}
                        <div className="col-span-5 image-container relative h-full">
                            <div className="w-full h-full rounded-[2.5rem] overflow-hidden shadow-2xl border-8 border-white">
                                <img
                                    src={slideData?.image?.__image_url__ || ''}
                                    alt={slideData?.image?.__image_prompt__ || ''}
                                    className="w-full h-full object-cover"
                                />
                            </div>
                            {/* Decorative element */}
                            <div className="absolute -bottom-6 -right-6 w-32 h-32 rounded-full blur-3xl opacity-20 -z-10"
                                 style={{ background: 'var(--primary-color, #6366f1)' }}></div>
                        </div>

                        {/* Right: Bullet Points */}
                        <div className="col-span-7 flex flex-col justify-center space-y-6">
                            <p className="text-xl text-gray-500 font-medium mb-4 leading-relaxed italic">
                                "{slideData?.description || 'Navigating complex market dynamics requires precision.'}"
                            </p>

                            <div className="space-y-4">
                                {bulletPoints.map((bullet, index) => (
                                    <div 
                                        key={index} 
                                        className="bullet-card flex items-start gap-5 p-6 rounded-[1.5rem] bg-white border border-gray-100 shadow-sm transition-all hover:shadow-md hover:border-gray-200"
                                    >
                                        {/* Icon Container */}
                                        <div className="flex-shrink-0 w-14 h-14 rounded-2xl flex items-center justify-center shadow-lg"
                                             style={{ 
                                                 background: 'linear-gradient(135deg, var(--primary-color, #6366f1) 0%, var(--secondary-color, #a855f7) 100%)',
                                                 boxShadow: '0 8px 16px -4px rgba(99, 102, 241, 0.3)'
                                             }}>
                                            <RemoteSvgIcon
                                                url={bullet.icon.__icon_url__}
                                                strokeColor={"currentColor"}
                                                className="w-7 h-7"
                                                color="white"
                                                title={bullet.icon.__icon_query__}
                                            />
                                        </div>

                                        {/* Text Content */}
                                        <div className="flex-1">
                                            <h3 className="text-xl font-bold text-gray-900 mb-1 tracking-tight">
                                                {bullet.title}
                                            </h3>
                                            <p className="text-base text-gray-500 leading-snug font-medium">
                                                {bullet.description}
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </>
    )
}

export default BulletWithIconsSlideLayout 