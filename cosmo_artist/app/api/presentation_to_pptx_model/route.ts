import { ApiError } from "@/models/errors";
import { NextRequest, NextResponse } from "next/server";
import puppeteer, { Browser, Page } from "puppeteer";
import { convertElementAttributesToPptxSlides } from "@/utils/pptx_models_utils";
import { PptxPresentationModel } from "@/types/pptx_models";
import fs from "fs";
import path from "path";

export async function GET(request: NextRequest) {
  let browser: Browser | null = null;
  let page: Page | null = null;

  try {
    const id = request.nextUrl.searchParams.get("id");
    if (!id) throw new ApiError("Missing ID");

    const tempDir = process.env.TEMP_DIRECTORY || "./data/temp";
    const screenshotsDir = path.join(tempDir, "screenshots");
    if (!fs.existsSync(screenshotsDir)) fs.mkdirSync(screenshotsDir, { recursive: true });

    browser = await puppeteer.launch({
      executablePath: process.env.PUPPETEER_EXECUTABLE_PATH,
      headless: true,
      args: ["--no-sandbox", "--disable-gpu"]
    });

    page = await browser.newPage();
    page.on('console', msg => console.log('BROWSER:', msg.text()));
    page.on('pageerror', err => console.error('BROWSER ERROR:', err.message));

    const port = process.env.PORT || "3005";
    const engineUrl = process.env.NEXT_PUBLIC_FAST_API || "http://127.0.0.1:5051";
    const targetUrl = `http://127.0.0.1:${port}/pdf-maker?id=${id}&fastapiUrl=${encodeURIComponent(engineUrl)}`;

    console.log(`[PPTXAPI] Visiting ${targetUrl}`);
    await page.goto(targetUrl, { waitUntil: "networkidle0", timeout: 120000 });
    
    // Wait for markers
    await page.waitForSelector(".slide-rendered-marker", { timeout: 60000 });
    
    // Extract slides info from DOM with high fidelity
    const rawData = await page.evaluate(async (SCALE_FACTOR) => {
      const slideMarkers = Array.from(document.querySelectorAll(".slide-rendered-marker"));

      const rgbToHex = (rgb: string): string => {
        if (!rgb || rgb === 'transparent' || rgb === 'rgba(0, 0, 0, 0)') return '';
        if (rgb.startsWith('#')) return rgb.replace('#', '').toUpperCase();
        
        const match = rgb.match(/^rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*(\d+(\.\d+)?))?\)$/);
        if (!match) return '';
        
        const r = parseInt(match[1]);
        const g = parseInt(match[2]);
        const b = parseInt(match[3]);
        
        const hex = ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1).toUpperCase();
        return hex;
      };

      const parseShadow = (shadowStr: string) => {
        if (!shadowStr || shadowStr === 'none') return undefined;
        // Basic parser for boxShadow: "rgba(0, 0, 0, 0.2) 0px 4px 6px -1px"
        const parts = shadowStr.split(' ');
        const color = rgbToHex(parts.slice(0, 3).join(' '));
        return {
          color: color || '000000',
          radius: 4, // default
          opacity: 0.2
        };
      };

      // Wait for fonts and images to load
      await document.fonts.ready;
      const images = Array.from(document.querySelectorAll('img'));
      await Promise.all(images.map(img => img.complete ? Promise.resolve() : new Promise(resolve => {
        img.onload = resolve;
        img.onerror = resolve;
      })));

      return slideMarkers.map(marker => {
        const elements: any[] = [];
        const markerRect = marker.getBoundingClientRect();

        // Scan ALL elements within the slide
        const allItems = marker.querySelectorAll('*');
        
        allItems.forEach((el: any) => {
          const rect = el.getBoundingClientRect();
          const style = window.getComputedStyle(el);
          
          // Wait for images to load if it's an image or has background
          const isImage = el.tagName === 'IMG';
          const iconUrl = el.getAttribute('data-path');
          const bgImage = style.backgroundImage !== 'none' ? style.backgroundImage.replace(/url\(['"]?(.*?)['"]?\)/, '$1') : null;
          const imageSrc = isImage ? (el as HTMLImageElement).src : (iconUrl || bgImage || undefined);

          const hasBackground = style.backgroundColor !== 'rgba(0, 0, 0, 0)' && style.backgroundColor !== 'transparent';
          const hasBorder = style.borderStyle !== 'none' && parseFloat(style.borderWidth) > 0;
          const isText = el.childNodes.length > 0 && Array.from(el.childNodes).some((n: any) => n.nodeType === 3 && n.textContent?.trim());
          const hasText = el.innerText && el.innerText.trim().length > 0 && isText;
          const hasShadow = style.boxShadow !== 'none';

          // Include elements that are images or icons
          if (!hasBackground && !hasBorder && !hasText && !imageSrc && !hasShadow) return;

          // Capture element relative to slide
          elements.push({
            tagName: el.tagName.toLowerCase(),
            className: el.className,
            innerText: hasText ? el.innerText : undefined,
            imageSrc: imageSrc,
            position: {
              left: (rect.left - markerRect.left) * SCALE_FACTOR,
              top: (rect.top - markerRect.top) * SCALE_FACTOR,
              width: rect.width * SCALE_FACTOR,
              height: rect.height * SCALE_FACTOR
            },
            background: {
              color: rgbToHex(style.backgroundColor),
              opacity: parseFloat(style.opacity)
            },
            border: hasBorder ? {
              color: rgbToHex(style.borderColor),
              width: parseFloat(style.borderWidth) * SCALE_FACTOR
            } : undefined,
            borderRadius: [
              parseFloat(style.borderTopLeftRadius) * SCALE_FACTOR,
              parseFloat(style.borderTopRightRadius) * SCALE_FACTOR,
              parseFloat(style.borderBottomRightRadius) * SCALE_FACTOR,
              parseFloat(style.borderBottomLeftRadius) * SCALE_FACTOR
            ],
            shadow: hasShadow ? parseShadow(style.boxShadow) : undefined,
            font: hasText ? {
              name: style.fontFamily.split(',')[0].replace(/['"]/g, ''),
              size: parseFloat(style.fontSize) * SCALE_FACTOR,
              weight: parseInt(style.fontWeight),
              color: rgbToHex(style.color),
              italic: style.fontStyle === 'italic'
            } : undefined,
            textAlign: style.textAlign,
            lineHeight: parseFloat(style.lineHeight) * SCALE_FACTOR,
            zIndex: parseInt(style.zIndex) || 0
          });
        });

        // Sort elements by zIndex to maintain layering
        elements.sort((a, b) => (a.zIndex || 0) - (b.zIndex || 0));

        return {
          elements,
          backgroundColor: rgbToHex(window.getComputedStyle(marker).backgroundColor) || 'FFFFFF',
          speakerNote: marker.getAttribute("data-speaker-note") || ""
        };
      });
    });

    console.log(`[PPTXAPI] Extracted attributes for ${rawData.length} slides.`);
    
    // Use the existing utility to convert raw attributes to valid PPTX models
    const pptxSlides = convertElementAttributesToPptxSlides(rawData);

    const presentation_pptx_model: PptxPresentationModel = {
      slides: pptxSlides
    };

    return NextResponse.json(presentation_pptx_model);
  } catch (error: any) {
    console.error("[PPTXAPI] Error:", error);
    return NextResponse.json({ detail: error.message }, { status: 500 });
  } finally {
    if (browser) await browser.close();
  }
}
