<template>
  <div class="log-container">
    <div class="log-header">
      <span class="header-icon">📋</span>
      <span class="header-title">SYSTEM LOGS</span>
      <span class="header-status">ACTIVE</span>
    </div>
    
    <div class="log-mask top"></div>
    <div class="log-list" ref="logListRef">
      <div v-for="(log, index) in logs" :key="index" class="log-item">
        <span class="time">[{{ log.time }}]</span>
        <span class="type" :class="log.type">{{ log.type.toUpperCase() }}</span>
        <span class="msg">{{ log.message }}</span>
      </div>
    </div>
    <div class="log-mask bottom"></div>
    
    <div class="log-footer">
      <span class="footer-item">LOG ENTRIES: {{ logs.length }}</span>
      <span class="footer-item">STATUS: STREAMING</span>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'

const logs = ref([])
const logListRef = ref(null)

const addLog = (type, message) => {
  const time = new Date().toLocaleTimeString('zh-CN', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
  logs.value.unshift({ time, type, message })
  if (logs.value.length > 20) logs.value.pop()
  
  // 自动滚动到顶部
  nextTick(() => {
    if (logListRef.value) {
      logListRef.value.scrollTop = 0
    }
  })
}

// 模拟一些初始日志
setTimeout(() => {
  addLog('info', '系统初始化完成')
  addLog('info', '无人机系统就绪')
  addLog('info', '医院数据库连接成功')
}, 1000)

defineExpose({ addLog })
</script>

<style scoped>
.log-container {
  height: 200px;
  overflow: hidden;
  position: relative;
  font-family: 'Roboto Mono', monospace;
  font-size: 11px;
  background: rgba(0, 0, 0, 0.6);
  border: 1px solid rgba(0, 255, 136, 0.3);
  border-radius: 4px;
  box-shadow: 0 0 20px rgba(0, 255, 136, 0.1);
}

.log-header {
  position: relative;
  padding: 8px 12px;
  border-bottom: 1px solid rgba(0, 255, 136, 0.2);
  background: rgba(0, 255, 136, 0.05);
  display: flex;
  align-items: center;
  gap: 10px;
  z-index: 3;
}

.header-icon {
  font-size: 14px;
}

.header-title {
  flex: 1;
  color: #00ff88;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.header-status {
  color: #00ff88;
  font-size: 10px;
  background: rgba(0, 255, 136, 0.1);
  padding: 2px 6px;
  border-radius: 2px;
  text-transform: uppercase;
}

.log-mask {
  position: absolute;
  left: 0;
  width: 100%;
  z-index: 2;
}

.log-mask.top {
  top: 40px;
  height: 30px;
  background: linear-gradient(to bottom, rgba(0, 0, 0, 0.8), transparent);
}

.log-mask.bottom {
  bottom: 30px;
  height: 30px;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.8), transparent);
}

.log-list {
  position: relative;
  z-index: 1;
  height: calc(100% - 70px);
  overflow-y: auto;
  margin-top: 40px;
  padding: 0 12px;
}

.log-item {
  padding: 4px 0;
  border-bottom: 1px dashed rgba(0, 255, 136, 0.1);
  animation: slideDown 0.3s ease-out;
  color: #00ff88;
  text-shadow: 0 0 3px rgba(0, 255, 136, 0.3);
}

.time {
  color: rgba(0, 255, 136, 0.6);
  margin-right: 12px;
  font-size: 10px;
}

.type {
  margin-right: 12px;
  font-size: 10px;
  text-transform: uppercase;
  background: rgba(0, 255, 136, 0.1);
  padding: 1px 4px;
  border-radius: 2px;
}

.type.info {
  color: #00ff88;
}

.type.warn {
  color: #ff4d4f;
  background: rgba(255, 77, 79, 0.1);
}

.msg {
  color: #00ff88;
  word-wrap: break-word;
}

.log-footer {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  padding: 6px 12px;
  border-top: 1px solid rgba(0, 255, 136, 0.2);
  background: rgba(0, 255, 136, 0.05);
  display: flex;
  justify-content: space-between;
  z-index: 3;
}

.footer-item {
  color: rgba(0, 255, 136, 0.6);
  font-size: 10px;
  text-transform: uppercase;
}

/* 自定义滚动条 */
.log-list::-webkit-scrollbar {
  width: 4px;
}

.log-list::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.5);
}

.log-list::-webkit-scrollbar-thumb {
  background: #00ff88;
  border-radius: 2px;
}

.log-list::-webkit-scrollbar-thumb:hover {
  background: #00cc6e;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
    color: rgba(0, 255, 136, 0);
  }
  to {
    opacity: 1;
    transform: translateY(0);
    color: #00ff88;
  }
}
</style>

