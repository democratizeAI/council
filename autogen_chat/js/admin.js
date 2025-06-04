/**
 * Admin interface functionality for AutoGen Council
 * Styled to match the AutoGen Council Evolution Journey frontend
 */

document.addEventListener('DOMContentLoaded', () => {
  const adminForm = document.getElementById('adminForm');
  const cloudToggle = document.getElementById('cloud');
  const budgetInput = document.getElementById('budget');

  // Initialize form with current settings
  async function initializeForm() {
    try {
      // In a real implementation, these would be fetched from the server
      // For now, we'll use mock data
      const settings = {
        cloudEnabled: false,
        budget: 10
      };
      
      cloudToggle.checked = settings.cloudEnabled;
      budgetInput.value = settings.budget;
    } catch (error) {
      showNotification('Error loading settings: ' + error.message, 'error');
    }
  }

  // Handle form submission
  adminForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const cloudEnabled = cloudToggle.checked;
    const budget = parseFloat(budgetInput.value);
    
    if (isNaN(budget) || budget < 1) {
      showNotification('Please enter a valid budget amount', 'error');
      return;
    }
    
    try {
      // In a real implementation, these would be sent to the server
      // For demonstration, we'll simulate the API calls
      await simulateApiCall('/admin/cloud/' + cloudEnabled, 'POST');
      await simulateApiCall('/admin/cap/' + budget, 'POST');
      
      showNotification('Settings updated successfully', 'success');
    } catch (error) {
      showNotification('Error updating settings: ' + error.message, 'error');
    }
  });

  // Simulate API call with a delay
  function simulateApiCall(url, method) {
    return new Promise((resolve) => {
      setTimeout(() => {
        console.log(`${method} ${url}`);
        resolve({ success: true });
      }, 500);
    });
  }

  // Show notification
  function showNotification(message, type = 'success') {
    // Remove any existing notifications
    const existingNotification = document.querySelector('.notification');
    if (existingNotification) {
      existingNotification.remove();
    }
    
    // Create new notification
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.style.borderLeftColor = type === 'success' ? '#10b981' : '#ef4444';
    
    notification.innerHTML = message;
    
    // Add to document
    document.body.appendChild(notification);
    
    // Remove after delay
    setTimeout(() => {
      notification.style.opacity = '0';
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  }

  // Initialize the form
  initializeForm();
});
