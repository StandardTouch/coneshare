/**
 * End-to-end e-sign flow with ~500-page PDF, range loading, dual signers, and verification.
 *
 * Run (stack must be up):
 *   cd e2e && npx playwright test esign-large-pdf-flow.spec.js --project=esign-e2e
 */
import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

const API_BASE = process.env.E2E_API_URL || 'http://localhost:8000/api/v1';
const COMPOSE = process.env.COMPOSE_CMD || 'COMPOSE_PROJECT_NAME=coneshare docker-compose';

const ARTIFACT_DIR = path.resolve(process.cwd(), '../artifacts/esign-e2e');

function dockerExecDjango(args) {
  return execSync(`${COMPOSE} exec -T backend python manage.py ${args}`, {
    encoding: 'utf8',
  }).trim();
}

function signerMeta(email) {
  return JSON.parse(dockerExecDjango(`get_signer_otp --email=${email}`));
}

async function obtainToken(request, email, password = 'password123') {
  const res = await request.post(`${API_BASE}/token/`, {
    data: { email, password },
  });
  expect(res.ok()).toBeTruthy();
  const body = await res.json();
  return body.access;
}

test.describe.configure({ mode: 'serial', timeout: 600_000 });

test.describe('E-sign large PDF flow', () => {
  /** @type {Record<string, unknown>} */
  let fixture;
  let requestId;
  let range206Count = 0;
  let pdfBytesTransferred = 0;

  test.beforeAll(async () => {
    try {
      execSync('docker ps', { stdio: 'pipe' });
    } catch {
      test.skip(true, 'Docker is not available in this environment');
    }
    fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
    const raw = dockerExecDjango('prepare_esign_e2e');
    fixture = JSON.parse(raw.split('\n').filter(Boolean).pop());
  });

  test('placement editor: Range loading, thumbnails, field placement', async ({ page, request }) => {
    range206Count = 0;
    pdfBytesTransferred = 0;

    page.on('response', async (response) => {
      const url = response.url();
      if (!url.includes('/esign/') || !url.includes('/pdf')) return;
      if (response.status() === 206) range206Count += 1;
      try {
        pdfBytesTransferred += (await response.body()).length;
      } catch {
        // ignore aborted bodies
      }
    });

    await page.goto('/login');
    await page.getByPlaceholder('you@company.com').fill(fixture.requester_email);
    await page.getByPlaceholder('••••••••').fill('password123');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible({ timeout: 60_000 });

    await page.goto(`/documents/${fixture.document_id}`);
    await page.getByRole('button', { name: 'Request Signature' }).click();
    await page.getByLabel(/Request Title/i).fill('E2E Large PDF Sign');
    await page.getByRole('button', { name: 'Add Signer' }).click();
    await page.locator('select').first().selectOption(fixture.signer1_id);
    await page.getByRole('button', { name: 'Add Signer' }).click();
    await page.locator('select').nth(1).selectOption(fixture.signer2_id);
    await page.getByRole('button', { name: 'Next' }).click();

    await expect(page.getByTestId('esign-thumbnail-sidebar')).toBeVisible({ timeout: 180_000 });
    await expect(page.getByTestId('esign-thumb-500')).toBeVisible({ timeout: 120_000 });

    await page.getByRole('button', { name: 'Jump to last page' }).click();
    await expect(page.locator('[data-page-number="500"]')).toBeVisible({ timeout: 120_000 });
    await page.getByText('Signature', { exact: true }).first().dragTo(page.locator('[data-page-number="500"]'));

    await page.getByRole('textbox', { name: 'Page number' }).fill('1');
    await page.getByRole('button', { name: 'Go' }).click();
    await page.getByText('Date', { exact: true }).first().dragTo(page.locator('[data-page-number="1"]'));

    await page.getByRole('textbox', { name: 'Page number' }).fill(String(fixture.landscape_page));
    await page.getByRole('button', { name: 'Go' }).click();
    await page.getByText('Date', { exact: true }).first().dragTo(
      page.locator(`[data-page-number="${fixture.landscape_page}"]`)
    );

    await page.screenshot({
      path: path.join(ARTIFACT_DIR, 'placement-last-page-thumbnails.png'),
    });

    await page.getByRole('button', { name: 'Save & Send' }).click();
    await expect(page).toHaveURL(/\/signatures/, { timeout: 120_000 });

    expect(range206Count).toBeGreaterThan(0);
    expect(pdfBytesTransferred).toBeLessThan(fixture.file_size_bytes * 0.35);

    const meta = JSON.parse(dockerExecDjango('get_latest_esign_request'));
    requestId = meta.id;
    expect(meta.status).toBe('sent');
  });

  test('PDF endpoint access control', async ({ playwright }) => {
    const { token: signerToken } = signerMeta(fixture.signer1_email);
    const requesterCtx = await playwright.request.newContext();
    const requesterToken = await obtainToken(requesterCtx, fixture.requester_email);

    const signer1Ctx = await playwright.request.newContext();
    const signer1Token = await obtainToken(signer1Ctx, fixture.signer1_email);
    const noOtp = await signer1Ctx.get(`${API_BASE}/esign/sign/${signerToken}/pdf/`, {
      headers: { Authorization: `Bearer ${signer1Token}` },
    });
    expect(noOtp.status()).toBe(403);

    const outsiderCtx = await playwright.request.newContext();
    const outsiderToken = await obtainToken(outsiderCtx, fixture.outsider_email);
    const outsiderTry = await outsiderCtx.get(`${API_BASE}/esign/sign/${signerToken}/pdf/`, {
      headers: { Authorization: `Bearer ${outsiderToken}` },
    });
    expect(outsiderTry.status()).toBe(403);

    const ownerPdf = await requesterCtx.get(
      `${API_BASE}/esign/documents/${fixture.document_id}/pdf/`,
      { headers: { Authorization: `Bearer ${requesterToken}` } }
    );
    expect(ownerPdf.ok()).toBeTruthy();
  });

  async function signAs(page, email) {
    const meta = signerMeta(email);
    await page.goto('/login');
    await page.getByPlaceholder('you@company.com').fill(email);
    await page.getByPlaceholder('••••••••').fill('password123');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();

    await page.goto(`/sign/${meta.token}`);
    await page.getByRole('button', { name: 'Request Verification Code' }).click();
    const otp = signerMeta(email);
    await page.getByPlaceholder('Enter 6-digit code').fill(otp.code);
    await page.getByRole('button', { name: 'Verify' }).click();

    await expect(page.getByTestId('esign-thumbnail-sidebar')).toBeVisible({ timeout: 180_000 });
    await page.screenshot({
      path: path.join(ARTIFACT_DIR, `signing-${email.replace('@', '_')}.png`),
    });

    const fields = page.locator('[data-testid^="esign-field-"]');
    const count = await fields.count();
    for (let i = 0; i < count; i += 1) {
      await fields.nth(i).click();
      const dialog = page.getByRole('dialog');
      if (await dialog.isVisible().catch(() => false)) {
        const canvas = dialog.locator('canvas');
        if (await canvas.isVisible().catch(() => false)) {
          const box = await canvas.boundingBox();
          if (box) {
            await page.mouse.move(box.x + 20, box.y + 20);
            await page.mouse.down();
            await page.mouse.move(box.x + 100, box.y + 40);
            await page.mouse.up();
          }
          await dialog.getByRole('button', { name: 'Save' }).click();
        }
      }
    }

    await page.getByRole('button', { name: 'Submit Signature' }).click();
    await expect(page).toHaveURL(/\/signatures/, { timeout: 120_000 });
  }

  test('signer one completes OTP and signs', async ({ page }) => {
    await signAs(page, fixture.signer1_email);
  });

  test('signer two completes OTP and signs', async ({ page }) => {
    await signAs(page, fixture.signer2_email);
  });

  test('verify signed PDF and portal download ACL', async ({ playwright }) => {
    await expect
      .poll(() => JSON.parse(dockerExecDjango('get_latest_esign_request')).status, {
        timeout: 300_000,
      })
      .toBe('completed');

    dockerExecDjango(
      `verify_esign_e2e --request-id=${requestId} --num-pages=${fixture.num_pages} --landscape-page=${fixture.landscape_page}`
    );

    const downloadPath = `${API_BASE}/esign/requests/${requestId}/download_signed/`;

    for (const email of [fixture.requester_email, fixture.signer1_email, fixture.signer2_email]) {
      const ctx = await playwright.request.newContext();
      const token = await obtainToken(ctx, email);
      const res = await ctx.get(downloadPath, {
        headers: { Authorization: `Bearer ${token}` },
      });
      expect(res.ok()).toBeTruthy();
    }

    const outsiderCtx = await playwright.request.newContext();
    const outsiderToken = await obtainToken(outsiderCtx, fixture.outsider_email);
    const denied = await outsiderCtx.get(downloadPath, {
      headers: { Authorization: `Bearer ${outsiderToken}` },
    });
    expect([403, 404]).toContain(denied.status());
  });
});
