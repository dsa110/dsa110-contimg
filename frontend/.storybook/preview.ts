import type { Preview } from '@storybook/react-vite';
import '../src/index.css';  // Import Tailwind styles

const preview: Preview = {
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    backgrounds: {
      default: 'light',
      values: [
        { name: 'light', value: '#f9fafb' },
        { name: 'dark', value: '#1f2937' },
        { name: 'white', value: '#ffffff' },
      ],
    },
  },
};

export default preview;
