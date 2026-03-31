<script setup>
import { onMounted, onBeforeUnmount, ref, reactive, computed } from 'vue'
import axios from 'axios'
import * as Cesium from 'cesium'
import Dashboard from './components/Dashboard.vue'
import DroneCam from './components/DroneCam.vue'
import PanelBox from './components/ui/PanelBox.vue'
import LoadingScreen from './components/ui/LoadingScreen.vue'
import ViewSwitch from './components/ViewSwitch.vue'
import HUDOverlay from './components/HUDOverlay.vue'
import AlarmModal from './components/AlarmModal.vue'
import BottomPanel from './components/BottomPanel.vue'

// 引入Cesium地图和无人机相关的hook
import { useCesiumMap } from './hooks/useCesiumMap'
import { useDrone } from './hooks/useDrone'
import { useAudio } from './hooks/useAudio'
import { useLocalWeather } from './hooks/useLocalWeather'

const resources = ref([])
const hospitals = ref([])
const hospitalPressure = ref(0)
const bottomPanelRef = ref(null)
const viewMode = ref('2d')
const showPanels = ref(true)
const showHospitals = ref(true)
const showRoadNodes = ref(true)

const alarmVisible = ref(false)
const alarmMessage = ref('')
const alarmType = ref('')
const alarmBatteryLevel = ref(null)
const alarmTimestamp = ref('')

// ================= 🌟 业务闭环核心状态 =================
// 1. 表单双向绑定
const selectedStartNode = ref('西直门桥') // 默认发货仓
const selectedEndNode = ref('') // 目标医院
const selectedResource = ref(null) // 调拨物资
const dispatchQuantity = ref(10) // 派发数量

const hospitalNeeds = ref({})

const currentNeeds = computed(() => {
  if (!selectedEndNode.value || !hospitalNeeds.value) return {}
  return hospitalNeeds.value[selectedEndNode.value] || {}
})

// 🌟 拉取后端物资缺口数据 (如果你后端还没写好接口，就先用这个完美匹配 JSON 的备用数据)
const fetchHospitalNeeds = async () => {
  try {
    const res = await axios.get('http://127.0.0.1:8000/api/hospital_needs')
    hospitalNeeds.value = res.data
  } catch (e) {
    console.log('未连接实时缺口接口，使用本地完美映射的演示数据')
    // 🚨 核心修改：这里的 Key 必须和 resources.json 里的 name 一字不差！
    hospitalNeeds.value = {
      '北京积水潭医院': {
        'RhD阴性O型红细胞悬液（稀有血型/冷链）': 15,
        'ECMO一次性耗材包（紧急体外循环/高价值）': 2,
        '破伤风人免疫球蛋白TIG（外伤暴露/急）': 30,
        '急诊手术缝合包（无菌/手术耗材）': 120,
      },
      '北京大学人民医院': {
        '去甲肾上腺素注射液（升压/抢救）': 50,
        '人白蛋白 20%（扩容/肝衰/稀缺）': 20,
        '冷沉淀（Cryoprecipitate，凝血因子/冷链）': 10,
        '甲型流感抗病毒药奥司他韦（流行季/急需）': 80,
      },
      '北京协和医院': {
        'mRNA疫苗（-80℃超低温/冷链）': 200,
        '狂犬病免疫球蛋白RIG（暴露后急需/冷链）': 15,
        '主动脉球囊反搏IABP耗材包（心源性休克/急）': 3,
        '重组组织型纤溶酶原激活剂rt-PA（卒中溶栓/急）': 8,
      },
    }
  }
}

const startNodes = ['西直门桥', '北展桥', '复兴门桥', '建国门桥', '东直门桥', '德胜门桥']

