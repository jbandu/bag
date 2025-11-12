import { defineConfig, devices } from '@playwright/test';
import * as dotenv from 'dotenv';

// Load environment variables
dotenv.config();

/**
 * Playwright configuration for Baggage Operations Platform
 * Tests against Railway deployment or local environment
 */
export default defineConfig({
  testDir: './tests/e2e',

  // Maximum time one test can run for
  timeout: 30 * 1000,

  // Test execution settings
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  // Reporter to use
  reporter: [
    ['html', { outputFolder: 'test-results/html' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
    ['list']
  ],

  // Shared settings for all projects
  use: {
    // Base URL from environment or default to Railway deployment
    baseURL: process.env.API_BASE_URL || process.env.RAILWAY_STATIC_URL || 'http://localhost:8000',

    // Dashboard URL
    // dashboardURL: process.env.DASHBOARD_URL || 'http://localhost:8501',

    // Collect trace when retrying the failed test
    trace: 'on-first-retry',

    // Screenshot on failure
    screenshot: 'only-on-failure',

    // Video on failure
    video: 'retain-on-failure',

    // Extra HTTP headers
    extraHTTPHeaders: {
      'Accept': 'application/json',
    },
  },

  // Configure projects for major browsers
  projects: [
    {
      name: 'API Tests',
      testMatch: /.*\.api\.spec\.ts/,
      use: {
        ...devices['Desktop Chrome'],
      },
    },

    {
      name: 'Dashboard Tests - Chrome',
      testMatch: /.*\.ui\.spec\.ts/,
      use: {
        ...devices['Desktop Chrome'],
      },
    },

    {
      name: 'Dashboard Tests - Firefox',
      testMatch: /.*\.ui\.spec\.ts/,
      use: {
        ...devices['Desktop Firefox'],
      },
    },

    {
      name: 'Dashboard Tests - Safari',
      testMatch: /.*\.ui\.spec\.ts/,
      use: {
        ...devices['Desktop Safari'],
      },
    },

    // Mobile testing
    {
      name: 'Mobile Chrome',
      testMatch: /.*\.ui\.spec\.ts/,
      use: {
        ...devices['Pixel 5'],
      },
    },
  ],

  // Run local dev server before starting tests
  webServer: process.env.CI ? undefined : {
    command: 'python3 api_server.py',
    url: 'http://localhost:8000/health',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});
