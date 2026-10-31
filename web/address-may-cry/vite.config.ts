import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'node:fs';
import path from 'node:path';

// Fallback resolver for BatchWorkspace before Session B creates it
function batchFallbackPlugin() {
  const batchFilePath = path.resolve(__dirname, 'src/features/batch/BatchWorkspace.tsx');
  const fallbackPath = path.resolve(__dirname, 'src/features/single/BatchStub.tsx');

  return {
    name: 'batch-fallback-resolver',
    resolveId(source: string, importer?: string) {
      if (source.includes('features/batch/BatchWorkspace')) {
        if (!fs.existsSync(batchFilePath)) {
          return fallbackPath;
        }
      }
      return null;
    }
  };
}

export default defineConfig({
  plugins: [batchFallbackPlugin(), react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true
      }
    }
  },
  preview: {
    port: 5173,
    strictPort: true
  }
});
