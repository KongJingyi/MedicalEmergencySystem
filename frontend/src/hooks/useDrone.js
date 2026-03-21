// src/hooks/useDrone.js
import { ref, reactive, markRaw, watch, computed } from 'vue'
import axios from 'axios'
import * as Cesium from 'cesium'
import gcoord from 'gcoord'
import { Drone } from '../classes/Drone'
import { WeatherSystem } from '../classes/WeatherSystem'

export function useDrone(viewerRef, hospitalPressure) {
  // 1. 无人机机队管理 (Map映射: 载体ID -> Drone实例，统一管理所有无人机/车辆)
  const droneFleet = reactive(new Map())

  // 2. 当前激活的无人机Cesium实体 (用于关联DroneCam组件，展示第一视角)
  const activeDroneEntity = ref(null)

  // 3. 是否显示无人机第一视角窗口 (控制DroneCam组件的显隐)
  const showCamera = ref(false)

  // 4. 天气系统实例（懒加载）
  let weatherSystem = null

  // 5. 真实飞行遥测数据（供 HUD 使用）
  const telemetry = reactive({
    speed: 0,      // km/h
    altitude: 0,   // m
    heading: 0,    // deg
    pitch: 0,      // deg
    roll: 0,       // deg
    yaw: 0,        // deg（这里与 heading 保持一致）
    battery: 100,  // %
    lat: 0,        // deg
    lon: 0,        // deg
    time: ''       // 本地时间字符串
  })

  // 6. Cesium 场景帧回调，用于每帧同步当前激活实体的遥测
  let telemetryHandler = null

  // 7. 全局报警分发（通过 window 自定义事件让 App 统一处理）
  const triggerSystemAlarm = (msg, type, battery) => {
    window.dispatchEvent(
      new CustomEvent('system-alarm', {
        detail: { message: msg, type, batteryLevel: battery },
      })
    )
  }

  // 8. 简易电量监控定时器
  let batteryTimer = null

  // 9. 路径剖面数据（距离-高度），供 ECharts 使用
  const routeProfile = ref([])
  // 10. 轨迹配色轮询索引（让不同调度任务显示不同颜色）
  let pathColorCursor = 0
  const PATH_COLORS = [
    Cesium.Color.CYAN,
    Cesium.Color.ORANGE,
    Cesium.Color.MAGENTA,
    Cesium.Color.LIME,
    Cesium.Color.DEEPSKYBLUE,
    Cesium.Color.HOTPINK,
    Cesium.Color.GOLD,
  ]

  const nextPathColor = () => {
    const color = PATH_COLORS[pathColorCursor % PATH_COLORS.length]
    pathColorCursor += 1
    return color
  }

  const initWeather = () => {
    if (viewerRef.value && !weatherSystem) {
      weatherSystem = new WeatherSystem(viewerRef.value)
    }
  }

  const changeWeather = (type) => {
    if (!weatherSystem) initWeather()
    switch (type) {
      case 'rain':
        weatherSystem.setRain()
        break
      case 'snow':
        weatherSystem.setSnow()
        break
      case 'fog':
        weatherSystem.setFog()
        break
      default:
        weatherSystem.setSunny()
        break
    }
  }

  // ================= 无人机调度核心方法 =================

  // 调度无人机/车辆执行配送任务（入参为待配送资源 + 起终点节点名）
  // startNode/endNode 建议传 road_nodes.json 中的 name；也可传医院名，由后端做吸附
  // 🌟 兼容两种入参写法：
  // 1) dispatch(resource, { startNode, endNode })
  // 2) dispatch(resource, startNode, endNode)
  const dispatch = async (resource, startNodeOrOptions, endNodeMaybe) => {
    let startNode = '西直门桥'
    let endNode = '北京积水潭医院'

    if (
      startNodeOrOptions &&
      typeof startNodeOrOptions === 'object' &&
      !Array.isArray(startNodeOrOptions)
    ) {
      // 写法 1：对象解构
      startNode = startNodeOrOptions.startNode ?? startNode
      endNode = startNodeOrOptions.endNode ?? endNode
    } else {
      // 写法 2：两个字符串
      startNode = startNodeOrOptions ?? startNode
      endNode = endNodeMaybe ?? endNode
    }

    try {
      console.log(`🚀 发起请求: 起点=${startNode}, 终点=${endNode}`)

      // 调用后端路径规划接口，获取配送方式推荐（无人机/车辆）
      const res = await axios.post('http://127.0.0.1:8000/api/plan_route', {
        resource_id: resource.id,
        start_node: startNode,
        end_node: endNode,
      })

      const result = res.data
      const isDrone = result.recommend
      const rawPath = result.path
      
      // 🌟 获取后端分配的专属高度，如果没有则兜底 200
      const assignedAltitude = result.altitude || 200
      
      // 🌟 统一设定一个“安全悬停高度”，避开北京的建筑群和地形起伏
      const safeHoverAltitude = 800

      if (viewerRef.value && rawPath && rawPath.length > 0) {
        const wgs84Path = rawPath
        if (wgs84Path.length < 2) {
          alert("⚠️ 路径点不足，无法绘制路径！请检查起终点名称是否在路网中。")
          return
        }

        const profileData = []
        const pathWithAltitude = [] // 🌟 新建一个带高度的三维路径数组
        const flat = [] // 给画线用的数组
        let accumulatedDistance = 0

        for (let i = 0; i < wgs84Path.length; i++) {
          const [lng, lat] = wgs84Path[i]

          // 🌟 核心修改：起降与巡航高度逻辑
          let currentAlt = 0
          
          if (isDrone) {
            if (i === 0 || i === wgs84Path.length - 1) {
               // 起点和终点：在 80 米安全高度悬停（垂直起降）
              currentAlt = safeHoverAltitude
            } else {
               // 巡航阶段：爬升到专属分配的高度层 (120, 150, 180 等)
              currentAlt = assignedAltitude
            }
          } else {
            // 救护车：稍微垫高 2 米，防止轮胎陷进 3D 地形里
            currentAlt = 20
          }

          // 组装给 Drone.js 用的 3D 坐标 [经度, 纬度, 高度]
          pathWithAltitude.push([lng, lat, currentAlt])
          // 组装给 Cesium 画线用的连续数组
          flat.push(lng, lat, currentAlt)

          if (i > 0) {
            const [prevLng, prevLat] = wgs84Path[i - 1]
            const prevPos = Cesium.Cartesian3.fromDegrees(prevLng, prevLat)
            const currPos = Cesium.Cartesian3.fromDegrees(lng, lat)
            const dist = Cesium.Cartesian3.distance(prevPos, currPos)
            accumulatedDistance += dist
          }

          profileData.push({
            distance: accumulatedDistance / 1000,
            altitude: currentAlt,
          })
        }

        routeProfile.value = profileData

        const viewer = viewerRef.value
        
        // 绘制三维空中立体光带航线
        viewer.entities.add({
          polyline: {
            positions: Cesium.Cartesian3.fromDegreesArrayHeights(flat),
            width: 3,
            material: new Cesium.PolylineGlowMaterialProperty({
              glowPower: 0.2,
              color: nextPathColor(), // 使用了你写的轮询变色！
            }),
            clampToGround: false, // 必须 false
          },
        })

        // 启动！
        createAndFly(isDrone, resource.id, pathWithAltitude)
      } else {
        alert('后端未返回有效路径！请检查路网配置。')
      }
    } catch (error) {
      console.error("资源调度路径规划请求失败:", error);
      alert("调度失败！路径规划接口异常，请检查后端服务是否正常运行");
    }
  }

  // 根据后端推荐结果，创建无人机/车辆并执行飞行/行驶逻辑
  const createAndFly = (isDrone, resourceId, pathData, pathColor) => {
    const viewer = viewerRef.value;
    if (!viewer) return;

    // 生成唯一载体ID（区分无人机/车辆 + 资源ID + 时间戳，避免重复）
    const id = `${isDrone ? 'drone' : 'car'}-${resourceId}-${Date.now()}`;

    // 实例化无人机/车辆对象（传入Cesium实例和唯一ID）
    const newVehicle = new Drone(viewer, id);

    // 绑定载体到达目的地的回调事件
    newVehicle.onArrivedCallback = (finishedId) => {
      // 到达后提升医院压力值（业务逻辑）
      hospitalPressure.value += 10;
      console.log(`载体 ${finishedId} 已完成配送任务，到达目的地！`);
    };

    // 区分载体类型（无人机 / 救护车）
    const type = isDrone ? 'DRONE' : 'AMBULANCE';

    // 为机队面板提供一个友好的类型文案
    newVehicle.logicalType = isDrone ? '无人机' : '救护车';

    // 执行载体的飞行/行驶方法：直接吃经过纠偏的路径数组
    newVehicle.flyTo(pathData, type, pathColor);

    // 将新载体加入机队统一管理
    droneFleet.set(id, newVehicle);

    // 关联第一视角，自动打开无人机视角
    activeDroneEntity.value = markRaw(newVehicle.entity);
    showCamera.value = true;

    // 🌟 每次调度都先飞到该任务起飞点，再切换到新实体跟随，避免只有首次移动镜头
    if (Array.isArray(pathData) && pathData.length > 0) {
      const [startLng, startLat, startAlt = 0] = pathData[0]
      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(
          startLng,
          startLat,
          Math.max(startAlt + (isDrone ? 700 : 350), 350)
        ),
        duration: 1.2,
      })
    }

    viewer.trackedEntity = undefined
    setTimeout(() => {
      viewer.trackedEntity = newVehicle.entity
      viewer.flyTo(newVehicle.entity, {
        duration: 1.0,
        offset: new Cesium.HeadingPitchRange(
          0,
          Cesium.Math.toRadians(-50),
          isDrone ? 600 : 300
        ),
      })
    }, 150)
  }

  // 根据载具ID，查找对应配送载体并锁定视角
  const viewVehicle = (vehicleId) => {
    const viewer = viewerRef.value
    if (!viewer) return

    let targetVehicle = null;
    // 遍历机队，匹配包含当前载具ID的载体
    for (const [key, val] of droneFleet) {
      if (key.includes(String(vehicleId))) {
        targetVehicle = val;
        break;
      }
    }

    // 找到载体则关联视角并强制锁定，否则弹窗提示
    if (targetVehicle) {
      activeDroneEntity.value = markRaw(targetVehicle.entity);
      showCamera.value = true;
      // 🌟 核心：强行将 Cesium 相机锁定到这个实体上
      viewer.trackedEntity = targetVehicle.entity;
    } else {
      alert("未找到该载具，可能尚未起飞或已结束任务！");
    }
  }

  // 🌟 新增：解除视角锁定，恢复自由移动
  const unlockCamera = () => {
    const viewer = viewerRef.value
    if (viewer) {
      viewer.trackedEntity = undefined // 这一句是恢复自由平移的灵魂！
      activeDroneEntity.value = null   // 清空当前激活实体
      showCamera.value = false         // 关闭第一视角 HUD
    }
  }

  // 关闭无人机第一视角窗口
  const closeCamera = () => {
    showCamera.value = false;
    activeDroneEntity.value = null;
  }

  // 清空所有无人机/车辆载体，重置视角（资源清理/重置业务使用）
  const clearAll = () => {
    // 遍历机队，执行每个载体的移除方法
    droneFleet.forEach(drone => drone.remove());
    // 清空机队映射
    droneFleet.clear();
    // 关闭第一视角
    closeCamera();

    // 清理电量监控
    if (batteryTimer) {
      clearInterval(batteryTimer)
      batteryTimer = null
    }
  }

  // ================= 遥测同步：把 Cesium 实体状态喂给 HUD =================

  const attachTelemetry = () => {
    const viewer = viewerRef.value
    if (!viewer || telemetryHandler) return

    let lastPosition = null
    let lastTime = null
    let lastBatteryTime = null

    telemetryHandler = (scene, time) => {
      const entity = activeDroneEntity.value
      if (!entity || !entity.position) return

      // 使用场景当前时间或 clock 时间均可，这里统一用 clock
      const currentTime = viewer.clock.currentTime
      const position = entity.position.getValue(currentTime)
      const orientation = entity.orientation
        ? entity.orientation.getValue(currentTime)
        : null

      if (!position) return

      // 高度 & 经纬度
      const cartographic = Cesium.Cartographic.fromCartesian(position)
      telemetry.altitude = cartographic.height
      telemetry.lat = Cesium.Math.toDegrees(cartographic.latitude)
      telemetry.lon = Cesium.Math.toDegrees(cartographic.longitude)

      // 速度（基于前后两帧位置和时间差）
      if (lastPosition && lastTime) {
        const distance = Cesium.Cartesian3.distance(lastPosition, position) // m
        const dt = Cesium.JulianDate.secondsDifference(currentTime, lastTime)
        if (dt > 0) {
          const speedMs = distance / dt
          telemetry.speed = speedMs * 3.6 // km/h
        }
      }
      lastPosition = position
      lastTime = currentTime

      // 姿态：Heading / Pitch / Roll
      if (orientation) {
        const hpr = Cesium.HeadingPitchRoll.fromQuaternion(orientation)
        telemetry.heading = Cesium.Math.toDegrees(hpr.heading)
        telemetry.pitch = Cesium.Math.toDegrees(hpr.pitch)
        telemetry.roll = Cesium.Math.toDegrees(hpr.roll)
        telemetry.yaw = telemetry.heading
      }

      // 当前时间字符串
      const jsDate = Cesium.JulianDate.toDate(currentTime)
      telemetry.time = jsDate.toLocaleTimeString('zh-CN', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })

      // 简单电量衰减：按时间线性递减，独立于帧率
      if (telemetry.battery > 0) {
        if (!lastBatteryTime) {
          lastBatteryTime = currentTime
        } else {
          const dtBattery = Cesium.JulianDate.secondsDifference(
            currentTime,
            lastBatteryTime
          )
          if (dtBattery > 0.5) {
            // 每秒约 0.05%，可按需要调整
            const consume = 0.05 * dtBattery
            telemetry.battery = Math.max(0, telemetry.battery - consume)
            lastBatteryTime = currentTime
          }
        }
      }
    }

    viewer.scene.preUpdate.addEventListener(telemetryHandler)
  }

  const startBatteryMonitor = () => {
    if (batteryTimer) return
    batteryTimer = setInterval(() => {
      droneFleet.forEach((vehicle, id) => {
        if (typeof vehicle.battery !== 'number') return
        // 模拟电量消耗
        vehicle.battery = Math.max(0, vehicle.battery - 1)
        if (vehicle.battery < 20 && !vehicle.alarmed) {
          triggerSystemAlarm(
            `载具 ${id} 电量极低，即将返航！`,
            'low_battery',
            Number(vehicle.battery.toFixed(1))
          )
          vehicle.alarmed = true
        }
      })
    }, 5000)
  }

  const detachTelemetry = () => {
    const viewer = viewerRef.value
    if (viewer && telemetryHandler) {
      viewer.scene.preUpdate.removeEventListener(telemetryHandler)
      telemetryHandler = null
    }
  }

  // 当当前激活实体变化时，自动挂载/卸载遥测监听
  watch(
    activeDroneEntity,
    (entity) => {
      if (entity) {
        attachTelemetry()
        startBatteryMonitor()
      } else {
        detachTelemetry()
      }
    }
  )

  // ================= 机队面板数据：把 Map 转成数组 =================
  const activeFleetList = computed(() => {
    const list = []
    droneFleet.forEach((vehicle, id) => {
      list.push({
        id,
        type: vehicle.logicalType || (id.startsWith('drone') ? '无人机' : '救护车'),
        battery:
          typeof vehicle.battery === 'number'
            ? Math.round(vehicle.battery)
            : Math.floor(Math.random() * 40 + 60),
        status: vehicle.status || '执行任务中',
      })
    })
    return list
  })

  return {
    droneFleet,
    activeDroneEntity,
    showCamera,
    dispatch,
    viewVehicle,
    unlockCamera,
    closeCamera,
    clearAll,
    changeWeather,
    telemetry,
    activeFleetList,
    routeProfile,
  }
}