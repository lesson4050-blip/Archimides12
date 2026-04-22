import * as z from 'zod'

export const Schema = z.object({
    title: z.string().max(50).describe('The main title of the slide').default('Image with Description'),
    description: z.string().max(350).describe('The body text or description of the slide').default('Focus on companies with 500+ employees in Financial Services, Healthcare, and Technology sectors. Target $3.5M in new pipeline with sub-$150 CAC through account-based marketing and content-led strategies.'),
    image: z.object({
        __image_url__: z.string().describe('The URL of the featured image'),
        __image_prompt__: z.string().max(100).describe('A description for generating a replacement image')
    }).describe('The large image displayed on the right side of the slide').default({
        __image_url__: 'https://presenton-public-assets.s3.ap-southeast-1.amazonaws.com/replaceable_template_image.png',
        __image_prompt__: 'Close up of diverse business hands joined together in a circle, representing teamwork and partnership.'
    })
});

export const layoutId = 'title-description-image-right';
export const layoutName = 'Title Description Image Right';
export const layoutDescription = 'A high-end editorial split slide with massive typography on the left and a double-bezel featured image on the right.';

const dynamicSlideLayout: React.FC<{ data: Partial<z.infer<typeof Schema>> }> = ({ data }) => {
    const { title, description, image } = data;

    return (
        <>
            <link
                href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap"
                rel="stylesheet"
            />
            <div className="relative w-full h-full rounded-sm max-w-[1280px] shadow-2xl max-h-[720px] aspect-video z-20 mx-auto overflow-hidden flex font-['Plus_Jakarta_Sans']"
                style={{
                    backgroundColor: 'var(--background-color,#FAFAFA)',
                    fontFamily: 'var(--body-font-family,"Plus Jakarta Sans")',
                }}
            >
                {/* Subtle Grain Overlay for Premium Physical Feel */}
                <div className="absolute inset-0 pointer-events-none opacity-[0.03] mix-blend-overlay z-50" style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=%220 0 200 200%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cfilter id=%22noiseFilter%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.65%22 numOctaves=%223%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23noiseFilter)%22/%3E%3C/svg%3E")' }}></div>

                <div className="flex w-full h-full items-center justify-between px-[70px] py-[60px] relative z-20">
                    {/* Left Side: Typography */}
                    <div className="flex flex-col justify-center gap-[24px] w-full max-w-[480px]">
                        {/* Eyebrow tag */}
                        <div className="w-fit rounded-full px-4 py-1.5 text-[11px] uppercase tracking-[0.2em] font-bold"
                            style={{ 
                                backgroundColor: 'var(--card-color, rgba(0,0,0,0.05))',
                                color: 'var(--background-text,#111827)'
                            }}>
                            Overview
                        </div>

                        {title && (
                            <h1
                                className="font-semibold text-[56px] leading-[1.05] tracking-[-0.03em]"
                                style={{ color: 'var(--background-text,#111827)' }}
                            >
                                {title}
                            </h1>
                        )}
                        {description && (
                            <p
                                className="font-normal text-[18px] leading-[1.65] opacity-80"
                                style={{ color: 'var(--background-text,#374151)' }}
                            >
                                {description}
                            </p>
                        )}
                    </div>

                    {/* Right Side: Featured Image (Double Bezel) */}
                    <div className="flex-shrink-0 w-[580px] h-[600px] p-[2.5px] rounded-[2.5rem] bg-black/5 dark:bg-white/5 border border-black/5 shadow-inner">
                        <div className="w-full h-full rounded-[calc(2.5rem-2.5px)] overflow-hidden shadow-[inset_0_1px_1px_rgba(255,255,255,0.8)] bg-white relative">
                            {image?.__image_url__ && (
                                <img
                                    src={image.__image_url__}
                                    alt={image.__image_prompt__ || 'Slide Visual'}
                                    className="w-full h-full object-cover transform transition-transform duration-1000 hover:scale-105"
                                />
                            )}
                            {/* Inner glass reflection */}
                            <div className="absolute inset-0 rounded-[calc(2.5rem-2.5px)] pointer-events-none shadow-[inset_0_0_0_1px_rgba(255,255,255,0.2)]" />
                        </div>
                    </div>
                </div>

                {/* Header/Logo positioning */}
                {((data as any)?.__companyName__ || (data as any)?._logo_url__) && (
                    <div className="flex items-center gap-3 absolute top-8 left-[70px] z-40 mix-blend-difference opacity-90">
                        {(data as any)?._logo_url__ && <img src={(data as any)?._logo_url__} alt="logo" className="h-[24px] object-contain" />}
                        {(data as any)?.__companyName__ && (
                            <>
                                {(data as any)?._logo_url__ && <span className="w-[1px] h-4 bg-white/30"></span>}
                                <span className="text-sm font-semibold tracking-wide text-white">
                                    {(data as any)?.__companyName__}
                                </span>
                            </>
                        )}
                    </div>
                )}
            </div>
        </>
    );
};

export default dynamicSlideLayout;
