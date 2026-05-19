import React, { useEffect, useRef } from 'react'
import * as z from "zod";
import gsap from 'gsap';

/**
 * Zod Schema for the slide content.
 */
export const Schema = z.object({
    title: z.string().max(40).describe('The main heading of the slide').default('Timeline'),
    milestones: z.array(z.object({
        year: z.string().max(4).describe('Time period or date label'),
        description: z.string().max(100).describe('Description text for the milestone'),
    })).min(2).max(6).describe('List of milestone items for the timeline').default([
        { year: '2017', description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed facilisis lacinia dictum.' },
        { year: '2018', description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed facilisis lacinia dictum.' },
        { year: '2019', description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed facilisis lacinia dictum.' },
        { year: '2020', description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed facilisis lacinia dictum.' },
        { year: '2021', description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed facilisis lacinia dictum.' },
        { year: '2022', description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed facilisis lacinia dictum.' },
        { year: '2023', description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed facilisis lacinia dictum.' },
        { year: '2024', description: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed facilisis lacinia dictum.' },
    ]),
});

/**
 * Layout metadata.
 */
export const layoutId = 'timeline-alternating-cards-slide';
export const layoutName = 'Horizontal Timeline With Cards';
export const layoutDescription = 'A visual timeline layout featuring centered title, horizontal dashed axis line, and 2-6 milestone cards alternating above and below the axis. Each card shows a date label and description with colored accent dots.';

/**
 * React Component for the slide.
 */
const dynamicSlideLayout: React.FC<{ data: Partial<z.infer<typeof Schema>> }> = ({ data }) => {
    const { title, milestones } = data;
    const containerRef = useRef<HTMLDivElement>(null);
    const titleRef = useRef<HTMLDivElement>(null);

    const accentColors = ['#FF5E97', '#DF66FF', '#38BDF8', '#4ADE80', '#FFBD59', '#F472B6'];

    // Dynamic positioning based on number of items
    const itemCount = milestones?.length || 0;
    const cardWidth = 216;
    const spacing = itemCount <= 3 ? 220 : itemCount <= 4 ? 180 : itemCount <= 5 ? 150 : 130;
    const totalWidth = (itemCount - 1) * spacing + cardWidth;
    const slideWidth = 1280;
    const startX = (slideWidth - totalWidth) / 2;

    // Generate config dynamically
    const config = milestones?.map((_, i) => {
        const isTop = i % 2 === 0;
        const boxX = startX + i * spacing;
        const dotCenterX = boxX + cardWidth / 2;

        return {
            boxX,
            boxY: isTop ? 220 : 452.9,
            yearX: boxX,
            yearY: isTop ? 245 : 478,
            descX: boxX + 15,
            descY: isTop ? 282 : 515,
            dotX: dotCenterX - (isTop ? 23.7 : 10.9),
            dotY: isTop ? 389.4 : 403.1,
            type: isTop ? 'primary' : 'secondary',
            dotColor: accentColors[i % accentColors.length],
        };
    }) || [];

    // Generate white dots between items
    const whiteDots = config.slice(0, -1).map((item, i) => {
        const nextItem = config[i + 1];
        return (item.boxX + cardWidth / 2 + nextItem.boxX + cardWidth / 2) / 2 - 6.65;
    });

    // Calculate timeline line boundaries
    const lineStartX = config.length > 0 ? config[0].boxX + cardWidth / 2 - 50 : 62;
    const lineEndX = config.length > 0 ? config[config.length - 1].boxX + cardWidth / 2 + 50 : 1218;

    useEffect(() => {
        if (!containerRef.current) return;

        const ctx = gsap.context(() => {
            // Initial states
            gsap.set(titleRef.current, { y: 40, opacity: 0 });
            gsap.set('.timeline-axis', { scaleX: 0, transformOrigin: 'left center', opacity: 0 });
            gsap.set('.milestone-node', { scale: 0, opacity: 0 });
            gsap.set('.milestone-card', { y: (i) => (i % 2 === 0 ? -40 : 40), opacity: 0 });
            gsap.set('.bg-accent-blob', { scale: 0, opacity: 0 });

            // Animation Timeline
            const tl = gsap.timeline({ defaults: { ease: 'power4.out', duration: 1.2 } });

            tl.to('.bg-accent-blob', { scale: 1, opacity: 0.25, stagger: 0.2, duration: 2 })
              .to(titleRef.current, { y: 0, opacity: 1 }, '-=1.5')
              .to('.timeline-axis', { scaleX: 1, opacity: 1, duration: 1.5, ease: 'power3.inOut' }, '-=1.2')
              .to('.milestone-node', { scale: 1, opacity: 1, stagger: 0.1, ease: 'back.out(1.8)' }, '-=1')
              .to('.milestone-card', { y: 0, opacity: 1, stagger: 0.15 }, '-=0.8');

            // Floating animation for blobs
            gsap.to('.bg-accent-blob-1', {
                x: '+=25',
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
                className="relative w-full rounded-sm max-w-[1280px] shadow-2xl max-h-[720px] aspect-video bg-[#080615] z-20 mx-auto overflow-hidden border border-white/5 text-white"
                style={{
                    fontFamily: "'Plus Jakarta Sans', sans-serif",
                }}
            >
                <style dangerouslySetInnerHTML={{ __html: `
                    .glass-timeline-card {
                        background: rgba(255, 255, 255, 0.02);
                        backdrop-filter: blur(12px);
                        border: 1px solid rgba(255, 255, 255, 0.08);
                        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
                    }

                    .bg-grid {
                        background-image: linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px),
                                        linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
                        background-size: 50px 50px;
                    }

                    .neon-glow-dot {
                        box-shadow: 0 0 15px currentColor;
                    }
                ` }} />

                {/* Grid & Accent Blobs */}
                <div className="absolute inset-0 bg-grid opacity-30 pointer-events-none" />
                <div className="bg-accent-blob bg-accent-blob-1 absolute -top-20 -left-20 w-[450px] h-[450px] rounded-full blur-[110px] pointer-events-none" 
                     style={{ background: 'rgba(139, 92, 246, 0.2)' }}></div>
                <div className="bg-accent-blob bg-accent-blob-2 absolute -bottom-20 -right-20 w-[500px] h-[500px] rounded-full blur-[120px] pointer-events-none" 
                     style={{ background: 'rgba(236, 72, 153, 0.15)' }}></div>

                {/* Header / Logo */}
                {((data as any)?.__companyName__ || (data as any)?._logo_url__) && (
                    <div className="absolute top-0 left-0 right-0 px-12 pt-8 z-30 flex justify-between items-center">
                        <div className="flex items-center gap-3">
                            {(data as any)?._logo_url__ && <img src={(data as any)?._logo_url__} alt="logo" className="w-8 h-8 object-contain" />}
                            {(data as any)?.__companyName__ && <span className="text-lg font-bold tracking-tight text-white/90 uppercase">
                                {(data as any)?.__companyName__}
                            </span>}
                        </div>
                        <div className="h-[1px] flex-1 mx-8 bg-white/10" />
                        <div className="text-xs font-bold uppercase tracking-widest text-white/40">
                            Roadmap / Milestones
                        </div>
                    </div>
                )}

                {/* Title Section */}
                <div 
                    ref={titleRef}
                    className="absolute left-1/2 -translate-x-1/2 top-[68.6px] w-[540px] text-center z-10"
                >
                    <div className="inline-block px-3 py-1 rounded-full text-[10px] font-extrabold uppercase tracking-[0.2em] bg-white/5 text-purple-300 mb-2 border border-white/10">
                        Strategic Journey
                    </div>
                    <h1 
                        className="text-4xl lg:text-5xl font-extrabold tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-white via-white/90 to-white/70"
                        style={{ fontFamily: 'Outfit' }}
                    >
                        {title}
                    </h1>
                    <div className="w-20 h-1.5 bg-gradient-to-r from-[#FF5E97] to-[#DF66FF] mx-auto rounded-full mt-4" />
                </div>

                {/* Central Axis Line */}
                <div className="timeline-axis absolute top-[413.1px] h-[2px] z-10"
                    style={{ left: `${lineStartX}px`, width: `${lineEndX - lineStartX}px` }}
                >
                    <svg width="100%" height="100%" overflow="visible">
                        <line x1="0%" y1="50%" x2="100%" y2="50%" stroke="rgba(223, 102, 255, 0.4)" strokeWidth="2" strokeDasharray="6,6" />
                    </svg>
                </div>

                {/* Timeline Elements Loop */}
                {milestones && milestones.map((m, i) => {
                    const item = config[i];
                    return (
                        <div key={i} className="z-20">
                            {/* Card Background */}
                            <div
                                className="milestone-card glass-timeline-card absolute rounded-3xl p-5 flex flex-col items-center justify-center text-center transition-all duration-300 hover:bg-white/[0.05] hover:border-white/20"
                                style={{ left: item.boxX, top: item.boxY, width: '216px', height: '139.2px' }}
                            >
                                {/* Accent small indicator */}
                                <div 
                                    className="w-8 h-1 rounded-full mb-3"
                                    style={{ backgroundColor: item.dotColor }}
                                />
                                {/* Year */}
                                <div className="text-xl font-bold tracking-tight text-white mb-2" style={{ fontFamily: 'Outfit' }}>
                                    {m.year}
                                </div>
                                {/* Description */}
                                <p className="text-[11.2px] font-medium leading-[14.8px] text-white/60">
                                    {m.description}
                                </p>
                            </div>

                            {/* Dot/Marker */}
                            {item.type === 'primary' ? (
                                <div
                                    className="milestone-node neon-glow-dot absolute flex items-center justify-center rounded-full bg-[#080615] border-2 transition-all duration-300"
                                    style={{ 
                                        left: item.dotX, 
                                        top: item.dotY, 
                                        width: '47.4px', 
                                        height: '47.4px', 
                                        borderColor: item.dotColor,
                                        color: item.dotColor 
                                    }}
                                >
                                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: 'currentColor' }} />
                                </div>
                            ) : (
                                <div 
                                    className="milestone-node neon-glow-dot absolute rounded-full border border-white/20 transition-all duration-300"
                                    style={{ 
                                        left: item.dotX, 
                                        top: item.dotY, 
                                        width: '21.8px', 
                                        height: '21.8px', 
                                        backgroundColor: item.dotColor,
                                        color: item.dotColor
                                    }}
                                />
                            )}
                        </div>
                    );
                })}

                {/* Decorative White Dots (Now Neon Purple Glowing Nodes) */}
                {whiteDots.map((x, i) => (
                    <div
                        key={`white-dot-${i}`}
                        className="absolute rounded-full border border-purple-500/30 bg-[#DF66FF]/20"
                        style={{ left: x, top: '407.4px', width: '13.3px', height: '13.3px' }}
                    />
                ))}
            </div>
        </>
    );
};

export default dynamicSlideLayout;
