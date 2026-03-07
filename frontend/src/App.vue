<script setup>
import { onMounted, ref } from 'vue'
import axios from 'axios'
import Dashboard from './components/Dashboard.vue'
import DroneCam from './components/DroneCam.vue'
import PanelBox from './components/ui/PanelBox.vue'
import ResourceRadar from './components/charts/ResourceRadar.vue'
import LoadingScreen from './components/ui/LoadingScreen.vue'
import FleetList from './components/FleetList.vue'
import ViewSwitch from './components/ViewSwitch.vue'
import HUDOverlay from './components/HUDOverlay.vue'
import AlarmModal from './components/AlarmModal.vue'
import BottomPanel from './components/BottomPanel.vue'

// 引入Cesium地图和无人机相关的hook
import { useCesiumMap } from './hooks/useCesiumMap'
import { useDrone } from './hooks/useDrone'
import { useAudio } from './hooks/useAudio'

// 资源列表数据（后端接口获取）
const resources = ref([])
// 医院压力值（用于无人机调度决策）
const hospitalPressure = ref(0)
const selectedResource = ref(null)
const logRef = ref(null)
const bottomPanelRef = ref(null)
const viewMode = ref('2d')
const alarmVisible = ref(false)
const alarmMessage = ref('')
const alarmType = ref('')
const alarmBatteryLevel = ref(null)
const alarmTimestamp = ref('')
// 是否显示所有 UI 控制面板
const showPanels = ref(true)

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

// 解构音频Hook的方法
const { playClick, playRadar, playWarning, stopWarning } = useAudio()

// 包一层，增加系统日志
const dispatch = async (resource) => {
  playClick()
  bottomPanelRef.value?.logRef?.addLog('info', `调度指令下达: ${resource.name}`)
  await droneDispatch(resource)
}

// 从后端接口获取资源列表数据
const fetchResources = async () => {
  try {
    const res = await axios.get('http://127.0.0.1:8000/api/resources')
    playRadar()
    resources.value = res.data
    if (!selectedResource.value && resources.value && resources.value.length > 0) {
      selectedResource.value = resources.value[0]
    }
  } catch (e) {
    console.error('资源列表数据请求失败，请检查接口服务是否正常', e)
  }
}

