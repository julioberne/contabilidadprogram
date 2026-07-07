import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// SOL-06: Code splitting — separar vendors pesados en chunks independientes
export default defineConfig({
  plugins: [react()],
  test: {
    // Vitest — config para tests de hooks React
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test-setup.js',
  },
  build: {
    rollupOptions: {
      output: {
        // Vite 8 (Rolldown) requiere manualChunks como función
        manualChunks(id) {
          if (id.includes('node_modules/@mantine/')) return 'vendor-mantine';
          if (id.includes('node_modules/@blocknote/')) return 'vendor-blocknote';
          if (id.includes('node_modules/react-big-calendar') || id.includes('node_modules/moment')) return 'vendor-calendar';
          if (id.includes('node_modules/@supabase/')) return 'vendor-supabase';
        },
      },
    },
  },
})

