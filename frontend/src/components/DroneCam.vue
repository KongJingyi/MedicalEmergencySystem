<script setup>
import { onMounted, onBeforeUnmount, ref, toRaw, computed, watch } from 'vue'
import * as Cesium from 'cesium'
import PanelBox from './ui/PanelBox.vue'
import { useAudio } from '../hooks/useAudio'

const props = defineProps({
  mainViewer: Object,
  vehicle: Object
})

const emit = defineEmits(['close'])
const { playClick } = useAudio()

const miniContainer = ref(null)
let miniViewer = null
let removeListener = null

const thermalMode = ref(false)
const speed = ref(0)
const distance = ref(0)
const altitude = ref(0)
const heading = ref(0)
const pitch = ref(0)
const roll = ref(0)
const displaySpeed = ref(0)
const displayDistance = ref(0)

const toggleThermal = () => {
  playClick()
  thermalMode.value = !thermalMode.value
}

const animateNumber = (current, target, setter, step = 1) => {
  const diff = target - current
  if (Math.abs(diff) < step) {
    setter(target)
    return
  }
  setter(current + Math.sign(diff) * step)
}

let animationFrame = null
let lastUpdateTime = 0

const getMainViewer = () => {
  if (!props.mainViewer) return null
  // 兼容两种传法：Viewer 实例 / ref(Viewer)
  return props.mainViewer?.scene ? props.mainViewer : props.mainViewer?.value || null
}

const bindMainViewerSync = () => {
  const mainViewer = getMainViewer()
  if (!mainViewer || !mainViewer.scene) return
  if (removeListener) {
    removeListener()
    removeListener = null
  }
  removeListener = mainViewer.scene.preRender.addEventListener(() => {
    syncCamera()
  })
}

const updateDisplayValues = () => {
  const now = Date.now()
  if (now - lastUpdateTime > 50) {
    animateNumber(displaySpeed.value, speed.value, (v) => displaySpeed.value = v, 2)
    animateNumber(displayDistance.value, distance.value, (v) => displayDistance.value = v, 0.01)
    lastUpdateTime = now
  }
  animationFrame = requestAnimationFrame(updateDisplayValues)
}

const initMiniViewer = async () => {
  miniViewer = new Cesium.Viewer(miniContainer.value, {
    infoBox: false,
    selectionIndicator: false,
    timeline: false,
    animation: false,
    baseLayerPicker: false,
    homeButton: false,
    geocoder: false,
    navigationHelpButton: false,
    sceneModePicker: false,
    fullscreenButton: false,
    creditContainer: document.createElement("div"),
    terrainProvider: await Cesium.createWorldTerrainAsync(),
  })

  try {
    const tileset = await Cesium.Cesium3DTileset.fromIonAssetId(96188);
    miniViewer.scene.primitives.add(tileset);
    tileset.style = new Cesium.Cesium3DTileStyle({
      color: { conditions: [['true', 'color("white", 0.6)']] }
    });
  } catch (e) { console.error("3D建筑瓦片加载失败", e) }

  bindMainViewerSync()
  
  updateDisplayValues()
}

const syncCamera = () => {
  const mainViewer = getMainViewer()
  if (!props.vehicle || !miniViewer || !mainViewer || !mainViewer.clock) return
  if (miniViewer.isDestroyed && miniViewer.isDestroyed()) return
  
  const time = mainViewer.clock.currentTime
  const rawVehicle = toRaw(props.vehicle)
  if (!rawVehicle || !rawVehicle.position || !rawVehicle.orientation) return
  const position = rawVehicle.position.getValue(time)
  const orientation = rawVehicle.orientation.getValue(time)

  if (position && orientation) {
    const transform = Cesium.Transforms.headingPitchRollToFixedFrame(
        position,
        Cesium.HeadingPitchRoll.fromQuaternion(orientation)
    )

    const hpr = Cesium.HeadingPitchRoll.fromQuaternion(orientation)
    const headingAngle = hpr.heading
    const pitchAngle = hpr.pitch
    const rollAngle = hpr.roll
    
    const lookDownAngle = Cesium.Math.toRadians(15.0) 

    miniViewer.camera.setView({
      destination: position,
      orientation: {
        heading: headingAngle,
        pitch: pitchAngle - lookDownAngle,
        roll: rollAngle
      }
    })
    
    const cartographic = Cesium.Cartographic.fromCartesian(position)
    altitude.value = cartographic.height
    
    speed.value = Math.random() * 30 + 45
    distance.value = Math.random() * 2 + 0.5
    pitch.value = Cesium.Math.toDegrees(pitchAngle)
    roll.value = Cesium.Math.toDegrees(rollAngle)
    heading.value = Cesium.Math.toDegrees(headingAngle)
  }
}

