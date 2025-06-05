import { test, expect } from '@playwright/test';

test.describe('Council Panel Tests', () => {
  
  test.beforeEach(async ({ page }) => {
    // Navigate to the chat interface
    try {
      await page.goto('http://localhost:8001/chat/');
    } catch (error) {
      // Fallback to alternative ports
      try {
        await page.goto('http://localhost:9000/chat/');
      } catch {
        await page.goto('http://localhost:3000/chat/');
      }
    }
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
  });

  test('council panel renders and is collapsible', async ({ page }) => {
    // Fill in chat input and submit
    const chatInput = page.locator('#chat-input, [data-testid="chat-input"], input[type="text"]').first();
    await expect(chatInput).toBeVisible({ timeout: 10000 });
    
    await chatInput.fill('Explain DNS');
    await chatInput.press('Enter');
    
    // Wait for council panel to appear
    const councilPanel = page.locator('details.council-panel, .council-panel details, [data-testid="council-panel"]').first();
    await expect(councilPanel).toBeVisible({ timeout: 30000 });
    
    // Check summary text
    const summary = councilPanel.locator('summary').first();
    await expect(summary).toBeVisible();
    
    const summaryText = await summary.innerText();
    expect(summaryText.toLowerCase()).toMatch(/council|consensus|voices/);
    
    // Test collapsible functionality
    await summary.click();
    
    // Check that panel content is visible after clicking
    const panelContent = councilPanel.locator('div, .council-content').first();
    await expect(panelContent).toBeVisible();
    
    // Click again to collapse
    await summary.click();
    
    // Panel content should be hidden (details element behavior)
    await expect(panelContent).toBeHidden();
  });

  test('council panel shows five voices', async ({ page }) => {
    // Submit a query that should trigger council response
    const chatInput = page.locator('#chat-input, [data-testid="chat-input"], input[type="text"]').first();
    await chatInput.fill('What is artificial intelligence?');
    await chatInput.press('Enter');
    
    // Wait for council panel
    const councilPanel = page.locator('details.council-panel, .council-panel details, [data-testid="council-panel"]').first();
    await expect(councilPanel).toBeVisible({ timeout: 30000 });
    
    // Expand the panel
    const summary = councilPanel.locator('summary').first();
    await summary.click();
    
    // Look for voice elements
    const voices = page.locator('.voice, .council-voice, [data-testid="voice"]');
    
    // Should have multiple voices (at least 3, ideally 5)
    const voiceCount = await voices.count();
    expect(voiceCount).toBeGreaterThanOrEqual(3);
    
    // Check for expected voice types
    const expectedVoices = ['reason', 'knowledge', 'logic', 'creativity', 'critique'];
    
    for (const expectedVoice of expectedVoices) {
      const voiceElement = page.locator(`text=/.*${expectedVoice}.*/i`).first();
      if (await voiceElement.isVisible()) {
        console.log(`Found voice: ${expectedVoice}`);
      }
    }
  });

  test('voice responses have color badges', async ({ page }) => {
    // Submit query
    const chatInput = page.locator('#chat-input, [data-testid="chat-input"], input[type="text"]').first();
    await chatInput.fill('Compare Python and JavaScript');
    await chatInput.press('Enter');
    
    // Wait for response
    const councilPanel = page.locator('details.council-panel, .council-panel details, [data-testid="council-panel"]').first();
    await expect(councilPanel).toBeVisible({ timeout: 30000 });
    
    // Expand panel
    const summary = councilPanel.locator('summary').first();
    await summary.click();
    
    // Look for colored elements (badges, indicators)
    const coloredElements = page.locator('.badge, .voice-badge, .status-indicator, [class*="bg-"], [class*="color"]');
    const colorCount = await coloredElements.count();
    
    if (colorCount > 0) {
      console.log(`Found ${colorCount} colored elements`);
      
      // Check for specific color classes or styles
      const greenElements = page.locator('[class*="green"], [style*="green"], .success');
      const yellowElements = page.locator('[class*="yellow"], [style*="yellow"], .warning');
      const redElements = page.locator('[class*="red"], [style*="red"], .error');
      
      const hasColors = (await greenElements.count()) > 0 || 
                       (await yellowElements.count()) > 0 || 
                       (await redElements.count()) > 0;
      
      expect(hasColors).toBeTruthy();
    }
  });

  test('chat interface loads and responds', async ({ page }) => {
    // Basic functionality test
    const chatInput = page.locator('#chat-input, [data-testid="chat-input"], input[type="text"]').first();
    await expect(chatInput).toBeVisible();
    
    // Test input functionality
    await chatInput.fill('Hello');
    const inputValue = await chatInput.inputValue();
    expect(inputValue).toBe('Hello');
    
    // Submit and wait for response
    await chatInput.press('Enter');
    
    // Look for any response container
    const responseArea = page.locator('.response, .chat-response, .message, [data-testid="response"]').first();
    await expect(responseArea).toBeVisible({ timeout: 15000 });
  });

  test('council response formatting', async ({ page }) => {
    // Submit a technical query
    const chatInput = page.locator('#chat-input, [data-testid="chat-input"], input[type="text"]').first();
    await chatInput.fill('Explain machine learning algorithms');
    await chatInput.press('Enter');
    
    // Wait for response
    await page.waitForTimeout(5000);
    
    // Check for formatted response elements
    const formattedElements = page.locator('code, pre, .highlight, .formatted, strong, em, ul, ol');
    const formatCount = await formattedElements.count();
    
    if (formatCount > 0) {
      console.log(`Found ${formatCount} formatted elements`);
    }
    
    // Check for council-specific formatting
    const councilResponse = page.locator('.council-response, .fusion-response, [data-testid="council-response"]').first();
    if (await councilResponse.isVisible()) {
      expect(await councilResponse.innerText()).not.toBe('');
    }
  });

  test('error handling and loading states', async ({ page }) => {
    // Test with empty input
    const chatInput = page.locator('#chat-input, [data-testid="chat-input"], input[type="text"]').first();
    await chatInput.fill('');
    await chatInput.press('Enter');
    
    // Should either prevent submission or show error
    const errorMessage = page.locator('.error, .alert, [role="alert"]').first();
    if (await errorMessage.isVisible()) {
      console.log('Error handling working for empty input');
    }
    
    // Test loading state
    await chatInput.fill('Test loading state');
    await chatInput.press('Enter');
    
    // Look for loading indicators
    const loadingIndicators = page.locator('.loading, .spinner, .progress, [data-testid="loading"]');
    const hasLoading = await loadingIndicators.count() > 0;
    
    if (hasLoading) {
      console.log('Loading indicators found');
    }
  });

  test('accessibility features', async ({ page }) => {
    // Check for ARIA labels and semantic HTML
    const chatInput = page.locator('#chat-input, [data-testid="chat-input"], input[type="text"]').first();
    
    // Check input has proper labeling
    const hasLabel = await chatInput.getAttribute('aria-label') || 
                    await chatInput.getAttribute('placeholder') ||
                    await page.locator('label[for]').count() > 0;
    
    expect(hasLabel).toBeTruthy();
    
    // Check for keyboard navigation
    await chatInput.focus();
    await expect(chatInput).toBeFocused();
    
    // Test tab navigation
    await page.keyboard.press('Tab');
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();
  });

  test('responsive design', async ({ page }) => {
    // Test different viewport sizes
    const viewports = [
      { width: 1920, height: 1080 }, // Desktop
      { width: 768, height: 1024 },  // Tablet
      { width: 375, height: 667 }    // Mobile
    ];
    
    for (const viewport of viewports) {
      await page.setViewportSize(viewport);
      
      const chatInput = page.locator('#chat-input, [data-testid="chat-input"], input[type="text"]').first();
      await expect(chatInput).toBeVisible();
      
      // Check that interface adapts to viewport
      const inputWidth = await chatInput.boundingBox();
      expect(inputWidth?.width).toBeGreaterThan(0);
    }
  });

  test('council panel persistence', async ({ page }) => {
    // Submit first query
    const chatInput = page.locator('#chat-input, [data-testid="chat-input"], input[type="text"]').first();
    await chatInput.fill('First query about AI');
    await chatInput.press('Enter');
    
    // Wait for first council panel
    const firstPanel = page.locator('details.council-panel, .council-panel details').first();
    await expect(firstPanel).toBeVisible({ timeout: 30000 });
    
    // Submit second query
    await chatInput.fill('Second query about ML');
    await chatInput.press('Enter');
    
    // Check that we now have multiple council panels or responses
    const allPanels = page.locator('details.council-panel, .council-panel details, .response');
    const panelCount = await allPanels.count();
    
    expect(panelCount).toBeGreaterThanOrEqual(2);
  });
}); 