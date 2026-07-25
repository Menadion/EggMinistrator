/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        forest: {
          950: '#033018',
          900: '#06451f',
          800: '#075426',
          700: '#0b6d35',
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
