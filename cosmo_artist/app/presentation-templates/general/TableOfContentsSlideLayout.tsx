import React, { useRef } from 'react'
import * as z from "zod";
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';

export const layoutId = 'table-of-contents-slide'
export const layoutName = 'Table of Contents'
export const layoutDescription = 'A premium table of contents layout with a high-end architectural aesthetic and smooth animations.'

const tableOfContentsSlideSchema = z.object({
    sections: z.array(z.object({
        number: z.number().min(1).meta({
            description: "Section number"
        }),
        title: z.string().min(1).max(80).meta({
            description: "Section title"
        }),
        pageNumber: z.string().min(1).max(10).meta({
            description: "Page number for this section"
        })
    })).default([
        { number: 1, title: "Executive Summary", pageNumber: "03" },
        { number: 2, title: "Market Analysis", pageNumber: "05" },
        { number: 3, title: "The Solution", pageNumber: "08" },
        { number: 4, title: "Technical Roadmap", pageNumber: "12" },
        { number: 5, title: "Business Model", pageNumber: "15" },
        { number: 6, title: "The Team", pageNumber: "18" }
    ]).meta({
        description: "List of table of contents sections",
    })
})

export const Schema = tableOfContentsSlideSchema

export type TableOfContentsSlideData = z.infer<typeof tableOfContentsSlideSchema>

interface TableOfContentsSlideLayoutProps {
    data?: Partial<TableOfContentsSlideData>
}

const TableOfContentsSlideLayout: React.FC<TableOfContentsSlideLayoutProps> = ({ data: slideData }) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const sections = slideData?.sections || []
    
    useGSAP(() => {
        const tl = gsap.timeline();
        
        tl.from('.toc-title', {
            x: -50,
            opacity: 0,
            duration: 1,
            ease: 'power4.out'
        });

        tl.from('.toc-item', {
            x: 30,
            opacity: 0,
            duration: 0.6,
            stagger: 0.1,
            ease: 'power3.out'
        }, "-=0.6");

        tl.from('.toc-line', {
            height: 0,
            opacity: 0,
            duration: 1.2,
            ease: 'power2.inOut'
        }, "-=1");
    }, { scope: containerRef });

    return (
        <div
            ref={containerRef}
            className="w-full h-full aspect-video bg-[#fafafa] relative overflow-hidden flex flex-col p-16 text-[#0a0a0a]"
            style={{
                fontFamily: "'Plus Jakarta Sans', sans-serif",
            }}
        >
            <style dangerouslySetInnerHTML={{ __html: `
                @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@600;800&family=Plus+Jakarta+Sans:wght@300;400;500;700&display=swap');
                
                .glass-number {
                    background: rgba(0, 0, 0, 0.03);
                    border: 1px solid rgba(0, 0, 0, 0.08);
                }

                .architectural-grid {
                    background-image: radial-gradient(#000000 0.5px, transparent 0.5px);
                    background-size: 30px 30px;
                    opacity: 0.05;
                }
            ` }} />

            {/* Background elements */}
            <div className="absolute inset-0 architectural-grid" />
            
            <div className="absolute top-0 right-0 w-1/3 h-full bg-[#f0f0f0] z-0" />
            <div className="toc-line absolute left-[4.5rem] top-32 bottom-32 w-[1px] bg-black/10 z-0" />

            {/* Header */}
            <div className="relative z-10 flex justify-between items-center mb-20">
                <div className="flex items-center gap-3">
                    {(slideData as any)?._logo_url__ && (
                        <img src={(slideData as any)?._logo_url__} alt="logo" className="w-8 h-8 object-contain filter grayscale" />
                    )}
                    {(slideData as any)?.__companyName__ && (
                        <span className="text-sm font-bold tracking-[0.3em] uppercase opacity-40">
                            {(slideData as any)?.__companyName__}
                        </span>
                    )}
                </div>
            </div>

            {/* Main Content */}
            <div className="relative z-10 flex-1 flex flex-col justify-start">
                <div className="flex gap-24">
                    {/* Left: Title */}
                    <div className="w-1/3">
                        <h1 className="toc-title text-6xl lg:text-7xl font-extrabold tracking-tighter leading-[0.9]" style={{ fontFamily: 'Outfit' }}>
                            TABLE OF<br/>CONTENTS
                        </h1>
                        <div className="mt-12 h-1 w-20 bg-black" />
                    </div>

                    {/* Right: List */}
                    <div className="flex-1 space-y-4">
                        {sections.map((section, index) => (
                            <div key={index} className="toc-item group flex items-center gap-12 py-4 border-b border-black/5 hover:border-black/20 transition-all cursor-default">
                                <div className="glass-number w-14 h-14 flex items-center justify-center rounded-lg text-sm font-bold opacity-30 group-hover:opacity-100 group-hover:bg-black group-hover:text-white transition-all">
                                    {section.number.toString().padStart(2, '0')}
                                </div>
                                
                                <div className="flex-1">
                                    <h3 className="text-2xl font-bold tracking-tight group-hover:translate-x-2 transition-transform duration-300" style={{ fontFamily: 'Outfit' }}>
                                        {section.title}
                                    </h3>
                                </div>

                                <div className="text-xl font-medium opacity-20 group-hover:opacity-100">
                                    {section.pageNumber}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Pagination / Footer */}
            <div className="absolute bottom-16 left-16 flex items-center gap-6 opacity-30">
                <span className="text-xs font-bold tracking-widest uppercase">Agenda</span>
                <div className="w-8 h-[1px] bg-black" />
            </div>
        </div>
    )
}

export default TableOfContentsSlideLayout