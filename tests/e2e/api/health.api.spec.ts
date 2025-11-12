import { test, expect } from '@playwright/test';

/**
 * Health Check & Metrics API Tests
 */

test.describe('Health & Metrics Endpoints', () => {

  test('GET / - should return API welcome message', async ({ request }) => {
    const response = await request.get('/');

    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data).toHaveProperty('service', 'Baggage Operations Intelligence Platform');
    expect(data).toHaveProperty('version');
    expect(data).toHaveProperty('status', 'operational');
    expect(data).toHaveProperty('endpoints');
    expect(data).toHaveProperty('agents');
    expect(data.agents).toHaveLength(8);
  });

  test('GET /health - should return healthy status', async ({ request }) => {
    const response = await request.get('/health');

    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data).toHaveProperty('status', 'healthy');
    expect(data).toHaveProperty('timestamp');
    expect(data).toHaveProperty('service', 'baggage-operations-api');
    expect(data).toHaveProperty('version');
  });

  test('GET /metrics - should return operational metrics', async ({ request }) => {
    const response = await request.get('/metrics');

    expect(response.status()).toBe(200);

    const data = await response.json();

    // Either returns metrics or unavailable status
    if (data.status === 'metrics_unavailable') {
      expect(data).toHaveProperty('reason');
    } else {
      expect(data).toHaveProperty('bags_processed');
      expect(data).toHaveProperty('scans_processed');
      expect(data).toHaveProperty('high_risk_bags_detected');
      expect(data).toHaveProperty('timestamp');
    }
  });

  test('GET /health - should respond within acceptable time', async ({ request }) => {
    const startTime = Date.now();
    await request.get('/health');
    const endTime = Date.now();

    const responseTime = endTime - startTime;
    expect(responseTime).toBeLessThan(1000); // Should respond within 1 second
  });

  test('GET /docs - should return API documentation', async ({ request }) => {
    const response = await request.get('/docs');
    expect(response.status()).toBe(200);
    expect(response.headers()['content-type']).toContain('text/html');
  });
});
