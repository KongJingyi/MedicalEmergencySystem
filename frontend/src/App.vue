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
import DecisionReport from './components/ui/DecisionReport.vue'
// EventTimeline 已整合进 BottomPanel（指挥中心事件流）

// 引入Cesium地图和无人机相关的hook
import { useCesiumMap } from './hooks/useCesiumMap'
import { useDrone } from './hooks/useDrone'
import { useAudio } from './hooks/useAudio'
import { useLocalWeather } from './hooks/useLocalWeather'
import { useTilesetManager } from './hooks/useTilesetManager'
import { useTrafficLayer } from './hooks/useTrafficLayer'

const resources = ref([])
const hospitals = ref([])
const hospitalPressure = ref(0)
const bottomPanelRef = ref(null)
const decisionReportRef = ref(null)
const viewMode = ref('2d')
const showPanels = ref(true)
const bottomPanelExpanded = ref(false)
const shortageOpen = ref(false)
const dispatchOpen = ref(false)
const fleetOpen = ref(false)
const showHospitals = ref(false)
const showRoadNodes = ref(false)

const alarmVisible = ref(false)
const alarmMessage = ref('')
const alarmType = ref('')
const alarmBatteryLevel = ref(null)
const alarmTimestamp = ref('')
const currentWeatherMode = ref('sunny')
const systemLogs = ref([])

// ================= 🌟 业务闭环核心状态 =================
// 1. 表单双向绑定
const selectedStartNode = ref('') // 默认发货仓（加载医院后自动赋值）
const selectedEndNode = ref('') // 目标医院
const selectedResource = ref(null) // 调拨物资
const dispatchQuantity = ref(10) // 派发数量
const roadCongestionLevel = ref('mid') // low / mid / high
const shortageHospital = ref('')
const shortageResourceId = ref(null)
const shortageQty = ref(20)
const shortageResult = ref(null)
const shortageHistory = ref([])
const showShortagePrompt = ref(false)
const showRecommendationDialog = ref(false)

const hospitalNeeds = ref({})
const tollStations = ref([])

const currentNeeds = computed(() => {
  if (!selectedEndNode.value || !hospitalNeeds.value) return {}
  return hospitalNeeds.value[selectedEndNode.value] || {}
})


const selectedShortageResource = computed(() => {
  return (resources.value || []).find(r => String(r.id) === String(shortageResourceId.value)) || null
})