onMounted(() => {
  initMiniViewer()
})

watch(
  () => props.mainViewer,
  () => {
    bindMainViewerSync()
  }
)

onBeforeUnmount(() => {
  if (removeListener) {
    removeListener()
    removeListener = null
  }
  if (animationFrame) {
    cancelAnimationFrame(animationFrame)
  }
  if (miniViewer) {
    miniViewer.destroy()
  }
})
</script>

<template>
  <PanelBox title="无人机第一视角" class="drone-cam-panel">
    <template #header-extra>
      <span class="rec-dot">●</span>
      <span class="rec-text">REC</span>
      <button 
        class="thermal-btn" 
        :class="{ active: thermalMode }"
        @click="toggleThermal"
      >
        🔥 热成像
      </button>
      <span class="close-btn" @click="playClick(); $emit('close')">✖</span>
    </template>
    
    <div class="video-container">
      <div 
        ref="miniContainer" 
        class="mini-cesium"
        :class="{ 'thermal-filter': thermalMode }"
      ></div>
      
      <div class="cockpit-overlay">
        <svg class="crosshair-svg" viewBox="0 0 400 200">
          <defs>
            <filter id="glow">
              <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
          </defs>
          
          <circle cx="200" cy="100" r="40" fill="none" stroke="rgba(0, 255, 136, 0.6)" stroke-width="1" filter="url(#glow)"/>
          <circle cx="200" cy="100" r="60" fill="none" stroke="rgba(0, 255, 136, 0.3)" stroke-width="1" stroke-dasharray="5,5"/>
          <circle cx="200" cy="100" r="80" fill="none" stroke="rgba(0, 255, 136, 0.2)" stroke-width="1" stroke-dasharray="3,7"/>
          
          <line x1="160" y1="100" x2="175" y2="100" stroke="rgba(0, 255, 136, 0.8)" stroke-width="2"/>
          <line x1="225" y1="100" x2="240" y2="100" stroke="rgba(0, 255, 136, 0.8)" stroke-width="2"/>
          <line x1="200" y1="60" x2="200" y2="75" stroke="rgba(0, 255, 136, 0.8)" stroke-width="2"/>
          <line x1="200" y1="125" x2="200" y2="140" stroke="rgba(0, 255, 136, 0.8)" stroke-width="2"/>
          
          <line x1="120" y1="100" x2="140" y2="100" stroke="rgba(0, 255, 136, 0.4)" stroke-width="1"/>
          <line x1="260" y1="100" x2="280" y2="100" stroke="rgba(0, 255, 136, 0.4)" stroke-width="1"/>
          
          <path d="M 200 100 L 200 95 L 205 100 L 200 105 Z" fill="rgba(0, 255, 136, 0.8)"/>
          
          <text x="200" y="30" text-anchor="middle" fill="rgba(0, 255, 136, 0.8)" font-family="Orbitron, monospace" font-size="10" filter="url(#glow)">
            ALT: {{ altitude.toFixed(0) }}m
          </text>
          <text x="200" y="185" text-anchor="middle" fill="rgba(0, 255, 136, 0.8)" font-family="Orbitron, monospace" font-size="10" filter="url(#glow)">
            HDG: {{ heading.toFixed(0) }}°
          </text>
        </svg>
        
        <div class="speed-display">
          <div class="speed-value">
            <span class="speed-number">{{ displaySpeed.toFixed(0) }}</span>
            <span class="speed-unit">km/h</span>
          </div>
          <div class="speed-label">速度</div>
        </div>
        
        <div class="distance-display">
          <div class="distance-value">
            <span class="distance-number">{{ displayDistance.toFixed(2) }}</span>
            <span class="distance-unit">km</span>
          </div>
          <div class="distance-label">剩余距离</div>
        </div>
        
        <div class="mode-indicator" v-if="thermalMode">
          <span class="mode-text">🌡️ 热成像模式</span>
        </div>
        
        <div class="corner-bracket top-left"></div>
        <div class="corner-bracket top-right"></div>
        <div class="corner-bracket bottom-left"></div>
        <div class="corner-bracket bottom-right"></div>
      </div>
    </div>
  </PanelBox>
</template>

<style scoped>
.drone-cam-panel {
  position: absolute;
  bottom: 20px;
  right: 20px;
  width: 480px;
  height: 280px;
  z-index: 1000;
}

.rec-dot {
  color: var(--neon-red);
  margin-right: 5px;
  animation: blink 1s infinite;
  font-size: 14px;
}

