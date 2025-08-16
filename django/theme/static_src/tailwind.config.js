module.exports = {
  content: [
    '../../templates/**/*.html',
    '../../../v1/templates/**/*.html',
  ],
  theme: {
    extend: {},
  },
  plugins: [require('daisyui')],
  daisyui: {
    themes: ['light', 'dark'],
  },
}
