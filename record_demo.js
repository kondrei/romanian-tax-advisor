const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  console.log('Starting Playwright browser recording...');

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
      '--disable-software-rasterizer',
      '--no-zygote'
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

  // Helper to type prompt, submit, and wait for agent answer & tool tag
  async function askQuestion(promptText, expectedToolTag) {
    console.log(`\n--- Asking: "${promptText}" ---`);
    await page.fill('#input', promptText);
    await page.waitForTimeout(800);
    await page.click('button.send-btn');

    // Wait for the stream to complete and the tool tag or copy button to appear
    console.log(`Waiting for agent response and tool call: ${expectedToolTag}...`);
    try {
      await page.waitForSelector(`.tool-tag:has-text("${expectedToolTag}")`, { timeout: 45000 });
      console.log(`✓ Detected tool call: ${expectedToolTag}`);
    } catch (err) {
      console.log(`Warning: tool tag selector timed out, waiting for general completion...`);
      await page.waitForSelector('.copy-btn', { timeout: 30000 });
    }

    await page.waitForTimeout(4000); // Pause for clear visual recording
  }

  // Question 1: Tax Calculator Tool (calculate_tax_liability)
  await askQuestion(
    "Calculare impozit pe venit de 100000 RON pentru o microîntreprindere cu 1 angajat",
    "calculate_tax_liability"
  );

  // Question 2: Tax Code Search Tool (search_romanian_tax_code)
  await askQuestion(
    "Ce prevederi speciale conține Articolul 47 din Codul Fiscal?",
    "search_romanian_tax_code"
  );

  // Question 3: Tax Infographic Generator Tool (generate_tax_infographic)
  await askQuestion(
    "Generează o reprezentare vizuală sub formă de infografic pentru taxe PFA 2026",
    "generate_tax_infographic"
  );

  console.log('\nAll demo interactions completed. Finalizing video...');
  await page.waitForTimeout(3000);

  const videoPage = page.video();
  await context.close();
  await browser.close();

  if (videoPage) {
    const videoPath = await videoPage.path();
    const finalDest = path.join(__dirname, 'agent_tools_demo.webm');
    fs.copyFileSync(videoPath, finalDest);
    console.log(`\n✅ Demo Video successfully recorded and saved to:\n${finalDest}`);
  }
})();