// ================= 🌟 机队指挥中心状态 =================
// 使用 reactive 让状态可变，真实模拟机队
const fleetList = reactive([
  { id: 'D-01', type: '无人机', battery: 100, status: '待命', startNode: '西直门桥', position: { lon: 116.3557, lat: 39.9407 } },
  { id: 'D-02', type: '无人机', battery: 98, status: '待命', startNode: '北展桥', position: { lon: 116.3427, lat: 39.9387 } },
  { id: 'D-03', type: '无人机', battery: 76, status: '任务中', startNode: '复兴门桥', position: { lon: 116.3566, lat: 39.9071 } },
  { id: 'D-04', type: '无人机', battery: 100, status: '待命', startNode: '建国门桥', position: { lon: 116.4363, lat: 39.9089 } },
  { id: 'D-05', type: '无人机', battery: 69, status: '返航中', startNode: '东直门桥', position: { lon: 116.4339, lat: 39.9408 } },
  { id: 'A-01', type: '救护车', battery: 100, status: '待命', startNode: '西直门桥', position: { lon: 116.3557, lat: 39.9407 } },
  { id: 'A-02', type: '救护车', battery: 85, status: '任务中', startNode: '复兴门桥', position: { lon: 116.3566, lat: 39.9071 } },
])

// 自动计算统计数据
const fleetStats = computed(() => {
  const total = fleetList.length;
  const idle = fleetList.filter(v => v.status === '待命').length;
  const active = total - idle;
  return { total, idle, active };
})

const { viewerRef, initMap, toggleLayer } = useCesiumMap()
const {
  activeDroneEntity,
  dispatch: droneDispatch,
  showCamera,
  closeCamera,
  changeWeather: changeDroneWeather,
  telemetry,
  routeProfile,
  viewVehicle,
  unlockCamera,
} = useDrone(viewerRef, hospitalPressure)
const { playClick, playRadar, playWarning, stopWarning } = useAudio()

// 🌟 挂载局部天气
const { isSettingLocation, currentRainZone, activateWeatherSetter, clearWeather } = useLocalWeather(viewerRef)

// 🌟 覆盖原有的 changeWeather 函数
const changeWeather = (type) => {
  if (type === 'localRain') {
    bottomPanelRef.value?.logRef?.addLog('warn', '👉 请在地图上点击位置，部署局部暴雨区...')
    activateWeatherSetter()
  } else if (type === 'sunny') {
    bottomPanelRef.value?.logRef?.addLog('info', '☀️ 气象武器已解除，天空恢复晴朗。')
    clearWeather()
    changeDroneWeather('sunny')
  } else {
    changeDroneWeather(type)
  }
}

// ================= 🌟 调度方案一：AI 智能分配 =================
const handleAIDispatch = async () => {
  playClick()
  if (!selectedResource.value || !selectedEndNode.value) return alert("请先选择调拨物资和目标医院！")

  // 1. 寻找第一架“待命”的无人机或车辆
  const availableVehicle = fleetList.find(v => v.status === '待命')
  if (!availableVehicle) {
    bottomPanelRef.value?.logRef?.addLog('warn', `🚨 警告：当前全市无可用运力！请等待载具返航。`)
    alert("当前无可用运力，请稍后再试！")
    return
  }

  bottomPanelRef.value?.logRef?.addLog('info', `[AI 统管] 系统已自动分配 ${availableVehicle.id} 执行任务。`)
  
  // 执行具体的调度扣减逻辑
  executeDispatch(availableVehicle, selectedStartNode.value)
}

// ================= 🌟 调度方案二：人工强制派单 =================
const handleManualDispatch = (vehicle) => {
  playClick()
  if (vehicle.status !== '待命') return alert("该载具正在执行任务或充电中，无法派单！")
  if (!selectedResource.value || !selectedEndNode.value) return alert("请在上方表单中配置好收货医院和物资！")

  bottomPanelRef.value?.logRef?.addLog('info', `[人工微操] 指挥员强制派单给 ${vehicle.id}。`)
  
  // 强制使用该载具的驻扎点作为起点
  executeDispatch(vehicle, vehicle.startNode)
}

// ================= 核心执行器 =================
const executeDispatch = async (vehicle, startNode) => {
  const resName = selectedResource.value.name
  const target = selectedEndNode.value
  const qty = dispatchQuantity.value
  const forcedType = vehicle.type === '无人机' ? 'DRONE' : 'AMBULANCE'

  try {
    // 锁定载具状态
    vehicle.status = '任务中'

    // 调用底层渲染
    await droneDispatch(selectedResource.value, { 
      startNode: startNode, 
      endNode: target,
      forcedType: forcedType,
      vehicleId: vehicle.id,
      rainZone: currentRainZone.value,
    })

    // 动态扣减医院缺口数据
    if (hospitalNeeds.value[target] && hospitalNeeds.value[target][resName] !== undefined) {
      hospitalNeeds.value[target][resName] = Math.max(0, hospitalNeeds.value[target][resName] - qty)
      bottomPanelRef.value?.logRef?.addLog('info', `✅ [调度成功] ${vehicle.id} 已发车，${target} 缺口扣减: ${resName} -${qty}`)
    }
  } catch (e) {
    vehicle.status = '待命' // 失败回滚
    bottomPanelRef.value?.logRef?.addLog('warn', `❌ 调度失败: ${e.message}`)
  }
}

