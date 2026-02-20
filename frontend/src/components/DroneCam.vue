<script setup>
import { onMounted, onBeforeUnmount, ref, toRaw } from 'vue'
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

  removeListener = props.mainViewer.scene.preRender.addEventListener(() => {
    syncCamera()
  })
}

const syncCamera = () => {
  if (!props.vehicle || !miniViewer) return
  
  const time = props.mainViewer.clock.currentTime
  const rawVehicle = toRaw(props.vehicle)
  const position = rawVehicle.position.getValue(time)
  const orientation = rawVehicle.orientation.getValue(time)

  if (position && orientation) {
    const transform = Cesium.Transforms.headingPitchRollToFixedFrame(
        position,
        Cesium.HeadingPitchRoll.fromQuaternion(orientation)
    )

    const hpr = Cesium.HeadingPitchRoll.fromQuaternion(orientation)
    const heading = hpr.heading
    const pitch = hpr.pitch
    const roll = hpr.roll
    
    const lookDownAngle = Cesium.Math.toRadians(15.0) 

    miniViewer.camera.setView({
      destination: position,
      orientation: {
        heading: heading,
        pitch: pitch - lookDownAngle,
        roll: roll
      }
    })
  }
}

onMounted(() => {
  initMiniViewer()
})

onBeforeUnmount(() => {
  if (miniViewer) {
    if (removeListener) removeListener()
    miniViewer.destroy()
  }
})
</script>

<template>
  <PanelBox title="无人机第一视角" class="drone-cam-panel">
    <template #header-extra>
      <span class="rec-dot">●</span>
      <span class="rec-text">REC</span>
      <span class="close-btn" @click="playClick(); $emit('close')">✖</span>
    </template>
    
    <div ref="miniContainer" class="mini-cesium"></div>
    
    <div class="crosshair">
      <svg viewBox="0 0 100 100" width="100%" height="100%">
        <line x1="45" y1="50" x2="55" y2="50" stroke="rgba(0,255,0,0.5)" stroke-width="1"/>
        <line x1="50" y1="45" x2="50" y2="55" stroke="rgba(0,255,0,0.5)" stroke-width="1"/>
      </svg>
    </div>
  </PanelBox>
</template>

<style scoped>
.drone-cam-panel {
  position: absolute;
  bottom: 20px;
  right: 20px;
  width: 450px;
  height: 230px;
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
  margin-right: auto;
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

.mini-cesium {
  width: 100%;
  height: 180px;
  border-radius: 4px;
  overflow: hidden;
}

.crosshair {
  position: absolute;
  top: 50px;
  left: 0;
  width: 100%;
  height: 100px;
  pointer-events: none;
  z-index: 5;
}

@keyframes blink {
  0% { opacity: 1; }
  50% { opacity: 0; }
  100% { opacity: 1; }
}
</style>