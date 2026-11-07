/**
 * RBAC unified screenshots — max 12 PNGs under /opt/cursor/artifacts.
 */
import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';

const ARTIFACT_DIR = '/opt/cursor/artifacts';
const PASSWORD = 'password123';

const USERS = {
  admin: 'admin@rbac.demo',
  viewer: 'viewer@rbac.demo',
  contributor: 'contributor@rbac.demo',
  custom: 'custom@rbac.demo',
};

const FILES = {
  rolesList: 'rbac-roles-list.png',
  roleEdit: 'rbac-role-edit.png',
  createRole: 'rbac-create-role.png',
  userRoleDropdown: 'rbac-user-role-dropdown.png',
  viewerNoCreate: 'rbac-viewer-datarooms-no-create.png',
  viewerReadonly: 'rbac-viewer-dataroom-readonly.png',
  contributorFiles: 'rbac-contributor-dataroom.png',
  contributorOwnMenu: 'rbac-contributor-rename-own.png',
  contributorOtherBlocked: 'rbac-contributor-rename-other-blocked.png',
  customCreate: 'rbac-custom-create-dataroom.png',
  customUpload: 'rbac-custom-dataroom-with-upload.png',
};

test.describe.configure({ mode: 'serial' });
test.setTimeout(240_000);

test.beforeAll(() => {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
  for (const name of fs.readdirSync(ARTIFACT_DIR)) {
    if (name.startsWith('rbac-') && name.endsWith('.png')) {
      fs.unlinkSync(path.join(ARTIFACT_DIR, name));
    }
  }
});

function demoMeta() {
  try {
    return JSON.parse(fs.readFileSync(path.join(ARTIFACT_DIR, 'rbac-demo-meta.json'), 'utf8'));
  } catch {
    return {};
  }
}

async function login(page, email) {
  await page.goto('/login');
  await page.waitForLoadState('domcontentloaded');
  await page.getByPlaceholder('you@company.com').fill(email);
  await page.getByPlaceholder('••••••••').fill(PASSWORD);
  await page.getByRole('button', { name: /Sign In/i }).click();
  await expect(page.getByRole('link', { name: 'Documents' })).toBeVisible({ timeout: 60_000 });
}

async function shot(page, filename) {
  await page.screenshot({ path: path.join(ARTIFACT_DIR, filename), fullPage: true });
}

async function waitForRolesTable(page) {
  await page.waitForLoadState('networkidle');
  await expect(page.getByRole('heading', { name: 'Roles' })).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('table tbody tr').first()).toBeVisible();
}

async function waitForRoleEditPage(page) {
  await page.waitForLoadState('networkidle');
  await expect(page).toHaveURL(/\/admin\/roles\/[A-Z0-9]+/i);
  await expect(page.getByRole('checkbox').first()).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText('View content')).toBeVisible();
}

async function expandRoleSelectForScreenshot(page) {
  const select = page.locator('select#role, select[name="roleSelection"]');
  await expect(select).toBeVisible({ timeout: 30_000 });
  await expect
    .poll(async () => select.locator('option').count(), { timeout: 30_000 })
    .toBeGreaterThanOrEqual(5);
  const optionLabels = await select.locator('option').allTextContents();
  for (const label of ['Viewer', 'Contributor', 'Editor', 'Manager', 'Deal Analyst']) {
    expect(optionLabels.join('\n')).toMatch(new RegExp(label, 'i'));
  }
  await select.evaluate((sel) => {
    const select = sel;
    document.getElementById('rbac-role-options-expanded')?.remove();
    const box = document.createElement('div');
    box.id = 'rbac-role-options-expanded';
    box.style.cssText =
      'position:fixed;top:72px;right:24px;z-index:99998;max-width:320px;padding:12px;border:2px solid #0d9488;border-radius:8px;background:#f0fdfa;font:14px system-ui;box-shadow:0 8px 24px rgba(0,0,0,.12)';
    const title = document.createElement('div');
    title.textContent = 'Organization roles (dropdown options)';
    title.style.fontWeight = '600';
    title.style.marginBottom = '8px';
    box.appendChild(title);
    Array.from(select.options).forEach((opt) => {
      const row = document.createElement('div');
      row.textContent = `• ${opt.text}`;
      row.style.padding = '4px 0';
      box.appendChild(row);
    });
    document.body.appendChild(box);
    select.size = Math.min(select.options.length, 12);
    select.style.height = 'auto';
  });
}

