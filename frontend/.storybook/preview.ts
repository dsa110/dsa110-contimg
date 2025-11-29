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
      options: {
        light: { name: 'light', value: '#f9fafb' },
        dark: { name: 'dark', value: '#1f2937' },
        white: { name: 'white', value: '#ffffff' }
      }
    },
  },

  initialGlobals: {
    backgrounds: {
      value: 'light'
    }
  }
};

export default preview;