const hospitalMapByName = computed(() => {
  const m = new Map()
  ;(hospitals.value || []).forEach(h => m.set(h.name, h))
  return m
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

const startNodeGroups = computed(() => {
  const hospitalNames = (hospitals.value || []).map(h => h.name).filter(Boolean)
  const tollNames = (tollStations.value || []).map(n => n.name).filter(Boolean)
  return { toll: tollNames, hospital: hospitalNames }
})
const startNodes = computed(() => {
  // 先医院后收费站，保证医院名字始终优先可见
  return [...startNodeGroups.value.hospital, ...startNodeGroups.value.toll]
})

// ================= 🌟 机队指挥中心状态 =================
// 使用 reactive 让状态可变，真实模拟机队
const pad2 = (n) => String(n).padStart(2, '0')
const pick = (arr, idx) => arr[idx % arr.length]
const jitter = (base, step, i) => base + step * ((i % 5) - 2) + (i % 3) * step * 0.15

const generateFleet = (prefix, typeText, count, baseLon, baseLat) => {
  const startPool = ['西直门桥', '北展桥', '复兴门桥', '建国门桥', '东直门桥']
  return Array.from({ length: count }, (_, i) => {
    const no = i + 1
    // 进入页面时统一空闲，便于演示时从“0任务”开始派单
    const status = '待命'
    const battery = Math.max(35, 100 - (no - 1) * 2)
    return {
      id: `${prefix}-${pad2(no)}`,
      type: typeText,
      battery,
      status,
      startNode: pick(startPool, i),
      position: {
        lon: jitter(baseLon, 0.01, i),
        lat: jitter(baseLat, 0.006, i),
      },
    }
  })
}

const fleetList = reactive([
  ...generateFleet('D', '无人机', 20, 116.36, 39.935),
  ...generateFleet('A', '救护车', 20, 116.36, 39.925),
])

// 自动计算统计数据
const fleetStats = computed(() => {
  const total = fleetList.length;
  const idle = fleetList.filter(v => v.status === '待命').length;
  const active = total - idle;
  return { total, idle, active };
})

const { viewerRef, initMap, toggleLayer } = useCesiumMap()
const { isTrafficVisible, toggleTrafficLayer } = useTrafficLayer(viewerRef)
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
  isCameraFollowing,
  toggleCameraFollow,
} = useDrone(viewerRef, hospitalPressure)
const { playClick, playRadar, playWarning, stopWarning } = useAudio()

// 🌟 挂载局部天气
const { isSettingLocation, currentRainZone, activateWeatherSetter, clearWeather } = useLocalWeather(viewerRef)

// 🌟 覆盖原有的 changeWeather 函数
const changeWeather = (type) => {
  if (type === 'localRain') {
    currentWeatherMode.value = 'rain'
    addLog('WARN', '👉 请在地图上点击位置，部署局部暴雨区...')
    activateWeatherSetter()
  } else if (type === 'sunny') {
    currentWeatherMode.value = 'sunny'
    addLog('INFO', '☀️ 气象武器已解除，天空恢复晴朗。')
    clearWeather()
    changeDroneWeather('sunny')
  } else {
    currentWeatherMode.value = type
    changeDroneWeather(type)
  }
}

// ================= 🌟 调度方案一：AI 智能分配 =================
const handleAIDispatch = async () => {
  playClick()
  if (!selectedResource.value || !selectedEndNode.value) return alert("请先选择调拨物资和目标医院！")
  const aiStartNode = selectedStartNode.value
  if (aiStartNode && aiStartNode === selectedEndNode.value) {
    const msg = '⚠️ 起点医院与目标医院相同，禁止发车/发无人机，请重新选择目的医院。'
    alert(msg)
    addLog('WARN', msg)
    return
  }

  const target = selectedEndNode.value
  const qty = dispatchQuantity.value
  const resName = selectedResource.value.name

  const idleDrones = fleetList.filter(v => v.status === '待命' && v.type === '无人机')
  const idleAmbulances = fleetList.filter(v => v.status === '待命' && v.type === '救护车')

  if (idleDrones.length === 0 && idleAmbulances.length === 0) {
    const msg = '🚨 警告：当前全市无可用运力！请等待载具返航。'
    addLog('WARN', msg)
    alert("当前无可用运力，请稍后再试！")
    return
  }

  // 运力约束下的智能兜底：如果某一类运力耗尽，先把强制类型设为剩余可用类型
  let forcedType = null
  let preAssignedVehicle = null
  if (idleDrones.length === 0 && idleAmbulances.length > 0) {
    forcedType = 'AMBULANCE'
    preAssignedVehicle = idleAmbulances[0]
    preAssignedVehicle.status = '任务中'
    const msg = `⚖️ AI 约束调度：无人机已无可用，改由 ${preAssignedVehicle.id} 执行地面配送。`
    addLog('WARN', msg)
  } else if (idleAmbulances.length === 0 && idleDrones.length > 0) {
    forcedType = 'DRONE'
    preAssignedVehicle = idleDrones[0]
    preAssignedVehicle.status = '任务中'
    const msg = `⚖️ AI 约束调度：救护车已无可用，改由 ${preAssignedVehicle.id} 执行空中配送。`
    addLog('WARN', msg)
  }

  // 🌟 前端演示策略：人为调拥堵可影响推荐方向（仅在运力约束未触发时生效）
  if (!forcedType) {
    if (roadCongestionLevel.value === 'high') {
      forcedType = 'DRONE'
      addLog('INFO', '🚦 拥堵策略：道路高拥堵，系统偏向推荐无人机。')
    } else if (roadCongestionLevel.value === 'low') {
      forcedType = 'AMBULANCE'
      addLog('INFO', '🚦 拥堵策略：道路低拥堵，系统偏向推荐救护车。')
    } else {
      addLog('INFO', '🚦 拥堵策略：中等拥堵，保持综合评估。')
    }
  }

  try {
    // 不再“先选第一台车”，而是让后端先做 AI 推荐，再回填车辆
    const result = await droneDispatch(selectedResource.value, {
      startNode: aiStartNode,
      endNode: target,
      forcedType: forcedType,
      vehicleId: preAssignedVehicle?.id ?? null,
      rainZone: currentRainZone.value,
      qty: qty,
    })

    if (!result) {
      if (preAssignedVehicle) preAssignedVehicle.status = '待命'
      return
    }

    // 如果不是预分配场景，按 AI 推荐类型分配最合适的待命载具
    let assignedVehicle = preAssignedVehicle
    if (!assignedVehicle) {
      const recommendedType = result.recommend ? '无人机' : '救护车'
      assignedVehicle = fleetList.find(v => v.status === '待命' && v.type === recommendedType) || null

      // 推荐类型无车可用时，回退到任意待命载具（并记录）
      if (!assignedVehicle) {
        assignedVehicle = fleetList.find(v => v.status === '待命') || null
        if (assignedVehicle) {
          const fallbackMsg = `⚠️ 推荐类型运力不足，已回退由 ${assignedVehicle.id} 执行任务。`
          addLog('WARN', fallbackMsg)
        }
      }

      if (assignedVehicle) assignedVehicle.status = '任务中'
    }

    if (result.analysis) {
      decisionReportRef.value?.showReport(result)
    }

    if (hospitalNeeds.value[target] && hospitalNeeds.value[target][resName] !== undefined) {
      hospitalNeeds.value[target][resName] = Math.max(0, hospitalNeeds.value[target][resName] - qty)
    }

    const vehicleCode = assignedVehicle?.id || 'AUTO'
    const modeText = result.recommend ? '无人机' : '救护车'
    const okMsg = `✅ [AI 智调] ${vehicleCode} 起点=${aiStartNode} -> ${target}，模式=${modeText}，${resName} -${qty}`
    addLog('SUCCESS', okMsg)
  } catch (e) {
    if (preAssignedVehicle) preAssignedVehicle.status = '待命'
    const errMsg = `❌ AI 调度失败: ${e.message}`
    addLog('ERROR', errMsg)
  }
}

// ================= 🌟 调度方案二：人工强制派单 =================
const handleManualDispatch = (vehicle) => {
  playClick()
  if (vehicle.status !== '待命') return alert("该载具正在执行任务或充电中，无法派单！")
  if (!selectedResource.value || !selectedEndNode.value) return alert("请在上方表单中配置好收货医院和物资！")

  addLog('INFO', `[人工微操] 指挥员强制派单给 ${vehicle.id}。`)
  
  // 强制使用该载具的驻扎点作为起点
  executeDispatch(vehicle, vehicle.startNode)
}

// ================= 核心执行器 =================
const executeDispatch = async (vehicle, startNode) => {
  const resName = selectedResource.value.name
  const target = selectedEndNode.value
  const qty = dispatchQuantity.value
  const forcedType = vehicle.type === '无人机' ? 'DRONE' : 'AMBULANCE'

  if (startNode && target && startNode === target) {
    const msg = '⚠️ 起点医院与目标医院相同，禁止发车/发无人机，请重新选择目的医院。'
    alert(msg)
    addLog('WARN', msg)
    return
  }

  try {
    // 锁定载具状态
    vehicle.status = '任务中'

    // 前端即时熔断：无人机禁飞天气
    if (forcedType === 'DRONE' && ['snow', 'fog'].includes(currentWeatherMode.value)) {
      vehicle.status = '待命'
      const msg = `❌ 前端熔断：当前天气 ${currentWeatherMode.value}，无人机禁飞，请改派救护车。`
      alert(msg)
      addLog('WARN', msg)
      return
    }

    // 前端即时熔断：无人机载重上限（5kg）
    const unitWeight = Number(selectedResource.value?.weight_kg || 0.5)
    const totalWeight = unitWeight * Number(qty || 1)
    if (forcedType === 'DRONE' && totalWeight > 5.0) {
      vehicle.status = '待命'
      const msg = `❌ 前端熔断：总重量 ${totalWeight.toFixed(2)}kg 超过无人机上限 5kg，请改派救护车。`
      alert(msg)
      addLog('WARN', msg)
      return
    }

    // 调用底层渲染
    const result = await droneDispatch(selectedResource.value, {
      startNode: startNode, 
      endNode: target,
      forcedType: forcedType,
      vehicleId: vehicle.id,
      rainZone: currentRainZone.value,
      qty: qty,
    })

    if (result && result.analysis) {
      decisionReportRef.value?.showReport(result)
    }
    addLog('SUCCESS', `${vehicle.id} 已发往 ${target}，运载 ${qty} 单位 ${resName}。`)

    // 动态扣减医院缺口数据
    if (hospitalNeeds.value[target] && hospitalNeeds.value[target][resName] !== undefined) {
      hospitalNeeds.value[target][resName] = Math.max(0, hospitalNeeds.value[target][resName] - qty)
      addLog('SUCCESS', `✅ [调度成功] ${vehicle.id} 已发车，${target} 缺口扣减: ${resName} -${qty}`)
    }
  } catch (e) {
    vehicle.status = '待命' // 失败回滚
    addLog('ERROR', `❌ 调度失败: ${e.message}`)
  }
}

// 仅用于镜头跟踪
const trackVehicle = (item) => {
  playClick()
  addLog('INFO', `视角锁定至载具: ${item.id}`)
  viewVehicle(item.id)
}

const fetchHospitals = async () => {
  try {
    const res = await axios.get('http://127.0.0.1:8000/api/hospitals')
    hospitals.value = res.data || []
    if (!selectedStartNode.value && hospitals.value.length > 0) {
      selectedStartNode.value = hospitals.value[0].name
    } else if (!selectedStartNode.value && tollStations.value.length > 0) {
      selectedStartNode.value = tollStations.value[0].name
    }
    if (!selectedEndNode.value && hospitals.value.length > 0) {
      selectedEndNode.value = hospitals.value[0].name
    }
  } catch (e) { console.error('医院数据请求失败', e) }
}

const fetchTollStations = async () => {
  try {
    const res = await axios.get('http://127.0.0.1:8000/api/road_nodes')
    const nodes = res.data || []
    tollStations.value = nodes.filter(n => n.node_type === '收费站')
  } catch (e) {
    console.error('收费站节点请求失败', e)
    tollStations.value = []
  }
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
  alarmVisible.value = true; playWarning(); addLog('WARN', `警报: ${message}`)
}
const addLog = (type, msg) => {
  const time = new Date().toLocaleTimeString('zh-CN', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
  const upperType = String(type || 'INFO').toUpperCase()
  systemLogs.value.unshift({ time, type: upperType, msg })
  if (systemLogs.value.length > 100) {
    systemLogs.value = systemLogs.value.slice(0, 100)
  }
}

const haversineKm = (lng1, lat1, lng2, lat2) => {
  const toRad = (d) => (d * Math.PI) / 180
  const R = 6371
  const dLat = toRad(lat2 - lat1)
  const dLng = toRad(lng2 - lng1)
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return R * c
}

const estimateHospitalStock = (hospitalName, resourceId) => {
  // 前端演示用：稳定伪随机库存（同样输入始终同结果）
  const str = `${hospitalName}-${resourceId}`
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = (hash * 31 + str.charCodeAt(i)) % 100000
  }
  return 15 + (hash % 120) // 15~134
}

const publishShortageRequest = () => {
  const targetHospital = shortageHospital.value
  const resource = selectedShortageResource.value
  const qty = Number(shortageQty.value || 0)

  if (!targetHospital || !resource || qty <= 0) {
    alert('请先选择急缺医院、物资和数量。')
    return
  }

  const target = hospitalMapByName.value.get(targetHospital)
  if (!target) {
    alert('目标医院坐标不存在，无法生成推荐。')
    return
  }

  const candidates = (hospitals.value || [])
    .filter(h => h.name !== targetHospital)
    .map((h) => {
      const dist = haversineKm(target.lng, target.lat, h.lng, h.lat)
      const stock = estimateHospitalStock(h.name, resource.id)
      // 综合评分：库存权重高，距离越近分越高
      const score = stock * 0.65 + (120 / (dist + 1)) * 0.35
      return {
        hospital: h.name,
        distanceKm: Number(dist.toFixed(1)),
        stock,
        score: Number(score.toFixed(1)),
      }
    })
    .sort((a, b) => b.score - a.score)
    .slice(0, 3)

  shortageResult.value = {
    targetHospital,
    resourceName: resource.name,
    qty,
    recommendations: candidates,
    time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
  }

  // 关键：把“实际发布的急缺信息”写入图表数据源（不再依赖演示假数据）
  if (!hospitalNeeds.value[targetHospital]) {
    hospitalNeeds.value[targetHospital] = {}
  }
  hospitalNeeds.value[targetHospital][resource.name] = qty
  // 切换右侧图表到当前发布医院，确保发布后立刻可见
  selectedEndNode.value = targetHospital

  const recordId = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
  shortageHistory.value.unshift({
    id: recordId,
    hospital: targetHospital,
    resourceName: resource.name,
    qty,
    time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
    status: 'pending',
    recommendations: candidates,
  })
  if (shortageHistory.value.length > 12) {
    shortageHistory.value = shortageHistory.value.slice(0, 12)
  }
  showShortagePrompt.value = true
  showRecommendationDialog.value = false

  addLog(
    'WARN',
    `📣 急缺求助已发布：${targetHospital} 急缺 ${resource.name} x${qty}，系统已生成跨院支援推荐。`
  )
}

const applyRecommendation = (rec) => {
  const res = selectedShortageResource.value
  if (!res || !shortageResult.value) return
  selectedStartNode.value = rec.hospital
  selectedEndNode.value = shortageResult.value.targetHospital
  selectedResource.value = res
  dispatchQuantity.value = shortageResult.value.qty
  dispatchOpen.value = true
  showRecommendationDialog.value = false
  showShortagePrompt.value = false

  // 将当前对应急缺记录标记为“已调度”
  const targetName = shortageResult.value.targetHospital
  const targetRes = shortageResult.value.resourceName
  const targetQty = shortageResult.value.qty
  const idx = shortageHistory.value.findIndex(
    (x) =>
      x.hospital === targetName &&
      x.resourceName === targetRes &&
      Number(x.qty) === Number(targetQty) &&
      x.status !== 'dispatched'
  )
  if (idx >= 0) {
    shortageHistory.value[idx] = {
      ...shortageHistory.value[idx],
      status: 'dispatched',
      dispatchTime: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
    }
  }

  addLog('SUCCESS', `✅ 已应用推荐：由 ${rec.hospital} 向 ${shortageResult.value.targetHospital} 发起调拨。`)
}

const goDispatchFromPrompt = () => {
  showShortagePrompt.value = false
  showRecommendationDialog.value = true
}

const openDispatchForRecord = (recordId) => {
  const record = shortageHistory.value.find((x) => x.id === recordId)
  if (!record) return
  const res = (resources.value || []).find((r) => r.name === record.resourceName)
  if (res) {
    shortageResourceId.value = res.id
  }
  shortageHospital.value = record.hospital
  shortageQty.value = record.qty
  shortageResult.value = {
    targetHospital: record.hospital,
    resourceName: record.resourceName,
    qty: record.qty,
    recommendations: record.recommendations || [],
    time: record.time,
  }
  showRecommendationDialog.value = true
}
const confirmAlarm = () => { stopWarning(); alarmVisible.value = false }
const dismissAlarm = () => { stopWarning(); alarmVisible.value = false }
const handleViewChange = (mode) => { viewMode.value = mode }
const togglePanels = () => { showPanels.value = !showPanels.value }
const toggleBottomPanel = () => { bottomPanelExpanded.value = !bottomPanelExpanded.value }
const handleSystemAlarm = (e) => { const d = e.detail || {}; triggerAlarm(d.message, d.type, d.batteryLevel) }

onMounted(async () => {
  await initMap('cesiumContainer')
  // 需求：先不显示原始人工标注医院点，只保留按调度路径动态打点
  toggleLayer('hospital', false)
  // 去掉默认黄色路网节点点位
  toggleLayer('road', false)
  const { loadOptimizedCityModel } = useTilesetManager(viewerRef)
  console.log("正在加载优化版 3D Tiles 城市模型...")
  const cloudTileset = await loadOptimizedCityModel(4589530, false)
  if (cloudTileset) {
    console.log("云端模型加载完毕！")
  } else {
    console.warn("云端模型加载失败，回退到本地 /Beijing3D/tileset.json ...")
    const localTileset = await loadOptimizedCityModel('/Beijing3D/tileset.json', true)
    if (localTileset) {
      console.log("本地模型加载完毕！")
    } else {
      console.error("云端与本地模型均加载失败，请检查 Token/Asset 权限或本地模型目录。")
    }
  }
  fetchResources()
  fetchTollStations()
  fetchHospitals()
  fetchHospitalNeeds()
  window.addEventListener('system-alarm', handleSystemAlarm)
})
onBeforeUnmount(() => { window.removeEventListener('system-alarm', handleSystemAlarm) })
</script>

<template>
  <LoadingScreen />
  <div id="cesiumContainer"></div>
  <div v-if="showShortagePrompt && shortageResult" class="center-prompt-mask">
    <div class="center-prompt-card">
      <div class="title">📚 急缺发布记录</div>
      <div class="history-list">
        <div class="history-row" v-for="item in shortageHistory" :key="item.id">
          <div class="line1">
            <span class="hosp">{{ item.hospital }}</span>
            <span class="time">{{ item.time }}</span>
          </div>
          <div class="line2">
            急缺：{{ item.resourceName }} × {{ item.qty }}
          </div>
        </div>
      </div>
      <div class="actions">
        <button class="primary" @click="goDispatchFromPrompt">去调度</button>
        <button @click="showShortagePrompt = false">稍后</button>
      </div>
    </div>
  </div>

  <div v-if="showRecommendationDialog && shortageResult" class="center-prompt-mask">
    <div class="recommend-card">
      <div class="title">🏥 推荐支援医院列表</div>
      <div class="desc">
        目标：{{ shortageResult.targetHospital }} ｜ 物资：{{ shortageResult.resourceName }} x{{ shortageResult.qty }}
      </div>
      <div class="rec-list">
        <div class="rec-row" v-for="rec in shortageResult.recommendations" :key="`dlg-${rec.hospital}-${rec.score}`">
          <div class="left">
            <div class="name">{{ rec.hospital }}</div>
            <div class="meta">库存 {{ rec.stock }} · 距离 {{ rec.distanceKm }}km · 评分 {{ rec.score }}</div>
          </div>
          <button class="primary" @click="applyRecommendation(rec)">去调度</button>
        </div>
      </div>
      <div class="actions">
        <button @click="showRecommendationDialog = false">关闭</button>
      </div>
    </div>
  </div>
  
  <div class="header-bar">
    <h2>无人机调度监控系统 - 医院资源调配可视化平台</h2>
  </div>

  <button class="ui-toggle-btn" @click="togglePanels">
    {{ showPanels ? '隐藏面板' : '显示面板' }}
  </button>

  <div v-if="showPanels">
    <Dashboard
      :shortageHistory="shortageHistory"
      @go-dispatch="openDispatchForRecord"
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

    <ViewSwitch
      :traffic-active="isTrafficVisible"
      :is-following="isCameraFollowing"
      @change="handleViewChange"
      @toggle-traffic="toggleTrafficLayer"
      @toggle-follow="toggleCameraFollow"
    />
    <HUDOverlay :visible="viewMode === '3d' && showCamera" :telemetry="telemetry" :pathData="routeProfile" />
    <AlarmModal :visible="alarmVisible" :message="alarmMessage" :type="alarmType" :batteryLevel="alarmBatteryLevel" :timestamp="alarmTimestamp" @confirm="confirmAlarm" @dismiss="dismissAlarm" />

    <div class="ui-layer">
      <div class="left-panel">

        <PanelBox title="🚨 医院急缺求助发布" class="left-accordion-item">
          <template #header-extra>
            <button class="panel-fold-btn" @click.stop="shortageOpen = !shortageOpen">
              {{ shortageOpen ? '收起' : '展开' }}
            </button>
          </template>
          <div v-if="shortageOpen" class="dispatch-form" @click.stop>
            <div class="form-row">
              <span class="label">急缺院</span>
              <select v-model="shortageHospital" class="cyber-select">
                <option value="" disabled>请选择医院</option>
                <option v-for="h in hospitals" :key="`short-${h.name}`" :value="h.name">{{ h.name }}</option>
              </select>
            </div>
            <div class="form-row">
              <span class="label">急缺物资</span>
              <select v-model="shortageResourceId" class="cyber-select">
                <option :value="null" disabled>请选择物资</option>
                <option v-for="r in resources" :key="`short-res-${r.id}`" :value="r.id">{{ r.name }}</option>
              </select>
            </div>
            <div class="form-row">
              <span class="label">急缺量</span>
              <input type="number" v-model="shortageQty" class="cyber-input" min="1" max="999">
            </div>
            <button class="mega-dispatch-btn" @click="publishShortageRequest">
              📣 发布紧缺并求助
            </button>
          </div>
        </PanelBox>
        
        <PanelBox title="🚑 应急物资调拨指令台" class="left-accordion-item">
          <template #header-extra>
            <button class="panel-fold-btn" @click.stop="dispatchOpen = !dispatchOpen">
              {{ dispatchOpen ? '收起' : '展开' }}
            </button>
          </template>
          <div v-if="dispatchOpen" class="dispatch-form" @click.stop>
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

            <div class="form-row">
              <span class="label">道路拥堵</span>
              <select v-model="roadCongestionLevel" class="cyber-select">
                <option value="low">低拥堵（偏救护车）</option>
                <option value="mid">中拥堵（综合评估）</option>
                <option value="high">高拥堵（偏无人机）</option>
              </select>
            </div>

            <button class="mega-dispatch-btn" @click="handleAIDispatch">
              🚀 调度可用运力
            </button>
          </div>
        </PanelBox>
        
        <PanelBox title="📡 运力" class="left-accordion-item">
          <template #header-extra>
            <button class="panel-fold-btn" @click.stop="fleetOpen = !fleetOpen">
              {{ fleetOpen ? '收起' : '展开' }}
            </button>
          </template>
          <div v-if="fleetOpen" class="fleet-stats" @click.stop>
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

          <div v-if="fleetOpen" class="vehicle-list" @click.stop>
            <div v-for="item in fleetList" :key="item.id" class="resource-item" :class="{ 'is-busy': item.status !== '待命' }">
              <div class="info">
                <div class="name">[{{ item.type }}] {{ item.id }}</div>
                <div class="details">
                  <span
                    v-if="item.type === '无人机'"
                    class="detail"
                    :class="{'low-battery': item.battery < 30}"
                  >
                    电量: {{ item.battery }}%
                  </span>
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
        <button class="bottom-panel-toggle" @click="toggleBottomPanel">
          {{ bottomPanelExpanded ? '收起监控' : '展开监控' }}
        </button>
      </div>

      <div class="bottom-panel-expanded" v-if="bottomPanelExpanded">
        <BottomPanel ref="bottomPanelRef" :logs="systemLogs" />
      </div>
    </div>
    <DecisionReport ref="decisionReportRef" />
  </div>
</template>

<style scoped>
#cesiumContainer { width: 100vw; height: 100vh; }
.header-bar { position: absolute; top: 0; left: 0; width: 100%; height: 60px; background: linear-gradient(to bottom, rgba(0,0,0,0.9), rgba(0,0,0,0)); z-index: 1000; display: flex; justify-content: center; align-items: center; }
.header-bar h2 { color: var(--neon-blue); font-family: 'Orbitron', 'Roboto Mono', monospace, sans-serif; text-shadow: 0 0 10px var(--neon-blue); letter-spacing: 1px; margin: 0; font-size: 16px; font-weight: 600; }
.ui-toggle-btn { position: absolute; top: 70px; right: 20px; z-index: 2000; background: rgba(0, 0, 0, 0.6); border: 1px solid var(--neon-blue); color: var(--neon-blue); padding: 4px 10px; border-radius: 4px; font-size: 12px; cursor: pointer; transition: all 0.2s; }
.ui-toggle-btn:hover { background: rgba(0, 210, 255, 0.25); box-shadow: 0 0 10px rgba(0, 210, 255, 0.5); }
.weather-controls { position: absolute; top: 20px; right: 20px; z-index: 2000; display: flex; gap: 8px; background: var(--bg-glass); backdrop-filter: blur(10px); padding: 8px; border-radius: 4px; border: 1px solid var(--border-color); width: 390px; justify-content: center; }
.weather-controls button { background: transparent; border: 1px solid var(--border-color); font-size: 16px; cursor: pointer; transition: all 0.3s; border-radius: 4px; padding: 4px 8px; color: var(--text-primary); }
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
.layer-controls { position: absolute; top: 74px; right: 20px; z-index: 1996; display: flex; flex-direction: column; gap: 6px; background: var(--bg-glass); backdrop-filter: blur(10px); padding: 6px 10px; border-radius: 4px; border: 1px solid var(--border-color); }
.layer-switch { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-primary); }

