import React, { useRef, useEffect } from 'react'
import * as z from "zod";
import gsap from 'gsap';

export const layoutId = 'metrics-slide'
export const layoutName = 'Metrics'
export const layoutDescription = 'A premium slide layout for showcasing key business metrics with large numbers and descriptive text boxes.'

const metricsSlideSchema = z.object({
    title: z.string().min(2).max(100).default('Key Performance Indicators').meta({
        description: "Main title of the slide",
    }),
    metrics: z.array(z.object({
        label: z.string().min(2).max(50).meta({
            description: "Metric label/title"
        }),
        value: z.string().min(1).max(10).meta({
            description: "Metric value (e.g., 150+, 95%, $2M). No long values. Keep simple number."
        }),
        description: z.string().min(10).max(150).meta({
            description: "Detailed description of the metric. Explanation of the metric."
        }),
    })).min(1).max(4).default([
        {
            value: '150+',
            label: 'Global Clients',
            description: 'A diverse network of industry leaders trusting our ecosystem for mission-critical operations.'
        },
        {
            value: '99.9%',
            label: 'System Uptime',
            description: 'Unmatched reliability powered by our decentralized architecture and predictive maintenance.'
        },
        {
            value: '2.4s',
            label: 'Avg. Latency',
            description: 'Industry-leading performance speeds that redefine the boundaries of real-time interaction.'
        }
    ]).meta({
        description: "List of key business metrics to display",
    })
})

export const Schema = metricsSlideSchema

export type MetricsSlideData = z.infer<typeof metricsSlideSchema>

interface MetricsSlideLayoutProps {
    data?: Partial<MetricsSlideData>
}

const MetricsSlideLayout: React.FC<MetricsSlideLayoutProps> = ({ data: slideData }) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const titleRef = useRef<HTMLHeadingElement>(null);
    const metrics = slideData?.metrics || []

    useEffect(() => {
        if (!containerRef.current) return;

        const ctx = gsap.context(() => {
            // Initial states
            gsap.set(titleRef.current, { y: 50, opacity: 0 });
            gsap.set('.metric-card', { y: 60, opacity: 0 });
            gsap.set('.bg-accent-blob', { scale: 0, opacity: 0 });

            // Animation Timeline
            const tl = gsap.timeline({ defaults: { ease: 'power4.out', duration: 1.2 } });

            tl.to('.bg-accent-blob', { scale: 1, opacity: 0.25, stagger: 0.2, duration: 2 })
              .to(titleRef.current, { y: 0, opacity: 1 }, '-=1.5')
              .to('.metric-card', { y: 0, opacity: 1, stagger: 0.15 }, '-=1.0');

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
        <div
            ref={containerRef}
            className="w-full h-full aspect-video bg-[#080615] relative overflow-hidden flex flex-col p-12 text-white border border-white/5"
            style={{
                fontFamily: "'Plus Jakarta Sans', sans-serif",
            }}
        >
            <style dangerouslySetInnerHTML={{ __html: `
                @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@600;800&family=Plus+Jakarta+Sans:wght@300;400;500;700&display=swap');
                
                .glass-card {
                    background: rgba(255, 255, 255, 0.03);
                    backdrop-filter: blur(16px);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    box-shadow: 0 10px 40px -10px rgba(0, 0, 0, 0.5);
                }

                .glow-text {
                    text-shadow: 0 0 30px rgba(223, 102, 255, 0.4);
                }

                .bg-grid {
                    background-image: linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px),
                                    linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
                    background-size: 50px 50px;
                }
            ` }} />

            {/* Grid Background overlay */}
            <div className="absolute inset-0 bg-grid opacity-40 pointer-events-none" />
            
            {/* Background floating accent blobs */}
            <div className="bg-accent-blob bg-accent-blob-1 absolute -top-20 -left-20 w-[450px] h-[450px] rounded-full blur-[110px] pointer-events-none" 
                 style={{ background: 'rgba(139, 92, 246, 0.25)' }}></div>
            <div className="bg-accent-blob bg-accent-blob-2 absolute -bottom-20 -right-20 w-[500px] h-[500px] rounded-full blur-[120px] pointer-events-none" 
                 style={{ background: 'rgba(236, 72, 153, 0.2)' }}></div>

            {/* Header / Logo */}
            <div className="relative z-10 flex justify-between items-center mb-8">
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
                    Metrics Insight
                </div>
            </div>

            {/* Main Content */}
            <div className="relative z-10 flex-1 flex flex-col justify-center max-w-6xl mx-auto w-full">
                <div className="mb-10">
                    <div className="inline-block px-3 py-1 rounded-full text-[10px] font-extrabold uppercase tracking-[0.2em] bg-white/5 text-purple-300 mb-4 border border-white/10">
                        Performance Analytics
                    </div>
                    <h1 
                        ref={titleRef}
                        className="text-5xl lg:text-6xl font-extrabold tracking-tighter leading-[1.1] text-transparent bg-clip-text bg-gradient-to-r from-[#FF5E97] via-[#DF66FF] to-white"
                        style={{ fontFamily: 'Outfit' }}
                    >
                        {slideData?.title}
                    </h1>
                </div>

                <div className={`grid gap-6 ${
                    metrics.length === 1 ? 'grid-cols-1 max-w-2xl mx-auto' :
                    metrics.length === 2 ? 'grid-cols-2 max-w-4xl mx-auto' :
                    metrics.length === 3 ? 'grid-cols-3' :
                    'grid-cols-4'
                } w-full`}>
                    {metrics.map((metric, index) => (
                        <div 
                            key={index} 
                            className="metric-card glass-card rounded-3xl p-8 flex flex-col relative group transition-all duration-300 hover:bg-white/[0.06] hover:border-white/20"
                        >
                            {/* Accent indicator line */}
                            <div className="w-12 h-1 bg-gradient-to-r from-[#FF5E97] to-[#DF66FF] rounded-full mb-6" />
                            
                            <div className="mb-2">
                                <span className="text-xs font-bold uppercase tracking-[0.15em] text-white/50">
                                    {metric.label}
                                </span>
                            </div>

                            <div 
                                className="metric-value text-5xl lg:text-6xl font-extrabold mb-4 tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-[#FF5E97] via-[#DF66FF] to-white glow-text" 
                                style={{ fontFamily: 'Outfit' }}
                            >
                                {metric.value}
                            </div>

                            <p className="text-sm text-white/60 leading-relaxed font-medium mt-auto">
                                {metric.description}
                            </p>
                        </div>
                    ))}
                </div>
            </div>

            {/* Footer decoration */}
            <div className="absolute bottom-12 right-12 flex items-center gap-4 opacity-30">
                <div className="w-12 h-[1px] bg-white/20" />
                <span className="text-[10px] uppercase tracking-[0.4em] font-bold">Confidential</span>
            </div>
        </div>
    )
}

export default MetricsSlideLayout

