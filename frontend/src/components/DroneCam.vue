<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'
import * as Cesium from 'cesium'

// 接收父组件传来的参数
const props = defineProps({
  mainViewer: Object, // 主地图的 viewer 对象 (用来同步时间)
  vehicle: Object     // 无人机实体 (用来获取位置)
})

const miniContainer = ref(null)
let miniViewer = null
let removeListener = null

// 初始化小地图
const initMiniViewer = async () => {
  // 1. 初始化一个“极简模式”的 Cesium Viewer
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
    creditContainer: document.createElement("div"), // 隐藏版权信息
    // 关键：为了性能，如果有地形和建筑，这里也要加上，否则画面不一致
    terrainProvider: await Cesium.createWorldTerrainAsync(),
  })

  // 2. 加载建筑 (跟主地图保持一致)
  try {
    const tileset = await Cesium.Cesium3DTileset.fromIonAssetId(96188);
    miniViewer.scene.primitives.add(tileset);
    tileset.style = new Cesium.Cesium3DTileStyle({
      color: { conditions: [['true', 'color("white", 0.6)']] }
    });
  } catch (e) { console.error(e) }

  // 3. 核心逻辑：每一帧都把相机“钉”在无人机上
  // 监听主地图的渲染事件，同步更新小地图
  removeListener = props.mainViewer.scene.preRender.addEventListener(() => {
    syncCamera()
  })
}

// 相机同步函数 (参考了你提供的 GitHub 代码逻辑)
const syncCamera = () => {
  if (!props.vehicle || !miniViewer) return
  
  // 获取当前时间 (跟主地图同步)
  const time = props.mainViewer.clock.currentTime
  
  // 获取无人机当前的 位置 和 姿态
  const position = props.vehicle.position.getValue(time)
  const orientation = props.vehicle.orientation.getValue(time)

  if (position && orientation) {
    // 1. 计算转换矩阵
    const transform = Cesium.Transforms.headingPitchRollToFixedFrame(
        position,
        Cesium.HeadingPitchRoll.fromQuaternion(orientation)
    )

    // 2. 计算相机的目标位置和方向
    // 这里的逻辑是将相机放在无人机位置，并调整角度
    // 参考了你发的代码：向下看 30 度
    const hpr = Cesium.HeadingPitchRoll.fromQuaternion(orientation)
    const heading = hpr.heading
    const pitch = hpr.pitch
    const roll = hpr.roll
    
    // 微调视角：稍微向下俯视，增强飞行感
    const lookDownAngle = Cesium.Math.toRadians(15.0) 

    miniViewer.camera.setView({
      destination: position, // 相机就在无人机身上
      orientation: {
        heading: heading, // 跟随无人机机头朝向
        pitch: pitch - lookDownAngle, // 稍微低头
        roll: roll  // 跟随侧身
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
  <div class="drone-cam-panel">
    <div class="cam-header">
      <span class="rec-dot">●</span> 
      <span>无人机机载画面 REC</span>
    </div>
    <div ref="miniContainer" class="mini-cesium"></div>
    
    <div class="crosshair">
      <svg viewBox="0 0 100 100" width="100%" height="100%">
        <line x1="45" y1="50" x2="55" y2="50" stroke="rgba(0,255,0,0.5)" stroke-width="1"/>
        <line x1="50" y1="45" x2="50" y2="55" stroke="rgba(0,255,0,0.5)" stroke-width="1"/>
      </svg>
    </div>
  </div>
</template>

<style scoped>
.drone-cam-panel {
  position: absolute;
  bottom: 20px;
  right: 20px;
  width: 320px;
  height: 200px;
  background: #000;
  border: 2px solid #00d2ff;
  border-radius: 4px;
  overflow: hidden;
  z-index: 1000;
  box-shadow: 0 0 20px rgba(0, 0, 0, 0.8);
}

.cam-header {
  position: absolute;
  top: 5px;
  left: 10px;
  z-index: 10;
  color: white;
  font-family: monospace;
  font-size: 12px;
  display: flex;
  align-items: center;
  text-shadow: 1px 1px 2px black;
}

.rec-dot {
  color: red;
  margin-right: 5px;
  animation: blink 1s infinite;
}

.mini-cesium {
  width: 100%;
  height: 100%;
}

.crosshair {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  pointer-events: none; /* 让鼠标穿透，不影响地图操作 */
  z-index: 5;
}

@keyframes blink {
  0% { opacity: 1; }
  50% { opacity: 0; }
  100% { opacity: 1; }
}
</style>

