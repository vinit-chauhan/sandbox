#!/usr/bin/env node
/**
 * Full user flow test for Local LLM Chat with screenshots at each step.
 * Run: node browser-test-full-flow.mjs
 */
import { chromium } from 'playwright';
import { mkdirSync, existsSync } from 'fs';
import { join } from 'path';

const BASE = 'http://localhost';
const TEST_FILE = '/tmp/test-document.txt';
const SCREENSHOT_DIR = '/tmp/llm-chat-screenshots';

const report = {
  steps: [],
  screenshots: [],
  layoutCorrect: false,
  uploadWorked: false,
  chatStreamed: false,
  assistantResponse: null,
  visualBugs: [],
  errors: []
};

function step(name, fn) {
  report.steps.push({ name, status: 'pending' });
  return fn;
}

async function main() {
  mkdirSync(SCREENSHOT_DIR, { recursive: true });

  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    page.setViewportSize({ width: 1280, height: 800 });

    // 1. Navigate and snapshot initial page
    report.steps.push({ name: 'Navigate to localhost', status: 'in_progress' });
    await page.goto(BASE, { waitUntil: 'networkidle', timeout: 10000 });
    await page.screenshot({ path: join(SCREENSHOT_DIR, '01-initial-page.png') });
    report.screenshots.push('01-initial-page.png');
    report.steps[report.steps.length - 1].status = 'done';

    // 2. Verify layout
    report.steps.push({ name: 'Verify two-column layout', status: 'in_progress' });
    const aside = page.locator('aside');
    const main = page.locator('main');
    const hasAside = (await aside.count()) > 0;
    const hasMain = (await main.count()) > 0;
    const header = await page.getByText('Local LLM Chat', { exact: true }).count() > 0;
    const dropZone = await page.getByText('Drop files here').count() > 0;
    const startConv = await page.getByText('Start a conversation').count() > 0;
    const textarea = await page.locator('textarea').count() > 0;
    report.layoutCorrect = hasAside && hasMain && header && dropZone && startConv && textarea;
    await page.screenshot({ path: join(SCREENSHOT_DIR, '02-layout-verified.png') });
    report.screenshots.push('02-layout-verified.png');
    report.steps[report.steps.length - 1].status = 'done';

    // 3. Upload file via hidden file input
    report.steps.push({ name: 'Upload test-document.txt', status: 'in_progress' });
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(TEST_FILE);
    // Wait for upload to complete (progress bar disappears, document appears)
    await page.waitForTimeout(2000);
    const docVisible = await page.getByText('test-document.txt', { exact: true }).count() > 0;
    report.uploadWorked = docVisible;
    await page.screenshot({ path: join(SCREENSHOT_DIR, '03-after-upload.png') });
    report.screenshots.push('03-after-upload.png');
    report.steps[report.steps.length - 1].status = docVisible ? 'done' : 'failed';

    // 4. Snapshot showing document in sidebar
    await page.screenshot({ path: join(SCREENSHOT_DIR, '04-document-in-sidebar.png') });
    report.screenshots.push('04-document-in-sidebar.png');

    // 5. Ensure document checkbox is checked
    report.steps.push({ name: 'Ensure document checked', status: 'in_progress' });
    const row = page.locator('div.group:has-text("test-document.txt")');
    const checkbox = row.locator('input[type="checkbox"]').first();
    if ((await checkbox.count()) > 0) {
      const checked = await checkbox.isChecked();
      if (!checked) await checkbox.check();
    }
    await page.waitForTimeout(500);
    await page.screenshot({ path: join(SCREENSHOT_DIR, '05-checkbox-checked.png') });
    report.screenshots.push('05-checkbox-checked.png');
    report.steps[report.steps.length - 1].status = 'done';

    // 6. Type question and send
    report.steps.push({ name: 'Type question and send', status: 'in_progress' });
    const chatTextarea = page.locator('textarea[placeholder*="Type a message"]');
    await chatTextarea.fill('How tall is the Eiffel Tower according to the document?');
    await page.waitForTimeout(400);
    await page.getByRole('button', { name: 'Send' }).click();
    await page.waitForTimeout(1500);
    await page.screenshot({ path: join(SCREENSHOT_DIR, '06-message-sent.png') });
    report.screenshots.push('06-message-sent.png');
    report.steps[report.steps.length - 1].status = 'done';

    // 7-8. Wait ~35 seconds, check periodically
    report.steps.push({ name: 'Wait for model response', status: 'in_progress' });
    for (let i = 0; i < 7; i++) {
      await page.waitForTimeout(5000);
      await page.screenshot({ path: join(SCREENSHOT_DIR, `07-wait-${i + 1}.png`) });
    }
    report.steps[report.steps.length - 1].status = 'done';

    // 9. Final snapshot - get assistant response text
    const assistantBubbles = page.locator('div.flex.justify-start div.rounded-2xl');
    const lastBubble = assistantBubbles.last();
    const text = await lastBubble.textContent().catch(() => null);
    if (text && text.trim().length > 10 && !text.includes('animate-bounce')) {
      report.chatStreamed = true;
      report.assistantResponse = text.trim();
    }
    await page.screenshot({ path: join(SCREENSHOT_DIR, '09-final-conversation.png') });
    report.screenshots.push('09-final-conversation.png');

  } catch (err) {
    report.errors.push(err.message);
  } finally {
    if (browser) await browser.close();
  }

  // Output report
  console.log(JSON.stringify({
    ...report,
    screenshotDir: SCREENSHOT_DIR,
    screenshotList: report.screenshots
  }, null, 2));
}

main();
