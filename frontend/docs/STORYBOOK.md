# Storybook Guide

This document explains how Storybook is set up in the DSA-110 Continuum Imaging
Pipeline frontend and best practices for using it during development.

## Overview

[Storybook](https://storybook.js.org/) is a tool for developing UI components in
isolation. It allows us to:

- Build and test components independently from the main application
- Document component APIs and usage patterns
- Catch visual regressions early
- Share a living style guide with the team

## Quick Start

```bash
# Start Storybook development server
cd frontend
npm run storybook

# Build static Storybook for deployment
npm run build-storybook
```

Storybook runs at `http://localhost:6006` by default.

## Configuration

### Main Config (`.storybook/main.ts`)

```typescript
import type { StorybookConfig } from "@storybook/react-vite";

const config: StorybookConfig = {
  stories: ["../src/**/*.stories.@(js|jsx|mjs|ts|tsx)"],
  addons: ["@storybook/addon-docs", "@storybook/addon-a11y"],
  framework: "@storybook/react-vite",
};

export default config;
```

**Key settings:**

- **stories**: Finds all `*.stories.tsx` files in `src/`
- **addons**:
  - `addon-docs`: Auto-generates documentation from stories
  - `addon-a11y`: Accessibility testing panel
- **framework**: Uses Vite for fast builds (matches our main app)

### Preview Config (`.storybook/preview.ts`)

Global decorators and parameters that apply to all stories. This is where we:

- Import global CSS (`index.css` for Tailwind)
- Add context providers if needed
- Set default viewport sizes

## Writing Stories

### File Location

Place story files next to their components:

```
src/components/common/
├── Card.tsx
├── Card.stories.tsx    # Stories for Card
├── QAMetrics.tsx
└── QAMetrics.stories.tsx
```

### Basic Story Structure

```typescript
import type { Meta, StoryObj } from "@storybook/react";
import { MyComponent } from "./MyComponent";

// Meta: Defines the component and its default configuration
const meta: Meta<typeof MyComponent> = {
  title: "Components/MyComponent", // Sidebar location
  component: MyComponent,
  tags: ["autodocs"], // Auto-generate docs page
  parameters: {
    layout: "centered", // or 'fullscreen', 'padded'
  },
  argTypes: {
    // Control types for the Controls panel
    variant: {
      control: "select",
      options: ["primary", "secondary"],
    },
    disabled: { control: "boolean" },
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

// Stories: Different states/variants of the component
export const Default: Story = {
  args: {
    children: "Click me",
  },
};

export const Disabled: Story = {
  args: {
    children: "Disabled button",
    disabled: true,
  },
};
```

### Story Organization

Use the `title` property to organize stories in the sidebar:

```typescript
// Flat structure
title: "Card";

// Nested structure (recommended)
title: "Components/Common/Card";
title: "Components/Layout/AppLayout";
title: "Pages/ImageDetail";
```

Current organization:

- `Components/Common/` - Reusable UI primitives (Card, QAMetrics, etc.)
- Future: `Components/Layout/`, `Components/Provenance/`, `Pages/`

## Existing Stories

### Card (`src/components/common/Card.stories.tsx`)

| Story        | Description                        |
| ------------ | ---------------------------------- |
| Default      | Basic card with title              |
| WithSubtitle | Card with title and subtitle       |
| WithActions  | Card with action buttons in header |
| Hoverable    | Card with hover effect             |
| NoPadding    | Card without body padding          |
| FullExample  | Complete example with all features |

### CoordinateDisplay (`src/components/common/CoordinateDisplay.stories.tsx`)

| Story          | Description                       |
| -------------- | --------------------------------- |
| Default        | Standard RA/Dec display           |
| Compact        | Single-line layout                |
| WithoutDecimal | HMS/DMS only (no decimal degrees) |
| WithLabel      | With custom label prefix          |

### ImageThumbnail (`src/components/common/ImageThumbnail.stories.tsx`)

| Story         | Description              |
| ------------- | ------------------------ |
| Default       | Standard thumbnail       |
| Small         | 100px thumbnail          |
| Large         | 300px thumbnail          |
| NonExpandable | Click-to-expand disabled |

### QAMetrics (`src/components/common/QAMetrics.stories.tsx`)

| Story       | Description              |
| ----------- | ------------------------ |
| Good        | Green "good" grade badge |
| Warning     | Yellow "uncertain" grade |
| Fail        | Red "fail" grade         |
| Compact     | Inline/compact layout    |
| FullMetrics | All metrics displayed    |

## Best Practices

### 1. Write Stories for Every Component

Every reusable component should have stories covering:

- **Default state**: The most common usage
- **Edge cases**: Empty data, loading states, errors
- **Variants**: Different sizes, colors, layouts
- **Interactive states**: Hover, focus, disabled

### 2. Use Args for Dynamic Props

```typescript
// ✅ Good: Use args for configurable props
export const Primary: Story = {
  args: {
    variant: "primary",
    size: "medium",
    children: "Button text",
  },
};

// ❌ Avoid: Hardcoding in render
export const Primary: Story = {
  render: () => <Button variant="primary">Button text</Button>,
};
```

Args enable the Controls panel, making stories interactive.

### 3. Document with JSDoc

```typescript
interface CardProps {
  /** The card's title displayed in the header */
  title: string;
  /** Optional subtitle below the title */
  subtitle?: string;
  /** Whether the card shows a hover effect */
  hoverable?: boolean;
}
```

These comments appear in the auto-generated docs.

### 4. Test Accessibility

The `addon-a11y` panel shows accessibility violations. Check it for:

- Color contrast issues
- Missing ARIA labels
- Keyboard navigation problems

### 5. Use Decorators for Context

If a component needs context (router, state, etc.):

```typescript
// In the story file
const meta: Meta<typeof MyComponent> = {
  component: MyComponent,
  decorators: [
    (Story) => (
      <QueryClientProvider client={queryClient}>
        <Story />
      </QueryClientProvider>
    ),
  ],
};

// Or globally in .storybook/preview.ts
```

## Adding Stories for New Components

1. **Create the story file** next to your component:

   ```bash
   touch src/components/common/NewComponent.stories.tsx
   ```

2. **Copy the template**:

   ```typescript
   import type { Meta, StoryObj } from "@storybook/react";
   import { NewComponent } from "./NewComponent";

   const meta: Meta<typeof NewComponent> = {
     title: "Components/Common/NewComponent",
     component: NewComponent,
     tags: ["autodocs"],
     parameters: {
       layout: "centered",
     },
   };

   export default meta;
   type Story = StoryObj<typeof meta>;

   export const Default: Story = {
     args: {
       // Add default props here
     },
   };
   ```

3. **Add variant stories** for different states

4. **Check in Storybook** - stories hot-reload automatically

## Troubleshooting

### Storybook won't start

```bash
# Clear cache and restart
rm -rf node_modules/.cache/storybook
npm run storybook
```

### Stories not appearing

- Check the file ends with `.stories.tsx`
- Verify the `title` in meta is unique
- Ensure `export default meta` is present

### Component not rendering

- Check if the component needs providers (Router, QueryClient, etc.)
- Add necessary decorators to the story or preview.ts
- Check browser console for errors

### Styles missing

- Ensure `index.css` is imported in `.storybook/preview.ts`
- Tailwind classes should work automatically

## Future Improvements

- [ ] Add stories for page components
- [ ] Add stories for provenance components
- [ ] Set up Chromatic for visual regression testing
- [ ] Deploy static Storybook to GitHub Pages
- [ ] Add interaction tests with `@storybook/test`

## Resources

- [Storybook Docs](https://storybook.js.org/docs)
- [Writing Stories](https://storybook.js.org/docs/writing-stories)
- [Args](https://storybook.js.org/docs/writing-stories/args)
- [Decorators](https://storybook.js.org/docs/writing-stories/decorators)
- [Addon Docs](https://storybook.js.org/docs/writing-docs)
