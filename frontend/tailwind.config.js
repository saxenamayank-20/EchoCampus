/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  // dark mode follows a "dark" class on <html>, so the toggle can switch it
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"] },
      // electric lime. 300-500 are the bright ones (buttons, dots, dark mode text), always with dark text on them.
      // 600+ are deep enough for text and links on a white page
      colors: {
        brand: {
          50: "#f6ffe3", 100: "#ebffc2", 200: "#d6ff8a", 300: "#c4ff52", 400: "#b6ff3b", 500: "#9be51a",
          600: "#4d7c0f", 700: "#3f6212", 800: "#33500f", 900: "#263c0c", 950: "#141f06",
        },
      },
    },
  },
  plugins: [],
};
