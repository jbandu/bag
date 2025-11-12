# E2E Test Automation Framework

Comprehensive Playwright-based test automation for the Baggage Operations Intelligence Platform.

## 📋 Overview

This test framework provides:
- **API Tests**: Comprehensive testing of REST API endpoints
- **Dashboard UI Tests**: Full Streamlit dashboard functionality testing
- **CI/CD Integration**: GitHub Actions workflow for automated testing
- **Railway Deployment Testing**: Test against live Railway deployments

## 🚀 Quick Start

### Prerequisites

- Node.js 20+
- npm or yarn
- Python 3.11+ (for local server testing)

### Installation

```bash
# Install dependencies
npm install

# Install Playwright browsers
npx playwright install --with-deps
```

### Running Tests

```bash
# Run all tests
npm test

# Run with UI mode (interactive)
npm run test:ui

# Run API tests only
npm run test:api

# Run Dashboard tests only
npm run test:dashboard

# Run in headed mode (see browser)
npm run test:headed

# Debug mode
npm run test:debug

# View test report
npm run report
```

## 🧪 Test Suites

### API Tests (`tests/e2e/api/`)

#### Health & Metrics Tests
- `health.api.spec.ts` - Health checks, metrics, API documentation

#### Bags API Tests
- `bags.api.spec.ts` - Comprehensive bag management testing
  - Pagination (limit/offset)
  - Filtering (status, risk, location, airline, date range, passenger, PNR)
  - Single bag queries
  - Batch operations (up to 100 bags)

#### Scans API Tests
- `scans.api.spec.ts` - Scan event processing
  - Single scan processing
  - Scan event listing with filters
  - Batch scan processing
  - Type B message handling
  - BaggageXML processing

### Dashboard UI Tests (`tests/e2e/dashboard/`)

#### Dashboard Tests
- `dashboard.ui.spec.ts` - Full Streamlit dashboard testing
  - Layout and navigation
  - Auto-refresh functionality
  - Real-time monitoring tab
  - Risk assessment visualizations
  - Active cases management
  - Analytics and trends
  - Responsive design
  - Performance benchmarks

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# API Configuration
API_BASE_URL=http://localhost:8000           # Local API server
# API_BASE_URL=https://your-app.railway.app  # Railway deployment

# Dashboard Configuration
DASHBOARD_URL=http://localhost:8501          # Local dashboard
# DASHBOARD_URL=https://dashboard.railway.app # Railway dashboard

# Railway Configuration (for CI/CD)
RAILWAY_STATIC_URL=https://your-api.railway.app
RAILWAY_DASHBOARD_URL=https://your-dashboard.railway.app
```

### Playwright Configuration

Edit `playwright.config.ts` to customize:
- Test timeout
- Number of parallel workers
- Browser projects
- Reporter settings
- Screenshot/video capture

## 🎯 GitHub Actions Integration

### Automatic Testing

Tests run automatically on:
- **Push** to `main`, `develop`, or `claude/**` branches
- **Pull Requests** to `main` or `develop`
- **Manual Trigger** via GitHub Actions UI

### Manual Workflow Dispatch

Trigger tests manually with custom parameters:

1. Go to **Actions** → **Playwright E2E Tests**
2. Click **Run workflow**
3. Select options:
   - **Deployment URL**: Custom Railway URL to test
   - **Test Suite**: `all`, `api`, or `dashboard`

### Secrets Configuration

Add these secrets to your GitHub repository:

| Secret | Description | Required |
|--------|-------------|----------|
| `RAILWAY_STATIC_URL` | Railway API deployment URL | Yes |
| `RAILWAY_DASHBOARD_URL` | Railway dashboard URL | Optional |
| `ANTHROPIC_API_KEY` | Claude API key (for local tests) | Optional |

**To add secrets:**
1. Go to repository **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add name and value

## 📊 Test Reports

### Local Reports

After running tests:
```bash
npm run report
```

This opens an interactive HTML report with:
- Test results
- Screenshots
- Videos (on failures)
- Trace files

### CI Reports

GitHub Actions generates:
- HTML reports (artifacts)
- JUnit XML (for CI integration)
- JSON results
- Screenshots and videos (on failures)

**To view:**
1. Go to **Actions** → Select workflow run
2. Scroll to **Artifacts**
3. Download and extract reports

## 🧩 Test Examples

### API Test Example

```typescript
test('should filter bags by risk score', async ({ request }) => {
  const response = await request.get('/api/v1/bags?risk_min=0.7');

  expect(response.status()).toBe(200);

  const data = await response.json();
  data.bags.forEach((bag: any) => {
    expect(bag.risk_score).toBeGreaterThanOrEqual(0.7);
  });
});
```

### UI Test Example

```typescript
test('should display auto-refresh toggle', async ({ page }) => {
  await page.goto(DASHBOARD_URL);

  await expect(page.locator('text=Enable Auto-Refresh')).toBeVisible();

  // Click toggle
  await page.click('text=Enable Auto-Refresh');
});
```

## 🔍 Debugging Tests

### Debug Mode

```bash
# Step through tests
npm run test:debug

# Or specific test file
npx playwright test tests/e2e/api/bags.api.spec.ts --debug
```

### View Trace

```bash
# Show trace for failed test
npx playwright show-trace test-results/trace.zip
```

### Screenshots

Screenshots are automatically captured on failures.

Location: `test-results/` directory

## 📈 Best Practices

### Writing Tests

1. **Use descriptive test names**
   ```typescript
   test('should filter bags by location and risk score', ...)
   ```

2. **Group related tests**
   ```typescript
   test.describe('Pagination', () => { ... });
   ```

3. **Handle async operations**
   ```typescript
   await expect(page.locator('...')).toBeVisible();
   ```

4. **Clean up after tests**
   ```typescript
   test.afterEach(async ({ page }) => {
     await page.close();
   });
   ```

### Performance

- Run tests in parallel when possible
- Use `test.describe.configure({ mode: 'serial' })` for dependent tests
- Set appropriate timeouts

### CI/CD

- Keep tests fast (<30s per test)
- Use retries for flaky tests
- Upload artifacts on failures only

## 🐛 Troubleshooting

### Tests fail locally but pass in CI

- Check environment variables
- Verify Python/Node versions match
- Ensure databases are running (local tests)

### "Cannot connect to server" errors

- Check `baseURL` in `playwright.config.ts`
- Verify API server is running
- Check firewall/network settings

### Timeout errors

- Increase timeout in test or config
- Check if server is slow to respond
- Verify network connectivity

### Browser installation issues

```bash
# Reinstall browsers
npx playwright install --with-deps
```

## 📚 Resources

- [Playwright Documentation](https://playwright.dev)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [GitHub Actions](https://docs.github.com/en/actions)
- [Railway Documentation](https://docs.railway.app)

## 🤝 Contributing

1. Write tests for new features
2. Ensure all tests pass before committing
3. Follow existing test patterns
4. Add documentation for complex tests

## 📞 Support

For issues or questions:
- GitHub Issues: https://github.com/jbandu/bag/issues
- Email: support@numberlabs.ai

---

**Number Labs** | AI-Powered Baggage Operations
