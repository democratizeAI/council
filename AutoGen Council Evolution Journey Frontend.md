# AutoGen Council Evolution Journey Frontend

A beautiful, responsive frontend for the AutoGen Council Evolution Journey story that preserves the rich formatting while making content easily swappable.

## Features

- **Modern Design**: Clean, dark-themed interface with visual hierarchy
- **Responsive Layout**: Works on all devices from mobile to desktop
- **Content Swapping**: Easy content updates via structured JSON
- **Rich Formatting**: Support for all original formatting elements:
  - Emoji section markers
  - Code blocks with syntax highlighting
  - Tables with proper alignment
  - Status indicators
  - Breakthrough moments
- **Navigation**: Table of contents with smooth scrolling
- **Accessibility**: Proper heading structure and contrast

## Files Structure

```
/
├── index.html           # Main HTML file
├── css/
│   └── styles.css       # Custom styling
├── js/
│   ├── app.js           # Main application logic
│   └── content-loader.js # Content loading and processing
└── data/
    └── content.json     # Structured content for easy swapping
```

## How to Use

1. **View the Frontend**: Open `index.html` in any modern web browser

2. **Update Content**: To swap content, simply edit the `data/content.json` file:
   - Update the title, subtitle, or timeline text
   - Modify existing sections or add new ones
   - Each section has a title, optional emoji, and content in HTML format

3. **Content Structure**:
   ```json
   {
     "title": "Main Title",
     "subtitle": "Subtitle Text",
     "timeline": "Timeline HTML",
     "sections": [
       {
         "title": "Section Title",
         "emoji": "🔥", // Optional
         "content": "HTML content with <tags> as needed"
       },
       // More sections...
     ]
   }
   ```

4. **Deploy**: The frontend is static HTML/CSS/JS and can be deployed on any web server

## Technical Implementation

- Built with vanilla JavaScript for maximum compatibility
- Styled with Tailwind CSS and custom CSS
- Uses highlight.js for code syntax highlighting
- No dependencies beyond included CDN resources

## Customization

- **Colors**: Edit the gradient colors in `index.html` and theme colors in `styles.css`
- **Typography**: Adjust font sizes and weights in `styles.css`
- **Layout**: Modify the container width and spacing in `index.html`

## Browser Compatibility

Tested and working in:
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS/Android)
