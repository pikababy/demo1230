import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  // GitHub Pages 部署需要设置 base URL
  // 本地开发时不需要，只在构建时生效
  base: process.env.VITE_BASE_URL || '/',
})
