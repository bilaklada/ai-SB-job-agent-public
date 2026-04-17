// Tailwind CSS v4 configuration
// Note: v4 uses CSS-first configuration via @import in globals.css
// This file is for IDE support and content paths only

import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  // Tailwind v4 theme customization happens in globals.css via @theme directive
  // Keep this minimal for compatibility
} satisfies Config;

export default config;
