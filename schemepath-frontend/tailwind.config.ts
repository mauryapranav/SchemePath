import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Status badge palette (mirrors globals.css CSS vars)
        status: {
          confirmed: "#22c55e", // green-500
          one_step:  "#eab308", // yellow-500
          locked:    "#9ca3af", // gray-400
          unknown:   "#6b7280", // gray-500
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
