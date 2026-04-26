import React, { useRef } from 'react'
import * as z from "zod";
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';

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
    const metrics = slideData?.metrics || []

    useGSAP(() => {
        const tl = gsap.timeline();
        
        tl.from('.slide-bg-element', {
            opacity: 0,
            scale: 0.8,
            duration: 1.5,
            ease: 'power3.out'
        });

        tl.from('.slide-title', {
            y: 30,
            opacity: 0,
            duration: 1,
            ease: 'power4.out'
        }, "-=1");

        tl.from('.metric-card', {
            y: 50,
            opacity: 0,
            duration: 0.8,
            stagger: 0.2,
            ease: 'back.out(1.4)'
        }, "-=0.5");

        tl.from('.metric-value', {
            scale: 0.5,
            opacity: 0,
            duration: 1,
            stagger: 0.2,
            ease: 'elastic.out(1, 0.5)'
        }, "-=0.8");
    }, { scope: containerRef });

    return (
        <div
            ref={containerRef}
            className="w-full h-full aspect-video bg-[#050505] relative overflow-hidden flex flex-col p-12 text-white"
            style={{
                fontFamily: "'Plus Jakarta Sans', sans-serif",
            }}
        >
            {/* Base styles for premium fonts */}
            <style dangerouslySetInnerHTML={{ __html: `
                @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@600;800&family=Plus+Jakarta+Sans:wght@300;400;500;700&display=swap');
                
                .glass-card {
                    background: rgba(255, 255, 255, 0.03);
                    backdrop-filter: blur(12px);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
                }

                .glow-text {
                    text-shadow: 0 0 20px rgba(147, 51, 234, 0.5);
                }

                .bg-grid {
                    background-image: linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
                                    linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
                    background-size: 40px 40px;
                }
            ` }} />

            {/* Background elements */}
            <div className="absolute inset-0 bg-grid opacity-30" />
            
            <div className="slide-bg-element absolute -top-20 -right-20 w-96 h-96 bg-purple-600/20 rounded-full blur-[100px]" />
            <div className="slide-bg-element absolute -bottom-20 -left-20 w-96 h-96 bg-blue-600/20 rounded-full blur-[100px]" />

            {/* Header / Logo */}
            <div className="relative z-10 flex justify-between items-center mb-8">
                <div className="flex items-center gap-3">
                    {(slideData as any)?._logo_url__ && (
                        <img src={(slideData as any)?._logo_url__} alt="logo" className="w-10 h-10 object-contain" />
                    )}
                    {(slideData as any)?.__companyName__ && (
                        <span className="text-xl font-bold tracking-tight text-white/90 uppercase">
                            {(slideData as any)?.__companyName__}
                        </span>
                    )}
                </div>
                <div className="h-[2px] flex-1 mx-8 bg-gradient-to-r from-purple-500/50 to-transparent opacity-30" />
            </div>

            {/* Main Content */}
            <div className="relative z-10 flex-1 flex flex-col justify-center max-w-6xl mx-auto w-full">
                <h1 className="slide-title text-5xl lg:text-7xl font-extrabold mb-16 tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-white to-white/60" style={{ fontFamily: 'Outfit' }}>
                    {slideData?.title}
                </h1>

                <div className={`grid gap-8 ${
                    metrics.length === 1 ? 'grid-cols-1' :
                    metrics.length === 2 ? 'grid-cols-2' :
                    'grid-cols-3'
                }`}>
                    {metrics.map((metric, index) => (
                        <div key={index} className="metric-card glass-card rounded-2xl p-8 flex flex-col relative group transition-all hover:bg-white/[0.05]">
                            {/* Decorative Corner */}
                            <div className="absolute top-0 left-0 w-8 h-8 border-t-2 border-l-2 border-purple-500/30 rounded-tl-2xl" />
                            
                            <div className="mb-6">
                                <span className="text-sm font-semibold uppercase tracking-[0.2em] text-purple-400 opacity-80">
                                    {metric.label}
                                </span>
                            </div>

                            <div className="metric-value text-6xl lg:text-7xl font-extrabold mb-6 glow-text tracking-tighter" style={{ fontFamily: 'Outfit' }}>
                                {metric.value}
                            </div>

                            <p className="text-lg text-white/60 leading-relaxed font-medium">
                                {metric.description}
                            </p>
                        </div>
                    ))}
                </div>
            </div>

            {/* Footer decoration */}
            <div className="absolute bottom-12 right-12 flex items-center gap-4 opacity-40">
                <div className="w-12 h-[1px] bg-white/30" />
                <span className="text-[10px] uppercase tracking-[0.4em] font-bold">Confidential</span>
            </div>
        </div>
    )
}

export default MetricsSlideLayout
