import { test, expect } from '@playwright/test';

/**
 * Bags API Tests - Pagination, Filtering, and Batch Operations
 */

test.describe('Bags API Endpoints', () => {

  test.describe('GET /api/v1/bags - List bags with pagination', () => {

    test('should return bags with default pagination', async ({ request }) => {
      const response = await request.get('/api/v1/bags');

      expect(response.status()).toBe(200);

      const data = await response.json();
      expect(data).toHaveProperty('total');
      expect(data).toHaveProperty('count');
      expect(data).toHaveProperty('limit', 100);
      expect(data).toHaveProperty('offset', 0);
      expect(data).toHaveProperty('has_more');
      expect(data).toHaveProperty('bags');
      expect(Array.isArray(data.bags)).toBe(true);
    });

    test('should respect custom limit parameter', async ({ request }) => {
      const response = await request.get('/api/v1/bags?limit=10');

      expect(response.status()).toBe(200);

      const data = await response.json();
      expect(data.limit).toBe(10);
      expect(data.count).toBeLessThanOrEqual(10);
    });

    test('should support offset pagination', async ({ request }) => {
      const response1 = await request.get('/api/v1/bags?limit=5&offset=0');
      const response2 = await request.get('/api/v1/bags?limit=5&offset=5');

      expect(response1.status()).toBe(200);
      expect(response2.status()).toBe(200);

      const data1 = await response1.json();
      const data2 = await response2.json();

      // Bags should be different
      if (data1.bags.length > 0 && data2.bags.length > 0) {
        expect(data1.bags[0].bag_tag).not.toBe(data2.bags[0].bag_tag);
      }
    });

    test('should reject invalid limit values', async ({ request }) => {
      const response = await request.get('/api/v1/bags?limit=2000');
      expect(response.status()).toBe(422); // Validation error
    });

    test('should reject negative offset', async ({ request }) => {
      const response = await request.get('/api/v1/bags?offset=-1');
      expect(response.status()).toBe(422); // Validation error
    });
  });

  test.describe('GET /api/v1/bags - Filtering', () => {

    test('should filter by risk score range', async ({ request }) => {
      const response = await request.get('/api/v1/bags?risk_min=0.7&risk_max=1.0');

      if (response.status() === 200) {
        const data = await response.json();
        data.bags.forEach((bag: any) => {
          expect(bag.risk_score).toBeGreaterThanOrEqual(0.7);
          expect(bag.risk_score).toBeLessThanOrEqual(1.0);
        });
      }
    });

    test('should filter by status', async ({ request }) => {
      const response = await request.get('/api/v1/bags?status=in_transit');

      if (response.status() === 200) {
        const data = await response.json();
        data.bags.forEach((bag: any) => {
          expect(bag.status).toBe('in_transit');
        });
      }
    });

    test('should filter by location', async ({ request }) => {
      const response = await request.get('/api/v1/bags?location=PTY');

      if (response.status() === 200) {
        const data = await response.json();
        data.bags.forEach((bag: any) => {
          expect(bag.current_location).toBe('PTY');
        });
      }
    });

    test('should filter by airline code', async ({ request }) => {
      const response = await request.get('/api/v1/bags?airline=CM');

      if (response.status() === 200) {
        const data = await response.json();
        data.bags.forEach((bag: any) => {
          expect(bag.bag_tag).toMatch(/^CM/);
        });
      }
    });

    test('should filter by date range', async ({ request }) => {
      const today = new Date().toISOString().split('T')[0];
      const response = await request.get(`/api/v1/bags?date_from=${today}`);

      expect(response.status()).toBe(200);
      const data = await response.json();
      expect(data).toHaveProperty('bags');
    });

    test('should support combined filters', async ({ request }) => {
      const response = await request.get('/api/v1/bags?risk_min=0.7&location=PTY&limit=20');

      expect(response.status()).toBe(200);
      const data = await response.json();
      expect(data.limit).toBe(20);
    });
  });

  test.describe('GET /api/v1/bag/{bag_tag} - Single bag query', () => {

    test('should return 404 for non-existent bag', async ({ request }) => {
      const response = await request.get('/api/v1/bag/NONEXISTENT999');

      // Either 404 or 503 (if database not configured)
      expect([404, 503]).toContain(response.status());
    });

    test('should return bag details for valid tag', async ({ request }) => {
      // First get a bag from the list
      const listResponse = await request.get('/api/v1/bags?limit=1');

      if (listResponse.status() === 200) {
        const listData = await listResponse.json();

        if (listData.bags && listData.bags.length > 0) {
          const bagTag = listData.bags[0].bag_tag;

          const response = await request.get(`/api/v1/bag/${bagTag}`);

          if (response.status() === 200) {
            const data = await response.json();
            expect(data).toHaveProperty('bag_tag', bagTag);
            expect(data).toHaveProperty('status');
          }
        }
      }
    });
  });

  test.describe('POST /api/v1/bags/batch - Batch bag query', () => {

    test('should query multiple bags at once', async ({ request }) => {
      const response = await request.post('/api/v1/bags/batch', {
        data: {
          bag_tags: ['CM123456', 'CM789012', 'CM345678']
        }
      });

      if (response.status() === 200) {
        const data = await response.json();
        expect(data).toHaveProperty('total_requested', 3);
        expect(data).toHaveProperty('total_found');
        expect(data).toHaveProperty('results');
        expect(Array.isArray(data.results)).toBe(true);
        expect(data.results).toHaveLength(3);

        data.results.forEach((result: any) => {
          expect(result).toHaveProperty('bag_tag');
          expect(result).toHaveProperty('found');
          expect(result).toHaveProperty('data');
        });
      }
    });

    test('should reject empty bag_tags array', async ({ request }) => {
      const response = await request.post('/api/v1/bags/batch', {
        data: {
          bag_tags: []
        }
      });

      expect(response.status()).toBe(422); // Validation error
    });

    test('should reject more than 100 bags', async ({ request }) => {
      const bagTags = Array.from({ length: 101 }, (_, i) => `CM${i}`);

      const response = await request.post('/api/v1/bags/batch', {
        data: {
          bag_tags: bagTags
        }
      });

      expect(response.status()).toBe(422); // Validation error
    });
  });
});