.rec-text {
  color: var(--neon-red);
  font-family: 'Orbitron', 'Roboto Mono', monospace, sans-serif;
  font-size: 12px;
  margin-right: 10px;
}

.thermal-btn {
  background: rgba(255, 77, 79, 0.2);
  border: 1px solid rgba(255, 77, 79, 0.4);
  color: #ff4d4f;
  font-family: 'Orbitron', monospace;
  font-size: 10px;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  margin-right: 10px;
  transition: all 0.3s;
}

.thermal-btn:hover {
  background: rgba(255, 77, 79, 0.3);
  box-shadow: 0 0 15px rgba(255, 77, 79, 0.4);
}

.thermal-btn.active {
  background: rgba(255, 77, 79, 0.5);
  box-shadow: 0 0 20px rgba(255, 77, 79, 0.6);
  animation: pulse 1s infinite;
}

.close-btn {
  cursor: pointer;
  padding: 0 5px;
  font-size: 14px;
  color: var(--text-secondary);
  transition: color 0.3s;
}
.close-btn:hover {
  color: var(--neon-red);
}

.video-container {
  position: relative;
  width: 100%;
  height: 220px;
  overflow: hidden;
  border-radius: 4px;
}

.mini-cesium {
  width: 100%;
  height: 100%;
  transition: filter 0.5s ease;
}

.mini-cesium.thermal-filter {
  filter: 
    hue-rotate(180deg) 
    saturate(2) 
    invert(1)
    contrast(1.2);
}

.cockpit-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 5;
}

.crosshair-svg {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
  height: 100%;
}

.speed-display {
  position: absolute;
  top: 15px;
  left: 15px;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 255, 136, 0.4);
  border-radius: 6px;
  padding: 8px 12px;
}

.speed-value {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.speed-number {
  font-family: 'Orbitron', monospace;
  font-size: 28px;
  font-weight: 700;
  color: #00ff88;
  text-shadow: 0 0 15px rgba(0, 255, 136, 0.6);
  animation: numberGlow 0.1s ease-in-out infinite;
}

.speed-unit {
  font-family: 'Rajdhani', monospace;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
}

.speed-label {
  font-family: 'Orbitron', monospace;
  font-size: 9px;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-top: 2px;
}

.distance-display {
  position: absolute;
  top: 15px;
  right: 15px;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 210, 255, 0.4);
  border-radius: 6px;
  padding: 8px 12px;
}

.distance-value {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.distance-number {
  font-family: 'Orbitron', monospace;
  font-size: 28px;
  font-weight: 700;
  color: #00d2ff;
  text-shadow: 0 0 15px rgba(0, 210, 255, 0.6);
  animation: numberGlow 0.1s ease-in-out infinite;
}

.distance-unit {
  font-family: 'Rajdhani', monospace;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
}

.distance-label {
  font-family: 'Orbitron', monospace;
  font-size: 9px;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-top: 2px;
}

.mode-indicator {
  position: absolute;
  bottom: 15px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(255, 77, 79, 0.3);
  border: 1px solid rgba(255, 77, 79, 0.6);
  border-radius: 4px;
  padding: 4px 12px;
}

.mode-text {
  font-family: 'Orbitron', monospace;
  font-size: 11px;
  color: #ff4d4f;
  text-shadow: 0 0 10px rgba(255, 77, 79, 0.5);
  animation: blink 1s infinite;
}

.corner-bracket {
  position: absolute;
  width: 30px;
  height: 30px;
  border: 2px solid rgba(0, 255, 136, 0.5);
}

.corner-bracket.top-left {
  top: 5px;
  left: 5px;
  border-right: none;
  border-bottom: none;
}

.corner-bracket.top-right {
  top: 5px;
  right: 5px;
  border-left: none;
  border-bottom: none;
}

.corner-bracket.bottom-left {
  bottom: 5px;
  left: 5px;
  border-right: none;
  border-top: none;
}

.corner-bracket.bottom-right {
  bottom: 5px;
  right: 5px;
  border-left: none;
  border-top: none;
}

@keyframes blink {
  0% { opacity: 1; }
  50% { opacity: 0.3; }
  100% { opacity: 1; }
}

@keyframes pulse {
  0%, 100% { 
    box-shadow: 0 0 20px rgba(255, 77, 79, 0.6);
  }
  50% { 
    box-shadow: 0 0 30px rgba(255, 77, 79, 0.9);
  }
}

@keyframes numberGlow {
  0%, 100% {
    text-shadow: 0 0 15px rgba(0, 255, 136, 0.6);
  }
  50% {
    text-shadow: 0 0 20px rgba(0, 255, 136, 0.8);
  }
}
</style>
