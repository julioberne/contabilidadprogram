/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brutalBg: '#FCF9F2',
        brutalGreen: '#00FF66',
        brutalAmber: '#FFB000',
        brutalCrimson: '#FF3B30',
        brutalNeutral: '#EBE6D8',
      },
      fontFamily: {
        mono: ['"IBM Plex Mono"', 'Courier New', 'monospace'],
      },
      borderWidth: {
        3: '3px',
      },
      boxShadow: {
        brutal: '4px 4px 0px #000000',
        brutalActive: '2px 2px 0px #000000',
      }
    },
  },
  plugins: [],
}
