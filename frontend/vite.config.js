import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  preview: {
    // Vite's preview server rejects unrecognized Host headers by default
    // (protects against DNS-rebinding locally) — a PaaS host (Railway,
    // Render, ...) puts this behind its own dynamically-assigned domain,
    // which isn't known ahead of time, so that check is disabled here.
    allowedHosts: true,
  },
})
