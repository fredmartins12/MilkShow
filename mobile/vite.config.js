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
        name: 'MilkShow Enterprise',
        short_name: 'MilkShow',
        description: 'Gestão inteligente de fazendas leiteiras',
        theme_color: '#020617',
        background_color: '#020617',
        display: 'standalone',
        orientation: 'portrait',
        scope: '/app/',
        start_url: '/app/',
        icons: [
          { src: '/app/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/app/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
        ],
      },
    }),
  ],
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
