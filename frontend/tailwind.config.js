/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        dark: {
          900: '#0b0e14',
          850: '#10141d',
          800: '#161b26',
          750: '#1c2230',
          700: '#232a3b',
          600: '#323c52',
        },
        brand: {
          500: '#3b82f6',
          600: '#2563eb',
        },
        bull: {
          DEFAULT: '#10b981',
          light: '#34d399',
          glow: 'rgba(16, 185, 129, 0.2)'
        },
        bear: {
          DEFAULT: '#ef4444',
          light: '#f87171',
          glow: 'rgba(239, 68, 68, 0.2)'
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
