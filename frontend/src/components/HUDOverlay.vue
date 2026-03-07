<template>
  <div class="hud-overlay" v-if="visible">
    <div class="hud-center">
      <div class="crosshair-horizontal"></div>
      <div class="crosshair-vertical"></div>
      <div class="crosshair-center"></div>
    </div>

    <div class="hud-left">
      <div class="hud-panel">
        <div class="panel-title">高度</div>
        <div class="panel-value">{{ altitude.toFixed(1) }}</div>
        <div class="panel-unit">米</div>
      </div>
    </div>

    <div class="hud-right">
      <div class="hud-panel">
        <div class="panel-title">速度</div>
        <div class="speed-gauge">
          <div class="gauge-bg">
            <svg viewBox="0 0 100 50" class="gauge-svg">
              <path
                d="M 10 50 A 40 40 0 0 1 90 50"
                fill="none"
                stroke="rgba(0, 210, 255, 0.2)"
                stroke-width="8"
                stroke-linecap="round"
              />
              <path
                d="M 10 50 A 40 40 0 0 1 90 50"
                fill="none"
                :stroke="getSpeedColor(speed)"
                stroke-width="8"
                stroke-linecap="round"
                :stroke-dasharray="getSpeedDash(speed)"
                class="gauge-progress"
              />
            </svg>
            <div class="gauge-value">{{ speed.toFixed(0) }}</div>
          </div>
        </div>
        <div class="panel-unit">km/h</div>
      </div>
    </div>

    <div class="hud-bottom-center">
      <div class="hud-panel">
        <div class="panel-title">航向</div>
        <div class="compass">
          <div class="compass-ring" :style="{ transform: `rotate(${heading}deg)` }">
            <span class="compass-mark" v-for="i in 12" :key="i" :style="{ transform: `rotate(${i * 30}deg)` }"></span>
          </div>
          <div class="compass-value">{{ heading.toFixed(0) }}°</div>
        </div>
      </div>
    </div>

    <div class="hud-bottom-right">
      <AttitudeIndicator 
        :pitch="pitch"
        :roll="roll"
        :yaw="yaw"
      />
    </div>

    <div class="hud-corner top-left">
      <div class="corner-info">
        <span class="info-label">模式</span>
        <span class="info-value">跟随</span>
      </div>
    </div>

    <div class="hud-corner top-right">
      <div class="corner-info">
        <span class="info-label">信号</span>
        <span class="info-value signal">强</span>
      </div>
    </div>

    <div class="hud-corner bottom-left">
      <div class="corner-info">
        <span class="info-label">坐标</span>
        <span class="info-value">{{ position.lat.toFixed(4) }}, {{ position.lon.toFixed(4) }}</span>
      </div>
    </div>

    <div class="hud-corner top-right-second">
      <div class="corner-info">
        <span class="info-label">时间</span>
        <span class="info-value">{{ currentTime }}</span>
      </div>
    </div>
  </div>
  
  <ElevationChart 
    :visible="showElevationChart"
    :pathData="pathData"
    @close="showElevationChart = false"
  />
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import AttitudeIndicator from './hud/AttitudeIndicator.vue'
import ElevationChart from './hud/ElevationChart.vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  }
})

const altitude = ref(150.5)
const speed = ref(45.2)
const heading = ref(270.5)
const position = ref({ lat: 39.9042, lon: 116.4074 })
const currentTime = ref('')

const pitch = ref(0)
const roll = ref(0)
const yaw = ref(0)

const showElevationChart = ref(false)
const pathData = ref([])

const getSpeedColor = (speed) => {
  if (speed < 30) return '#00ff88'
  if (speed < 60) return '#00d2ff'
  if (speed < 90) return '#ffd700'
  return '#ff4d4f'
}

const getSpeedDash = (speed) => {
  const maxSpeed = 120
  const percentage = Math.min(speed / maxSpeed, 1)
  const circumference = 2 * Math.PI * 40 * 0.5
  return `${circumference * percentage} ${circumference}`
}

