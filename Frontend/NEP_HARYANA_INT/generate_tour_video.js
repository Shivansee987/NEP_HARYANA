import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const FFMPEG_PATH = path.resolve(__dirname, '../../venv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe');
const FRAMES_DIR = path.resolve(__dirname, 'temp_frames');
const OUTPUT_MP4 = path.resolve(__dirname, '../../website_full_tour.mp4');
const OUTPUT_WEBP = path.resolve(__dirname, '../../website_full_tour.webp');
const ARTIFACTS_MP4 = 'C:\\Users\\Devansh Datta\\.gemini\\antigravity-ide\\brain\\a3301853-447f-4f46-aa8a-c9c168769d37\\website_full_tour.mp4';
const ARTIFACTS_WEBP = 'C:\\Users\\Devansh Datta\\.gemini\\antigravity-ide\\brain\\a3301853-447f-4f46-aa8a-c9c168769d37\\website_full_tour_1790429286534.webp';

if (!fs.existsSync(FRAMES_DIR)) {
  fs.mkdirSync(FRAMES_DIR, { recursive: true });
} else {
  fs.readdirSync(FRAMES_DIR).forEach(f => fs.unlinkSync(path.join(FRAMES_DIR, f)));
}

let frameIndex = 0;

async function captureFrame(page, count = 1) {
  const buffer = await page.screenshot({ type: 'jpeg', quality: 85 });
  for (let i = 0; i < count; i++) {
    const filename = path.join(FRAMES_DIR, `frame_${String(frameIndex++).padStart(5, '0')}.jpg`);
    fs.writeFileSync(filename, buffer);
  }
}

async function smoothScroll(page, distance, steps = 15, delay = 60) {
  const delta = distance / steps;
  for (let i = 0; i < steps; i++) {
    await page.evaluate((d) => window.scrollBy(0, d), delta);
    await new Promise(r => setTimeout(r, delay));
    await captureFrame(page, 1);
  }
}

async function loginUser(page, email, password, targetUrl) {
  await page.goto('http://localhost:5173/auth/login', { waitUntil: 'networkidle0' });
  await page.evaluate(() => {
    sessionStorage.clear();
    localStorage.clear();
  });
  await page.reload({ waitUntil: 'networkidle0' });
  await captureFrame(page, 3);

  // Type credentials
  const emailInput = await page.$('input[type="email"]');
  if (emailInput) {
    await emailInput.click({ clickCount: 3 });
    await emailInput.type(email, { delay: 30 });
  }

  const passInput = await page.$('input[type="password"]');
  if (passInput) {
    await passInput.click({ clickCount: 3 });
    await passInput.type(password, { delay: 30 });
  }

  await captureFrame(page, 3);
  await page.keyboard.press('Enter');

  // Wait for target or navigation
  try {
    await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 5000 });
  } catch (e) {}
  
  if (targetUrl && !page.url().includes(targetUrl)) {
    await page.goto(targetUrl, { waitUntil: 'networkidle0' });
  }
  await new Promise(r => setTimeout(r, 600));
  await captureFrame(page, 5);
}

async function showSidebarHover(page) {
  await page.mouse.move(35, 250);
  await new Promise(r => setTimeout(r, 450));
  await captureFrame(page, 12);
  await page.mouse.move(600, 250);
  await new Promise(r => setTimeout(r, 350));
  await captureFrame(page, 6);
}

