"use client";

import React, { useMemo } from 'react';
import { getLayoutByLayoutId } from '../../presentation-templates';

interface PresentationLayoutRendererProps {
  slide: any;
  theme?: any;
}

/**
 * Smart renderer that bridges the gap between generic slide data 
 * and professional layout-specific schemas.
 */
export const PresentationLayoutRenderer: React.FC<PresentationLayoutRendererProps> = ({ slide, theme }) => {
  // 1. Find the professional layout component
  const layoutEntry = useMemo(() => {
    // If slide.layout is something like "modern:intro-slide", getLayoutByLayoutId will find it
    return getLayoutByLayoutId(slide.layout);
  }, [slide.layout]);

  // 2. Map generic slide content to template-specific data
  const templateData = useMemo(() => {
    const { content, images, icons } = slide;
    
    // Default mapping for most professional templates
    const data: any = {
      title: content?.title || "",
      description: content?.description || (typeof content?.body === 'string' ? content.body : ""),
      mainDescription: content?.description || (typeof content?.body === 'string' ? content.body : ""),
    };

    // If template expects "sections" (like in modern:bullet-with-icons-description-grid)
    if (Array.isArray(content?.body)) {
      data.sections = content.body.map((item: any, idx: number) => ({
        title: item.heading || item.title || `Item ${idx + 1}`,
        description: item.description || "",
        icon: icons?.[idx] ? {
            __icon_url__: icons[idx],
            __icon_query__: "icon" 
        } : undefined
      }));
    }

    // Handle images (most templates expect an "image" object with __image_url__)
    if (images && images.length > 0) {
      data.image = {
        __image_url__: images[0],
        __image_prompt__: slide.content?.image_prompts?.[0] || "supporting image"
      };
    }

    // Pass through company/logo metadata if available
    data.__companyName__ = slide.properties?.companyName || "";
    data._logo_url__ = slide.properties?.logoUrl || "";

    return data;
  }, [slide]);

  // 3. Fallback to dummy renderer if layout not found
  if (!layoutEntry) {
    console.warn(`[PresentationLayoutRenderer] Layout not found: ${slide.layout}. Falling back to default.`);
    // We would normally import V1ContentRender here, but to avoid circularity if needed, 
    // we just show a basic error or the raw content.
    return (
      <div className="w-full h-full bg-white p-10 flex flex-col items-center justify-center border-4 border-dashed border-red-200">
        <h1 className="text-2xl font-bold text-red-500 mb-4">Layout Missing: {slide.layout}</h1>
        <div className="text-gray-800 max-w-2xl">
          <h2 className="text-xl font-bold">{slide.content?.title}</h2>
          <p>{typeof slide.content?.body === 'string' ? slide.content.body : 'Multiple items structure'}</p>
        </div>
      </div>
    );
  }

  const LayoutComponent = layoutEntry.component;

  return (
    <div className="w-full h-full presentation-layout-container">
      <LayoutComponent data={templateData} />
    </div>
  );
};
