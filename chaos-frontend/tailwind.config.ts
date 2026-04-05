import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        chaos: {
          bg: '#111318',
          panel: '#1A1D24',
          cyan: '#00E5FF',
          red: '#FF4D4D',
          yellow: '#FFD166',
          text: '#A0AEC0'
        }
      }
    },
  },
  plugins: [],
};
export default config;