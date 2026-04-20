import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        cookie: {
          50: "#FFF8F0",
          100: "#FFECD6",
          200: "#FFD4A8",
          300: "#FFB870",
          400: "#FF9A3D",
          500: "#F47B20",
          600: "#D65E0A",
          700: "#A8450A",
          800: "#7A320C",
          900: "#4D200A",
        },
      },
    },
  },
  plugins: [],
};

export default config;