const updateTime = () => {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('zh-CN', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const generatePathData = () => {
  const data = []
  let distance = 0
  let altitude = 50
  for (let i = 0; i < 20; i++) {
    distance += Math.random() * 0.5 + 0.3
    altitude += (Math.random() - 0.5) * 30
    altitude = Math.max(20, Math.min(200, altitude))
    data.push({
      distance: distance,
      altitude: altitude
    })
  }
  return data
}

let updateInterval = null

onMounted(() => {
  updateTime()
  pathData.value = generatePathData()
  
  updateInterval = setInterval(() => {
    updateTime()
    altitude.value = Math.max(0, altitude.value + (Math.random() - 0.5) * 2)
    speed.value = Math.max(0, Math.min(120, speed.value + (Math.random() - 0.5) * 5))
    heading.value = (heading.value + (Math.random() - 0.5) * 2 + 360) % 360
    
    pitch.value = Math.max(-45, Math.min(45, pitch.value + (Math.random() - 0.5) * 3))
    roll.value = Math.max(-30, Math.min(30, roll.value + (Math.random() - 0.5) * 2))
    yaw.value = (yaw.value + (Math.random() - 0.5) * 5 + 360) % 360
  }, 1000)
})

onBeforeUnmount(() => {
  if (updateInterval) clearInterval(updateInterval)
})

defineExpose({
  showElevationChart,
  pathData
})
</script>

<style scoped>
.hud-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  pointer-events: none;
  z-index: 1500;
  background: radial-gradient(circle at center, transparent 0%, rgba(0, 0, 0, 0.1) 100%);
}

.hud-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.crosshair-horizontal {
  position: absolute;
  width: 200px;
  height: 2px;
  background: linear-gradient(to right, transparent, rgba(0, 210, 255, 0.8), transparent);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  box-shadow: 0 0 10px rgba(0, 210, 255, 0.5);
}

.crosshair-vertical {
  position: absolute;
  width: 2px;
  height: 200px;
  background: linear-gradient(to bottom, transparent, rgba(0, 210, 255, 0.8), transparent);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  box-shadow: 0 0 10px rgba(0, 210, 255, 0.5);
}

.crosshair-center {
  position: absolute;
  width: 20px;
  height: 20px;
  border: 2px solid rgba(0, 210, 255, 0.9);
  border-radius: 50%;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  box-shadow: 0 0 15px rgba(0, 210, 255, 0.6), inset 0 0 10px rgba(0, 210, 255, 0.3);
}

.hud-left,
.hud-right,
.hud-bottom-center,
.hud-bottom-right {
  position: absolute;
}

.hud-left {
  top: 50%;
  left: 40px;
  transform: translateY(-50%);
}

.hud-right {
  top: 50%;
  right: 40px;
  transform: translateY(-50%);
}

.hud-bottom-center {
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
}

.hud-bottom-right {
  bottom: 40px;
  right: 40px;
}

.hud-panel {
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(15px);
  border: 1px solid rgba(0, 210, 255, 0.4);
  border-radius: 8px;
  padding: 12px 16px;
  box-shadow: 
    0 0 25px rgba(0, 210, 255, 0.2),
    inset 0 0 30px rgba(0, 210, 255, 0.05);
  animation: fadeIn 0.5s ease-out;
}

.panel-title {
  font-family: 'Orbitron', 'Roboto Mono', monospace;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.6);
  text-transform: uppercase;
  letter-spacing: 2px;
  margin-bottom: 4px;
}

.panel-value {
  font-family: 'Orbitron', 'Roboto Mono', monospace;
  font-size: 32px;
  font-weight: 700;
  color: #00ff88;
  text-shadow: 0 0 15px rgba(0, 255, 136, 0.5);
  line-height: 1;
}

.panel-unit {
  font-family: 'Rajdhani', 'Roboto Mono', monospace;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-top: 4px;
}

.speed-gauge {
  width: 120px;
  height: 60px;
  position: relative;
}

.gauge-bg {
  width: 100%;
  height: 100%;
  position: relative;
}

.gauge-svg {
  width: 100%;
  height: 100%;
}

.gauge-progress {
  transition: stroke-dasharray 0.5s ease;
}

.gauge-value {
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  font-family: 'Orbitron', 'Roboto Mono', monospace;
  font-size: 24px;
  font-weight: 700;
  color: #00d2ff;
  text-shadow: 0 0 10px rgba(0, 210, 255, 0.5);
}

.compass {
  width: 100px;
  height: 100px;
  position: relative;
  border: 2px solid rgba(0, 210, 255, 0.3);
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.5);
}

.compass-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 80px;
  height: 80px;
  transform: translate(-50%, -50%);
  transition: transform 0.5s ease;
}

.compass-mark {
  position: absolute;
  top: 0;
  left: 50%;
  width: 2px;
  height: 8px;
  background: rgba(0, 210, 255, 0.6);
  transform-origin: bottom center;
}

.compass-value {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-family: 'Orbitron', 'Roboto Mono', monospace;
  font-size: 18px;
  font-weight: 700;
  color: #00ff88;
  text-shadow: 0 0 10px rgba(0, 255, 136, 0.5);
}

.hud-corner {
  position: absolute;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(15px);
  border: 1px solid rgba(0, 210, 255, 0.3);
  border-radius: 4px;
  animation: fadeIn 0.5s ease-out;
}

.hud-corner.top-left {
  top: 20px;
  left: 20px;
}

.hud-corner.top-right {
  top: 20px;
  right: 20px;
}

.hud-corner.bottom-left {
  bottom: 20px;
  left: 20px;
}

.hud-corner.top-right-second {
  top: 60px;
  right: 20px;
}

.corner-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.info-label {
  font-family: 'Rajdhani', 'Roboto Mono', monospace;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.info-value {
  font-family: 'Orbitron', 'Roboto Mono', monospace;
  font-size: 14px;
  font-weight: 600;
  color: #00d2ff;
  text-shadow: 0 0 8px rgba(0, 210, 255, 0.4);
}

.info-value.signal {
  color: #00ff88;
  text-shadow: 0 0 8px rgba(0, 255, 136, 0.4);
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: scale(0.9);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
</style>
