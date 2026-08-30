/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"IBM Plex Sans Variable"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      colors: {
        // One green, derived. #0B5D3B is the brand colour and sits at 800;
        // every other step is the same hue (155deg) at a different lightness.
        // Before this there were eighteen different greens in the app --
        // four tokens, six raw hexes and eight stock Tailwind steps -- and
        // the login screen did not match the sidebar it opened onto.
        forest: {
          50: '#F0F9F6',
          100: '#DEF2EA',
          200: '#BFE3D4',
          300: '#93CDB5',
          400: '#5BB992',
          500: '#31A072',
          600: '#1C8258',
          700: '#116E48',
          800: '#0B5D3B',
          900: '#07462B',
          950: '#032B1A',
        },
        cream: {
          50: '#fffdf8',
          100: '#f8f4e9',
        },
      },
    },
  },
  plugins: [],
}
