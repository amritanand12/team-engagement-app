/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#fdf4f5',
          100: '#fbe8eb',
          200: '#f8d5db',
          300: '#f2b5bf',
          400: '#ea889b',
          500: '#de5c77',
          600: '#c93f5c',
          700: '#a82f49',
          800: '#8c293f',
          900: '#772639',
        }
      }
    },
  },
  plugins: [],
}
