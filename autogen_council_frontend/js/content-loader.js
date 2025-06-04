/**
 * Content Loader for AutoGen Council Journey
 * Handles the conversion of Markdown content to HTML with proper formatting
 */

class ContentLoader {
  constructor() {
    this.content = null;
    this.toc = [];
  }

  /**
   * Initialize the content loader
   */
  async init() {
    try {
      // Load the content from the data file
      const response = await fetch('data/content.json');
      this.content = await response.json();
      
      // Process the content and render it
      this.renderContent();
      this.buildTableOfContents();
      this.setupEventListeners();
      
      // Initialize code highlighting
      if (window.hljs) {
        document.querySelectorAll('pre code').forEach((el) => {
          hljs.highlightElement(el);
        });
      }
    } catch (error) {
      console.error('Error loading content:', error);
      document.getElementById('content').innerHTML = `
        <div class="bg-red-900 bg-opacity-20 border border-red-700 text-red-100 p-4 rounded-lg">
          <h3 class="text-xl font-bold mb-2">Error Loading Content</h3>
          <p>${error.message || 'Failed to load content. Please try again.'}</p>
        </div>
      `;
    }
  }

  /**
   * Render the main content
   */
  renderContent() {
    const contentContainer = document.getElementById('content');
    
    // Clear existing content
    contentContainer.innerHTML = '';
    
    // Update title and subtitle if available
    if (this.content.title) {
      document.getElementById('main-title').textContent = this.content.title;
    }
    
    if (this.content.subtitle) {
      document.getElementById('subtitle').textContent = this.content.subtitle;
    }
    
    if (this.content.timeline) {
      document.getElementById('timeline').innerHTML = this.content.timeline;
    }
    
    // Render each section
    this.content.sections.forEach((section, index) => {
      const sectionElement = document.createElement('section');
      sectionElement.id = `section-${this.slugify(section.title)}`;
      sectionElement.className = 'content-section mb-16';
      sectionElement.setAttribute('data-section-id', index);
      
      // Add section title with emoji if present
      let titleHTML = `<h2>${section.title}</h2>`;
      if (section.emoji) {
        titleHTML = `<h2><span class="section-emoji">${section.emoji}</span>${section.title}</h2>`;
      }
      
      // Add section content
      sectionElement.innerHTML = `
        ${titleHTML}
        ${this.processContent(section.content)}
      `;
      
      contentContainer.appendChild(sectionElement);
    });
  }

  /**
   * Build the table of contents
   */
  buildTableOfContents() {
    const tocContainer = document.getElementById('toc');
    tocContainer.innerHTML = '';
    
    this.content.sections.forEach((section, index) => {
      const sectionId = `section-${this.slugify(section.title)}`;
      const tocItem = document.createElement('a');
      tocItem.href = `#${sectionId}`;
      tocItem.className = 'nav-item';
      tocItem.setAttribute('data-section', index);
      
      // Add emoji if present
      if (section.emoji) {
        tocItem.innerHTML = `${section.emoji} ${section.title}`;
      } else {
        tocItem.textContent = section.title;
      }
      
      tocContainer.appendChild(tocItem);
    });
  }

  /**
   * Process content with special formatting
   */
  processContent(content) {
    // Replace code blocks with syntax highlighting
    content = this.processCodeBlocks(content);
    
    // Process tables
    content = this.processTables(content);
    
    // Process breakthrough moments
    content = this.processBreakthroughMoments(content);
    
    // Process status indicators
    content = this.processStatusIndicators(content);
    
    return content;
  }

  /**
   * Process code blocks with syntax highlighting
   */
  processCodeBlocks(content) {
    // Replace code blocks with proper formatting and copy button
    return content.replace(
      /<pre><code class="language-(\w+)">([\s\S]*?)<\/code><\/pre>/g, 
      (match, language, code) => {
        return `
          <div class="code-container">
            <div class="code-header">${language}</div>
            <button class="copy-button" data-code="${this.escapeHtml(code.trim())}">Copy</button>
            <pre><code class="language-${language}">${code}</code></pre>
          </div>
        `;
      }
    );
  }

  /**
   * Process tables with enhanced styling
   */
  processTables(content) {
    // Add wrapper for responsive tables
    return content.replace(
      /<table>([\s\S]*?)<\/table>/g,
      '<div class="overflow-x-auto"><table class="table-auto">$1</table></div>'
    );
  }

  /**
   * Process breakthrough moments with special styling
   */
  processBreakthroughMoments(content) {
    // Find content that should be highlighted as breakthrough moments
    return content.replace(
      /<p><strong>The Breakthrough Moment<\/strong>([\s\S]*?)<\/p>/g,
      '<div class="breakthrough"><strong>The Breakthrough Moment</strong>$1</div>'
    );
  }

  /**
   * Process status indicators
   */
  processStatusIndicators(content) {
    // Replace status emojis with styled indicators
    return content
      .replace(/🟢 ([^<]+)/g, '<span class="status"><span class="status-dot status-success"></span>$1</span>')
      .replace(/🟠 ([^<]+)/g, '<span class="status"><span class="status-dot status-warning"></span>$1</span>')
      .replace(/🔴 ([^<]+)/g, '<span class="status"><span class="status-dot status-error"></span>$1</span>');
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    // Copy button functionality
    document.querySelectorAll('.copy-button').forEach(button => {
      button.addEventListener('click', () => {
        const code = button.getAttribute('data-code');
        navigator.clipboard.writeText(code).then(() => {
          const originalText = button.textContent;
          button.textContent = 'Copied!';
          button.style.backgroundColor = 'rgba(16, 185, 129, 0.2)';
          
          setTimeout(() => {
            button.textContent = originalText;
            button.style.backgroundColor = '';
          }, 2000);
        });
      });
    });
    
    // Navigation highlighting
    const navItems = document.querySelectorAll('.nav-item');
    
    const highlightActiveSection = () => {
      const scrollPosition = window.scrollY;
      
      document.querySelectorAll('.content-section').forEach((section, index) => {
        const sectionTop = section.offsetTop;
        const sectionHeight = section.offsetHeight;
        
        if (
          scrollPosition >= sectionTop - 100 && 
          scrollPosition < sectionTop + sectionHeight - 100
        ) {
          navItems.forEach(item => item.classList.remove('active'));
          const activeNav = document.querySelector(`.nav-item[data-section="${index}"]`);
          if (activeNav) {
            activeNav.classList.add('active');
          }
        }
      });
    };
    
    window.addEventListener('scroll', highlightActiveSection);
    highlightActiveSection();
  }

  /**
   * Convert a string to a URL-friendly slug
   */
  slugify(text) {
    return text
      .toString()
      .toLowerCase()
      .replace(/\s+/g, '-')
      .replace(/[^\w\-]+/g, '')
      .replace(/\-\-+/g, '-')
      .replace(/^-+/, '')
      .replace(/-+$/, '');
  }

  /**
   * Escape HTML special characters
   */
  escapeHtml(unsafe) {
    return unsafe
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
}

// Initialize the content loader when the DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const loader = new ContentLoader();
  loader.init();
});
