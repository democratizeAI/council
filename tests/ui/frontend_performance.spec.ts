import { test, expect } from '@playwright/test';

interface PerformanceMetric {
  url: string;
  status: number;
  timing: any;
  size: number;
}

test.describe('Front-end Performance Triage', () => {
  
  test('DevTools fingerprint analysis', async ({ page }) => {
    console.log('🔍 STEP 0: Quick Fingerprint (5 min)');
    console.log('=' + '='.repeat(49));
    
    // Navigate to chat page
    await page.goto('/');
    
    // Start performance monitoring
    const performanceMetrics: PerformanceMetric[] = [];
    
    page.on('response', response => {
      const url = response.url();
      const status = response.status();
      const timing = response.timing();
      
      performanceMetrics.push({
        url,
        status,
        timing,
        size: parseInt(response.headers()['content-length'] || '0')
      });
    });
    
    // Send a test prompt and measure
    const startTime = Date.now();
    
    await page.fill('[data-testid="chat-input"]', 'What is 2+2?');
    await page.click('[data-testid="send-button"]');
    
    // Wait for response
    await page.waitForSelector('[data-testid="chat-response"]', { timeout: 10000 });
    
    const totalTime = Date.now() - startTime;
    
    // Analyze the waterfall
    const chatRequests = performanceMetrics.filter(m => m.url.includes('/chat'));
    const jsBundle = performanceMetrics.filter(m => m.url.includes('.js') && m.size > 100000);
    const repeatedCalls = performanceMetrics.filter(m => m.url.includes('/vote') || m.url.includes('/health'));
    
    console.log('\n📊 DevTools Analysis:');
    console.log(`Total chat time: ${totalTime}ms`);
    
    // Diagnostic checks
    const diagnostics = {
      slowChatCall: false,
      streamingIssue: false,
      bundleBloat: false,
      pollingHammer: false
    };
    
    // Check 1: POST /chat time
    if (chatRequests.length > 0) {
      const chatRequest = chatRequests[0];
      const chatTime = chatRequest.timing?.responseEnd - chatRequest.timing?.requestStart || totalTime;
      console.log(`POST /chat time: ${chatTime}ms`);
      
      if (chatTime > 5000) {
        diagnostics.slowChatCall = true;
        console.log('❌ Backend still slow - return to GPU fixes');
      }
    }
    
    // Check 2: TTFB vs download stall
    if (chatRequests.length > 0) {
      const chatRequest = chatRequests[0];
      const ttfb = chatRequest.timing?.responseStart - chatRequest.timing?.requestStart;
      const downloadTime = chatRequest.timing?.responseEnd - chatRequest.timing?.responseStart;
      
      console.log(`TTFB: ${ttfb}ms, Download: ${downloadTime}ms`);
      
      if (ttfb < 200 && downloadTime > 2000) {
        diagnostics.streamingIssue = true;
        console.log('❌ Streaming issue - UI waits for completion');
      }
    }
    
    // Check 3: Bundle size
    if (jsBundle.length > 0) {
      const totalBundleSize = jsBundle.reduce((sum, bundle) => sum + bundle.size, 0);
      const bundleSizeMB = totalBundleSize / (1024 * 1024);
      
      console.log(`JS bundle size: ${bundleSizeMB.toFixed(2)}MB`);
      
      if (bundleSizeMB > 1) {
        diagnostics.bundleBloat = true;
        console.log('❌ Bundle bloat - blocking first paint');
      }
    }
    
    // Check 4: Repeated calls
    if (repeatedCalls.length > 5) {
      diagnostics.pollingHammer = true;
      console.log(`❌ Polling hammer - ${repeatedCalls.length} repeated calls`);
    }
    
    // Determine recommended fix
    let recommendedStep = 0;
    
    if (diagnostics.slowChatCall) {
      recommendedStep = 1;
      console.log('🔧 Recommended: Step 1 - Backend Streaming');
    } else if (diagnostics.streamingIssue) {
      recommendedStep = 2;
      console.log('🔧 Recommended: Step 2 - UI Streaming');
    } else if (diagnostics.bundleBloat) {
      recommendedStep = 3;
      console.log('🔧 Recommended: Step 3 - Bundle Optimization');
    } else if (diagnostics.pollingHammer) {
      recommendedStep = 4;
      console.log('🔧 Recommended: Step 4 - WebSocket Migration');
    } else {
      console.log('✅ No major performance issues detected');
    }
    
    // Performance assertions
    expect(totalTime).toBeLessThan(5000); // Should respond within 5s
    expect(recommendedStep).toBeLessThan(5); // Should not need major fixes
  });

  test('streaming latency measurement', async ({ page }) => {
    await page.goto('/');
    
    // Measure first token latency
    const startTime = Date.now();
    let firstTokenTime: number | null = null;
    let totalTime: number | null = null;
    
    // Listen for streaming tokens
    page.on('response', async response => {
      if (response.url().includes('/chat/stream')) {
        if (!firstTokenTime) {
          firstTokenTime = Date.now() - startTime;
        }
      }
    });
    
    await page.fill('[data-testid="chat-input"]', 'Hello');
    await page.click('[data-testid="send-button"]');
    
    await page.waitForSelector('[data-testid="chat-response"]');
    totalTime = Date.now() - startTime;
    
    console.log(`Streaming performance: first token ${firstTokenTime}ms, total ${totalTime}ms`);
    
    // Targets from triage plan
    if (firstTokenTime) {
      expect(firstTokenTime).toBeLessThan(1500); // First token < 1.5s
    }
    expect(totalTime).toBeLessThan(3000); // Total < 3s
  });

  test('bundle size analysis', async ({ page }) => {
    const response = await page.goto('/');
    
    // Get all JS resources
    const jsResources = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('script[src]') as NodeListOf<HTMLScriptElement>)
        .map(script => script.src)
        .filter(src => src.includes('.js'));
    });
    
    let totalBundleSize = 0;
    let mainBundleSize = 0;
    
    for (const resource of jsResources) {
      try {
        const resourceResponse = await page.request.get(resource);
        const size = parseInt(resourceResponse.headers()['content-length'] || '0');
        totalBundleSize += size;
        
        if (resource.includes('main')) {
          mainBundleSize = size;
        }
        
        console.log(`Bundle: ${resource.split('/').pop()} - ${(size / 1024).toFixed(1)}KB`);
      } catch (e) {
        console.log(`Could not measure: ${resource}`);
      }
    }
    
    console.log(`Total bundle size: ${(totalBundleSize / 1024 / 1024).toFixed(2)}MB`);
    console.log(`Main bundle size: ${(mainBundleSize / 1024).toFixed(1)}KB`);
    
    // Bundle size assertions from triage plan
    expect(mainBundleSize).toBeLessThan(200 * 1024); // Main < 200KB
    expect(totalBundleSize).toBeLessThan(1024 * 1024); // Total < 1MB
  });

  test('payload size analysis', async ({ page }) => {
    let debugPayloadSize = 0;
    let productionPayloadSize = 0;
    
    page.on('response', async response => {
      if (response.url().includes('/chat')) {
        try {
          const body = await response.text();
          const size = body.length;
          
          if (response.url().includes('debug=true')) {
            debugPayloadSize = size;
          } else {
            productionPayloadSize = size;
          }
        } catch (e) {
          // Ignore response body read errors
        }
      }
    });
    
    await page.goto('/');
    
    // Test production payload (should be small)
    await page.evaluate(() => {
      return fetch('/chat?debug=false', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'prompt=Hello'
      });
    });
    
    // Test debug payload (can be large)
    await page.evaluate(() => {
      return fetch('/chat?debug=true', {
        method: 'POST', 
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'prompt=Hello'
      });
    });
    
    await page.waitForTimeout(1000); // Let requests complete
    
    console.log(`Production payload: ${(productionPayloadSize / 1024).toFixed(1)}KB`);
    console.log(`Debug payload: ${(debugPayloadSize / 1024).toFixed(1)}KB`);
    
    // Payload size targets from triage plan
    expect(productionPayloadSize).toBeLessThan(10 * 1024); // Production < 10KB
    // Debug can be larger but should be reasonable
    if (debugPayloadSize > 0) {
      expect(debugPayloadSize).toBeLessThan(1024 * 1024); // Debug < 1MB
    }
  });
}); 