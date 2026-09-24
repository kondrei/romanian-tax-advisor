const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  console.log('Starting Playwright browser recording for 4 prompts covering all 8 tools + image generation...');

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

  async function askQuestion(promptText, delayMs = 12000) {
    console.log(`\n--- Asking: "${promptText}" ---`);
    await page.fill('#input', promptText);
    await page.waitForTimeout(600);
    await page.click('button.send-btn');
    console.log(`Recording response streaming for ${delayMs / 1000}s...`);
    await page.waitForTimeout(delayMs);
  }

  // Prompt 1: RAG Search & Article Lookup (search_fiscal_code, lookup_fiscal_article)
  await askQuestion(
    "Caută în Codul Fiscal articole despre microîntreprinderi (search_fiscal_code) și afișează conținutul complet al Articolului 47 (lookup_fiscal_article).",
    12000
  );

  // Prompt 2: Tax Liability Calculation & Live BNR Exchange Rate (calculate_tax_liability, get_latest_exchange_rates)
  await askQuestion(
    "Calculează impozitul pe venit de 100000 RON pentru o microîntreprindere (calculate_tax_liability) și verifică cursul BNR actual pentru EUR (get_latest_exchange_rates).",
    12000
  );

  // Prompt 3: Firestore Catalog Query, Tax Rate Storage & Python Code Simulation (get_tax_rates_catalog, save_tax_rate, code_executor)
  await askQuestion(
    "Consultă catalogul de taxe din Firestore (get_tax_rates_catalog), salvează cota de 1% în baza de date (save_tax_rate) și execută o simulare Python pentru contribuții (code_executor).",
    14000
  );

  // Prompt 4: Infographic Image Generation (generate_tax_infographic)
  await askQuestion(
    "Generează o imagine sugestivă sub formă de infografic colorat pentru taxe PFA 2026 (generate_tax_infographic).",
    18000
  );

  console.log('\nAll 4 prompts (including image generation) completed. Finalizing video recording...');
  await page.waitForTimeout(3000);

  const videoPage = page.video();
  await context.close();
  await browser.close();

  if (videoPage) {
    const videoPath = await videoPage.path();
    const finalDest = path.join(__dirname, 'all_8_tools_and_image_demo.webm');
    fs.copyFileSync(videoPath, finalDest);
    console.log(`\n✅ Complete Demo Video (All 8 Tools & Image Generation) saved to:\n${finalDest}`);
  }
})();
