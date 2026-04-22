import * as z from 'zod';
import React from 'react';

export const Schema = z.object({
    title: z.string().max(30).describe('The main title of the slide').default('Key Takeaways'),
    description: z.string().max(300).describe('The main paragraph description on the slide').default('Focus on companies with 500+ employees in Financial Services, Healthcare, and Technology sectors. Target $3.5M in new pipeline with sub-$150 CAC through account-based marketing and content-led strategies.'),
    bullets: z.array(z.object({
        heading: z.string().max(40).describe('The heading for this bullet point'),
        description: z.string().max(120).describe('The description for this bullet point'),
    })).max(5).describe('A list of up to 5 bullet points, each with a heading and description').default([
        { heading: 'Market expansion', description: 'Prioritize high-growth verticals and geographic regions with strong demand.' },
        { heading: 'Customer retention', description: 'Reduce churn through proactive support and tailored success programs.' },
        { heading: 'Product innovation', description: 'Ship features that align with top customer requests and usage data.' },
        { heading: 'Operational efficiency', description: 'Automate repetitive workflows to free capacity for strategic work.' },
        { heading: 'Team enablement', description: 'Invest in training and tools so teams can execute at scale.' },
    ]),
    image: z.object({
        __image_url__: z.string().describe('The URL of the featured image'),
        __image_prompt__: z.string().max(100).describe('A description for generating a replacement image')
    }).optional().describe('An optional image to display next to the bullets'),
});

export const layoutId = 'title-description-bullet-list';
export const layoutName = 'Title Description Bullet List';
export const layoutDescription = 'A clean two-column layout with a main title and description on the left, and up to 5 bullet points on the right. Each bullet has a heading and a short description. Ideal for key takeaways, feature highlights, or structured lists with context.';

const dynamicSlideLayout: React.FC<{ data: Partial<z.infer<typeof Schema>> }> = ({ data }) => {
    const { title, description, bullets, image } = data;

    return (
        <>
            <link
                href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap"
                rel="stylesheet"
            />
            <div
                className="relative w-full rounded-sm max-w-[1280px] shadow-lg max-h-[720px] aspect-video bg-white z-20 mx-auto overflow-hidden"
                style={{
                    backgroundColor: 'var(--background-color,#FFFFFF)',
                    fontFamily: 'var(--body-font-family,Montserrat)',
                }}
            >
                <div className="flex h-full w-full items-center justify-between px-[80px] gap-12">
                    {/* Left Section: Title + Description */}
                    <div className="flex flex-col flex-1 justify-center">
                        {title && (
                            <h1
                                className="text-[40px] font-bold mb-6 leading-tight"
                                style={{ letterSpacing: '-1.2px', color: 'var(--background-text,#111827)' }}
                            >
                                {title}
                            </h1>
                        )}
                        {description && (
                            <p
                                className="text-[16px] leading-[28px] max-w-[420px] opacity-80"
                                style={{ color: 'var(--background-text,#374151)' }}
                            >
                                {description}
                            </p>
                        )}
                    </div>

                    {/* Middle Section: Bullet list */}
                    <div className="flex flex-col flex-1 justify-center gap-4">
                        {bullets?.map((item, index) => (
                            <div
                                key={index}
                                className="flex flex-col justify-center px-5 py-3 rounded-[8px]"
                                style={{
                                    backgroundColor: 'var(--card-color,#F3F4F6)',
                                    borderLeft: '4px solid var(--stroke,#4C68DF)',
                                }}
                            >
                                <h3
                                    className="text-[16px] font-bold leading-tight"
                                    style={{ color: 'var(--background-text,#111827)' }}
                                >
                                    {item.heading}
                                </h3>
                                <p
                                    className="text-[14px] leading-tight mt-1 opacity-70"
                                    style={{ color: 'var(--background-text,#374151)' }}
                                >
                                    {item.description}
                                </p>
                            </div>
                        ))}
                    </div>

                    {/* Right Section: Optional Image */}
                    {image?.__image_url__ && (
                        <div className="flex-shrink-0 w-[320px] h-[480px] p-[2px] rounded-[24px] bg-black/5 border border-black/5 shadow-inner">
                            <div className="w-full h-full rounded-[22px] overflow-hidden bg-gray-100">
                                <img
                                    src={image.__image_url__}
                                    alt={image.__image_prompt__ || 'Slide Visual'}
                                    className="w-full h-full object-cover"
                                />
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </>
    );
};

export default dynamicSlideLayout;
