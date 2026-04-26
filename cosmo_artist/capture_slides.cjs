const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function captureSlides(presentationId, outputDir) {
  console.log(`Capturing slides for ${presentationId} to ${outputDir}`);
  const browser = await puppeteer.launch({ 
      headless: true,
      executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
  });
  const page = await browser.newPage();
  
  // Set viewport to 1280x720, which is standard 16:9
  await page.setViewport({ width: 1280, height: 720, deviceScaleFactor: 2 });
  
  const url = `http://localhost:3005/pdf-maker?id=${presentationId}&fastapiUrl=http://localhost:5051`;
  console.log(`Navigating to ${url}`);
  
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 120000 });
  
  // Wait for the slides to render
  try {
    await page.waitForSelector('.slide-rendered-marker', { timeout: 60000 });
  } catch (e) {
    console.error("Timeout waiting for slides to render.");
    const html = await page.evaluate(() => document.body.innerHTML);
    console.error("Current page HTML:", html);
    await browser.close();
    process.exit(1);
  }

  // Ensure output directory exists
  if (!fs.existsSync(outputDir)){
      fs.mkdirSync(outputDir, { recursive: true });
  }

  // Get all slide elements
  const slides = await page.$$('.slide-rendered-marker');
  console.log(`Found ${slides.length} slides.`);
  
  for (let i = 0; i < slides.length; i++) {
    const slide = slides[i];
    const imagePath = path.join(outputDir, `slide_${i}.png`);
    await slide.screenshot({ path: imagePath });
    console.log(`Saved screenshot for slide ${i} to ${imagePath}`);
  }
  
  await browser.close();
}

const args = process.argv.slice(2);
if (args.length < 2) {
  console.error("Usage: node capture_slides.js <presentationId> <outputDir>");
  process.exit(1);
}

captureSlides(args[0], args[1]);
