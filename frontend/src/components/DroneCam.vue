<script setup>
import { onMounted, onBeforeUnmount, ref, toRaw } from 'vue'
import * as Cesium from 'cesium'

// 定义组件接收的属性
const props = defineProps({
  mainViewer: Object, // 主地图的Cesium Viewer实例（父组件传入）
  vehicle: Object     // 无人机的Cesium实体对象（当前选中的无人机）
})

const miniContainer = ref(null)
let miniViewer = null
let removeListener = null

// 初始化迷你Cesium视角容器（无人机第一视角专用）
const initMiniViewer = async () => {
  // 1. 创建迷你窗口的Cesium Viewer，隐藏所有默认控件，仅保留三维场景
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
    creditContainer: document.createElement("div"), // 隐藏Cesium默认的版权信息
    // 加载Cesium全球地形数据，让迷你视角有地形高程
    terrainProvider: await Cesium.createWorldTerrainAsync(),
  })

  // 2. 加载Cesium官方3D建筑瓦片集（透明白色样式，仅做视觉辅助）
  try {
    const tileset = await Cesium.Cesium3DTileset.fromIonAssetId(96188);
    miniViewer.scene.primitives.add(tileset);
    tileset.style = new Cesium.Cesium3DTileStyle({
      color: { conditions: [['true', 'color("white", 0.6)']] }
    });
  } catch (e) { console.error("3D建筑瓦片加载失败", e) }

  // 3. 监听主地图的预渲染事件，实时同步无人机视角到迷你窗口
  // 主地图视角变化时，立即执行同步逻辑，保证视角一致性
  removeListener = props.mainViewer.scene.preRender.addEventListener(() => {
    syncCamera()
  })
}

// 同步主地图的无人机视角到迷你窗口（核心逻辑）
// 参考Cesium官方相机同步方案 + GitHub开源实现优化
const syncCamera = () => {
  if (!props.vehicle || !miniViewer) return
  
  // 获取主地图当前的时间戳（用于获取无人机实时的位置/姿态）
  const time = props.mainViewer.clock.currentTime
  
  // 转换为原始对象（解除Vue的Proxy代理，保证Cesium API正常调用）
  const rawVehicle = toRaw(props.vehicle)
  // 获取无人机当前时间的位置和姿态（四元数）
  const position = rawVehicle.position.getValue(time)
  const orientation = rawVehicle.orientation.getValue(time)

  if (position && orientation) {
    // 1. 根据无人机的位置和姿态，计算出相机的变换矩阵
    const transform = Cesium.Transforms.headingPitchRollToFixedFrame(
        position,
        Cesium.HeadingPitchRoll.fromQuaternion(orientation)
    )

    // 2. 从四元数中解析出无人机的航向、俯仰、翻滚角度
    const hpr = Cesium.HeadingPitchRoll.fromQuaternion(orientation)
    const heading = hpr.heading
    const pitch = hpr.pitch
    const roll = hpr.roll
    
    // 设置相机俯视角度（15度，模拟无人机摄像头向下看的效果）
    const lookDownAngle = Cesium.Math.toRadians(15.0) 

    // 3. 设置迷你窗口的相机视角，与无人机保持同步
    miniViewer.camera.setView({
      destination: position, // 相机位置与无人机完全重合
      orientation: {
        heading: heading, // 航向与无人机保持一致（左右转向）
        pitch: pitch - lookDownAngle, // 俯仰角减去俯视角度，实现向下看
        roll: roll  // 翻滚角与无人机保持一致（机身倾斜）
      }
    })
  }
}

// 组件挂载后初始化迷你视角
onMounted(() => {
  initMiniViewer()
})

// 组件销毁前清理资源，防止内存泄漏
onBeforeUnmount(() => {
  if (miniViewer) {
    if (removeListener) removeListener() // 移除事件监听
    miniViewer.destroy() // 销毁Cesium实例
  }
})
</script>

<template>
  <div class="drone-cam-panel">
    <div class="cam-header">
      <span class="rec-dot">●</span> 
      <span>无人机第一视角 | REC</span>
      <span class="close-btn" @click="$emit('close')">✖</span>
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
  right: 10px;
  z-index: 10;
  color: white;
  font-family: monospace;
  font-size: 12px;
  display: flex;
  align-items: center;
  text-shadow: 1px 1px 2px black;
}

.close-btn {
  margin-left: auto;
  cursor: pointer;
  padding: 0 5px;
  font-size: 14px;
}
.close-btn:hover {
  color: #ff4d4f;
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
  pointer-events: none; /* 避免遮挡鼠标事件，不影响Cesium场景的交互操作 */
  z-index: 5;
}

@keyframes blink {
  0% { opacity: 1; }
  50% { opacity: 0; }
  100% { opacity: 1; }
}
</style>