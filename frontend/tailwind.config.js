/** @type {import('tailwindcss').Config} **/
module.exports = {
  darkMode: "class",
  content: ["./src/**/.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#0B0B10",
        foreground: "#E5E7EB",
        accent: {
          violet: "#7C3AED",
          fuchsia: "#C026D3",
          blue: "#2563EB",
        },
      },
    },
  },
  plugins: [],
};
