import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import cesium from 'vite-plugin-cesium' // 1. 引入插件

export default defineConfig({
  plugins: [
    vue(),
    cesium() // 2. 启用插件
  ],
})