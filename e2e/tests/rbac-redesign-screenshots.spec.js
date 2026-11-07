/**
 * RBAC redesign screenshot pack (max 12). Requires:
 *   backend migrate + seed_rbac_screenshots + create_test_data
 *   backend runserver :8000, frontend dev :5173
 */
import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const ARTIFACT_DIR = '/opt/cursor/artifacts';
const DEMO_DATAROOM_ID = process.env.RBAC_DEMO_DATAROOM_ID || '01M6VTTX2D7RYK5FN2CNPRAYMP';

async function login(page, email) {
  await page.goto('/login');
  await page.getByPlaceholder('you@company.com').fill(email);
  await page.getByPlaceholder('••••••••').fill('password123');
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible({ timeout: 30000 });
}

test.beforeAll(() => {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
});

test('01 roles list', async ({ page }) => {
  await login(page, 'admin@coneshare.com');
  await page.goto('/admin/roles');
  await expect(page.getByRole('heading', { name: /Roles/i })).toBeVisible();
  await page.screenshot({ path: path.join(ARTIFACT_DIR, '01-roles-list.png'), fullPage: true });
});

test('02 admin role edit', async ({ page }) => {
  await login(page, 'admin@coneshare.com');
  await page.goto('/admin/roles');
  const adminRow = page.locator('table tbody tr', { hasText: 'Admin' }).first();
  await adminRow.getByRole('link').first().click();
  await page.waitForURL(/\/admin\/roles\//);
  await expect(page.getByRole('heading', { name: /Admin/i })).toBeVisible({ timeout: 15000 });
  await page.screenshot({ path: path.join(ARTIFACT_DIR, '02-admin-role-edit.png'), fullPage: true });
});

test('03 limited role edit', async ({ page }) => {
  await login(page, 'admin@coneshare.com');
  await page.goto('/admin/roles');
  const limitedRow = page.locator('table tbody tr', { hasText: 'Limited' }).first();
  await limitedRow.getByRole('link').first().click();
  await page.screenshot({ path: path.join(ARTIFACT_DIR, '03-limited-role-edit.png'), fullPage: true });
});

test('04 admin settings without retired toggles', async ({ page }) => {
  await login(page, 'admin@coneshare.com');
  await page.goto('/admin/settings');
  await expect(page.getByRole('heading', { name: /Settings/i })).toBeVisible();
  await expect(page.getByText('AUTOMATION_ENABLED')).toHaveCount(0);
  await page.screenshot({ path: path.join(ARTIFACT_DIR, '04-admin-settings.png'), fullPage: true });
});

test('05 limited sidebar', async ({ page }) => {
  await login(page, 'limited@coneshare.com');
  await page.goto('/dashboard');
  await page.screenshot({ path: path.join(ARTIFACT_DIR, '05-limited-sidebar.png'), fullPage: true });
});

test('06 limited dataroom', async ({ page }) => {
  await login(page, 'limited@coneshare.com');
  await page.goto(`/datarooms/${DEMO_DATAROOM_ID}`);
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: path.join(ARTIFACT_DIR, '06-limited-dataroom.png'), fullPage: true });
});

test('07 manager dataroom with signature pdf', async ({ page }) => {
  await login(page, 'manager@coneshare.com');
  await page.goto(`/datarooms/${DEMO_DATAROOM_ID}`);
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: path.join(ARTIFACT_DIR, '07-manager-pdf-signature-visible.png'), fullPage: true });
});

test('08 limited pdf no signature', async ({ page }) => {
  await login(page, 'limited@coneshare.com');
  await page.goto(`/datarooms/${DEMO_DATAROOM_ID}`);
  await page.waitForLoadState('networkidle');
  const pdfLink = page.getByText('Signature Demo.pdf');
  if (await pdfLink.count()) {
    await pdfLink.first().click();
  }
  await page.screenshot({ path: path.join(ARTIFACT_DIR, '08-limited-pdf-no-signature.png'), fullPage: true });
});