/* ==== 模块一：派单表单样式 ==== */
.dispatch-form { display: flex; flex-direction: column; gap: 9px; }
.form-row { display: flex; align-items: center; gap: 8px; }
.form-row .label {
  color: rgba(255,255,255,0.7);
  font-size: 12px;
  width: 62px;
  min-width: 62px;
  white-space: nowrap;
  word-break: keep-all;
}
.cyber-select, .cyber-input { flex: 1; background: rgba(0, 20, 40, 0.6); color: #00d2ff; border: 1px solid rgba(0, 210, 255, 0.4); border-radius: 4px; padding: 5px 8px; font-size: 12px; outline: none; transition: border-color 0.3s; min-width: 0; box-sizing: border-box; }
.cyber-select:focus, .cyber-input:focus { border-color: #00d2ff; box-shadow: 0 0 8px rgba(0, 210, 255, 0.5); }
.cyber-select {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.cyber-select option { background: #001220; color: #fff; }
.needs-hint { font-size: 12px; color: rgba(255,255,255,0.6); text-align: right; margin-top: -6px; }
.needs-hint .highlight { color: #ff4d4f; font-weight: bold; font-size: 14px; }
.mega-dispatch-btn { margin-top: 8px; background: linear-gradient(90deg, rgba(0,210,255,0.2) 0%, rgba(0,210,255,0.6) 50%, rgba(0,210,255,0.2) 100%); border: 1px solid #00d2ff; color: #fff; padding: 9px; font-size: 13px; font-weight: bold; border-radius: 4px; cursor: pointer; text-shadow: 0 0 5px #00d2ff; box-shadow: 0 0 15px rgba(0, 210, 255, 0.3); transition: all 0.3s ease; }
.mega-dispatch-btn:hover { background: rgba(0, 210, 255, 0.8); box-shadow: 0 0 25px rgba(0, 210, 255, 0.6); transform: scale(1.02); }

/* ==== 模块二：机队指挥中心样式 ==== */
.fleet-stats { display: flex; justify-content: space-around; background: rgba(0, 0, 0, 0.4); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 8px 0; margin-bottom: 8px; }
.stat-box { display: flex; flex-direction: column; align-items: center; }
.stat-box .num { font-size: 20px; font-weight: bold; font-family: 'Orbitron', monospace; }
.stat-box .text { font-size: 11px; color: rgba(255,255,255,0.6); margin-top: 4px; }
.num.blue { color: #00d2ff; text-shadow: 0 0 8px #00d2ff; }
.num.green { color: #00ffaa; text-shadow: 0 0 8px #00ffaa; }
.num.red { color: #ff4d4f; text-shadow: 0 0 8px #ff4d4f; }

.vehicle-list { max-height: 210px; overflow-y: auto; padding-right: 4px; }
.vehicle-list::-webkit-scrollbar { width: 4px; }
.vehicle-list::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.5); }
.vehicle-list::-webkit-scrollbar-thumb { background: var(--neon-blue); border-radius: 2px; }

.resource-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 7px; border-bottom: 1px solid rgba(255,255,255,0.1); background: rgba(0,0,0,0.2); margin-bottom: 5px; border-radius: 4px; transition: all 0.3s; }
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
.panel-fold-btn {
  border: 1px solid rgba(0, 210, 255, 0.35);
  background: rgba(0, 0, 0, 0.42);
  color: #9fe9ff;
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 10px;
  cursor: pointer;
}
.panel-fold-btn:hover {
  background: rgba(0, 210, 255, 0.15);
}

</style>
<style>
.ui-layer { position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; padding: 14px; box-sizing: border-box; display: flex; justify-content: space-between; }
.ui-layer .panel-box, .ui-layer .panel-box * { pointer-events: auto; }
.left-panel { width: clamp(300px, 20vw, 350px); display: flex; flex-direction: column; gap: 12px; }
.bottom-panel {
  position: absolute;
  right: 16px;
  bottom: 16px;
  pointer-events: auto;
}
.bottom-panel-toggle {
  border: 1px solid rgba(0, 210, 255, 0.45);
  background: rgba(0, 0, 0, 0.72);
  color: #9be7ff;
  font-size: 12px;
  font-weight: 700;
  border-radius: 6px;
  padding: 6px 10px;
  cursor: pointer;
  box-shadow: 0 0 10px rgba(0, 210, 255, 0.2);
}
.bottom-panel-toggle:hover {
  background: rgba(0, 210, 255, 0.18);
}
.bottom-panel-expanded {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  bottom: 14px;
  width: min(760px, 86vw);
  max-height: 36vh;
  pointer-events: auto;
  z-index: 2500;
}

/* 左侧业务面板整体下移，避开顶部标题层的点击覆盖 */
.left-panel {
  margin-top: 56px;
}

.center-prompt-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.36);
  z-index: 3200;
  display: flex;
  align-items: center;
  justify-content: center;
}
.center-prompt-card,
.recommend-card {
  width: min(560px, 86vw);
  background: rgba(4, 12, 22, 0.92);
  border: 1px solid rgba(0, 210, 255, 0.4);
  border-radius: 10px;
  box-shadow: 0 0 30px rgba(0, 210, 255, 0.2);
  padding: 16px;
  color: #e7f8ff;
}
.center-prompt-card .title,
.recommend-card .title {
  font-size: 18px;
  color: #7ee7ff;
  font-weight: 700;
}
.center-prompt-card .desc,
.recommend-card .desc {
  margin-top: 8px;
  color: rgba(255, 255, 255, 0.82);
  font-size: 13px;
}
.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px 18px;
  padding: 8px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.12);
}
.history-list {
  margin-top: 8px;
  max-height: 260px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.history-row {
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
  border-radius: 8px;
  padding: 8px 10px;
}
.history-row .line1 {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.history-row .hosp {
  color: #ffffff;
  font-weight: 700;
  font-size: 13px;
}
.history-row .time {
  color: #9adfff;
  font-size: 11px;
}
.history-row .line2 {
  margin-top: 4px;
  color: rgba(255, 255, 255, 0.84);
  font-size: 12px;
}
.detail-grid .k {
  color: rgba(173, 230, 255, 0.78);
}
.detail-grid .v {
  color: #ffffff;
  font-weight: 700;
}
.actions {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.actions button,
.rec-row button {
  border: 1px solid rgba(255, 255, 255, 0.22);
  background: rgba(255, 255, 255, 0.05);
  color: #e5f7ff;
  border-radius: 6px;
  font-size: 12px;
  padding: 6px 12px;
  cursor: pointer;
}
.actions .primary,
.rec-row .primary {
  border-color: rgba(0, 210, 255, 0.65);
  background: rgba(0, 210, 255, 0.2);
  color: #9defff;
}
.rec-list {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.rec-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.03);
}
.rec-row .name {
  font-size: 13px;
  color: #fff;
  font-weight: 700;
}
.rec-row .meta {
  margin-top: 2px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.72);
}
</style>