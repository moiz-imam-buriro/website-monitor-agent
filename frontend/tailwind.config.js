/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
      colors: {
        page: "var(--page)",
        card: "var(--card)",
        hover: "var(--hover)",
        line: "var(--line)",
        ink: "var(--ink)",
        subtle: "var(--subtle)",
        muted: "var(--muted)",
        accent: "var(--accent)",
        "accent-ink": "var(--accent-ink)",
        overlay: "var(--overlay)",
        up: "var(--up)",
        "up-tint": "var(--up-tint)",
        down: "var(--down)",
        "down-tint": "var(--down-tint)",
        "on-down": "var(--on-down)",
        degraded: "var(--degraded)",
        "degraded-tint": "var(--degraded-tint)",
      },
    },
  },
  plugins: [],
};
