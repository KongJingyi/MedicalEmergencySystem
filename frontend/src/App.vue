<script setup>
import { onMounted, ref } from 'vue'
import axios from 'axios'
import Dashboard from './components/Dashboard.vue'
import DroneCam from './components/DroneCam.vue'
import PanelBox from './components/ui/PanelBox.vue'
import ResourceRadar from './components/charts/ResourceRadar.vue'
import SystemLog from './components/ui/SystemLog.vue'
import LoadingScreen from './components/ui/LoadingScreen.vue'

// 引入Cesium地图和无人机相关的hook
import { useCesiumMap } from './hooks/useCesiumMap'
import { useDrone } from './hooks/useDrone'

// 资源列表数据（后端接口获取）
const resources = ref([])
// 医院压力值（用于无人机调度决策）
const hospitalPressure = ref(0)
const selectedResource = ref(null)
const logRef = ref(null)

// 解构Cesium地图Hook的方法和响应式对象
const { viewerRef, initMap } = useCesiumMap()

// 解构无人机Hook的方法和响应式对象，传入地图实例和医院压力值
const {
  activeDroneEntity,
  dispatch: droneDispatch,
  showCamera,
  viewVehicle,
  closeCamera,
  changeWeather,
} = useDrone(viewerRef, hospitalPressure)

// 包一层，增加系统日志
const dispatch = async (resource) => {
  logRef.value?.addLog('info', `调度指令下达: ${resource.name}`)
  await droneDispatch(resource)
}

// 从后端接口获取资源列表数据
const fetchResources = async () => {
  try {
    const res = await axios.get('http://127.0.0.1:8000/api/resources')
    resources.value = res.data
    if (!selectedResource.value && resources.value && resources.value.length > 0) {
      selectedResource.value = resources.value[0]
    }
  } catch (e) {
    console.error('资源列表数据请求失败，请检查接口服务是否正常', e)
  }
}

const selectResource = (item) => {
  selectedResource.value = item
}

onMounted(() => {
  // 初始化Cesium地图容器
  initMap('cesiumContainer')
  // 获取资源数据
  fetchResources()
})
</script>

<template>
  <LoadingScreen />
  <div id="cesiumContainer"></div>
  
  <div class="header-bar">
    <h2>无人机调度监控系统 - 医院资源调配可视化平台</h2>
  </div>

  <Dashboard :hospitalPressure="hospitalPressure" />

  <DroneCam 
    v-if="showCamera && activeDroneEntity && viewerRef" 
    :mainViewer="viewerRef" 
    :vehicle="activeDroneEntity" 
    @close="closeCamera"
  />

  <div class="weather-controls">
    <button @click="changeWeather('sunny')" title="晴天">☀️</button>
    <button @click="changeWeather('rain')" title="下雨">🌧️</button>
    <button @click="changeWeather('snow')" title="下雪">❄️</button>
    <button @click="changeWeather('fog')" title="大雾">🌫️</button>
  </div>

  <div class="ui-layer">
    <div class="left-panel">
      <PanelBox title="物资列表">
        <ul style="padding: 0; margin: 0; list-style: none;">
          <li
            v-for="item in resources"
            :key="item.id"
            class="resource-item"
            :class="{ selected: selectedResource && selectedResource.id === item.id }"
            @click="selectResource(item)"
          >
            <div class="info">
              <b>{{ item.name }}</b>
              <span class="tag" v-if="item.urgency_level >= 4">紧急调配</span>
              <br />
              <small>适宜储存温度: {{ item.min_temp }}~{{ item.max_temp }}℃</small>
            </div>
            <div class="btn-group">
              <button @click.stop="dispatch(item)" class="btn-dispatch">调度无人机</button>
              <button @click.stop="viewVehicle(item.id)" class="btn-view" title="第一视角">👁️</button>
            </div>
          </li>
        </ul>
      </PanelBox>

      <PanelBox title="物资属性分析" style="height: 380px;">
        <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
          <ResourceRadar :data="selectedResource" />
        </div>
      </PanelBox>
    </div>

    <div class="bottom-panel">
      <PanelBox title="系统日志">
        <SystemLog ref="logRef" />
      </PanelBox>
    </div>
  </div>