// 仅用于镜头跟踪
const trackVehicle = (item) => {
  playClick()
  bottomPanelRef.value?.logRef?.addLog('info', `视角锁定至载具: ${item.id}`)
  viewVehicle(item.id)
}

const fetchHospitals = async () => {
  try {
    const res = await axios.get('http://127.0.0.1:8000/api/hospitals')
    hospitals.value = res.data || []
    if (!selectedEndNode.value && hospitals.value.length > 0) {
      selectedEndNode.value = hospitals.value[0].name
    }
  } catch (e) { console.error('医院数据请求失败', e) }
}

const fetchResources = async () => {
  try {
    const res = await axios.get('http://127.0.0.1:8000/api/resources')
    playRadar()
    resources.value = res.data
    if (!selectedResource.value && resources.value.length > 0) {
      selectedResource.value = resources.value[0]
    }
  } catch (e) { console.error('资源请求失败', e) }
}

const triggerAlarm = (message, type, batteryLevel = null) => {
  alarmMessage.value = message; alarmType.value = type; alarmBatteryLevel.value = batteryLevel;
  alarmTimestamp.value = new Date().toLocaleTimeString('zh-CN', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
  alarmVisible.value = true; playWarning(); bottomPanelRef.value?.logRef?.addLog('warn', `警报: ${message}`)
}
const confirmAlarm = () => { stopWarning(); alarmVisible.value = false }
const dismissAlarm = () => { stopWarning(); alarmVisible.value = false }
const handleViewChange = (mode) => { viewMode.value = mode }
const togglePanels = () => { showPanels.value = !showPanels.value }
const handleSystemAlarm = (e) => { const d = e.detail || {}; triggerAlarm(d.message, d.type, d.batteryLevel) }

onMounted(() => {
  initMap('cesiumContainer')
  fetchResources()
  fetchHospitals()
  fetchHospitalNeeds()
  window.addEventListener('system-alarm', handleSystemAlarm)
})
onBeforeUnmount(() => { window.removeEventListener('system-alarm', handleSystemAlarm) })
</script>

<template>
  <LoadingScreen />
  <div id="cesiumContainer"></div>
  
  <div class="header-bar">
    <h2>无人机调度监控系统 - 医院资源调配可视化平台</h2>
  </div>

  <button class="ui-toggle-btn" @click="togglePanels">
    {{ showPanels ? '隐藏面板' : '显示面板' }}
  </button>

  <div v-if="showPanels">
    <Dashboard
      :hospitalName="selectedEndNode"
      :needsData="currentNeeds"
    />

    <DroneCam v-if="showCamera && activeDroneEntity && viewerRef" :mainViewer="viewerRef" :vehicle="activeDroneEntity" @close="closeCamera" />

    <div class="weather-controls">
      <button @click="playClick(); changeWeather('sunny')" title="清除天气">☀️ 恢复晴朗</button>
      <button 
        @click="playClick(); changeWeather('localRain')" 
        class="rain-bomb-btn"
        :class="{ 'is-active': isSettingLocation }"
        title="点击部署暴雨禁飞区"
      >
        🌧️ 部署局部暴雨
      </button>
    </div>

    <div class="layer-controls">
      <label class="layer-switch"><input type="checkbox" v-model="showHospitals" @change="toggleLayer('hospital', showHospitals)"/> <span>医院图层</span></label>
      <label class="layer-switch"><input type="checkbox" v-model="showRoadNodes" @change="toggleLayer('road', showRoadNodes)"/> <span>路网节点</span></label>
    </div>

    <ViewSwitch @change="handleViewChange" />
    <button
      v-if="activeDroneEntity"
      class="unlock-view-btn"
      @click="unlockCamera"
    >
      🌍 解除锁定 (恢复自由移动)
    </button>
    <HUDOverlay :visible="viewMode === '3d' && showCamera" :telemetry="telemetry" :pathData="routeProfile" />
    <AlarmModal :visible="alarmVisible" :message="alarmMessage" :type="alarmType" :batteryLevel="alarmBatteryLevel" :timestamp="alarmTimestamp" @confirm="confirmAlarm" @dismiss="dismissAlarm" />

    <div class="ui-layer">
      <div class="left-panel">
        
        <PanelBox title="🚑 应急物资调拨指令台">
          <div class="dispatch-form">
            <div class="form-row">
              <span class="label">起点仓</span>
              <select v-model="selectedStartNode" class="cyber-select">
                <option v-for="node in startNodes" :key="node" :value="node">{{ node }}</option>
              </select>
            </div>
            
            <div class="form-row">
              <span class="label">目标院</span>
              <select v-model="selectedEndNode" class="cyber-select">
                <option v-for="h in hospitals" :key="h.name" :value="h.name">{{ h.name }}</option>
              </select>
            </div>

            <div class="form-row">
              <span class="label">发物资</span>
              <select v-model="selectedResource" class="cyber-select">
                <option v-for="r in resources" :key="r.id" :value="r">{{ r.name }}</option>
              </select>
            </div>

            <div class="form-row">
              <span class="label">下发量</span>
              <input type="number" v-model="dispatchQuantity" class="cyber-input" min="1" max="500">
            </div>

            <div v-if="selectedResource" class="needs-hint">
              当前 {{ selectedEndNode }} 缺口: 
              <span class="highlight">{{ currentNeeds[selectedResource.name] || 0 }}</span>
            </div>

            <button class="mega-dispatch-btn" @click="handleAIDispatch">
              🚀 AI 智能匹配可用运力发货
            </button>
          </div>
        </PanelBox>
        
        <PanelBox title="📡 机队指挥中心">
          <div class="fleet-stats">
            <div class="stat-box">
              <span class="num blue">{{ fleetStats.total }}</span>
              <span class="text">总运力</span>
            </div>
            <div class="stat-box">
              <span class="num green">{{ fleetStats.idle }}</span>
              <span class="text">待命可用</span>
            </div>
            <div class="stat-box">
              <span class="num red">{{ fleetStats.active }}</span>
              <span class="text">执行任务</span>
            </div>
          </div>

          <div class="vehicle-list">
            <div v-for="item in fleetList" :key="item.id" class="resource-item" :class="{ 'is-busy': item.status !== '待命' }">
              <div class="info">
                <div class="name">[{{ item.type }}] {{ item.id }}</div>
                <div class="details">
                  <span class="detail" :class="{'low-battery': item.battery < 30}">电量: {{ item.battery }}%</span>
                  <span class="detail status" :class="{'ready': item.status === '待命'}">{{ item.status }}</span>
                </div>
              </div>
              <div class="btn-group">
                <button @click.stop="trackVehicle(item)" class="track-btn">视角</button>
                <button 
                  @click.stop="handleManualDispatch(item)" 
                  class="manual-dispatch-btn"
                  :disabled="item.status !== '待命'">
                  人工派单
                </button>
              </div>
            </div>
          </div>
        </PanelBox>

      </div>

      <div class="bottom-panel">
        <BottomPanel ref="bottomPanelRef" />
      </div>
    </div>
  </div>
</template>

<style scoped>
#cesiumContainer { width: 100vw; height: 100vh; }
.header-bar { position: absolute; top: 0; left: 0; width: 100%; height: 60px; background: linear-gradient(to bottom, rgba(0,0,0,0.9), rgba(0,0,0,0)); z-index: 1000; display: flex; justify-content: center; align-items: center; }
.header-bar h2 { color: var(--neon-blue); font-family: 'Orbitron', 'Roboto Mono', monospace, sans-serif; text-shadow: 0 0 10px var(--neon-blue); letter-spacing: 2px; margin: 0; font-size: 18px; font-weight: 600; }
.ui-toggle-btn { position: absolute; top: 70px; right: 20px; z-index: 2000; background: rgba(0, 0, 0, 0.6); border: 1px solid var(--neon-blue); color: var(--neon-blue); padding: 4px 10px; border-radius: 4px; font-size: 12px; cursor: pointer; transition: all 0.2s; }
.ui-toggle-btn:hover { background: rgba(0, 210, 255, 0.25); box-shadow: 0 0 10px rgba(0, 210, 255, 0.5); }
.weather-controls { position: absolute; top: 20px; right: 20px; z-index: 2000; display: flex; gap: 10px; background: var(--bg-glass); backdrop-filter: blur(10px); padding: 10px; border-radius: 4px; border: 1px solid var(--border-color); width: 480px; justify-content: center; }
.weather-controls button { background: transparent; border: 1px solid var(--border-color); font-size: 20px; cursor: pointer; transition: all 0.3s; border-radius: 4px; padding: 5px 10px; color: var(--text-primary); }
.weather-controls button:hover { transform: scale(1.2); background: rgba(0, 210, 255, 0.2); border-color: var(--neon-blue); box-shadow: 0 0 10px rgba(0, 210, 255, 0.4); }

/* ==== 局部暴雨按钮：红色脉冲呼吸灯 ==== */
.rain-bomb-btn {
  background: rgba(255, 77, 79, 0.12);
  border: 1px solid rgba(255, 77, 79, 0.55);
  color: #ff7875;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.5px;
  padding: 6px 12px;
  border-radius: 6px;
  box-shadow: 0 0 14px rgba(255, 77, 79, 0.18);
}

.rain-bomb-btn:hover {
  background: rgba(255, 77, 79, 0.25);
  border-color: rgba(255, 77, 79, 0.9);
  color: #fff;
  box-shadow: 0 0 22px rgba(255, 77, 79, 0.35);
  transform: translateY(-1px);
}

.rain-bomb-btn.is-active {
  background: rgba(255, 77, 79, 0.35);
  border-color: rgba(255, 77, 79, 1);
  color: #fff;
  animation: pulse-red-strong 1.6s infinite;
}

@keyframes pulse-red-strong {
  0% { box-shadow: 0 0 0 0 rgba(255, 77, 79, 0.45); }
  70% { box-shadow: 0 0 0 12px rgba(255, 77, 79, 0); }
  100% { box-shadow: 0 0 0 0 rgba(255, 77, 79, 0); }
}
.layer-controls { position: absolute; top: 80px; right: 20px; z-index: 2000; display: flex; flex-direction: column; gap: 8px; background: var(--bg-glass); backdrop-filter: blur(10px); padding: 8px 12px; border-radius: 4px; border: 1px solid var(--border-color); }
.layer-switch { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-primary); }

