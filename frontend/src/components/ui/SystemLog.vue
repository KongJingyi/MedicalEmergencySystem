<template>
  <div class="log-container">
    <div class="log-header">
      <span class="header-icon">📋</span>
      <span class="header-title">SYSTEM LOGS</span>
      <div class="header-actions">
        <button @click="clearLogs" class="header-btn" title="清空日志">🗑️</button>
        <button @click="downloadCSV" class="header-btn" title="下载CSV">💾</button>
      </div>
      <span class="header-status">ACTIVE</span>
    </div>
    
    <div class="log-list" ref="logListRef">
      <div v-for="(log, index) in logs" :key="index" class="log-item">
        <span class="time">[{{ log.time }}]</span>
        <span class="type" :class="log.type">{{ log.type.toUpperCase() }}</span>
        <span class="msg">{{ log.message }}</span>
      </div>
    </div>
    
    <div class="log-footer">
      <span class="footer-item">LOG ENTRIES: {{ logs.length }}</span>
      <span class="footer-item">STATUS: STREAMING</span>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { useAudio } from '../../hooks/useAudio'

const logs = ref([])
const logListRef = ref(null)
const { playClick } = useAudio()

const addLog = (type, message) => {
  const time = new Date().toLocaleTimeString('zh-CN', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
  logs.value.push({ time, type, message })
  if (logs.value.length > 20) logs.value.shift()
  
  // 自动滚动到底部
  nextTick(() => {
    if (logListRef.value) {
      logListRef.value.scrollTop = logListRef.value.scrollHeight
    }
  })
}

const clearLogs = () => {
  playClick()
  logs.value = []
}

const downloadCSV = () => {
  playClick()
  if (logs.value.length === 0) return
  
  // 构建CSV内容
  let csvContent = 'Time,Type,Message\n'
  
  // 反转数组，使最新的日志在最后
  const reversedLogs = [...logs.value].reverse()
  
  reversedLogs.forEach(log => {
    const time = log.time
    const type = log.type
    const message = log.message.replace(/"/g, '""') // 转义双引号
    csvContent += `"${time}","${type}","${message}"\n`
  })
  
  // 创建下载链接
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.setAttribute('href', url)
  link.setAttribute('download', `system-logs-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.csv`)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// 模拟一些初始日志
setTimeout(() => {
  addLog('info', '系统初始化完成')
  addLog('info', '无人机系统就绪')
  addLog('info', '医院数据库连接成功')
}, 1000)

defineExpose({ addLog, clearLogs, downloadCSV })
</script>

<style scoped>
.log-container {
  height: 250px;
  overflow: hidden;
  position: relative;
  font-family: 'Roboto Mono', monospace;
  font-size: 11px;
  background: rgba(0, 0, 0, 0.6);
  border: 1px solid rgba(0, 255, 136, 0.3);
  border-radius: 4px;
  box-shadow: 0 0 20px rgba(0, 255, 136, 0.1);
  display: flex;
  flex-direction: column;
}

.log-header {
  flex-shrink: 0;
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

.header-actions {
  display: flex;
  gap: 6px;
}

.header-btn {
  background: rgba(0, 255, 136, 0.1);
  border: 1px solid rgba(0, 255, 136, 0.3);
  color: #00ff88;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.header-btn:hover {
  background: rgba(0, 255, 136, 0.2);
  transform: scale(1.05);
  box-shadow: 0 0 8px rgba(0, 255, 136, 0.4);
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
  display: none;
}

.log-list {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 8px 12px;
  scroll-behavior: smooth;
  min-height: 0;
}

.log-item {
  padding: 6px 0;
  border-bottom: 1px dashed rgba(0, 255, 136, 0.1);
  animation: slideIn 0.3s ease-out;
  color: #00ff88;
  text-shadow: 0 0 3px rgba(0, 255, 136, 0.3);
  line-height: 1.4;
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
  flex-shrink: 0;
  padding: 10px 12px 6px 12px;
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
  width: 8px;
}

.log-list::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
}

.log-list::-webkit-scrollbar-thumb {
  background: linear-gradient(to bottom, #00ff88, #00cc6e);
  border-radius: 4px;
  box-shadow: 0 0 5px rgba(0, 255, 136, 0.3);
}

.log-list::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(to bottom, #00ff88, #00aa55);
  box-shadow: 0 0 8px rgba(0, 255, 136, 0.5);
}

.log-list::-webkit-scrollbar-thumb:active {
  background: #00aa55;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-10px);
    color: rgba(0, 255, 136, 0);
  }
  to {
    opacity: 1;
    transform: translateX(0);
    color: #00ff88;
  }
}
</style>

