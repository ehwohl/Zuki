import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['noise.svg'],
      manifest: {
        name: 'Zuki-OS',
        short_name: 'Zuki',
        description: 'Personal operating center — High Tech, Low Life',
        theme_color: '#0A0C10',
        background_color: '#0A0C10',
        display: 'standalone',
        display_override: ['window-controls-overlay', 'standalone'],
        icons: [
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png' },
        ],
      },
    }),
  ],
  build: {
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom'],
          'vendor-three': ['three', '@pixiv/three-vrm'],
          'vendor-d3': ['d3', 'topojson-client'],
          'vendor-motion': ['framer-motion'],
          'vendor-state': ['zustand'],
        },
      },
    },
  },
  server: {
    port: 5173,
  },
})
