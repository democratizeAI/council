
import { test, expect } from '@playwright/test';

test('chat latency performance', async ({ page }) => {
  await page.goto('/');
  
  // Measure chat response time
  const startTime = Date.now();
  
  await page.fill('[data-testid="chat-input"]', 'What is 2+2?');
  await page.click('[data-testid="send-button"]');
  
  // Wait for first token (streaming)
  await page.waitForSelector('[data-testid="chat-response"]', { 
    state: 'visible',
    timeout: 2000 
  });
  
  const firstTokenTime = Date.now() - startTime;
  
  // Wait for completion
  await page.waitForSelector('[data-testid="chat-complete"]', {
    timeout: 5000
  });
  
  const totalTime = Date.now() - startTime;
  
  // Performance assertions
  expect(firstTokenTime).toBeLessThan(1500); // First token < 1.5s
  expect(totalTime).toBeLessThan(3000);      // Total < 3s for local
  
  console.log(`Performance: first token ${firstTokenTime}ms, total ${totalTime}ms`);
});

test('bundle size check', async ({ page }) => {
  // Navigate and measure bundle loading
  const response = await page.goto('/');
  
  // Check main bundle size
  const bundles = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('script[src*="static/js"]'))
      .map(script => script.src);
  });
  
  for (const bundle of bundles) {
    const bundleResponse = await page.request.get(bundle);
    const size = parseInt(bundleResponse.headers()['content-length'] || '0');
    
    if (bundle.includes('main')) {
      expect(size).toBeLessThan(200 * 1024); // Main bundle < 200KB
    }
  }
});