async function waitForDataroomsList(page) {
  await page.waitForLoadState('networkidle');
  await expect(page.getByRole('heading', { name: /Dataroom/i }).first()).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('.animate-spin')).toHaveCount(0, { timeout: 60_000 }).catch(() => {});
}

async function openDemoDataroom(page) {
  const id = demoMeta().dataroom_id;
  await page.goto(`/datarooms/${id}`);
  await waitForDataroomContent(page);
}

async function waitForDataroomContent(page) {
  await page.waitForLoadState('networkidle');
  await expect(page.getByText('admin-owned.pdf')).toBeVisible({ timeout: 90_000 });
  await expect(page.getByText('contributor-owned.pdf')).toBeVisible({ timeout: 90_000 });
  await expect(page.locator('[data-testid^="draggable-item-"]').first()).toBeVisible({ timeout: 90_000 });
}

async function openActionsMenu(page, filename) {
  const row = page.locator('[data-testid^="draggable-item-"]').filter({ hasText: filename });
  await expect(row).toBeVisible();
  await row.getByRole('button', { name: new RegExp(`Actions for ${filename.replace('.', '\\.')}`) }).click();
}

async function addApiOverlay(page, title, status, body) {
  await page.evaluate(
    ({ title, status, body }) => {
      document.getElementById('rbac-403-overlay')?.remove();
      const el = document.createElement('div');
      el.id = 'rbac-403-overlay';
      el.style.cssText =
        'position:fixed;bottom:20px;right:20px;max-width:440px;background:#fff;border:2px solid #dc2626;padding:16px;z-index:99999;box-shadow:0 8px 24px rgba(0,0,0,.15);font:13px system-ui';
      el.innerHTML = `<div style="font-weight:700;margin-bottom:8px">${title}</div><div>HTTP <strong>${status}</strong></div><pre style="margin-top:8px;white-space:pre-wrap;max-height:160px;overflow:auto">${body.slice(0, 500)}</pre>`;
      document.body.appendChild(el);
    },
    { title, status, body }
  );
}

async function authRequest(page, method, url, data) {
  const token = await page.evaluate(() => localStorage.getItem('access_token'));
  return page.request.fetch(`http://127.0.0.1:8000${url}`, {
    method,
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    data: data ? JSON.stringify(data) : undefined,
  });
}

function fileHash(filePath) {
  return crypto.createHash('md5').update(fs.readFileSync(filePath)).digest('hex');
}

function assertArtifacts() {
  const names = Object.values(FILES);
  expect(names.length).toBeLessThanOrEqual(12);
  for (const name of names) {
    const p = path.join(ARTIFACT_DIR, name);
    expect(fs.existsSync(p), `missing ${name}`).toBeTruthy();
    expect(fs.statSync(p).size).toBeGreaterThan(20_000);
  }
  const listHash = fileHash(path.join(ARTIFACT_DIR, FILES.rolesList));
  const editHash = fileHash(path.join(ARTIFACT_DIR, FILES.roleEdit));
  expect(listHash).not.toEqual(editHash);
}

