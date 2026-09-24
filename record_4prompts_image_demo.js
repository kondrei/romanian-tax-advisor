const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  console.log('Starting Playwright recording for 4 prompts (including image generation)...');

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

  // Prompt 1: RAG Search, Article Lookup & Tax Calculator
  await askQuestion(
    "Caută articole din Codul Fiscal (search_fiscal_code, Articolul 47 lookup_fiscal_article) și calculează impozitul de 1% pe venit pentru o microîntreprindere cu 100000 RON (calculate_tax_liability).",
    12000
  );

  // Prompt 2: Exchange Rates & Firestore Catalog Tools
  await askQuestion(
    "Verifică cursul BNR EUR (get_latest_exchange_rates), consultă catalogul de taxe din Firestore (get_tax_rates_catalog) și salvează cota de impozit în baza de date (save_tax_rate).",
    12000
  );

  // Prompt 3: Python Code Simulation
  await askQuestion(
    "Execută o simulare în Python (code_executor) pentru calculul comparativ al contribuțiilor CASS și CAS la PFA vs SRL.",
    12000
  );

  // Prompt 4: IMAGE GENERATION PROMPT (generate_tax_infographic)
  await askQuestion(
    "Generează o imagine sugestivă sub formă de infografic colorat cu pragurile și cotele de impozitare PFA 2026 (generate_tax_infographic).",
    18000
  );

  console.log('\nAll 4 prompts (including image generation) completed. Finalizing video recording...');
  await page.waitForTimeout(3000);

  const videoPage = page.video();
  await context.close();
  await browser.close();

  if (videoPage) {
    const videoPath = await videoPage.path();
    const finalDest = path.join(__dirname, 'all_tools_with_image_demo.webm');
    fs.copyFileSync(videoPath, finalDest);
    console.log(`\n✅ 4-Prompt Demo Video (with Image) saved to:\n${finalDest}`);
  }
})();
