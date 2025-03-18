/** @type {import('tailwindcss').Config} */
const typography = require('@tailwindcss/typography')
const primeui = require('tailwindcss-primeui')

module.exports = {
  darkMode: 'class',
  content: [
    "presets/**/*.{js,vue,ts}",
    "assets/themes/formkit.theme.ts"
  ],
  theme: {
    extend: {
      colors: {
        primary: 'rgb(var(--primary))',
        'primary-inverse': 'rgb(var(--primary-inverse))',
        'primary-hover': 'rgb(var(--primary-hover))',
        'primary-active-color': 'rgb(var(--primary-active-color))',

        'primary-highlight': 'rgb(var(--primary)/var(--primary-highlight-opacity))',
        'primary-highlight-inverse': 'rgb(var(--primary-highlight-inverse))',
        'primary-highlight-hover': 'rgb(var(--primary)/var(--primary-highlight-hover-opacity))',

        'primary-50': 'rgb(var(--primary-50))',
        'primary-100': 'rgb(var(--primary-100))',
        'primary-200': 'rgb(var(--primary-200))',
        'primary-300': 'rgb(var(--primary-300))',
        'primary-400': 'rgb(var(--primary-400))',
        'primary-500': 'rgb(var(--primary-500))',
        'primary-600': 'rgb(var(--primary-600))',
        'primary-700': 'rgb(var(--primary-700))',
        'primary-800': 'rgb(var(--primary-800))',
        'primary-900': 'rgb(var(--primary-900))',
        'primary-950': 'rgb(var(--primary-950))',

        'surface-0': 'rgb(var(--surface-0))',
        'surface-50': 'rgb(var(--surface-50))',
        'surface-100': 'rgb(var(--surface-100))',
        'surface-200': 'rgb(var(--surface-200))',
        'surface-300': 'rgb(var(--surface-300))',
        'surface-400': 'rgb(var(--surface-400))',
        'surface-500': 'rgb(var(--surface-500))',
        'surface-600': 'rgb(var(--surface-600))',
        'surface-700': 'rgb(var(--surface-700))',
        'surface-800': 'rgb(var(--surface-800))',
        'surface-900': 'rgb(var(--surface-900))',
        'surface-950': 'rgb(var(--surface-950))'
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace']
      },
      typography:(theme) => ({
        DEFAULT: {
          css: {
            table: {
              fontWeight: 'bold',
              borderCollapse: 'separate',
              borderSpacing: '2rem 1rem',
              '&:hover': {
                color: '#2c5282',
              },
            },
          },
        },
      }),
      backgroundImage: {
        'logo': "url('~/assets/images/TS_Cover_Pattern_Base.svg')",
      },
      animation: {
        "shadow-pop-bl": "shadow-pop-bl 0.3s cubic-bezier(0.470, 0.000, 0.745, 0.715)   both",
        "shadow-pop-br": "shadow-pop-br 0.3s cubic-bezier(0.470, 0.000, 0.745, 0.715)   both"
      },
      keyframes: {
        "shadow-pop-bl": {
          "0%": {
            "box-shadow": "0 0 #3e3e3e, 0 0 #3e3e3e, 0 0 #3e3e3e, 0 0 #3e3e3e, 0 0 #3e3e3e, 0 0 #3e3e3e, 0 0 #3e3e3e, 0 0 #3e3e3e",
            transform: "translateX(0) translateY(0)"
          },
          to: {
            "box-shadow": "-1px 1px #3e3e3e, -2px 2px #3e3e3e, -3px 3px #3e3e3e, -4px 4px #3e3e3e, -5px 5px #3e3e3e, -6px 6px #3e3e3e, -7px 7px #3e3e3e, -8px 8px #3e3e3e",
            transform: "translateX(8px) translateY(-8px)"
          }
        },
        "shadow-pop-br": {
          "0%": {
            "box-shadow": "0 0 #3e3e3e, 0 0 #3e3e3e, 0 0 #3e3e3e, 0 0 #3e3e3e, 0 0 #3e3e3e, 0 0 #3e3e3e, 0 0 #3e3e3e, 0 0 #3e3e3e",
            transform: "translateX(0) translateY(0)"
          },
          to: {
            "box-shadow": "1px 1px #3e3e3e, 2px 2px #3e3e3e, 3px 3px #3e3e3e, 4px 4px #3e3e3e, 5px 5px #3e3e3e, 6px 6px #3e3e3e, 7px 7px #3e3e3e, 8px 8px #3e3e3e",
            transform: "translateX(-8px) translateY(-8px)"
          }
        }
      },
    }
  },
  plugins: [
    typography,
    primeui
  ]
}
