import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import puppeteer from "puppeteer";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const groupName = searchParams.get("group");

  if (!groupName) {
    return NextResponse.json({ error: "Missing group name" }, { status: 400 });
  }

  if (groupName === "general") {
    try {
      const cachePath = path.join(process.cwd(), "public", "layouts_general.json");
      if (fs.existsSync(cachePath)) {
        const cacheData = fs.readFileSync(cachePath, "utf-8");
        return NextResponse.json(JSON.parse(cacheData));
      }
    } catch (err) {
      console.error("[API/Layout] Cache error:", err);
    }
  }

  const port = process.env.PORT || "3005";
  const engineUrl = process.env.NEXT_PUBLIC_FAST_API || "http://127.0.0.1:5051";
  const schemaPageUrl = `http://127.0.0.1:${port}/schema?group=${encodeURIComponent(groupName)}&fastapiUrl=${encodeURIComponent(engineUrl)}`;

  let browser;
  try {
    browser = await puppeteer.launch({
      executablePath: process.env.PUPPETEER_EXECUTABLE_PATH,
      headless: true,
      args: ["--no-sandbox", "--disable-setuid-sandbox"]
    });
    const page = await browser.newPage();
    await page.setRequestInterception(true);
    page.on('request', (req) => {
      if (['image', 'stylesheet', 'font'].includes(req.resourceType())) req.abort();
      else req.continue();
    });
    await page.goto(schemaPageUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForSelector("[data-layouts]", { timeout: 15000 });
    const result = await page.evaluate(() => ({
      dataLayouts: document.querySelector("[data-layouts]")?.getAttribute("data-layouts") || "[]",
      dataSettings: document.querySelector("[data-settings]")?.getAttribute("data-settings") || "null"
    }));
    const slides = JSON.parse(result.dataLayouts);
    return NextResponse.json({
      name: groupName,
      ordered: JSON.parse(result.dataSettings)?.ordered ?? false,
      slides: slides.map((s: any) => ({ id: s.id, name: s.name, description: s.description, json_schema: s.json_schema }))
    });
  } catch (err) {
    return NextResponse.json({ error: "Failed" }, { status: 500 });
  } finally {
    if (browser) await browser.close();
  }
}
