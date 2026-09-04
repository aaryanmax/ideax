/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        base: "#12151A",
        panel: "#171B21",
        panelAlt: "#1B1F26",
        border: "#2A2F38",
        borderHover: "#3A4048",
        ink: "#E7E4DA",
        muted: "#8B92A0",
        faint: "#5C6270",
        amber: "#D4A24C",
        amberText: "#E7C689",
        verified: "#8FAE7A",
        verifiedText: "#B7CDA6",
        danger: "#C1523A",
        dangerText: "#DE9E8C",
        sensorAccent: "#6F94A8",
      },
      fontFamily: {
        sans: ["Barlow", "sans-serif"],
        cond: ["Barlow Condensed", "sans-serif"],
        mono: ["IBM Plex Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
