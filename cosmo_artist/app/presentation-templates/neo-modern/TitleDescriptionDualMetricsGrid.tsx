import * as z from 'zod'

export const Schema = z.object({
    title: z.string().describe('The main heading of the slide').max(30).default('Description and Metrix'),
    description: z.string().describe('Supporting description text').max(250).default('Focus on companies with 500+ employees in Financial Services, Healthcare, and Technology sectors. Target $3.5M in new pipeline with sub-$150 CAC through account-based marketing and content-led strategies.'),
    primaryMetrics: z.array(z.object({
        label: z.string().max(25).describe('Label text for the metric'),
        value: z.string().max(8).describe('Value displayed for the metric')
    })).max(3).describe('List of primary metrics displayed').default([
        { label: 'Main Challenge: Delayed Client', value: '85%' },
        { label: 'Main Challenge: Delayed Client', value: '85%' },
        { label: 'Main Challenge: Delayed Client', value: '85%' }
    ]),
    secondaryMetrics: z.array(z.object({
        label: z.string().max(25).describe('Label text for the metric'),
        value: z.string().max(8).describe('Value displayed for the metric')
    })).max(3).describe('List of secondary metrics displayed').default([
        { label: 'Total Registered Users', value: '>500 M' },
        { label: 'Total Registered Users', value: '>500 M' },
        { label: 'Total Registered Users', value: '>500 M' }
    ])
});

export const layoutId = 'title-description-dual-metrics-grid';
export const layoutName = 'Title Description Dual Metrics Grid';
export const layoutDescription = 'A high-end bento grid metrics layout with double-bezeled metric cards.';

const dynamicSlideLayout: React.FC<{ data: Partial<z.infer<typeof Schema>> }> = ({ data }) => {
    const { title, description, primaryMetrics, secondaryMetrics } = data;

    return (
        <>
            <link
                href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap"
                rel="stylesheet"
            />
            <div className="relative w-full rounded-sm max-w-[1280px] shadow-2xl max-h-[720px] aspect-video bg-[#FAFAFA] z-20 mx-auto overflow-hidden flex items-center px-[70px] justify-between font-['Plus_Jakarta_Sans']"
                style={{
                    backgroundColor: 'var(--background-color,#FAFAFA)',
                    fontFamily: 'var(--body-font-family,"Plus Jakarta Sans")',
                }}
            >
                {/* Subtle Grain Overlay */}
                <div className="absolute inset-0 pointer-events-none opacity-[0.03] mix-blend-overlay z-50" style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=%220 0 200 200%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cfilter id=%22noiseFilter%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.65%22 numOctaves=%223%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23noiseFilter)%22/%3E%3C/svg%3E")' }}></div>

                {/* Left Content Section */}
                <div className="flex flex-col max-w-[460px] gap-[24px] relative z-20">
                    <div className="w-fit rounded-full px-4 py-1.5 text-[11px] uppercase tracking-[0.2em] font-bold"
                        style={{ 
                            backgroundColor: 'var(--card-color, rgba(0,0,0,0.05))',
                            color: 'var(--background-text,#111827)'
                        }}>
                        Metrics
                    </div>
                    {title && (
                        <h1 className="text-[52px] font-semibold leading-[1.05] tracking-[-0.03em]"
                            style={{ color: 'var(--background-text,#111827)' }}
                        >
                            {title}
                        </h1>
                    )}
                    {description && (
                        <p className="text-[18px] font-normal leading-[1.65] opacity-80"
                            style={{ color: 'var(--background-text,#374151)' }}
                        >
                            {description}
                        </p>
                    )}
                </div>

                {/* Right Metrics Bento Grid */}
                <div className="flex gap-[20px] items-stretch relative z-20 h-[580px]">
                    {/* Primary Metrics Column */}
                    <div className="flex flex-col justify-between gap-[20px] w-[270px]">
                        {primaryMetrics?.map((metric, index) => (
                            <div key={index} className="flex-1 p-[2.5px] rounded-[2rem] bg-black/5 dark:bg-white/5 overflow-hidden">
                                <div
                                    className="w-full h-full rounded-[calc(2rem-2.5px)] p-[32px] flex flex-col justify-end gap-2 shadow-[inset_0_1px_1px_rgba(255,255,255,0.4)]"
                                    style={{
                                        backgroundColor: 'var(--card-color,#111827)',
                                    }}
                                >
                                    <div className="text-[14px] font-medium leading-[1.4] opacity-80"
                                        style={{ color: '#FFFFFF' }}
                                    >
                                        {metric.label}
                                    </div>
                                    <div className="text-[44px] font-bold leading-none tracking-tight"
                                        style={{ color: '#FFFFFF' }}
                                    >
                                        {metric.value}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Secondary Metrics Column */}
                    <div className="flex flex-col justify-between gap-[20px] w-[270px]">
                        {secondaryMetrics?.map((metric, index) => (
                            <div key={index} className="flex-1 p-[2.5px] rounded-[2rem] bg-black/5 dark:bg-white/5 overflow-hidden">
                                <div
                                    className="w-full h-full rounded-[calc(2rem-2.5px)] p-[32px] flex flex-col justify-end gap-2 bg-white shadow-[inset_0_1px_1px_rgba(255,255,255,1),0_4px_24px_rgba(0,0,0,0.02)]"
                                >
                                    <div className="text-[14px] font-medium leading-[1.4] opacity-80"
                                        style={{ color: 'var(--background-text,#374151)' }}
                                    >
                                        {metric.label}
                                    </div>
                                    <div className="text-[44px] font-bold leading-none tracking-tight"
                                        style={{ color: 'var(--background-text,#111827)' }}
                                    >
                                        {metric.value}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
                
                {/* Header */}
                {((data as any)?.__companyName__ || (data as any)?._logo_url__) && (
                    <div className="flex items-center gap-3 absolute top-8 left-[70px] z-40">
                        {(data as any)?._logo_url__ && <img src={(data as any)?._logo_url__} alt="logo" className="h-[24px] object-contain" />}
                        {(data as any)?.__companyName__ && (
                            <>
                                {(data as any)?._logo_url__ && <span className="w-[1px] h-4 bg-black/10"></span>}
                                <span className="text-sm font-semibold tracking-wide" style={{ color: 'var(--background-text, #111827)' }}>
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
