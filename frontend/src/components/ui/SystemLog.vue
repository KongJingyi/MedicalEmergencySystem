<template>
  <div class="log-container">
    <div class="log-mask"></div>
    <div class="log-list">
      <div v-for="(log, index) in logs" :key="index" class="log-item">
        <span class="time">[{{ log.time }}]</span>
        <span class="type" :class="log.type">{{ log.type.toUpperCase() }}</span>
        <span class="msg">{{ log.message }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

// 暴露给父组件调用：addLog('INFO', '无人机已起飞')
const logs = ref([])

const addLog = (type, message) => {
  const time = new Date().toLocaleTimeString()
  logs.value.unshift({ time, type, message })
  if (logs.value.length > 20) logs.value.pop() // 只保留最近20条
}

defineExpose({ addLog })
</script>

<style scoped>
.log-container {
  height: 150px;
  overflow: hidden;
  position: relative;
  font-family: 'Consolas', monospace;
  font-size: 12px;
}
.log-mask {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 50px;
  background: linear-gradient(to bottom, var(--bg-glass), transparent);
  z-index: 2;
}
.log-list {
  position: relative;
  z-index: 1;
}
.log-item {
  padding: 4px 0;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.1);
  animation: slideDown 0.3s ease-out;
}
.time {
  color: #888;
  margin-right: 10px;
}
.type.info {
  color: var(--neon-blue);
}
.type.warn {
  color: var(--neon-red);
}
.msg {
  color: #fff;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>

