/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Custom colors for the forensics theme
        'forensic': {
          'dark': '#1a1f2e',
          'darker': '#0f1219',
          'accent': '#3b82f6',
          'danger': '#ef4444',
          'warning': '#f59e0b',
          'success': '#22c55e',
          'muted': '#6b7280',
        }
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(239, 68, 68, 0.5)' },
          '100%': { boxShadow: '0 0 20px rgba(239, 68, 68, 0.8)' },
        }
      }
    },
  },
  plugins: [],
}