/* ==== 模块一：派单表单样式 ==== */
.dispatch-form { display: flex; flex-direction: column; gap: 12px; }
.form-row { display: flex; align-items: center; gap: 10px; }
.form-row .label { color: rgba(255,255,255,0.7); font-size: 13px; width: 50px; }
.cyber-select, .cyber-input { flex: 1; background: rgba(0, 20, 40, 0.6); color: #00d2ff; border: 1px solid rgba(0, 210, 255, 0.4); border-radius: 4px; padding: 6px 10px; font-size: 13px; outline: none; transition: border-color 0.3s; }
.cyber-select:focus, .cyber-input:focus { border-color: #00d2ff; box-shadow: 0 0 8px rgba(0, 210, 255, 0.5); }
.cyber-select option { background: #001220; color: #fff; }
.needs-hint { font-size: 12px; color: rgba(255,255,255,0.6); text-align: right; margin-top: -6px; }
.needs-hint .highlight { color: #ff4d4f; font-weight: bold; font-size: 14px; }
.mega-dispatch-btn { margin-top: 10px; background: linear-gradient(90deg, rgba(0,210,255,0.2) 0%, rgba(0,210,255,0.6) 50%, rgba(0,210,255,0.2) 100%); border: 1px solid #00d2ff; color: #fff; padding: 12px; font-size: 14px; font-weight: bold; border-radius: 4px; cursor: pointer; text-shadow: 0 0 5px #00d2ff; box-shadow: 0 0 15px rgba(0, 210, 255, 0.3); transition: all 0.3s ease; }
.mega-dispatch-btn:hover { background: rgba(0, 210, 255, 0.8); box-shadow: 0 0 25px rgba(0, 210, 255, 0.6); transform: scale(1.02); }

/* ==== 模块二：机队指挥中心样式 ==== */
.fleet-stats { display: flex; justify-content: space-around; background: rgba(0, 0, 0, 0.4); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 10px 0; margin-bottom: 12px; }
.stat-box { display: flex; flex-direction: column; align-items: center; }
.stat-box .num { font-size: 20px; font-weight: bold; font-family: 'Orbitron', monospace; }
.stat-box .text { font-size: 11px; color: rgba(255,255,255,0.6); margin-top: 4px; }
.num.blue { color: #00d2ff; text-shadow: 0 0 8px #00d2ff; }
.num.green { color: #00ffaa; text-shadow: 0 0 8px #00ffaa; }
.num.red { color: #ff4d4f; text-shadow: 0 0 8px #ff4d4f; }

.vehicle-list { max-height: 250px; overflow-y: auto; padding-right: 4px; }
.vehicle-list::-webkit-scrollbar { width: 4px; }
.vehicle-list::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.5); }
.vehicle-list::-webkit-scrollbar-thumb { background: var(--neon-blue); border-radius: 2px; }

.resource-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 8px; border-bottom: 1px solid rgba(255,255,255,0.1); background: rgba(0,0,0,0.2); margin-bottom: 6px; border-radius: 4px; transition: all 0.3s; }
.resource-item:hover { background: rgba(0, 210, 255, 0.1); }
.resource-item.is-busy { opacity: 0.7; }
.resource-item .name { color: #fff; font-size: 13px; font-weight: bold; margin-bottom: 4px; }
.resource-item .details { display: flex; gap: 10px; }
.resource-item .detail { color: rgba(255,255,255,0.6); font-size: 11px; }
.detail.low-battery { color: #ff4d4f; }
.detail.status.ready { color: #00ffaa; }

.btn-group { display: flex; gap: 6px; }
.track-btn { background: rgba(0, 0, 0, 0.5); border: 1px solid rgba(255,255,255,0.3); color: #fff; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 11px; transition: all 0.2s; }
.track-btn:hover { background: rgba(255,255,255,0.2); }

.manual-dispatch-btn { background: rgba(0, 210, 255, 0.15); border: 1px solid #00d2ff; color: #00d2ff; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 11px; font-weight: bold; transition: all 0.2s; }
.manual-dispatch-btn:hover:not(:disabled) { background: #00d2ff; color: #000; box-shadow: 0 0 10px rgba(0,210,255,0.5); }
.manual-dispatch-btn:disabled { background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.1); color: rgba(255,255,255,0.3); cursor: not-allowed; }

/* ==== 解除锁定按钮样式 ==== */
.unlock-view-btn {
  position: absolute;
  top: 130px;
  right: 20px;
  z-index: 2000;
  background: rgba(255, 77, 79, 0.2);
  border: 1px solid #ff4d4f;
  color: #ff4d4f;
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: bold;
  cursor: pointer;
  box-shadow: 0 0 10px rgba(255, 77, 79, 0.3);
  transition: all 0.3s;
  animation: pulse-red 2s infinite;
}

.unlock-view-btn:hover {
  background: rgba(255, 77, 79, 0.6);
  color: #fff;
  box-shadow: 0 0 20px rgba(255, 77, 79, 0.6);
  transform: scale(1.05);
}

@keyframes pulse-red {
  0% { box-shadow: 0 0 0 0 rgba(255, 77, 79, 0.4); }
  70% { box-shadow: 0 0 0 10px rgba(255, 77, 79, 0); }
  100% { box-shadow: 0 0 0 0 rgba(255, 77, 79, 0); }
}

</style>
<style>
.ui-layer { position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; padding: 20px; box-sizing: border-box; display: flex; justify-content: space-between; }
.ui-layer .panel-box, .ui-layer .panel-box * { pointer-events: auto; }
.left-panel { width: clamp(320px, 22vw, 380px); display: flex; flex-direction: column; gap: 16px; }
.bottom-panel { position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); width: 900px; max-width: 90vw; }
</style>