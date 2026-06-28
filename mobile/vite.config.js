import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    tailwindcss(),
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      workbox: {
        // Ativa novo SW imediatamente — sem esperar fechar todas as abas
        skipWaiting: true,
        clientsClaim: true,
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        runtimeCaching: [
          {
            // Cache das APIs por 5 minutos — permite uso offline com dados recentes
            urlPattern: /\/api\/v1\/(dashboard|animais|producao|financeiro|estoque|sanitario)/,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'milkshow-api',
              networkTimeoutSeconds: 5,
              expiration: { maxEntries: 50, maxAgeSeconds: 300 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
        ],
      },
      manifest: {
        id: '/app/',
        name: 'MilkShow Enterprise',
        short_name: 'MilkShow',
        description: 'Gestão inteligente de fazendas leiteiras — controle de produção, rebanho, finanças e bot WhatsApp',
        theme_color: '#22c55e',
        background_color: '#f1f4f1',
        display: 'standalone',
        orientation: 'portrait',
        scope: '/app/',
        start_url: '/app/',
        categories: ['productivity', 'business', 'utilities'],
        icons: [
          { src: '/app/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
          { src: '/app/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
          { src: '/app/icon.svg',     sizes: 'any',     type: 'image/svg+xml', purpose: 'any' },
        ],
        screenshots: [
          { src: '/app/screenshot-desktop.png', sizes: '1536x864', type: 'image/png', form_factor: 'wide', label: 'Dashboard MilkShow' },
          { src: '/app/screenshot-mobile.png',  sizes: '390x844',  type: 'image/png', form_factor: 'narrow', label: 'MilkShow no celular' },
        ],
      },
    }),
  ],
  server: {
    proxy: {
      '/api': {
        target: 'https://milshow.com.br',
        changeOrigin: true,
        secure: true,
      }
    }
  },
  base: '/app/',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/recharts') || id.includes('node_modules/d3-') || id.includes('node_modules/victory-'))
            return 'vendor-recharts'
          if (id.includes('node_modules/firebase'))
            return 'vendor-firebase'
          if (id.includes('node_modules/lucide-react'))
            return 'vendor-lucide'
          if (id.includes('node_modules/react') || id.includes('node_modules/react-dom') || id.includes('node_modules/react-router'))
            return 'vendor-react'
        },
      },
    },
  },
})
