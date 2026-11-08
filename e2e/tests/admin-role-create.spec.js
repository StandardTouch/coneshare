/**
 * Admin custom role create flow (UI matches AdminRolesPage modal).
 */
import { test, expect } from '@playwright/test';
import path from 'path';

const ARTIFACT_DIR = '/opt/cursor/artifacts';

async function loginAdmin(page) {
  await page.goto('/login');
  await page.getByPlaceholder('you@company.com').fill('admin@coneshare.com');
  await page.getByPlaceholder('••••••••').fill('password123');
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible({ timeout: 30000 });
}

test('admin can create custom role without sending slug', async ({ page }) => {
  const roleName = `E2E Role ${Date.now()}`;

  await loginAdmin(page);
  await page.goto('/admin/roles');
  await expect(page.getByRole('heading', { name: /Roles/i })).toBeVisible();

  await page.getByRole('button', { name: /Create role/i }).click();
  await page.getByPlaceholder('Name').fill(roleName);
  await page.getByPlaceholder('Description').fill('Created from Playwright');
  await page.getByRole('button', { name: /^Create$/i }).click();

  await page.waitForURL(/\/admin\/roles\/.+/);
  await expect(page).toHaveURL(/\/admin\/roles\/[^/]+$/);
  await page.screenshot({
    path: path.join(ARTIFACT_DIR, 'admin-role-create-success.png'),
    fullPage: true,
  });
});