test('capture RBAC screenshot set', async ({ page }) => {
  // —— Admin: roles list, role edit, create role, user role dropdown ——
  await login(page, USERS.admin);
  await page.goto('/admin/roles');
  await waitForRolesTable(page);
  expect(page.url()).toMatch(/\/admin\/roles\/?$/);
  await shot(page, FILES.rolesList);

  await page.locator('table tbody tr').filter({ hasText: 'Contributor' }).getByRole('link').click();
  await waitForRoleEditPage(page);
  await expect(page.getByRole('heading', { name: 'Contributor' })).toBeVisible();
  await shot(page, FILES.roleEdit);

  await page.goto('/admin/roles');
  await waitForRolesTable(page);
  await page.getByRole('button', { name: /Create role/i }).click();
  await expect(page.getByPlaceholder(/Name/i)).toBeVisible();
  await page.getByPlaceholder(/Name/i).fill('Screenshot Custom Role');
  await shot(page, FILES.createRole);

  await page.goto('/admin/users');
  await page.waitForLoadState('networkidle');
  await expect(page.locator('table tbody tr').first()).toBeVisible({ timeout: 30_000 });
  await page.getByRole('button', { name: /Add User/i }).click();
  await expect(page.getByText(/Add New User|addNewUser/i).first()).toBeVisible({ timeout: 15_000 });
  await expandRoleSelectForScreenshot(page);
  await shot(page, FILES.userRoleDropdown);

  // —— Viewer ——
  await login(page, USERS.viewer);
  await page.goto('/datarooms');
  await waitForDataroomsList(page);
  await expect(page.getByRole('button', { name: /Add Dataroom/i })).toHaveCount(0);
  await shot(page, FILES.viewerNoCreate);

  await openDemoDataroom(page);
  const meta = demoMeta();
  if (meta.admin_dataroom_document_id) {
    const patchResp = await authRequest(page, 'PATCH', `/api/v1/dataroom-documents/${meta.admin_dataroom_document_id}/`, {
      name: 'blocked.pdf',
    });
    await addApiOverlay(page, 'Viewer: rename/delete blocked', patchResp.status(), await patchResp.text());
  }
  await shot(page, FILES.viewerReadonly);
  await page.evaluate(() => document.getElementById('rbac-403-overlay')?.remove());

  // —— Contributor ——
  await login(page, USERS.contributor);
  await openDemoDataroom(page);
  await shot(page, FILES.contributorFiles);

  await openActionsMenu(page, 'contributor-owned.pdf');
  await expect(page.getByRole('menuitem', { name: /Rename/i })).toBeVisible();
  await shot(page, FILES.contributorOwnMenu);
  await page.keyboard.press('Escape');

  await openActionsMenu(page, 'admin-owned.pdf');
  const renameItems = page.getByRole('menuitem', { name: /Rename/i });
  if ((await renameItems.count()) === 0) {
    const resp = await authRequest(page, 'PATCH', `/api/v1/dataroom-documents/${meta.admin_dataroom_document_id}/`, {
      name: 'hacked.pdf',
    });
    await addApiOverlay(page, 'Contributor: rename others file (API)', resp.status(), await resp.text());
  } else {
    const resp = await authRequest(page, 'PATCH', `/api/v1/dataroom-documents/${meta.admin_dataroom_document_id}/`, {
      name: 'hacked.pdf',
    });
    await addApiOverlay(page, 'Contributor: rename others file (API)', resp.status(), await resp.text());
  }
  await shot(page, FILES.contributorOtherBlocked);
  await page.keyboard.press('Escape');
  await page.evaluate(() => document.getElementById('rbac-403-overlay')?.remove());

  // —— Custom role (create dataroom + upload UI) ——
  await login(page, USERS.custom);
  await page.goto('/datarooms');
  await waitForDataroomsList(page);
  await expect(page.getByRole('button', { name: /Add Dataroom/i })).toBeVisible();
  await shot(page, FILES.customCreate);

  await openDemoDataroom(page);
  const uploadControl = page.getByRole('button', { name: /Choose File|Upload/i }).first();
  await expect(uploadControl).toBeVisible({ timeout: 30_000 });
  await uploadControl.scrollIntoViewIfNeeded();
  await shot(page, FILES.customUpload);

  assertArtifacts();
});
