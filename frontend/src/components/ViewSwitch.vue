<template>
  <div class="view-switch">
    <div class="switch-container">
      <button 
        class="switch-btn"
        :class="{ active: viewMode === '2d' }"
        @click="switchMode('2d')"
      >
        <span class="btn-icon">🗺️</span>
        <span class="btn-text">全局</span>
      </button>
      
      <div class="switch-divider"></div>
      
      <button 
        class="switch-btn"
        :class="{ active: isFollowing }"
        @click="toggleFollow"
      >
        <span class="btn-icon">🎯</span>
        <span class="btn-text">{{ isFollowing ? '取消镜头跟随' : '镜头跟随' }}</span>
      </button>

      <div class="switch-divider"></div>

      <button
        class="switch-btn"
        :class="{ active: trafficActive }"
        @click="toggleTraffic"
      >
        <span class="btn-icon">🚦</span>
        <span class="btn-text">路况</span>
      </button>
    </div>
    
    <div class="switch-status">
      <span class="status-dot" :data-mode="viewMode"></span>
      <span class="status-text">
        {{ viewMode === '2d' ? '全局视图' : (isFollowing ? '镜头跟随中' : '自由视角') }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAudio } from '../hooks/useAudio'

const props = defineProps({
  trafficActive: {
    type: Boolean,
    default: false,
  },
  isFollowing: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['change', 'toggle-traffic', 'toggle-follow'])

const { playClick } = useAudio()

const viewMode = ref('2d')

const switchMode = (mode) => {
  playClick()
  viewMode.value = mode
  emit('change', mode)
}

const toggleFollow = () => {
  playClick()
  emit('toggle-follow')
  // 让 UI 状态与跟随模式保持一致
  viewMode.value = props.isFollowing ? '2d' : '3d'
  emit('change', viewMode.value)
}

const toggleTraffic = () => {
  playClick()
  emit('toggle-traffic')
}

defineExpose({ viewMode })
</script>

<style scoped>
.view-switch {
  position: fixed;
  top: 90px;
  right: 20px;
  z-index: 2000;
}

.switch-container {
  display: flex;
  align-items: center;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 210, 255, 0.4);
  border-radius: 8px;
  padding: 4px;
  box-shadow: 
    0 0 20px rgba(0, 210, 255, 0.2),
    inset 0 0 30px rgba(0, 210, 255, 0.05);
  width: 480px;
  justify-content: center;
  box-sizing: border-box;
}

.switch-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.6);
  padding: 12px 20px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
  min-width: 80px;
}

.switch-btn:hover {
  background: rgba(0, 210, 255, 0.1);
  color: var(--neon-blue);
  transform: scale(1.05);
}

.switch-btn.active {
  background: rgba(0, 210, 255, 0.2);
  color: var(--neon-blue);
  box-shadow: 0 0 15px rgba(0, 210, 255, 0.3);
  border: 1px solid rgba(0, 210, 255, 0.3);
}

.btn-icon {
  font-size: 24px;
  line-height: 1;
}

.btn-text {
  font-family: 'Orbitron', 'Roboto Mono', monospace;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-weight: 600;
}

.switch-divider {
  width: 1px;
  height: 40px;
  background: rgba(0, 210, 255, 0.2);
  margin: 0 4px;
}

.switch-status {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding: 6px 12px;
  background: rgba(0, 0, 0, 0.6);
  border: 1px solid rgba(0, 210, 255, 0.2);
  border-radius: 4px;
  backdrop-filter: blur(10px);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.status-dot[data-mode="2d"] {
  background: #00ff88;
  box-shadow: 0 0 10px #00ff88;
}

.status-dot[data-mode="3d"] {
  background: #ff4d4f;
  box-shadow: 0 0 10px #ff4d4f;
}

.status-text {
  font-family: 'Rajdhani', 'Roboto Mono', monospace;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.8);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(1.2);
  }
}
</style>
