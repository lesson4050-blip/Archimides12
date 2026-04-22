export const dynamic = 'force-dynamic';

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
    // Force set viewport to match slide aspect ratio/size
    await page.setViewport({ width: 1280, height: 800 });
    
    page.on('console', msg => console.log('BROWSER:', msg.text()));
    page.on('pageerror', err => console.error('BROWSER ERROR:', err.message));

    const port = process.env.PORT || "3005";
    const engineUrl = process.env.NEXT_PUBLIC_FAST_API || "http://127.0.0.1:5051";
    const targetUrl = `http://127.0.0.1:${port}/pdf-maker?id=${id}&fastapiUrl=${encodeURIComponent(engineUrl)}`;

    console.log(`[PPTXAPI] Visiting ${targetUrl}`);
    await page.goto(targetUrl, { waitUntil: "networkidle0", timeout: 120000 });
    
    // 1. Wait for markers to appear
    await page.waitForSelector(".slide-rendered-marker", { timeout: 60000 });
    
    // 2. Wait for fonts and images in a separate, isolated evaluate
    await page.evaluate(async () => {
      if (document.fonts) await document.fonts.ready;
      const images = Array.from(document.querySelectorAll('img'));
      await Promise.all(images.map(img => img.complete ? Promise.resolve() : new Promise(resolve => {
        img.onload = resolve;
        img.onerror = resolve;
      })));
    });

    // 3. Extract slides info
    const rawData = await page.evaluate(async () => {
      console.log("[BROWSER] Extraction script started.");
      
      // Wait for all images to have a width > 0
      const imgs = Array.from(document.querySelectorAll('img'));
      await Promise.all(imgs.map(img => {
        if (img.complete && (img as any).naturalWidth > 0) return Promise.resolve();
        return new Promise(resolve => {
          img.onload = resolve;
          img.onerror = resolve;
          setTimeout(resolve, 3000); 
        });
      }));

      const slideMarkers = document.querySelectorAll(".slide-rendered-marker");
      console.log("[BROWSER] Found markers: " + slideMarkers.length);

      const rgbToHex = (rgb: any) => {
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

      const parseShadow = (shadowStr: any) => {
        if (!shadowStr || shadowStr === 'none') return undefined;
        const parts = shadowStr.split(' ');
        let colorStr = parts.find((p: any) => p.startsWith('rgb'));
        const color = colorStr ? rgbToHex(colorStr) : '000000';
        return {
          color: color || '000000',
          radius: 4,
          opacity: 0.2
        };
      };

      return Array.from(slideMarkers).map((marker, slideIdx) => {
        const elements: any[] = [];
        const markerRect = marker.getBoundingClientRect();
        const allItems = marker.querySelectorAll('*');
        let captured = 0;
        
        // Capture slide background
        const markerStyle = window.getComputedStyle(marker);
        const slideBgColor = rgbToHex(markerStyle.backgroundColor) || 'FFFFFF';

        allItems.forEach((el) => {
          if (el.classList.contains('slide-rendered-marker')) return;
          
          const rect = el.getBoundingClientRect();
          const isImage = el.tagName.toUpperCase() === 'IMG';
          const style = window.getComputedStyle(el);
          
          // Check for background image (often used for icons or cards)
          let backgroundImage = style.backgroundImage;
          if (backgroundImage === 'none') backgroundImage = '';
          const bgImageUrlMatch = backgroundImage.match(/url\(['"]?(.*?)['"]?\)/);
          const bgImageUrl = bgImageUrlMatch ? bgImageUrlMatch[1] : undefined;
          
          const iconUrl = el.getAttribute('data-path');
          const hasImage = isImage || !!iconUrl || !!bgImageUrl || el.classList.contains('image');
          
          // Filter out elements outside the slide or invisible
          if (!hasImage && (rect.width === 0 || rect.height === 0)) return;
          
          // Relaxed bounds check for images
          const padding = hasImage ? 5 : 0;
          if (rect.bottom < markerRect.top - padding || rect.top > markerRect.bottom + padding || 
              rect.right < markerRect.left - padding || rect.left > markerRect.right + padding) return;
          
          // CRITICAL FIX: Do not capture full-slide wrapper divs as shapes.
          if (!hasImage && rect.width >= 1270 && rect.height >= 710) return;

          const opacity = parseFloat(style.opacity);
          if (opacity === 0 || style.display === 'none' || style.visibility === 'hidden') return;

          const bgColor = rgbToHex(style.backgroundColor);
          const hasBackground = bgColor !== '' && bgColor !== '00000000';
          
          // Check for opacity (for glassmorphism support)
          let bgOpacity = 1.0;
          if (style.backgroundColor.startsWith('rgba')) {
            const bgOpacityMatch = style.backgroundColor.match(/rgba?\(.*,\s*([\d.]+)\)/);
            bgOpacity = bgOpacityMatch ? parseFloat(bgOpacityMatch[1]) : 1.0;
          }

          let finalImageSrc = isImage ? (el as HTMLImageElement).src : (bgImageUrl || iconUrl);
          if (finalImageSrc && finalImageSrc.startsWith('/static/')) {
             finalImageSrc = window.location.origin + finalImageSrc;
          }

          // Check for text content in this specific element (not children)
          let hasOwnText = false;
          for (let node of el.childNodes) {
            if (node.nodeType === 3 && (node.textContent?.trim()?.length ?? 0) > 0) {
              hasOwnText = true;
              break;
            }
          }
          
          const borderWidth = parseFloat(style.borderWidth);
          const hasBorder = borderWidth > 0 && rgbToHex(style.borderColor) !== '';

          // Capture Shadow
          const boxShadow = style.boxShadow;
          const hasShadow = boxShadow !== 'none' && boxShadow !== '';

          // CRITICAL FIX: Ignore empty container divs that just have background/border/shadow 
          if (!hasOwnText && !hasImage && (hasBackground || hasBorder || hasShadow)) {
             if (rect.width > 300 && rect.height > 300 && bgOpacity < 0.2) return; 
          }

          // ONLY CAPTURE VISUAL ELEMENTS
          if (!hasOwnText && !hasBackground && !hasImage && !hasBorder && !hasShadow) return;

          // DEBUG
          if (hasImage) console.log(`[BROWSER] Slide ${slideIdx}: Found IMAGE: ${el.tagName} src=${finalImageSrc} size=${Math.round(rect.width)}x${Math.round(rect.height)} at ${Math.round(rect.left)},${Math.round(rect.top)}`);

          captured++;
          elements.push({
            tagName: el.tagName.toLowerCase(),
            innerText: hasOwnText ? (el as any).innerText.trim() : undefined,
            position: {
              left: Math.round(rect.left - markerRect.left),
              top: Math.round(rect.top - markerRect.top),
              width: Math.round(rect.width),
              height: Math.round(rect.height)
            },
            background: hasBackground ? { color: bgColor, opacity: bgOpacity } : undefined,
            shadow: hasShadow ? parseShadow(boxShadow) : undefined,
            border: hasBorder ? {
                color: rgbToHex(style.borderColor),
                width: borderWidth,
                opacity: 1.0
            } : undefined,
            opacity: opacity,
            imageSrc: hasImage ? finalImageSrc : undefined,
            font: hasOwnText ? {
              name: style.fontFamily.split(',')[0].replace(/['"]/g, ''),
              size: parseFloat(style.fontSize),
              weight: parseInt(style.fontWeight),
              color: rgbToHex(style.color) || '000000',
              italic: style.fontStyle === 'italic'
            } : undefined,
            zIndex: parseInt(style.zIndex) || 0,
            borderRadius: style.borderRadius !== '0px' ? [
              parseFloat(style.borderTopLeftRadius),
              parseFloat(style.borderTopRightRadius),
              parseFloat(style.borderBottomRightRadius),
              parseFloat(style.borderBottomLeftRadius)
            ] : undefined,
            textAlign: style.textAlign,
            lineHeight: parseFloat(style.lineHeight) || 0
          });
        });

        console.log("[BROWSER] Slide " + slideIdx + ": Captured " + captured + " elements");
        if (elements.length > 0) {
          const e = elements[0];
          console.log("[BROWSER] Slide " + slideIdx + " Elem 0: Tag=" + e.tagName + " Pos=" + JSON.stringify(e.position) + " BG=" + JSON.stringify(e.background) + " Font=" + JSON.stringify(e.font));
        }
        elements.sort((a, b) => {
          const zDiff = (a.zIndex || 0) - (b.zIndex || 0);
          if (zDiff !== 0) return zDiff;
          const areaA = (a.position.width || 0) * (a.position.height || 0);
          const areaB = (b.position.width || 0) * (b.position.height || 0);
          return areaB - areaA;
        });

        return {
          elements,
          backgroundColor: slideBgColor,
          speakerNote: marker.getAttribute("data-speaker-note") || ""
        };
      });
    });

    console.log(`[PPTXAPI] Extracted ${rawData.length} slides data.`);
    rawData.forEach((s, idx) => {
      console.log(`[PPTXAPI] Slide ${idx}: Captured ${s.elements.length} elements.`);
    });
    
    // Use the existing utility to convert raw attributes to valid PPTX models
    const pptxSlides = convertElementAttributesToPptxSlides(rawData);

    const presentation_pptx_model: PptxPresentationModel = {
      slides: pptxSlides
    };

    // DEBUG: Save full model to file for audit
    try {
      const debugPath = path.join(process.cwd(), "..", "scratch", "last_pptx_model.json");
      fs.writeFileSync(debugPath, JSON.stringify(presentation_pptx_model, null, 2));
      console.log(`[PPTXAPI] Debug model saved to ${debugPath}`);
    } catch (e) {
      console.error("[PPTXAPI] Failed to save debug model:", e);
    }

    return NextResponse.json(presentation_pptx_model);
  } catch (error: any) {
    console.error("[PPTXAPI] Error:", error);
    return NextResponse.json({ detail: error.message }, { status: 500 });
  } finally {
    if (browser) await browser.close();
  }
}
