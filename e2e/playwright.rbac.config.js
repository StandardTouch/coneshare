import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testMatch: /rbac-unified-screenshots.spec.js/,
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'off',
    screenshot: 'off',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command:
        'bash -lc \'cd ../backend && export SECRET_KEY=django-insecure-development-key-for-coneshare SITE_DOMAIN=http://127.0.0.1:5173 DEBUG=True DATABASE_URL=postgres://coneshare:coneshare@127.0.0.1:5432/coneshare REDIS_URL=redis://127.0.0.1:6379/0 CORE_API_URL=http://127.0.0.1:8080 INTERNAL_API_TOKEN=supersecrettoken && python3 manage.py runserver 127.0.0.1:8000\'',
      url: 'http://127.0.0.1:8000/api/v1/_health/',
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      command:
        'bash -lc \'unset npm_config_prefix; export PATH="/home/ubuntu/.nvm/versions/node/v22.23.4/bin:$PATH"; cd ../frontend && VITE_DEV_API_TARGET=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1 --port 5173\'',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
});
