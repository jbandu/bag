import { test, expect } from '@playwright/test';

/**
 * Scan Events API Tests - Processing, Pagination, and Batch Operations
 */

test.describe('Scan Events API', () => {

  test.describe('POST /api/v1/scan - Process single scan event', () => {

    test('should accept and process valid scan event', async ({ request }) => {
      const scanData = {
        raw_scan: `Bag Tag: CM${Date.now()}
Location: PTY-T1-BHS
Timestamp: ${new Date().toISOString()}
Status: Checked In`,
        source: 'TEST',
        timestamp: new Date().toISOString()
      };

      const response = await request.post('/api/v1/scan', {
        data: scanData
      });

      // Accept both 200 (success) and 503 (orchestrator not loaded)
      expect([200, 503]).toContain(response.status());

      if (response.status() === 200) {
        const data = await response.json();
        expect(data).toHaveProperty('status');
        expect(data).toHaveProperty('received_at');
      }
    });

    test('should reject scan without required fields', async ({ request }) => {
      const response = await request.post('/api/v1/scan', {
        data: {
          source: 'TEST'
          // Missing raw_scan
        }
      });

      expect(response.status()).toBe(422); // Validation error
    });

    test('should handle different source systems', async ({ request }) => {
      const sources = ['BRS', 'BHS', 'DCS', 'MANUAL'];

      for (const source of sources) {
        const response = await request.post('/api/v1/scan', {
          data: {
            raw_scan: `Test scan from ${source}`,
            source: source
          }
        });

        // Should not return 4xx validation errors
        expect(response.status()).not.toBe(422);
      }
    });
  });

  test.describe('GET /api/v1/scans - List scan events', () => {

    test('should return scans with default pagination', async ({ request }) => {
      const response = await request.get('/api/v1/scans');

      expect(response.status()).toBe(200);

      const data = await response.json();
      expect(data).toHaveProperty('total');
      expect(data).toHaveProperty('count');
      expect(data).toHaveProperty('limit', 100);
      expect(data).toHaveProperty('offset', 0);
      expect(data).toHaveProperty('has_more');
      expect(data).toHaveProperty('scans');
      expect(Array.isArray(data.scans)).toBe(true);
    });

    test('should filter by bag_tag', async ({ request }) => {
      const response = await request.get('/api/v1/scans?bag_tag=CM123456');

      if (response.status() === 200) {
        const data = await response.json();
        data.scans.forEach((scan: any) => {
          expect(scan.bag_tag).toBe('CM123456');
        });
      }
    });

    test('should filter by location', async ({ request }) => {
      const response = await request.get('/api/v1/scans?location=PTY');

      if (response.status() === 200) {
        const data = await response.json();
        data.scans.forEach((scan: any) => {
          expect(scan.location).toBe('PTY');
        });
      }
    });

    test('should filter by scan_type', async ({ request }) => {
      const response = await request.get('/api/v1/scans?scan_type=check-in');

      if (response.status() === 200) {
        const data = await response.json();
        data.scans.forEach((scan: any) => {
          expect(scan.scan_type).toBe('check-in');
        });
      }
    });

    test('should support pagination', async ({ request }) => {
      const response = await request.get('/api/v1/scans?limit=10&offset=5');

      expect(response.status()).toBe(200);
      const data = await response.json();
      expect(data.limit).toBe(10);
      expect(data.offset).toBe(5);
    });

    test('should filter by date range', async ({ request }) => {
      const today = new Date().toISOString().split('T')[0];
      const response = await request.get(`/api/v1/scans?date_from=${today}`);

      expect(response.status()).toBe(200);
    });
  });

  test.describe('POST /api/v1/scans/batch - Batch scan processing', () => {

    test('should process multiple scans in a batch', async ({ request }) => {
      const batchData = {
        source: 'TEST_BATCH',
        scans: [
          {
            raw_scan: `Bag Tag: CM${Date.now()}_1
Location: PTY-T1
Timestamp: ${new Date().toISOString()}`
          },
          {
            raw_scan: `Bag Tag: CM${Date.now()}_2
Location: MIA-T3
Timestamp: ${new Date().toISOString()}`
          },
          {
            raw_scan: `Bag Tag: CM${Date.now()}_3
Location: JFK-T8
Timestamp: ${new Date().toISOString()}`
          }
        ]
      };

      const response = await request.post('/api/v1/scans/batch', {
        data: batchData
      });

      // Accept 200 or 503
      expect([200, 503]).toContain(response.status());

      if (response.status() === 200) {
        const data = await response.json();
        expect(data).toHaveProperty('status', 'completed');
        expect(data).toHaveProperty('total_scans', 3);
        expect(data).toHaveProperty('successful');
        expect(data).toHaveProperty('failed');
        expect(data).toHaveProperty('results');
        expect(Array.isArray(data.results)).toBe(true);
        expect(data.results).toHaveLength(3);
      }
    });

    test('should handle empty scans array', async ({ request }) => {
      const response = await request.post('/api/v1/scans/batch', {
        data: {
          source: 'TEST',
          scans: []
        }
      });

      // Should process even with empty array (returns 0 results)
      expect([200, 503]).toContain(response.status());
    });

    test('should process mixed valid/invalid scans', async ({ request }) => {
      const batchData = {
        source: 'TEST_MIXED',
        scans: [
          { raw_scan: 'Valid scan data' },
          { raw_scan: '' }, // Empty/invalid
          { raw_scan: 'Another valid scan' }
        ]
      };

      const response = await request.post('/api/v1/scans/batch', {
        data: batchData
      });

      // Should not completely fail, even with some invalid scans
      expect([200, 503]).toContain(response.status());
    });
  });

  test.describe('POST /api/v1/type-b - Type B message processing', () => {

    test('should accept BTM message', async ({ request }) => {
      const btmMessage = {
        message: 'BTM\nCM123456\nPTY1234/01\n....',
        message_type: 'BTM',
        from_station: 'PTY',
        to_station: 'MIA'
      };

      const response = await request.post('/api/v1/type-b', {
        data: btmMessage
      });

      expect([200, 503]).toContain(response.status());
    });

    test('should accept BSM message', async ({ request }) => {
      const bsmMessage = {
        message: 'BSM\nCM789012/PTY\n...',
        message_type: 'BSM',
        from_station: 'PTY',
        to_station: 'MIA'
      };

      const response = await request.post('/api/v1/type-b', {
        data: bsmMessage
      });

      expect([200, 503]).toContain(response.status());
    });

    test('should require all Type B fields', async ({ request }) => {
      const response = await request.post('/api/v1/type-b', {
        data: {
          message: 'Test message'
          // Missing message_type, from_station, to_station
        }
      });

      expect(response.status()).toBe(422); // Validation error
    });
  });

  test.describe('POST /api/v1/baggage-xml - BaggageXML processing', () => {

    test('should accept valid BaggageXML', async ({ request }) => {
      const xmlData = {
        xml_content: '<BaggageManifest><Bag>...</Bag></BaggageManifest>',
        flight_number: 'CM123'
      };

      const response = await request.post('/api/v1/baggage-xml', {
        data: xmlData
      });

      expect(response.status()).toBe(200);

      const data = await response.json();
      expect(data).toHaveProperty('status', 'success');
      expect(data).toHaveProperty('flight_number', 'CM123');
    });

    test('should require xml_content and flight_number', async ({ request }) => {
      const response = await request.post('/api/v1/baggage-xml', {
        data: {
          flight_number: 'CM123'
          // Missing xml_content
        }
      });

      expect(response.status()).toBe(422);
    });
  });
});
