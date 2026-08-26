const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  use: {
    // Phoenix test endpoint is configured for localhost. Keep the browser origin
    // on that canonical host so LiveView's websocket origin check remains active
    // instead of weakening endpoint security with check_origin: false.
    baseURL: process.env.HUMAN_VALUE_BASE_URL || 'http://localhost:4002',
    headless: true,
  },
  workers: 1,
  retries: 0,
});
