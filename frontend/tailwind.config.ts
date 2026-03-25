import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Golden Hour palette
        parchment: {
          50:  '#fdfaf4',
          100: '#fbf5ec',
          200: '#f5e9d3',
          300: '#ead4b0',
          400: '#d9b882',
        },
        amber: {
          DEFAULT: '#C07D10',
          hover:   '#A86A08',
          light:   '#E8A020',
          muted:   '#C07D1020',
        },
        mahogany: {
          DEFAULT: '#1E1209',
          light:   '#2D1C0E',
          medium:  '#4A3520',
        },
        bark: {
          DEFAULT: '#7A5C3A',
          light:   '#A08060',
        },
      },
      fontFamily: {
        display: ['Teko', 'sans-serif'],
        body:    ['Manrope', 'sans-serif'],
      },
      boxShadow: {
        card:  '0 2px 8px rgba(30, 18, 9, 0.08), 0 1px 3px rgba(30, 18, 9, 0.06)',
        'card-hover': '0 8px 24px rgba(30, 18, 9, 0.14), 0 2px 8px rgba(30, 18, 9, 0.08)',
        panel: '4px 0 24px rgba(30, 18, 9, 0.12)',
      },
    },
  },
  plugins: [],
} satisfies Config
