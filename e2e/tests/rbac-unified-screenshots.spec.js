/**
 * RBAC unified UI + enforcement screenshots (local stack).
 *
 *   # terminal 1 — backend
 *   cd backend && export SECRET_KEY=... DATABASE_URL=... REDIS_URL=... && python manage.py runserver 0.0.0.0:8000
 *   # terminal 2 — frontend
 *   cd frontend && VITE_DEV_API_TARGET=http://127.0.0.1:8000 npm run dev
 *   # seed once
 *   python manage.py seed_rbac_demo
 *   cd e2e && npx playwright test rbac-unified-screenshots.spec.js --project=chromium --config=playwright.rbac.config.js
 */
import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const ARTIFACT_DIR = '/opt/cursor/artifacts';
const PASSWORD = 'password123';

const USERS = {
  admin: 'admin@rbac.demo',
  viewer: 'viewer@rbac.demo',
  contributor: 'contributor@rbac.demo',
  custom: 'custom@rbac.demo',
};

test.beforeAll(() => {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
});

async function login(page, email) {
  await page.goto('/login');
  await page.getByPlaceholder('you@company.com').fill(email);
  await page.getByPlaceholder('••••••••').fill(PASSWORD);
  await page.getByRole('button', { name: /Sign In/i }).click();
  await expect(page.getByRole('link', { name: 'Documents' })).toBeVisible({ timeout: 30_000 });
}

function demoMeta() {
  try {
    const raw = fs.readFileSync(path.join(ARTIFACT_DIR, 'rbac-demo-meta.json'), 'utf8');
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

async function screenshotApiResult(page, label, status, body, filename) {
  await page.setContent(
    `<body style="font-family:system-ui;padding:2rem"><h1>${label}</h1><p><strong>HTTP ${status}</strong></p><pre>${body}</pre></body>`
  );
  await page.screenshot({ path: path.join(ARTIFACT_DIR, filename), fullPage: true });
}

async function authRequest(page, method, url, data) {
  const token = await page.evaluate(() => localStorage.getItem('access_token'));
  return page.request.fetch(`http://127.0.0.1:8000${url}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    data: data ? JSON.stringify(data) : undefined,
  });
}

async function openDemoDataroom(page) {
  const id = demoMeta().dataroom_id;
  if (id) {
    await page.goto(`/datarooms/${id}`);
    return;
  }
  await page.goto('/datarooms');
  await page.getByText('RBAC Demo Room').first().click();
  await page.waitForURL(/\/datarooms\//);
}

test.describe('RBAC admin + enforcement screenshots', () => {
  test('admin roles UI', async ({ page }) => {
    await login(page, USERS.admin);
    await page.goto('/admin/roles');
    await expect(page.getByRole('heading', { name: 'Roles' })).toBeVisible({ timeout: 15_000 });
    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'rbac-roles-list.png'), fullPage: true });

    const editLink = page.locator('table tbody tr').first().getByRole('link');
    await editLink.click();
    await page.waitForURL(/\/admin\/roles\//);
    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'rbac-role-edit.png'), fullPage: true });

    await page.goto('/admin/roles');
    await page.getByRole('button', { name: /Create role/i }).click();
    await page.getByPlaceholder(/Name/i).fill('Screenshot Custom');
    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'rbac-create-role.png') });

    await page.goto('/admin/users');
    await page.getByRole('button', { name: /Add User/i }).click();
    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'rbac-user-role-dropdown.png'), fullPage: true });
  });

  test('viewer enforcement', async ({ page }) => {
    await login(page, USERS.viewer);
    await page.goto('/datarooms');
    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'rbac-viewer-datarooms-list.png'), fullPage: true });
    const createResp = await authRequest(page, 'POST', '/api/v1/datarooms/', { name: 'Viewer Created Room' });
    await screenshotApiResult(
      page,
      'Viewer create dataroom',
      createResp.status(),
      await createResp.text(),
      'rbac-viewer-create-dataroom-403.png'
    );
    await openDemoDataroom(page);
    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'rbac-viewer-dataroom-readonly.png'), fullPage: true });
    const meta = demoMeta();
    if (meta.admin_dataroom_document_id) {
      const delResp = await authRequest(page, 'DELETE', `/api/v1/dataroom-documents/${meta.admin_dataroom_document_id}/`);
      await screenshotApiResult(
        page,
        'Viewer delete others file',
        delResp.status(),
        await delResp.text(),
        'rbac-viewer-delete-others-403.png'
      );
    }
  });

  test('contributor enforcement', async ({ page }) => {
    await login(page, USERS.contributor);
    await openDemoDataroom(page);
    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'rbac-contributor-dataroom.png'), fullPage: true });
    const meta = demoMeta();
    if (meta.admin_dataroom_document_id) {
      const resp = await authRequest(page, 'PATCH', `/api/v1/dataroom-documents/${meta.admin_dataroom_document_id}/`, {
        name: 'renamed-by-contributor.pdf',
      });
      await screenshotApiResult(
        page,
        'Contributor rename others file',
        resp.status(),
        await resp.text(),
        'rbac-contributor-rename-others-403.png'
      );
    }
  });

  test('custom role enforcement', async ({ page }) => {
    await login(page, USERS.custom);
    await page.goto('/datarooms');
    await page.screenshot({
      path: path.join(ARTIFACT_DIR, 'rbac-custom-create-dataroom.png'),
      fullPage: true,
    });
    await openDemoDataroom(page);
    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'rbac-custom-dataroom-with-upload.png'), fullPage: true });
    const createResp = await authRequest(page, 'POST', '/api/v1/datarooms/', { name: 'Custom Created Room' });
    await screenshotApiResult(
      page,
      'Custom role create dataroom (granted)',
      createResp.status(),
      await createResp.text(),
      'rbac-custom-create-dataroom-api.png'
    );
  });
});