async function runTour() {
  console.log('Launching Chrome from:', CHROME_PATH);
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: true,
    defaultViewport: { width: 1440, height: 900 },
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1440,900']
  });

  const page = await browser.newPage();

  console.log('1. Recording Landing Page...');
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle0' });
  await captureFrame(page, 15); // 1.5s pause at top
  await smoothScroll(page, 500, 15, 50);
  await captureFrame(page, 8);
  await smoothScroll(page, 600, 15, 50);
  await captureFrame(page, 10);
  await smoothScroll(page, 600, 15, 50);
  await captureFrame(page, 10);
  await smoothScroll(page, -1700, 20, 40);
  await captureFrame(page, 10);

  console.log('2. Recording Screening Committee Chair Dashboard...');
  await loginUser(page, 'chair@dev.local', 'DevPass@123', 'http://localhost:5173/checker/queue');
  await captureFrame(page, 15); // Show fixed KPI cards!
  
  // Hover over sidebar to show expand effect
  await showSidebarHover(page);

  // Switch tabs
  const buttons = await page.$$('button');
  for (const btn of buttons) {
    const text = await page.evaluate(el => el.textContent, btn);
    if (text && text.includes('Universities')) {
      await btn.click();
      await new Promise(r => setTimeout(r, 400));
      await captureFrame(page, 10);
      break;
    }
  }
  for (const btn of buttons) {
    const text = await page.evaluate(el => el.textContent, btn);
    if (text && text.includes('Colleges')) {
      await btn.click();
      await new Promise(r => setTimeout(r, 400));
      await captureFrame(page, 10);
      break;
    }
  }
  for (const btn of buttons) {
    const text = await page.evaluate(el => el.textContent, btn);
    if (text && text.includes('All Frameworks')) {
      await btn.click();
      await new Promise(r => setTimeout(r, 400));
      await captureFrame(page, 8);
      break;
    }
  }

  // Open first review
  const openButtons = await page.$$('button');
  for (const btn of openButtons) {
    const text = await page.evaluate(el => el.textContent, btn);
    if (text && text.includes('Open Review')) {
      await btn.click();
      try {
        await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 5000 });
      } catch (e) {}
      await captureFrame(page, 15);
      await smoothScroll(page, 400, 10, 50);
      await captureFrame(page, 10);
      await smoothScroll(page, -400, 10, 50);
      break;
    }
  }

  console.log('3. Recording State DHE Admin Console...');
  await loginUser(page, 'admin@dev.local', 'DevPass@123', 'http://localhost:5173/admin');
  await captureFrame(page, 15); // Show macro KPIs and charts
  await showSidebarHover(page);
  await smoothScroll(page, 500, 12, 50);
  await captureFrame(page, 10);
  await smoothScroll(page, -500, 12, 50);

  // College Management in Admin
  await page.goto('http://localhost:5173/admin/colleges', { waitUntil: 'networkidle0' });
  await captureFrame(page, 15);

  // Scoring in Admin
  await page.goto('http://localhost:5173/admin/scoring', { waitUntil: 'networkidle0' });
  await captureFrame(page, 15);

  console.log('4. Recording University Dashboard...');
  await loginUser(page, 'nodal@dev.local', 'DevPass@123', 'http://localhost:5173/university/dashboard');
  await captureFrame(page, 15);
  await showSidebarHover(page);
  await smoothScroll(page, 500, 15, 50);
  await captureFrame(page, 12);
  await smoothScroll(page, -500, 15, 50);

  console.log('5. Recording College Principal Dashboard...');
  await loginUser(page, 'principal@dev.local', 'DevPass@123', 'http://localhost:5173/institution/Dev%20Test%20College/DEV-COLLEGE-001/dashboard');
  await captureFrame(page, 15);
  await showSidebarHover(page);
  await smoothScroll(page, 600, 15, 50);
  await captureFrame(page, 12);
  await smoothScroll(page, -600, 15, 50);
  await captureFrame(page, 15);

  await browser.close();
  console.log(`Captured ${frameIndex} frames. Rendering MP4 and WebP...`);

  // Build MP4 with ffmpeg at 10 fps
  const ffmpegCmdMp4 = `"${FFMPEG_PATH}" -y -framerate 10 -i "${FRAMES_DIR}\\frame_%05d.jpg" -c:v libx264 -pix_fmt yuv420p -crf 22 -preset medium "${OUTPUT_MP4}"`;
  console.log('Running ffmpeg for MP4...');
  execSync(ffmpegCmdMp4, { stdio: 'inherit' });

  // Copy to artifacts
  fs.copyFileSync(OUTPUT_MP4, ARTIFACTS_MP4);

  // Build WebP animated for markdown embedding
  const ffmpegCmdWebp = `"${FFMPEG_PATH}" -y -framerate 10 -i "${FRAMES_DIR}\\frame_%05d.jpg" -vf "scale=960:-1" -loop 0 "${OUTPUT_WEBP}"`;
  console.log('Running ffmpeg for WebP animation...');
  execSync(ffmpegCmdWebp, { stdio: 'inherit' });

  fs.copyFileSync(OUTPUT_WEBP, ARTIFACTS_WEBP);

  console.log('DONE!');
  console.log('MP4 Video saved to:', OUTPUT_MP4);
  console.log('WebP Video saved to:', OUTPUT_WEBP);
}

runTour().catch(err => {
  console.error('Tour failed:', err);
  process.exit(1);
});