</template>

<style scoped>
#cesiumContainer { width: 100vw; height: 100vh; }
.header-bar {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 60px;
  background: linear-gradient(to bottom, rgba(0,0,0,0.9), rgba(0,0,0,0));
  z-index: 1000;
  display: flex;
  justify-content: center;
  align-items: center;
}
.header-bar h2 {
  color: var(--neon-blue);
  font-family: 'Orbitron', 'Roboto Mono', monospace, sans-serif;
  text-shadow: 0 0 10px var(--neon-blue);
  letter-spacing: 2px;
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}
.resource-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 15px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
  padding-bottom: 10px;
  width: 100%;
  box-sizing: border-box;
}

.resource-item {
  cursor: pointer;
}

.resource-item.selected {
  background: rgba(0, 210, 255, 0.08);
  border-radius: 6px;
  padding: 12px;
  margin-left: -12px;
  margin-right: -12px;
  width: calc(100% + 24px);
}

.resource-item .info {
  flex: 1;
  margin-right: 20px;
}

.resource-item .btn-group {
  white-space: nowrap;
  display: flex;
  align-items: flex-start;
  gap: 10px;
}
.tag { background: var(--neon-red); color: white; padding: 2px 5px; border-radius: 4px; font-size: 12px; margin-left: 5px; }
.btn-group { display: flex; gap: 10px; }
.btn-dispatch { background: linear-gradient(45deg, var(--neon-red), #ff7875); border: none; color: white; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-weight: bold; font-family: 'Rajdhani', 'Roboto Mono', monospace, sans-serif; text-transform: uppercase; letter-spacing: 1px; transition: all 0.3s; }
.btn-dispatch:hover { transform: scale(1.05); box-shadow: 0 0 15px rgba(255, 77, 79, 0.5); }
.btn-view { background: rgba(0, 210, 255, 0.2); border: 1px solid var(--neon-blue); color: var(--neon-blue); padding: 6px 10px; border-radius: 4px; cursor: pointer; transition: all 0.3s; font-family: 'Rajdhani', 'Roboto Mono', monospace, sans-serif; text-transform: uppercase; letter-spacing: 1px; }
.btn-view:hover { background: rgba(0, 210, 255, 0.4); transform: scale(1.05); box-shadow: 0 0 10px rgba(0, 210, 255, 0.4); }

.weather-controls {
  position: absolute;
  top: 20px;
  right: 20px;
  z-index: 2000;
  display: flex;
  gap: 10px;
  background: var(--bg-glass);
  backdrop-filter: blur(10px);
  padding: 10px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
  box-shadow: 0 0 20px rgba(0, 210, 255, 0.1);
  width: 450px;
  justify-content: center;
  box-sizing: border-box;
}
.weather-controls button {
  background: transparent;
  border: 1px solid var(--border-color);
  font-size: 20px;
  cursor: pointer;
  transition: all 0.3s;
  border-radius: 4px;
  padding: 5px 10px;
  color: var(--text-primary);
}
.weather-controls button:hover {
  transform: scale(1.2);
  background: rgba(0, 210, 255, 0.2);
  border-color: var(--neon-blue);
  box-shadow: 0 0 10px rgba(0, 210, 255, 0.4);
}
</style>

<style>
.ui-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  padding: 20px;
  box-sizing: border-box;
  display: flex;
  justify-content: space-between;
}

.ui-layer .sci-fi-panel {
  pointer-events: auto;
}

.left-panel {
  width: 450px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.bottom-panel {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  width: 800px;
  max-width: 90vw;
}
</style>
