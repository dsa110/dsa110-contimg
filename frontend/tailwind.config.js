/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // VASTER-inspired theme colors
        "theme-green": {
          DEFAULT: "#4fc3a1",
          dark: "#3da88a",
          light: "#7ed4bc",
        },
        "theme-blue": {
          DEFAULT: "#324960",
          dark: "#263a4d",
          light: "#4a6580",
        },
        // DSA-110 brand colors
        primary: {
          50: "#f0f9ff",
          100: "#e0f2fe",
          200: "#bae6fd",
          300: "#7dd3fc",
          400: "#38bdf8",
          500: "#0ea5e9",
          600: "#0284c7",
          700: "#0369a1",
          800: "#075985",
          900: "#0c4a6e",
          950: "#082f49",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      boxShadow: {
        card: "0 4px 8px rgba(0, 0, 0, 0.2)",
        "card-hover": "0 6px 12px rgba(0, 0, 0, 0.25)",
      },
    },
  },
  plugins: [],
};
