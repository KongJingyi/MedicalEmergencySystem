<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'
import axios from 'axios'
import * as Cesium from 'cesium'
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

// 资源 / 载具列表数据（后端接口获取 or 本地配置）
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
// 图层开关状态
const showHospitals = ref(true)
const showRoadNodes = ref(true)

// 目标医院（用于每架飞机飞向不同医院）
const hospitals = ref([])
const selectedHospitalName = ref('')

// 左上角“医疗资源应急调度台”中展示的 13 台载具
const vehiclePanelList = ref([
  // 10 架城市无人机
  { id: 'D-01', type: '无人机', battery: 92, status: '飞行中', startNode: '西直门桥', position: { lon: 116.3557, lat: 39.9407 } },
  { id: 'D-02', type: '无人机', battery: 88, status: '飞行中', startNode: '北展桥', position: { lon: 116.3427, lat: 39.9387 } },
  { id: 'D-03', type: '无人机', battery: 76, status: '任务中', startNode: '复兴门桥', position: { lon: 116.3566, lat: 39.9071 } },
  { id: 'D-04', type: '无人机', battery: 81, status: '待命', startNode: '建国门桥', position: { lon: 116.4363, lat: 39.9089 } },
  { id: 'D-05', type: '无人机', battery: 69, status: '返航中', startNode: '东直门桥', position: { lon: 116.4339, lat: 39.9408 } },
  { id: 'D-06', type: '无人机', battery: 97, status: '飞行中', startNode: '西直门桥', position: { lon: 116.3557, lat: 39.9407 } },
  { id: 'D-07', type: '无人机', battery: 63, status: '任务中', startNode: '北展桥', position: { lon: 116.3427, lat: 39.9387 } },
  { id: 'D-08', type: '无人机', battery: 58, status: '充电中', startNode: '复兴门桥', position: { lon: 116.3566, lat: 39.9071 } },
  { id: 'D-09', type: '无人机', battery: 84, status: '待命', startNode: '建国门桥', position: { lon: 116.4363, lat: 39.9089 } },
  { id: 'D-10', type: '无人机', battery: 91, status: '飞行中', startNode: '东直门桥', position: { lon: 116.4339, lat: 39.9408 } },
  
  // 3 台救护车
  { id: 'A-01', type: '救护车', battery: 85, status: '行驶中', startNode: '西直门桥', position: { lon: 116.3557, lat: 39.9407 } },
  { id: 'A-02', type: '救护车', battery: 72, status: '待命', startNode: '复兴门桥', position: { lon: 116.3566, lat: 39.9071 } },
  { id: 'A-03', type: '救护车', battery: 91, status: '任务中', startNode: '建国门桥', position: { lon: 116.4363, lat: 39.9089 } },
])

// 解构Cesium地图Hook的方法和响应式对象
const { viewerRef, initMap, toggleLayer } = useCesiumMap()

// 解构无人机Hook的方法和响应式对象，传入地图实例和医院压力值
const {
  activeDroneEntity,
  dispatch: droneDispatch,
  showCamera,
  viewVehicle,
  closeCamera,
  changeWeather,
  telemetry,
  routeProfile,
} = useDrone(viewerRef, hospitalPressure)

// 解构音频Hook的方法
const { playClick, playRadar, playWarning, stopWarning } = useAudio()

// 包一层，增加系统日志
const dispatch = async (resource) => {
  playClick()
  bottomPanelRef.value?.logRef?.addLog('info', `调度指令下达: ${resource.name}`)
  const startNode = vehiclePanelList.value?.[0]?.startNode || '西直门桥'
  const endNode = selectedHospitalName.value || '北京积水潭医院'
  bottomPanelRef.value?.logRef?.addLog(
    'info',
    `调度路径: ${startNode} → ${endNode}`
  )
  await droneDispatch(resource, { startNode, endNode })
}

// 载具调度（左上角 13 台载具列表使用）：镜头飞到对应载具位置
const dispatchVehicle = (item) => {
  playClick()
  bottomPanelRef.value?.logRef?.addLog('info', `调度载具: ${item.id} (${item.type})`)
  if (item.position && viewerRef.value) {
    viewerRef.value.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(
        item.position.lon,
        item.position.lat,
        item.type === '无人机' ? 800 : 500
      ),
      duration: 2,
    })
  }

  // 触发一次真实“调度任务”（起点 = 各自 startNode，终点 = 选择的医院）
  const resource = selectedResource.value || resources.value?.[0]
  if (resource) {
    const endNode = selectedHospitalName.value || '北京积水潭医院'
    bottomPanelRef.value?.logRef?.addLog(
      'info',
      `关联物资调度: ${resource.name} | ${item.startNode} → ${endNode}`
    )
    droneDispatch(resource, { startNode: item.startNode, endNode })
  } else {
    bottomPanelRef.value?.logRef?.addLog('warn', '未加载到物资数据，无法发起路径规划调度')
  }
}

