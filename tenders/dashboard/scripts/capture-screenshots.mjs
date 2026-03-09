import puppeteer from 'puppeteer-core';
import fs from 'node:fs/promises';
import path from 'node:path';

const outDir = '/Users/emirkoc/.openclaw/workspace/tenders/dashboard/screenshots';
await fs.mkdir(outDir, { recursive: true });

const browser = await puppeteer.launch({
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: true,
  defaultViewport: { width: 1440, height: 920 },
  args: ['--disable-gpu', '--hide-scrollbars', '--no-sandbox']
});

const page = await browser.newPage();
await page.goto('http://localhost:3099', { waitUntil: 'networkidle2' });
await new Promise(r => setTimeout(r, 1500));
await page.screenshot({ path: path.join(outDir, 'dashboard-karar-masasi-puppeteer.png'), fullPage: true });

await page.evaluate(() => {
  const btn = [...document.querySelectorAll('button')].find(b => /Arşiv/.test(b.textContent || ''));
  if (btn) btn.click();
});
await new Promise(r => setTimeout(r, 1200));
await page.screenshot({ path: path.join(outDir, 'dashboard-arsiv-red-puppeteer.png'), fullPage: true });

await browser.close();
console.log('OK');
