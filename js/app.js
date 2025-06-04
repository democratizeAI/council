/**
 * Main application script for AutoGen Council Journey
 */

document.addEventListener('DOMContentLoaded', () => {
  // Initialize smooth scrolling for navigation
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      e.preventDefault();
      
      const targetId = this.getAttribute('href').substring(1);
      const targetElement = document.getElementById(targetId);
      
      if (targetElement) {
        window.scrollTo({
          top: targetElement.offsetTop - 80,
          behavior: 'smooth'
        });
        
        // Update URL hash without scrolling
        history.pushState(null, null, `#${targetId}`);
      }
    });
  });
  
  // Mobile menu toggle
  const createMobileMenu = () => {
    const header = document.querySelector('header');
    
    // Create mobile menu button
    const mobileMenuBtn = document.createElement('button');
    mobileMenuBtn.className = 'md:hidden fixed bottom-4 right-4 bg-blue-600 text-white p-3 rounded-full shadow-lg z-50';
    mobileMenuBtn.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16m-7 6h7" />
      </svg>
    `;
    
    // Create mobile menu
    const mobileMenu = document.createElement('div');
    mobileMenu.className = 'fixed inset-0 bg-gray-900 bg-opacity-95 z-40 transform translate-x-full transition-transform duration-300 ease-in-out';
    mobileMenu.innerHTML = `
      <div class="flex flex-col h-full p-6">
        <div class="flex justify-end">
          <button id="close-menu" class="text-gray-400 hover:text-white">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div class="flex-grow overflow-auto py-8">
          <div id="mobile-toc" class="flex flex-col space-y-4"></div>
        </div>
      </div>
    `;
    
    document.body.appendChild(mobileMenuBtn);
    document.body.appendChild(mobileMenu);
    
    // Clone TOC items to mobile menu
    const updateMobileToc = () => {
      const mobileToc = document.getElementById('mobile-toc');
      mobileToc.innerHTML = '';
      
      document.querySelectorAll('#toc .nav-item').forEach(item => {
        const clone = item.cloneNode(true);
        clone.className = 'text-gray-200 hover:text-white text-lg py-2';
        mobileToc.appendChild(clone);
      });
    };
    
    // Toggle mobile menu
    mobileMenuBtn.addEventListener('click', () => {
      updateMobileToc();
      mobileMenu.classList.remove('translate-x-full');
    });
    
    document.getElementById('close-menu').addEventListener('click', () => {
      mobileMenu.classList.add('translate-x-full');
    });
    
    // Close menu when clicking a link
    mobileMenu.addEventListener('click', (e) => {
      if (e.target.tagName === 'A') {
        mobileMenu.classList.add('translate-x-full');
      }
    });
  };
  
  createMobileMenu();
  
  // Theme toggle functionality (future enhancement)
  const addThemeToggle = () => {
    const nav = document.querySelector('nav div');
    
    const themeToggle = document.createElement('button');
    themeToggle.className = 'ml-auto bg-gray-700 hover:bg-gray-600 rounded-md p-2';
    themeToggle.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
      </svg>
    `;
    
    nav.appendChild(themeToggle);
    
    // Theme toggle functionality would be implemented here
    themeToggle.addEventListener('click', () => {
      // This is a placeholder for future theme toggle functionality
      console.log('Theme toggle clicked');
    });
  };
  
  // Progress indicator
  const createProgressIndicator = () => {
    const progressBar = document.createElement('div');
    progressBar.className = 'fixed top-0 left-0 h-1 bg-blue-500 z-50 transition-all duration-300';
    progressBar.style.width = '0%';
    
    document.body.appendChild(progressBar);
    
    window.addEventListener('scroll', () => {
      const scrollTop = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const scrollPercent = (scrollTop / docHeight) * 100;
      
      progressBar.style.width = `${scrollPercent}%`;
    });
  };
  
  createProgressIndicator();
  
  // Handle initial hash navigation
  if (window.location.hash) {
    const targetId = window.location.hash.substring(1);
    const targetElement = document.getElementById(targetId);
    
    if (targetElement) {
      setTimeout(() => {
        window.scrollTo({
          top: targetElement.offsetTop - 80,
          behavior: 'smooth'
        });
      }, 500);
    }
  }
  
  // Add scroll to top button
  const addScrollToTopButton = () => {
    const scrollTopBtn = document.createElement('button');
    scrollTopBtn.className = 'fixed bottom-4 left-4 bg-gray-700 text-white p-3 rounded-full shadow-lg z-50 opacity-0 transition-opacity duration-300';
    scrollTopBtn.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18" />
      </svg>
    `;
    
    document.body.appendChild(scrollTopBtn);
    
    window.addEventListener('scroll', () => {
      if (window.scrollY > 500) {
        scrollTopBtn.classList.remove('opacity-0');
        scrollTopBtn.classList.add('opacity-100');
      } else {
        scrollTopBtn.classList.remove('opacity-100');
        scrollTopBtn.classList.add('opacity-0');
      }
    });
    
    scrollTopBtn.addEventListener('click', () => {
      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    });
  };
  
  addScrollToTopButton();
});
