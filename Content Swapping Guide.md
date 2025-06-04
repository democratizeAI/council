# Content Swapping Guide

This guide explains how to easily update the content of your AutoGen Council Evolution Journey frontend.

## Understanding the Content Structure

All content is stored in the `data/content.json` file, which has the following structure:

```json
{
  "title": "Main title at the top",
  "subtitle": "Subtitle text",
  "timeline": "Timeline HTML content",
  "sections": [
    {
      "title": "Section Title",
      "emoji": "🔥", // Optional emoji icon
      "content": "HTML content with formatting"
    },
    // More sections...
  ]
}
```

## How to Update Content

### Basic Information

1. **Title**: Update the `title` field to change the main heading
2. **Subtitle**: Update the `subtitle` field to change the subtitle text
3. **Timeline**: Update the `timeline` field to change the timeline HTML

### Sections

Each section in the `sections` array has:

- **title**: The section heading
- **emoji**: (Optional) An emoji icon that appears before the title
- **content**: The HTML content of the section

### Adding a New Section

To add a new section, add a new object to the `sections` array:

```json
{
  "title": "Your New Section",
  "emoji": "✨", // Optional
  "content": "<p>Your content goes here.</p>"
}
```

### Removing a Section

To remove a section, delete its entire object from the `sections` array.

### Reordering Sections

To change the order of sections, simply rearrange the objects in the `sections` array.

## HTML Formatting Guide

The `content` field uses HTML formatting. Here are common elements:

### Paragraphs

```html
<p>Your paragraph text here.</p>
```

### Headings

```html
<h3>Subsection Heading</h3>
<h4>Sub-subsection Heading</h4>
```

### Lists

Unordered list:
```html
<ul>
  <li>Item one</li>
  <li>Item two</li>
</ul>
```

Ordered list:
```html
<ol>
  <li>First step</li>
  <li>Second step</li>
</ol>
```

### Code Blocks

```html
<pre><code class="language-python">
def example():
    return "This is code"
</code></pre>
```

### Tables

```html
<table>
  <thead>
    <tr>
      <th>Header 1</th>
      <th>Header 2</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Data 1</td>
      <td>Data 2</td>
    </tr>
  </tbody>
</table>
```

### Emphasis

```html
<strong>Bold text</strong>
<em>Italic text</em>
```

### Status Indicators

The frontend automatically converts emoji status indicators:

- 🟢 Success/operational
- 🟠 Warning/in progress
- 🔴 Error/failed

## Testing Your Changes

After updating the content:

1. Open `index.html` in a web browser
2. Verify that your changes appear correctly
3. Check that all formatting is preserved
4. Test on different screen sizes for responsiveness

## Tips for Clean Content

- Keep HTML properly nested and formatted
- Use proper heading hierarchy (h3, h4, etc.)
- Include appropriate spacing between elements
- Maintain consistent formatting across sections
