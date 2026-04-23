import React, { useRef } from 'react'
import * as z from "zod";
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';
import { ImageSchema } from '../defaultSchemes';

export const layoutId = 'team-slide'
export const layoutName = 'Team Slide'
export const layoutDescription = 'A premium slide layout showcasing team members with a high-end editorial aesthetic.'

const teamMemberSchema = z.object({
    name: z.string().min(2).max(50).meta({
        description: "Team member's full name"
    }),
    position: z.string().min(2).max(50).meta({
        description: "Job title or position"
    }),
    description: z.string().max(150).meta({
        description: "Brief description of the team member (around 100 characters)"
    }),
    image: ImageSchema
});

const teamSlideSchema = z.object({
    title: z.string().min(3).max(40).default('The Brain Trust').meta({
        description: "Main title of the slide",
    }),
    companyDescription: z.string().min(10).max(150).default('Our team brings together decades of collective experience in engineering, design, and strategic operations to solve the world\'s most complex challenges.').meta({
        description: "Company description or team introduction text",
    }),
    teamMembers: z.array(teamMemberSchema).min(1).max(4).default([
        {
            name: 'Alexander Vance',
            position: 'Chief Architect',
            description: 'Visionary engineer behind our core neural processing engine.',
            image: {
                __image_url__: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=400&q=80',
                __image_prompt__: 'Professional male architect headshot'
            }
        },
        {
            name: 'Elena Rossi',
            position: 'Head of Operations',
            description: 'Scaling global infrastructure with precision and strategic foresight.',
            image: {
                __image_url__: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?auto=format&fit=crop&w=400&q=80',
                __image_prompt__: 'Professional female executive headshot'
            }
        },
        {
            name: 'Marcus Thorne',
            position: 'Strategy Director',
            description: 'Bridging the gap between complex technology and market dominance.',
            image: {
                __image_url__: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=400&q=80',
                __image_prompt__: 'Professional male strategist headshot'
            }
        }
    ]).meta({
        description: "List of team members with their information",
    })
})

export const Schema = teamSlideSchema

export type TeamSlideData = z.infer<typeof teamSlideSchema>

interface TeamSlideLayoutProps {
    data?: Partial<TeamSlideData>
}

const TeamSlideLayout: React.FC<TeamSlideLayoutProps> = ({ data: slideData }) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const teamMembers = slideData?.teamMembers || []

    useGSAP(() => {
        const tl = gsap.timeline();
        
        tl.from('.team-header', {
            y: -30,
            opacity: 0,
            duration: 1,
            ease: 'power3.out'
        });

        tl.from('.member-card', {
            y: 50,
            opacity: 0,
            duration: 0.8,
            stagger: 0.15,
            ease: 'power4.out'
        }, "-=0.5");

        tl.from('.member-image-container', {
            scale: 0.9,
            opacity: 0,
            duration: 1,
            stagger: 0.15,
            ease: 'back.out(1.7)'
        }, "-=0.8");
    }, { scope: containerRef });

    return (
        <div
            ref={containerRef}
            className="w-full h-full aspect-video bg-[#080808] relative overflow-hidden flex flex-col p-16 text-white"
            style={{
                fontFamily: "'Plus Jakarta Sans', sans-serif",
            }}
        >
            <style dangerouslySetInnerHTML={{ __html: `
                @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@600;800&family=Plus+Jakarta+Sans:wght@300;400;500;700&display=swap');
                
                .glass-card {
                    background: rgba(255, 255, 255, 0.02);
                    backdrop-filter: blur(10px);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                }

                .image-mask {
                    clip-path: polygon(0 0, 100% 0, 100% 85%, 85% 100%, 0 100%);
                }
                
                .accent-glow {
                    filter: drop-shadow(0 0 15px rgba(147, 51, 234, 0.3));
                }
            ` }} />

            {/* Background elements */}
            <div className="absolute top-0 right-0 w-[40%] h-full bg-gradient-to-l from-purple-900/10 to-transparent opacity-50" />
            <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-blue-600/10 rounded-full blur-[120px]" />

            {/* Main Content */}
            <div className="relative z-10 flex h-full gap-16">
                {/* Left Section: Header */}
                <div className="team-header w-1/3 flex flex-col justify-center">
                    <div className="flex items-center gap-3 mb-8">
                        {(slideData as any)?._logo_url__ && (
                            <img src={(slideData as any)?._logo_url__} alt="logo" className="w-8 h-8 object-contain" />
                        )}
                        <span className="text-xs font-bold tracking-[0.4em] uppercase text-purple-500">
                            Elite Force
                        </span>
                    </div>

                    <h1 className="text-6xl lg:text-7xl font-extrabold mb-8 tracking-tighter leading-[0.9]" style={{ fontFamily: 'Outfit' }}>
                        {slideData?.title}
                    </h1>

                    <div className="w-16 h-1 bg-white mb-8" />

                    <p className="text-lg text-white/50 leading-relaxed font-medium italic">
                        "{slideData?.companyDescription}"
                    </p>
                </div>

                {/* Right Section: Grid */}
                <div className="flex-1 flex items-center justify-center">
                    <div className={`grid ${teamMembers.length <= 2 ? 'grid-cols-2' : 'grid-cols-2'} gap-8 w-full`}>
                        {teamMembers.map((member, index) => (
                            <div key={index} className="member-card glass-card rounded-2xl p-6 flex items-start gap-6 group hover:bg-white/[0.05] transition-all duration-500">
                                <div className="member-image-container relative flex-shrink-0">
                                    <div className="image-mask w-24 h-24 overflow-hidden bg-white/10 rounded-xl accent-glow">
                                        <img
                                            src={member.image.__image_url__ || ''}
                                            alt={member.name}
                                            className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
                                        />
                                    </div>
                                    <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-purple-500 rounded-full border-2 border-[#080808]" />
                                </div>

                                <div className="flex-1">
                                    <h3 className="text-xl font-bold tracking-tight mb-1" style={{ fontFamily: 'Outfit' }}>
                                        {member.name}
                                    </h3>
                                    <p className="text-sm font-bold text-purple-400 uppercase tracking-widest mb-3 opacity-80">
                                        {member.position}
                                    </p>
                                    <p className="text-xs text-white/40 leading-relaxed line-clamp-3">
                                        {member.description}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Footer decoration */}
            <div className="absolute bottom-12 right-12 flex items-center gap-4 opacity-20">
                <span className="text-[10px] uppercase tracking-[0.5em] font-black">Archimedes Protocol Active</span>
            </div>
        </div>
    )
}

export default TeamSlideLayout