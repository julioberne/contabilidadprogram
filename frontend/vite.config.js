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
        // Rolldown (Vite 8): advancedChunks es el mecanismo NATIVO — el shim
        // de manualChunks ignoraba módulos alcanzados estáticamente por el
        // entry, y por eso React (1.4MB junto a BlockNote+Mantine) viajaba en
        // CADA carga inicial (auditoría 2026-09-04). Primer grupo que matchea
        // gana: React va primero para que nadie más lo absorba.
        advancedChunks: {
          // Los grupos NO deben absorber sus dependencias (React vivía dentro
          // de vendor-blocknote por esto y el entry cargaba 1.4MB de editor
          // en cada visita — auditoría 2026-09-04). Cada grupo captura SOLO
          // los módulos que matchean; lo compartido (react) tiene grupo propio.
          includeDependenciesRecursively: false,
          groups: [
            { name: 'vendor-react', test: /node_modules[\\/](react|react-dom|scheduler)[\\/]/ },
            { name: 'vendor-blocknote', test: /node_modules[\\/](@blocknote|@mantine|@tiptap|prosemirror|@emoji-mart|emoji-mart|@floating-ui|@tanstack|yjs|y-prosemirror|lib0|react-icons|tabbable|use-sync-external-store|clsx|orderedmap|rope-sequence|w3c-keyname|fast-deep-equal|@handlewithcare)/ },
            // vendor-calendar RETIRADO (2026-09-11): separar react-big-calendar
            // y moment creaba una dependencia CIRCULAR con el chunk de RRHH
            // (vendor-calendar importaba la fábrica CJS de moment desde
            // ProjectHubApp y RRHH importaba el calendario de vuelta) →
            // "TypeError: ue is not a function" y el módulo RRHH no cargaba.
            // El calendario viaja ahora DENTRO del chunk de RRHH, su único
            // consumidor — no toca el peso del entry (chunk perezoso).
            { name: 'vendor-supabase', test: /node_modules[\\/]@supabase[\\/]/ },
          ],
        },
      },
    },
  },
})

