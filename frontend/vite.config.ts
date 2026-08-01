import { defineConfig } from 'vite'
import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    babel({ presets: [reactCompilerPreset()] })
  ],
  server: {
    port: 5176,
    strictPort: true,
    proxy: {
      "/api": {
        target: "https://api.slashus.com",
        changeOrigin: true,
        cookieDomainRewrite: "",
        timeout:300000,
        proxyTimeout: 300000,
      },
      "/uploads": {
        target: "https://api.slashus.com",
        changeOrigin: true,
        cookieDomainRewrite: "",
        timeout:300000,
        proxyTimeout: 300000,
      },
    },
  }
})
