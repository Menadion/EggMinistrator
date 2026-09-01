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
        // The size grade ramp. Peewee -> Jumbo runs light to dark, so the
        // colour carries the order the six names already imply. Warm, to sit on
        // the cream ground, and deliberately low chroma: these are backgrounds
        // behind small text and must never read as a warning, because amber
        // already means "look at this" and red already means defective. The
        // previous palette was teal/sky/amber/orange/violet/rose -- six
        // unrelated hues for ordered data, with Medium landing on a warning
        // colour. Chart strength lives in `sizeChartColors` in components/Ui.jsx.
        grade: {
          100: '#FBF7F0',
          200: '#F5EDE0',
          300: '#EDE0CB',
          400: '#E2CFAF',
          500: '#D4BA8E',
          600: '#C2A169',
          ink: '#3D2F1A',
        },
      },
    },
  },
  plugins: [],
}