const fetchHospitals = async () => {
  try {
    const res = await axios.get('http://127.0.0.1:8000/api/hospitals')
    hospitals.value = res.data || []
    if (!selectedHospitalName.value && hospitals.value.length > 0) {
      selectedHospitalName.value = hospitals.value[0].name
    }
  } catch (e) {
    console.error('医院数据请求失败，请检查接口服务是否正常', e)
  }
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
      destination: Cesium.Cartesian3.fromDegrees(item.position.lon, item.position.lat, 500),
      duration: 2
    })
  }
}

const handleViewChange = (mode) => {
  viewMode.value = mode
  bottomPanelRef.value?.logRef?.addLog(
    'info',
    `切换视图模式: ${mode === '2d' ? '全局视图' : '驾驶舱视图'}`
  )

  const viewer = viewerRef.value
  if (!viewer) return

  if (mode === '3d') {
    // 恢复 3D 地球形态
    viewer.scene.morphTo3D(1.0)

    // 检查是否有活动的载具
    if (activeDroneEntity.value) {
      setTimeout(() => {
        viewer.trackedEntity = activeDroneEntity.value
        // 设置“驾驶舱”视角的后方偏移：此处用统一偏移
        const offsetDist = -60
        viewer.trackedEntity.viewFrom = new Cesium.Cartesian3(offsetDist, 0.0, 30.0)
      }, 1200)
    } else {
      bottomPanelRef.value?.logRef?.addLog(
        'warn',
        '当前无执行任务的载具，无法进入跟随视角'
      )
    }
  } else if (mode === '2d') {
    // 彻底解除相机锁定
    viewer.trackedEntity = undefined

    // 切换到 2D 模式
    viewer.scene.morphTo2D(1.0)

    // 飞回城市大局观视角
    setTimeout(() => {
      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(116.363, 39.935, 120000),
        duration: 1.5,
      })
    }, 1000)
  }
}

const togglePanels = () => {
  showPanels.value = !showPanels.value
}

const handleSystemAlarm = (e) => {
  const detail = e.detail || {}
  triggerAlarm(detail.message, detail.type, detail.batteryLevel)
}

onMounted(() => {
  // 初始化Cesium地图容器
  initMap('cesiumContainer')
  // 获取资源数据
  fetchResources()
  // 获取医院数据（用于目标选择）
  fetchHospitals()
  // 监听来自深层组件的系统报警事件
  window.addEventListener('system-alarm', handleSystemAlarm)
})

onBeforeUnmount(() => {
  window.removeEventListener('system-alarm', handleSystemAlarm)
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

    <div class="layer-controls">
      <label class="layer-switch">
        <input
          type="checkbox"
          v-model="showHospitals"
          @change="toggleLayer('hospital', showHospitals)"
        />
        <span>医院图层</span>
      </label>
      <label class="layer-switch">
        <input
          type="checkbox"
          v-model="showRoadNodes"
          @change="toggleLayer('road', showRoadNodes)"
        />
        <span>路网节点</span>
      </label>
    </div>

    <ViewSwitch @change="handleViewChange" />

    <HUDOverlay
      :visible="viewMode === '3d' && showCamera"
      :telemetry="telemetry"
      :pathData="routeProfile"
    />

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
          <div style="margin-bottom:10px; display:flex; gap:8px; align-items:center;">
            <span style="color: rgba(255,255,255,0.7); font-size:12px;">目标医院</span>
            <select
              v-model="selectedHospitalName"
              style="flex:1; background:rgba(0,0,0,0.4); color:#fff; border:1px solid rgba(0,210,255,0.3); border-radius:4px; padding:6px 8px; font-size:12px;"
            >
              <option v-for="h in hospitals" :key="h.name" :value="h.name">
                {{ h.name }}
              </option>
            </select>
          </div>
          <div class="vehicle-list">
            <div 
              v-for="item in vehiclePanelList" 
              :key="item.id"
              class="resource-item"
            >
              <div class="info">
                <div class="name">[{{ item.type }}] {{ item.id }}</div>
                <div class="details">
                  <span class="detail">电量: {{ item.battery }}%</span>
                  <span class="detail">状态: {{ item.status }}</span>
                </div>
              </div>
              <div class="btn-group">
                <button @click.stop="dispatchVehicle(item)" class="dispatch-btn">调度</button>
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

.layer-controls {
  position: absolute;
  top: 80px;
  right: 20px;
  z-index: 2000;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: var(--bg-glass);
  backdrop-filter: blur(10px);
  padding: 8px 12px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
  box-shadow: 0 0 12px rgba(0, 210, 255, 0.15);
}

.layer-switch {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-primary);
  font-family: 'Rajdhani', 'Roboto Mono', monospace, sans-serif;
}

.layer-switch input {
  accent-color: var(--neon-blue);
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
  width: clamp(320px, 22vw, 380px);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 左侧载具列表：固定小窗 + 滚轮 */
.vehicle-list {
  max-height: 320px;
  overflow-y: auto;
  padding-right: 4px;
}

.vehicle-list::-webkit-scrollbar {
  width: 4px;
}
.vehicle-list::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.5);
}
.vehicle-list::-webkit-scrollbar-thumb {
  background: var(--neon-blue);
  border-radius: 2px;
}
.vehicle-list::-webkit-scrollbar-thumb:hover {
  background: #00cc6e;
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
