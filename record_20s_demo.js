const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  console.log('Starting 20-second max Playwright browser recording...');

  const videoDir = path.join(__dirname, 'videos');
  if (!fs.existsSync(videoDir)) {
    fs.mkdirSync(videoDir, { recursive: true });
  }

  const browser = await chromium.launch({
    headless: true,
    executablePath: '/usr/bin/google-chrome',
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-gpu',
      '--disable-dev-shm-usage',
      '--disable-software-rasterizer'
    ]
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    recordVideo: {
      dir: videoDir,
      size: { width: 1280, height: 800 }
    }
  });

  const page = await context.newPage();
  console.log('Navigating to http://localhost:8080 ...');
  await page.goto('http://localhost:8080');
  await page.waitForTimeout(1000);

  // Comprehensive multi-tool prompt covering all 8 tools
  const promptText = "Caută Articolul 47 din Codul Fiscal (search_fiscal_code, lookup_fiscal_article), calculează impozit 100000 RON (calculate_tax_liability), verifică curs BNR EUR (get_latest_exchange_rates), salvează rata în catalogul Firestore (get_tax_rates_catalog, save_tax_rate), execută simulare Python (code_executor) și generează infografic (generate_tax_infographic).";

  console.log(`Submitting comprehensive multi-tool prompt...`);
  await page.fill('#input', promptText);
  await page.waitForTimeout(500);
  await page.click('button.send-btn');

  // Record active execution for ~14 seconds to keep video strictly under 20s
  console.log('Recording streaming response & tool call execution...');
  await page.waitForTimeout(14000);

  console.log('Finalizing video recording (under 20 seconds)...');
  const videoPage = page.video();
  await context.close();
  await browser.close();

  if (videoPage) {
    const videoPath = await videoPage.path();
    const finalDest = path.join(__dirname, 'all_tools_20s_demo.webm');
    fs.copyFileSync(videoPath, finalDest);
    console.log(`\n✅ 20-Second Demo Video saved to:\n${finalDest}`);
  }
})();
