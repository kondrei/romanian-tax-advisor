const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  console.log('Starting Playwright recording for 3 multi-tool prompts...');

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
  await page.waitForTimeout(2000);

  async function askQuestion(promptText, expectedToolTag) {
    console.log(`\n--- Asking: "${promptText}" ---`);
    await page.fill('#input', promptText);
    await page.waitForTimeout(600);
    await page.click('button.send-btn');

    console.log(`Waiting for agent response and tool call: ${expectedToolTag}...`);
    try {
      await page.waitForSelector(`.tool-tag:has-text("${expectedToolTag}")`, { timeout: 40000 });
      console.log(`✓ Detected tool call: ${expectedToolTag}`);
    } catch (err) {
      console.log(`Waiting for streaming completion...`);
      await page.waitForSelector('.copy-btn', { timeout: 30000 });
    }

    await page.waitForTimeout(3500);
  }

  // Prompt 1: RAG Search, Article Lookup & Tax Calculator
  await askQuestion(
    "Caută articole din Codul Fiscal (search_fiscal_code, Articolul 47 lookup_fiscal_article) și calculează impozitul de 1% pe venit pentru o microîntreprindere cu 100000 RON (calculate_tax_liability).",
    "calculate_tax_liability"
  );

  // Prompt 2: Exchange Rates & Firestore Tools
  await askQuestion(
    "Verifică cursul BNR EUR (get_latest_exchange_rates), consultă catalogul de taxe din Firestore (get_tax_rates_catalog) și salvează cota de impozit în baza de date (save_tax_rate).",
    "get_latest_exchange_rates"
  );

  // Prompt 3: Code Executor & Infographic Generator
  await askQuestion(
    "Execută o simulare în Python (code_executor) și generează o reprezentare vizuală sub formă de infografic pentru taxe PFA (generate_tax_infographic).",
    "generate_tax_infographic"
  );

  console.log('\nAll 3 prompts completed. Finalizing video recording...');
  await page.waitForTimeout(3000);

  const videoPage = page.video();
  await context.close();
  await browser.close();

  if (videoPage) {
    const videoPath = await videoPage.path();
    const finalDest = path.join(__dirname, 'all_8_tools_3prompts_demo.webm');
    fs.copyFileSync(videoPath, finalDest);
    console.log(`\n✅ 3-Prompt Demo Video saved to:\n${finalDest}`);
  }
})();
