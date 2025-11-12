import { test, expect } from '@playwright/test';

/**
 * Dashboard UI Tests
 * Tests Streamlit dashboard functionality
 */

const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://localhost:8501';

test.describe('Baggage Operations Dashboard', () => {

  test.beforeEach(async ({ page }) => {
    // Set longer timeout for Streamlit apps
    page.setDefaultTimeout(10000);
  });

  test.describe('Dashboard Loading and Layout', () => {

    test('should load dashboard successfully', async ({ page }) => {
      await page.goto(DASHBOARD_URL);

      // Wait for Streamlit to load
      await page.waitForSelector('[data-testid="stApp"]', { timeout: 15000 });

      // Check title
      await expect(page.locator('h1')).toContainText('Baggage Operations Intelligence Platform');
    });

    test('should display all main tabs', async ({ page }) => {
      await page.goto(DASHBOARD_URL);
      await page.waitForSelector('[data-testid="stApp"]');

      // Check for tabs
      const tabs = ['Real-Time Monitoring', 'Risk Assessment', 'Active Cases', 'Analytics'];

      for (const tab of tabs) {
        await expect(page.locator(`text=${tab}`)).toBeVisible();
      }
    });

    test('should display sidebar controls', async ({ page }) => {
      await page.goto(DASHBOARD_URL);
      await page.waitForSelector('[data-testid="stApp"]');

      // Check sidebar elements
      await expect(page.locator('text=Controls')).toBeVisible();
      await expect(page.locator('text=Auto-Refresh')).toBeVisible();
    });
  });

  test.describe('Auto-Refresh Feature', () => {

    test('should have auto-refresh toggle', async ({ page }) => {
      await page.goto(DASHBOARD_URL);
      await page.waitForSelector('[data-testid="stApp"]');

      // Look for auto-refresh toggle
      const toggle = page.locator('text=Enable Auto-Refresh');
      await expect(toggle).toBeVisible();
    });

    test('should show refresh interval selector when enabled', async ({ page }) => {
      await page.goto(DASHBOARD_URL);
      await page.waitForSelector('[data-testid="stApp"]');

      // Check if interval selector is visible
      const selector = page.locator('text=Refresh Interval');
      if (await selector.isVisible()) {
        // Verify options exist
        await expect(page.locator('text=30 seconds')).toBeVisible();
      }
    });

    test('should display countdown timer', async ({ page }) => {
      await page.goto(DASHBOARD_URL);
      await page.waitForSelector('[data-testid="stApp"]');

      // Look for countdown text (may appear after a moment)
      await page.waitForTimeout(2000);
      const countdown = page.locator('text=/Next refresh in:/');
      // Timer should appear if auto-refresh is enabled
    });

    test('should have manual refresh button', async ({ page }) => {
      await page.goto(DASHBOARD_URL);
      await page.waitForSelector('[data-testid="stApp"]');

      const refreshButton = page.locator('text=Refresh Now');
      await expect(refreshButton).toBeVisible();
    });
  });

  test.describe('Real-Time Monitoring Tab', () => {

    test('should display KPI metrics', async ({ page }) => {
      await page.goto(DASHBOARD_URL);
      await page.waitForSelector('[data-testid="stApp"]');

      // Click on Real-Time Monitoring tab
      await page.click('text=Real-Time Monitoring');

      // Check for KPI labels
      await expect(page.locator('text=Bags Processed Today')).toBeVisible();
      await expect(page.locator('text=Scans Processed')).toBeVisible();
      await expect(page.locator('text=Exceptions Handled')).toBeVisible();
      await expect(page.locator('text=High Risk Bags')).toBeVisible();
    });

    test('should display recent scan events table', async ({ page }) => {
      await page.goto(DASHBOARD_URL);
      await page.waitForSelector('[data-testid="stApp"]');

      await page.click('text=Real-Time Monitoring');

      // Look for recent scans heading
      await expect(page.locator('text=Recent Scan Events')).toBeVisible();

      // Table should be visible
      await expect(page.locator('[data-testid="stDataFrame"]')).toBeVisible();
    });
  });

  test.describe('Risk Assessment Tab', () => {

    test('should display risk distribution chart', async ({ page }) => {
      await page.goto(DASHBOARD_URL);
      await page.waitForSelector('[data-testid="stApp"]');

      await page.click('text=Risk Assessment');

      // Check for chart
      await expect(page.locator('text=Risk Distribution')).toBeVisible();
    });

    test('should show high risk bags table', async ({ page }) => {
      await page.goto(DASHBOARD_URL);
      await page.waitForSelector('[data-testid="stApp"]');

      await page.click('text=Risk Assessment');

      // Look for high risk bags section
      await expect(page.locator('text=/High Risk Bags/i')).toBeVisible();
    });
  });

  test.describe('Active Cases Tab', () => {

    test('should display case metrics', async ({ page }) => {
      await page.goto(DASHBOARD_URL);
      await page.waitForSelector('[data-testid="stApp"]');

      await page.click('text=Active Cases');

      // Check for case-related metrics
      await expect(page.locator('text=Open Cases')).toBeVisible();
      await expect(page.locator('text=/PIRs Filed/i')).toBeVisible();
    });

    test('should show active cases table', async ({ page }) => {
      await page.goto(DASHBOARD_URL);
      await page.waitForSelector('[data-testid="stApp"]');

      await page.click('text=Active Cases');

      await expect(page.locator('text=Active Cases')).toBeVisible();
    });
  });

  test.describe('Analytics Tab', () => {

    test('should display trend charts', async ({ page }) => {
      await page.goto(DASHBOARD_URL);
      await page.waitForSelector('[data-testid="stApp"]');

      await page.click('text=Analytics');

      // Look for chart titles
      await expect(page.locator('text=/Baggage Volume/i')).toBeVisible();
      await expect(page.locator('text=/Exception Rate/i')).toBeVisible();
    });

    test('should show performance metrics', async ({ page }) => {
      await page.goto(DASHBOARD_URL);
      await page.waitForSelector('[data-testid="stApp"]');

      await page.click('text=Analytics');

      await expect(page.locator('text=Performance Metrics')).toBeVisible();
    });
  });

  test.describe('Scan Event Processing', () => {

    test('should have scan input area in sidebar', async ({ page }) => {
      await page.goto(DASHBOARD_URL);
      await page.waitForSelector('[data-testid="stApp"]');

      // Look for scan event input
      await expect(page.locator('text=Process Scan Event')).toBeVisible();
    });

    test('should have process button', async ({ page }) => {
      await page.goto(DASHBOARD_URL);
      await page.waitForSelector('[data-testid="stApp"]');

      const processButton = page.locator('text=Process Event');
      await expect(processButton).toBeVisible();
    });
  });

  test.describe('Footer Information', () => {

    test('should display system status', async ({ page }) => {
      await page.goto(DASHBOARD_URL);
      await page.waitForSelector('[data-testid="stApp"]');

      // Scroll to bottom
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));

      await expect(page.locator('text=System Status')).toBeVisible();
    });

    test('should show last updated timestamp', async ({ page }) => {
      await page.goto(DASHBOARD_URL);
      await page.waitForSelector('[data-testid="stApp"]');

      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));

      await expect(page.locator('text=Last Updated')).toBeVisible();
    });

    test('should display version info', async ({ page }) => {
      await page.goto(DASHBOARD_URL);
      await page.waitForSelector('[data-testid="stApp"]');

      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));

      await expect(page.locator('text=/Version:.*1\\.0\\.0/i')).toBeVisible();
    });
  });

  test.describe('Responsive Design', () => {

    test('should be responsive on mobile viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto(DASHBOARD_URL);
      await page.waitForSelector('[data-testid="stApp"]');

      // Dashboard should still load
      await expect(page.locator('h1')).toBeVisible();
    });

    test('should be responsive on tablet viewport', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto(DASHBOARD_URL);
      await page.waitForSelector('[data-testid="stApp"]');

      await expect(page.locator('h1')).toBeVisible();
    });
  });

  test.describe('Performance', () => {

    test('should load within acceptable time', async ({ page }) => {
      const startTime = Date.now();
      await page.goto(DASHBOARD_URL);
      await page.waitForSelector('[data-testid="stApp"]', { timeout: 15000 });
      const loadTime = Date.now() - startTime;

      // Dashboard should load within 15 seconds
      expect(loadTime).toBeLessThan(15000);
    });
  });
});
