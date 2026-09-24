/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{html,ts}"],
  theme: {
    extend: {
      colors: {
        // Identidade visual YKR — Yōkai no Ki Ryūha.
        // "sumi" (墨, nanquim): índigo profundo / quase preto dos fundos.
        sumi: {
          50: "#f4f5fb",
          100: "#e6e8f5",
          200: "#c6cbe6",
          300: "#9aa2d0",
          400: "#6a73b3",
          500: "#474f97",
          600: "#353b78",
          700: "#2a2f5f",
          800: "#1c2044",
          900: "#12152e",
          950: "#0a0c1c",
        },
        // "carmesim" (紅, beni): vermelho carmim das ações e alertas.
        carmesim: {
          50: "#fdf3f4",
          100: "#fbe4e6",
          200: "#f6ccd1",
          300: "#eea3ac",
          400: "#e26f7f",
          500: "#d24457",
          600: "#b32a3f",
          700: "#961f33",
          800: "#7d1d2f",
          900: "#6b1c2c",
          950: "#3b0b14",
        },
        // "ouro" (金, kin): dourado envelhecido dos destaques nobres.
        ouro: {
          50: "#fbf8ef",
          100: "#f4ecd2",
          200: "#e8d6a1",
          300: "#dbbc6f",
          400: "#d0a44f",
          500: "#c48b34",
          600: "#a86f2a",
          700: "#875324",
          800: "#714324",
          900: "#613922",
          950: "#381d10",
        },
      },
      fontFamily: {
        // Fonte display para títulos (com fallback seguro caso não carregue).
        display: ["'Cinzel'", "'Times New Roman'", "serif"],
        sans: ["'Inter'", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
