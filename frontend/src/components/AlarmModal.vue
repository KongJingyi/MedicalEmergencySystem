<template>
  <div class="alarm-overlay" :class="{ active: visible }">
    <div class="alarm-flash"></div>
    
    <div class="alarm-modal" :class="{ visible }">
      <div class="alarm-header">
        <span class="alarm-icon">⚠️</span>
        <h2 class="alarm-title">系统警报</h2>
      </div>
      
      <div class="alarm-body">
        <div class="alarm-message">
          <p class="alarm-text">{{ message }}</p>
          <div class="alarm-details">
            <div class="detail-item">
              <span class="detail-label">警报类型</span>
              <span class="detail-value">{{ type }}</span>
            </div>
            <div class="detail-item" v-if="batteryLevel !== null">
              <span class="detail-label">当前电量</span>
              <span class="detail-value battery" :class="getBatteryClass(batteryLevel)">
                {{ batteryLevel }}%
              </span>
            </div>
            <div class="detail-item" v-if="timestamp">
              <span class="detail-label">触发时间</span>
              <span class="detail-value">{{ timestamp }}</span>
            </div>
          </div>
        </div>
      </div>
      
      <div class="alarm-footer">
        <button @click="handleConfirm" class="alarm-btn confirm">
          确认
        </button>
        <button @click="handleDismiss" class="alarm-btn dismiss">
          忽略
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  message: {
    type: String,
    default: '警告：电量过低，建议返航！'
  },
  type: {
    type: String,
    default: '电量过低'
  },
  batteryLevel: {
    type: Number,
    default: null
  },
  timestamp: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['confirm', 'dismiss'])

const getBatteryClass = (level) => {
  if (level < 20) return 'critical'
  if (level < 40) return 'warning'
  return 'normal'
}

const handleConfirm = () => {
  emit('confirm')
}

const handleDismiss = () => {
  emit('dismiss')
}

watch(() => props.visible, (newVal) => {
  if (newVal) {
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
  }
})
</script>

<style scoped>
.alarm-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 9999;
  pointer-events: none;
  transition: all 0.3s;
}

.alarm-overlay.active {
  pointer-events: auto;
}

.alarm-flash {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: radial-gradient(circle at center, transparent 0%, rgba(255, 0, 0, 0) 100%);
  opacity: 0;
  transition: opacity 0.3s;
}

.alarm-overlay.active .alarm-flash {
  animation: flashRed 1s infinite;
}

@keyframes flashRed {
  0%, 100% {
    opacity: 0;
    background: radial-gradient(circle at center, transparent 0%, rgba(255, 0, 0, 0) 100%);
  }
  50% {
    opacity: 0.3;
    background: radial-gradient(circle at center, transparent 0%, rgba(255, 0, 0, 0.4) 100%);
  }
}

.alarm-modal {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) scale(0.8);
  width: 500px;
  max-width: 90vw;
  background: rgba(10, 17, 32, 0.95);
  backdrop-filter: blur(20px);
  border: 2px solid rgba(255, 77, 79, 0.8);
  border-radius: 12px;
  box-shadow: 
    0 0 50px rgba(255, 77, 79, 0.5),
    inset 0 0 50px rgba(255, 77, 79, 0.2);
  opacity: 0;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  pointer-events: none;
}

.alarm-modal.visible {
  opacity: 1;
  transform: translate(-50%, -50%) scale(1);
  pointer-events: auto;
}

.alarm-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 24px;
  border-bottom: 2px solid rgba(255, 77, 79, 0.5);
  background: rgba(255, 77, 79, 0.1);
}

.alarm-icon {
  font-size: 32px;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.2);
    opacity: 0.8;
  }
}

.alarm-title {
  flex: 1;
  margin: 0;
  color: #ff4d4f;
  font-family: 'Orbitron', 'Roboto Mono', monospace;
  font-size: 24px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 3px;
  text-shadow: 0 0 15px rgba(255, 77, 79, 0.6);
}

.alarm-body {
  padding: 24px;
}

.alarm-message {
  text-align: center;
}

.alarm-text {
  font-family: 'Rajdhani', 'Roboto Mono', monospace;
  font-size: 18px;
  color: rgba(255, 255, 255, 0.9);
  margin: 0 0 20px 0;
  line-height: 1.6;
}

.alarm-details {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(255, 77, 79, 0.3);
  border-radius: 8px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.1);
}

.detail-item:last-child {
  border-bottom: none;
}

.detail-label {
  font-family: 'Rajdhani', 'Roboto Mono', monospace;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.detail-value {
  font-family: 'Orbitron', 'Roboto Mono', monospace;
  font-size: 16px;
  font-weight: 600;
  color: #ff4d4f;
  text-shadow: 0 0 8px rgba(255, 77, 79, 0.4);
}

.detail-value.battery {
  padding: 4px 12px;
  border-radius: 4px;
  background: rgba(255, 77, 79, 0.1);
}

.detail-value.battery.critical {
  color: #ff4d4f;
  background: rgba(255, 77, 79, 0.2);
  box-shadow: 0 0 10px rgba(255, 77, 79, 0.4);
}

.detail-value.battery.warning {
  color: #ffd700;
  background: rgba(255, 215, 0, 0.1);
  box-shadow: 0 0 10px rgba(255, 215, 0, 0.4);
}

.detail-value.battery.normal {
  color: #00ff88;
  background: rgba(0, 255, 136, 0.1);
  box-shadow: 0 0 10px rgba(0, 255, 136, 0.4);
}

.alarm-footer {
  display: flex;
  gap: 12px;
  padding: 20px 24px;
  border-top: 2px solid rgba(255, 77, 79, 0.5);
  background: rgba(255, 77, 79, 0.05);
}

.alarm-btn {
  flex: 1;
  padding: 14px 24px;
  border: 2px solid;
  border-radius: 8px;
  font-family: 'Orbitron', 'Roboto Mono', monospace;
  font-size: 14px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 2px;
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
}

.alarm-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s;
}

.alarm-btn:hover::before {
  left: 100%;
}

.alarm-btn.confirm {
  background: rgba(255, 77, 79, 0.2);
  border-color: #ff4d4f;
  color: #ff4d4f;
  box-shadow: 0 0 15px rgba(255, 77, 79, 0.3);
}

.alarm-btn.confirm:hover {
  background: rgba(255, 77, 79, 0.3);
  transform: scale(1.05);
  box-shadow: 0 0 20px rgba(255, 77, 79, 0.5);
}

.alarm-btn.dismiss {
  background: rgba(0, 210, 255, 0.1);
  border-color: rgba(0, 210, 255, 0.5);
  color: rgba(0, 210, 255, 0.8);
}

.alarm-btn.dismiss:hover {
  background: rgba(0, 210, 255, 0.2);
  transform: scale(1.05);
  box-shadow: 0 0 15px rgba(0, 210, 255, 0.4);
}
</style>
