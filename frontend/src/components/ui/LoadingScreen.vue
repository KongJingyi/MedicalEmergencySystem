<template>
  <div class="loading-overlay" v-if="visible">
    <div class="loader-content">
      <h1 class="glitch-text">SYSTEM INITIALIZING</h1>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progress + '%' }"></div>
      </div>
      <div class="status-text">加载地形数据... {{ progress }}%</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const visible = ref(true)
const progress = ref(0)

onMounted(() => {
  // 模拟加载过程
  const timer = setInterval(() => {
    progress.value += Math.floor(Math.random() * 10)
    if (progress.value >= 100) {
      progress.value = 100
      clearInterval(timer)
      setTimeout(() => {
        visible.value = false
      }, 500) // 稍微停顿后消失
    }
  }, 200)
})
</script>

<style scoped>
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: #000;
  z-index: 9999;
  display: flex;
  justify-content: center;
  align-items: center;
}
.loader-content {
  width: 400px;
  text-align: center;
}
.progress-bar {
  height: 4px;
  background: #333;
  margin: 20px 0;
  position: relative;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: var(--neon-blue);
  box-shadow: 0 0 10px var(--neon-blue);
  transition: width 0.2s;
}
.glitch-text {
  color: #fff;
  letter-spacing: 5px;
  animation: glitch 1s infinite;
}
.status-text {
  color: rgba(255, 255, 255, 0.8);
  font-size: 12px;
  margin-top: 6px;
}

@keyframes glitch {
  0% {
    text-shadow: 2px 0 red, -2px 0 blue;
  }
  50% {
    text-shadow: -2px 0 red, 2px 0 blue;
  }
  100% {
    text-shadow: 2px 0 red, -2px 0 blue;
  }
}
</style>

