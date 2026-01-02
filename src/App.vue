<script setup>
import { ref } from 'vue'
import FileUpload from './components/FileUpload.vue'
import ChunkUpload from './components/ChunkUpload.vue'

const activeTab = ref('chunk')
</script>

<template>
  <div class="app-container">
    <a-tabs v-model:activeKey="activeTab" centered class="main-tabs">
      <a-tab-pane key="chunk" tab="大文件分片上传">
        <ChunkUpload />
      </a-tab-pane>
      <a-tab-pane key="simple" tab="普通文件上传">
        <FileUpload />
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app {
  min-height: 100vh;
}

.app-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
}

.main-tabs {
  padding-top: 20px;
}

.main-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 0;
}

.main-tabs :deep(.ant-tabs-tab) {
  color: rgba(255, 255, 255, 0.7);
  font-size: 16px;
  padding: 12px 24px;
}

.main-tabs :deep(.ant-tabs-tab-active .ant-tabs-tab-btn) {
  color: #fff;
  font-weight: 600;
}

.main-tabs :deep(.ant-tabs-ink-bar) {
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  height: 3px;
}
</style>