// 触发报警
const triggerAlarm = (message, type, batteryLevel = null) => {
  alarmMessage.value = message
  alarmType.value = type
  alarmBatteryLevel.value = batteryLevel
  alarmTimestamp.value = new Date().toLocaleTimeString('zh-CN', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
  alarmVisible.value = true
  playWarning()
  bottomPanelRef.value?.logRef?.addLog('warn', `警报触发: ${message}`)
}

// 确认报警
const confirmAlarm = () => {
  stopWarning()
  alarmVisible.value = false
  bottomPanelRef.value?.logRef?.addLog('info', '警报已确认')
}

// 忽略报警
const dismissAlarm = () => {
  stopWarning()
  alarmVisible.value = false
  bottomPanelRef.value?.logRef?.addLog('warn', '警报已忽略')
}

const selectResource = (item) => {
  playClick()
  selectedResource.value = item
}

const selectFleet = (item) => {
  playClick()
  bottomPanelRef.value?.logRef?.addLog('info', `选中机队: ${item.id} (${item.type})`)
  if (item.position && viewerRef.value) {
    viewerRef.value.camera.flyTo({
      destination: {
        longitude: item.position.lon,
        latitude: item.position.lat,
        height: 500
      },
      duration: 2
    })
  }
}

const handleViewChange = (mode) => {
  viewMode.value = mode
  bottomPanelRef.value?.logRef?.addLog('info', `切换视图模式: ${mode === '2d' ? '全局视图' : '驾驶舱视图'}`)
}

const togglePanels = () => {
  showPanels.value = !showPanels.value
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

  <!-- 面板总开关按钮（始终可见） -->
  <button class="ui-toggle-btn" @click="togglePanels">
    {{ showPanels ? '隐藏面板' : '显示面板' }}
  </button>

  <!-- 所有 UI 控制面板：可整体显示 / 隐藏 -->
  <div v-if="showPanels">
    <Dashboard :hospitalPressure="hospitalPressure" />

    <DroneCam 
      v-if="showCamera && activeDroneEntity && viewerRef" 
      :mainViewer="viewerRef" 
      :vehicle="activeDroneEntity" 
      @close="closeCamera"
    />

    <div class="weather-controls">
      <button @click="playClick(); changeWeather('sunny')" title="晴天">☀️</button>
      <button @click="playClick(); changeWeather('rain')" title="下雨">🌧️</button>
      <button @click="playClick(); changeWeather('snow')" title="下雪">❄️</button>
      <button @click="playClick(); changeWeather('fog')" title="大雾">🌫️</button>
    </div>

    <ViewSwitch @change="handleViewChange" />

    <HUDOverlay :visible="viewMode === '3d' && showCamera" />

    <AlarmModal 
      :visible="alarmVisible"
      :message="alarmMessage"
      :type="alarmType"
      :batteryLevel="alarmBatteryLevel"
      :timestamp="alarmTimestamp"
      @confirm="confirmAlarm"
      @dismiss="dismissAlarm"
    />

    <div class="ui-layer">
      <div class="left-panel">
        <PanelBox title="医疗资源应急调度台">
          <div v-if="resources.length === 0" class="loading-text">加载中...</div>
          <div v-else>
            <div 
              v-for="item in resources" 
              :key="item.id"
              class="resource-item"
              :class="{ selected: selectedResource && selectedResource.id === item.id }"
              @click="selectResource(item)"
            >
              <div class="info">
                <div class="name">{{ item.name }}</div>
                <div class="details">
                  <span class="detail">库存: {{ item.stock }}</span>
                  <span class="detail">优先级: {{ item.priority }}</span>
                </div>
              </div>
              <div class="btn-group">
                <button @click.stop="dispatch(item)" class="dispatch-btn">调度</button>
              </div>
            </div>
          </div>
        </PanelBox>
        
        <FleetList @select="selectFleet" />
      </div>

      <div class="bottom-panel">
        <BottomPanel ref="bottomPanelRef" />
      </div>
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

.ui-toggle-btn {
  position: absolute;
  top: 70px;
  right: 20px;
  z-index: 2000;
  background: rgba(0, 0, 0, 0.6);
  border: 1px solid var(--neon-blue);
  color: var(--neon-blue);
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  font-family: 'Rajdhani', 'Roboto Mono', monospace, sans-serif;
  transition: all 0.2s;
}

.ui-toggle-btn:hover {
  background: rgba(0, 210, 255, 0.25);
  box-shadow: 0 0 10px rgba(0, 210, 255, 0.5);
}

.loading-text {
  color: rgba(255, 255, 255, 0.5);
  text-align: center;
  padding: 20px;
  font-family: 'Rajdhani', 'Roboto Mono', monospace, sans-serif;
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

.resource-item .name {
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 6px;
  font-family: 'Rajdhani', 'Roboto Mono', monospace, sans-serif;
}

.resource-item .details {
  display: flex;
  gap: 15px;
}

.resource-item .detail {
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
  font-family: 'Rajdhani', 'Roboto Mono', monospace, sans-serif;
}

.resource-item .btn-group {
  white-space: nowrap;
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.resource-item .dispatch-btn {
  background: linear-gradient(45deg, var(--neon-red), #ff7875);
  border: none;
  color: white;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
  font-family: 'Rajdhani', 'Roboto Mono', monospace, sans-serif;
  text-transform: uppercase;
  letter-spacing: 1px;
  transition: all 0.3s;
}

.resource-item .dispatch-btn:hover {
  transform: scale(1.05);
  box-shadow: 0 0 15px rgba(255, 77, 79, 0.5);
}

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
  width: 480px;
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

.ui-layer .panel-box,
.ui-layer .panel-box * {
  pointer-events: auto;
}

.left-panel {
  width: 320px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.bottom-panel {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  width: 900px;
  max-width: 90vw;
}
</style>
