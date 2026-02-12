<template>
  <div class="loading-overlay" :class="{ fading: isFading }" v-if="visible">
    <div class="loader-content">
      <h1 class="glitch-text">SYSTEM INITIALIZING</h1>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progress + '%' }"></div>
      </div>
      <div class="status-text">{{ statusText }} {{ progress }}%</div>
    </div>
    
    <div class="system-info">
      <div class="info-item">STATUS: INITIALIZING</div>
      <div class="info-item">SYSTEM: MEDICAL EMERGENCY RESPONSE</div>
      <div class="info-item">VERSION: 1.0.0</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const visible = ref(true)
const isFading = ref(false)
const progress = ref(0)
const statusText = ref('加载地形数据...')
const statusTexts = [
  '加载地形数据...',
  '初始化无人机系统...',
  '连接医院数据库...',
  '校准传感器...',
  '系统自检中...',
  '准备就绪...'
]

onMounted(() => {
  const totalDuration = 3000 // 3秒
  const steps = 100
  const stepDuration = totalDuration / steps
  
  let currentStep = 0
  const timer = setInterval(() => {
    currentStep++
    progress.value = Math.min(100, (currentStep / steps) * 100)
    
    // 更新状态文本
    const textIndex = Math.floor((progress.value / 100) * statusTexts.length)
    statusText.value = statusTexts[Math.min(textIndex, statusTexts.length - 1)]
    
    if (progress.value >= 100) {
      clearInterval(timer)
      
      // 等待1秒后开始淡出
      setTimeout(() => {
        isFading.value = true
        
        // 淡出动画结束后隐藏
        setTimeout(() => {
          visible.value = false
        }, 1000)
      }, 500)
    }
  }, stepDuration)
})
</script>

<style scoped>
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: #0B1120;
  z-index: 9999;
  display: flex;
  justify-content: center;
  align-items: center;
  transition: opacity 1s ease, visibility 1s ease;
}

.loading-overlay.fading {
  opacity: 0;
}

.loader-content {
  width: 400px;
  text-align: center;
  z-index: 2;
}

.progress-bar {
  height: 4px;
  background: rgba(0, 210, 255, 0.1);
  margin: 20px 0;
  position: relative;
  overflow: hidden;
  border: 1px solid var(--border-color);
  border-radius: 2px;
}

.progress-fill {
  height: 100%;
  background: var(--neon-blue);
  box-shadow: 0 0 10px var(--neon-blue);
  transition: width 0.2s ease;
}

.glitch-text {
  color: var(--neon-blue);
  font-family: 'Orbitron', 'Roboto Mono', monospace, sans-serif;
  letter-spacing: 5px;
  text-transform: uppercase;
  animation: glitch 1s infinite;
  text-shadow: 0 0 10px rgba(0, 210, 255, 0.5);
  margin-bottom: 30px;
}

.status-text {
  color: var(--text-secondary);
  font-size: 12px;
  margin-top: 10px;
  font-family: 'Rajdhani', 'Roboto Mono', monospace, sans-serif;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.system-info {
  position: absolute;
  bottom: 20px;
  left: 20px;
  font-family: 'Roboto Mono', monospace;
  font-size: 10px;
  color: rgba(0, 210, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.info-item {
  margin-bottom: 5px;
  opacity: 0.7;
}

@keyframes glitch {
  0% {
    text-shadow: 2px 0 var(--neon-red), -2px 0 var(--neon-blue);
  }
  50% {
    text-shadow: -2px 0 var(--neon-red), 2px 0 var(--neon-blue);
  }
  100% {
    text-shadow: 2px 0 var(--neon-red), -2px 0 var(--neon-blue);
  }
}
</style>

