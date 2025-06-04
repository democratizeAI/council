# Chat Interface Style Guide

This document outlines the design specifications for restyling the chat interface and all related files to match the AutoGen Council Evolution Journey frontend.

## Color Scheme

### Primary Colors
- Background: `bg-gray-900` (#111827)
- Text: `text-gray-100` (#f3f4f6)
- Accent: `from-blue-400 to-purple-600` gradient
- Highlight: `#a5b4fc` (indigo-300)

### Secondary Colors
- Background (lighter): `bg-gray-800` (#1f2937)
- Text (muted): `text-gray-400` (#9ca3af)
- Border: `border-gray-700` (#374151)
- Success: `#10b981` (green-500)
- Warning: `#f59e0b` (amber-500)
- Error: `#ef4444` (red-500)

## Typography

- Primary Font: System font stack
- Code Font: 'Fira Code', 'Courier New', monospace
- Headings: Bold, larger sizes
- Body Text: Regular weight, good contrast

## Component Styling

### Chat Messages
- User messages: Right-aligned, blue gradient background
- AI responses: Left-aligned, dark background with subtle border
- Timestamps and metadata: Small, muted text
- Code blocks: Dark background with syntax highlighting

### Input Area
- Input field: Dark background, light border, rounded corners
- Send button: Blue-to-purple gradient, white text, rounded

### Admin Controls
- Form elements: Dark backgrounds, light borders
- Buttons: Consistent with chat send button
- Toggles/Checkboxes: Custom styled to match theme

### Monitoring Panels
- Card-based layout with subtle shadows
- Graph containers with rounded corners
- Consistent header styling with main interface

## Layout & Spacing

- Container max width: `max-w-5xl`
- Consistent padding: `p-4` to `p-8` depending on context
- Proper spacing between elements: `mb-2` to `mb-8`
- Responsive adjustments for mobile devices

## Animation & Interaction

- Subtle fade-in animations for new content
- Hover effects for interactive elements
- Smooth transitions for state changes

## Accessibility Considerations

- Sufficient color contrast for text readability
- Focus states for keyboard navigation
- Proper heading hierarchy

## Implementation Notes

- Use Tailwind CSS classes consistently
- Apply custom CSS only when necessary
- Ensure responsive design works on all screen sizes
- Maintain consistent styling across all interfaces
