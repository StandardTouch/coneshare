/**
 * RBAC unified UI screenshot suite (run against local dev stack with seeded users).
 *
 *   COMPOSE_PROJECT_NAME=coneshare docker-compose up -d
 *   cd e2e && npx playwright test rbac-unified-screenshots.spec.js
 */
import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const ARTIFACT_DIR = '/opt/cursor/artifacts';

test.beforeAll(() => {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
});

test.describe('RBAC unified admin screenshots', () => {
  test.use({ storageState: 'playwright/.auth/admin.json' });

  test('roles list and flows', async ({ page }) => {
    await page.goto('/admin/roles');
    await expect(page.getByRole('heading', { name: 'Roles' })).toBeVisible();
    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'rbac-roles-list.png'), fullPage: true });

    const editLink = page.locator('table tbody tr').first().getByRole('link');
    if (await editLink.count()) {
      await editLink.click();
      await page.screenshot({ path: path.join(ARTIFACT_DIR, 'rbac-role-edit.png'), fullPage: true });
    }

    await page.goto('/admin/roles');
    await page.getByRole('button', { name: /Create role/i }).click();
    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'rbac-create-role.png') });

    await page.goto('/admin/users');
    await page.getByRole('button', { name: /Add user/i }).click();
    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'rbac-user-role-dropdown.png'), fullPage: true });
  });
});
