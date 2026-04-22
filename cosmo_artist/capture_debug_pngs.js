const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function capture() {
    const id = '32afc531-676d-4af1-bdc3-0325b6bc5ff3';
    const targetUrl = `http://127.0.0.1:3005/pdf-maker?id=${id}&fastapiUrl=http://127.0.0.1:5051`;
    const outDir = path.join(__dirname, 'data', 'exports', 'debug_pngs');
    
    if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

    console.log('Launching browser...');
    const browser = await puppeteer.launch({ headless: "new", args: ['--no-sandbox'] });
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });

    console.log(`Visiting ${targetUrl}...`);
    await page.goto(targetUrl, { waitUntil: 'networkidle0', timeout: 60000 });
    
    console.log('Waiting for slides...');
    await page.waitForSelector('.slide-rendered-marker', { timeout: 30000 });

    const slides = await page.$$('.slide-rendered-marker');
    console.log(`Found ${slides.length} slides. Capturing...`);

    for (let i = 0; i < slides.length; i++) {
        const filePath = path.join(outDir, `slide_${i + 1}.png`);
        await slides[i].screenshot({ path: filePath });
        console.log(`Saved ${filePath}`);
    }

    await browser.close();
}

capture().catch(err => {
    console.error(err);
    process.exit(1);
});
