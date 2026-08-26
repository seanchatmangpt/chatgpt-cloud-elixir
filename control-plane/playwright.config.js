const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: process.env.HUMAN_VALUE_BASE_URL || 'http://127.0.0.1:4002',
    headless: true,
  },
  workers: 1,
  retries: 0,
});
