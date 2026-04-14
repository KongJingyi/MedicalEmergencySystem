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
  // 3.1 是否镜头跟随当前载具（trackedEntity）
  const isCameraFollowing = ref(true)

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
  // 6.1 自定义镜头跟随回调（让相机朝向载具正前方，并保持水平视线）
  let followHandler = null

  const getVehicleTypeFromEntity = (entity, time) => {
    try {
      const t = entity?.properties?.vehicleType?.getValue?.(time)
      return t || null
    } catch {
      return null
    }
  }

  const computeForwardHeadingFromPath = (entity, time) => {
    if (!entity?.position?.getValue) return null

    // 用未来一个很小的时间步来取“前进方向”
    const dt = 0.35 // seconds
    const tForward = Cesium.JulianDate.addSeconds(time, dt, new Cesium.JulianDate())
    const tBack = Cesium.JulianDate.addSeconds(time, -dt, new Cesium.JulianDate())

    const p0 = entity.position.getValue(time)
    const p1 =
      entity.position.getValue(tForward) ||
      entity.position.getValue(Cesium.JulianDate.addSeconds(time, 1.0, new Cesium.JulianDate()))
    const pm1 = entity.position.getValue(tBack)

    // 优先使用 p0 -> p1，如果 p1 取不到就退化为 pm1 -> p0
    let v = null
    if (p0 && p1) {
      v = Cesium.Cartesian3.subtract(p1, p0, new Cesium.Cartesian3())
    } else if (pm1 && p0) {
      v = Cesium.Cartesian3.subtract(p0, pm1, new Cesium.Cartesian3())
    } else {
      return null
    }

    // 投影到 ENU 平面，取 east/north 分量，计算 heading
    const enu = Cesium.Transforms.eastNorthUpToFixedFrame(p0 || pm1)
    const east = Cesium.Matrix4.getColumn(enu, 0, new Cesium.Cartesian3())
    const north = Cesium.Matrix4.getColumn(enu, 1, new Cesium.Cartesian3())

    const eastComp = Cesium.Cartesian3.dot(v, east)
    const northComp = Cesium.Cartesian3.dot(v, north)

    if (!Number.isFinite(eastComp) || !Number.isFinite(northComp)) return null

    // heading=0 指向 north；atan2(east,north) 与 Cesium heading 约定一致
    return Math.atan2(eastComp, northComp)
  }

  const updateFollowCamera = () => {
    const viewer = viewerRef.value
    if (!viewer || !isCameraFollowing.value) return
    const entity = activeDroneEntity.value
    if (!entity?.position || !entity?.orientation) return

    const time = viewer.clock?.currentTime
    if (!time) return

    const position = entity.position.getValue(time)
    if (!position) return

    // ✅ 镜头始终朝向“沿路径前进方向”，而不是模型自身朝向
    const heading = computeForwardHeadingFromPath(entity, time)
    if (heading == null) return

    const vehicleType = getVehicleTypeFromEntity(entity, time)
    const behind = vehicleType === 'AMBULANCE' ? 35 : 55
    const up = vehicleType === 'AMBULANCE' ? 10 : 18

    const enu = Cesium.Transforms.eastNorthUpToFixedFrame(position)
    const east = Cesium.Matrix4.getColumn(enu, 0, new Cesium.Cartesian3())
    const north = Cesium.Matrix4.getColumn(enu, 1, new Cesium.Cartesian3())
    const upVec = Cesium.Matrix4.getColumn(enu, 2, new Cesium.Cartesian3())

    const sinH = Math.sin(heading)
    const cosH = Math.cos(heading)

    // 前进方向（水平面）：east*sin + north*cos
    const forward = Cesium.Cartesian3.add(
      Cesium.Cartesian3.multiplyByScalar(east, sinH, new Cesium.Cartesian3()),
      Cesium.Cartesian3.multiplyByScalar(north, cosH, new Cesium.Cartesian3()),
      new Cesium.Cartesian3()
    )

    // 相机在载具后方一点，并抬高一些
    const behindOffset = Cesium.Cartesian3.multiplyByScalar(forward, -behind, new Cesium.Cartesian3())
    const upOffset = Cesium.Cartesian3.multiplyByScalar(upVec, up, new Cesium.Cartesian3())
    const destination = Cesium.Cartesian3.add(
      Cesium.Cartesian3.add(position, behindOffset, new Cesium.Cartesian3()),
      upOffset,
      new Cesium.Cartesian3()
    )

    viewer.camera.setView({
      destination,
      orientation: {
        heading,
        pitch: 0.0, // 视线平行地面
        roll: 0.0,
      },
    })
  }

  const detachFollowCamera = () => {
    const viewer = viewerRef.value
    if (viewer?.scene && followHandler) {
      viewer.scene.preRender.removeEventListener(followHandler)
      followHandler = null
    }
  }

  const attachFollowCamera = () => {
    const viewer = viewerRef.value
    if (!viewer?.scene || followHandler) return
    viewer.trackedEntity = undefined // 防止和 Cesium 默认跟随打架
    followHandler = () => updateFollowCamera()
    viewer.scene.preRender.addEventListener(followHandler)
  }

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
    let vehicleId = null
    let forcedType = null
    let rainZone = null // 🌟 1. 新增接收天气参数
    let qty = 1

    if (
      startNodeOrOptions &&
      typeof startNodeOrOptions === 'object' &&
      !Array.isArray(startNodeOrOptions)
    ) {
      // 写法 1：对象解构
      startNode = startNodeOrOptions.startNode ?? startNode
      endNode = startNodeOrOptions.endNode ?? endNode
      vehicleId = startNodeOrOptions.vehicleId ?? null
      forcedType = startNodeOrOptions.forcedType ?? null
      rainZone = startNodeOrOptions.rainZone ?? null // 🌟 2. 提取天气参数
      qty = Number(startNodeOrOptions.qty || 1)
    } else {
      // 写法 2：两个字符串
      startNode = startNodeOrOptions ?? startNode
      endNode = endNodeMaybe ?? endNode
    }

    try {
      console.log(`🚀 发起请求: 起点=${startNode}, 终点=${endNode}, 雨区=${rainZone ? '有' : '无'}`)

      // 🌟 3. 将雨区坐标打包发给后端 API
      const payload = {
        resource_id: resource.id,
        start_node: startNode,
        end_node: endNode,
        vehicle_id: vehicleId,
        forced_type: forcedType,
        rain_zone: rainZone, // 传给后端，格式为 { lng: 116.x, lat: 39.x } 或 null
        qty: qty || 1, // 增加数量传参
      }

      // 调用后端路径规划接口，获取配送方式推荐（无人机/车辆）
      const res = await axios.post('http://127.0.0.1:8000/api/plan_route', payload)

      const result = res.data
      const isDrone = result.recommend
      const rawPath = result.path

      if (viewerRef.value && rawPath && rawPath.length > 0) {
        const wgs84Path = rawPath
        if (wgs84Path.length < 2) {
          alert("⚠️ 路径点不足，无法绘制路径！请检查起终点名称是否在路网中。")
          return
        }

        const profileData = []
        const pathWithAltitude = []
        const flat = []
        let accumulatedDistance = 0

        // 🌟 核心解析：区分接收 2D(救护车) 和 3D(无人机) 数据
        for (let i = 0; i < wgs84Path.length; i++) {
          const point = wgs84Path[i]
          const lng = point[0]
          const lat = point[1]

          // 如果后端传了第三个参数(高度)就用后端的，否则兜底 2 米(救护车)
          let alt = point.length > 2 ? point[2] : 2
          if (!isDrone) {
            alt = 2 // 救护车强制贴地
          } else {
            // ✅ 无人机高度钳制：保持在楼房上方一点点，避免飞太高
            alt = Math.max(40, Math.min(Number(alt || 0), 90))
          }

          pathWithAltitude.push([lng, lat, alt])
          flat.push(lng, lat, alt)

          // 距离累加
          if (i > 0) {
            const prevPos = Cesium.Cartesian3.fromDegrees(wgs84Path[i - 1][0], wgs84Path[i - 1][1])
            const currPos = Cesium.Cartesian3.fromDegrees(lng, lat)
            accumulatedDistance += Cesium.Cartesian3.distance(prevPos, currPos)
          }

          profileData.push({
            distance: accumulatedDistance / 1000,
            altitude: alt,
          })
        }

        routeProfile.value = profileData

        // 🌟 视觉盛宴：地空独立渲染样式！
        viewerRef.value.entities.add({
          polyline: {
            // Cesium 支持直接接收经纬度+高度的 flat 数组
            positions: Cesium.Cartesian3.fromDegreesArrayHeights(flat),
            width: isDrone ? 3 : 8, // 无人机细光束，救护车宽车道

            // 材质区分
            material: isDrone
              // 无人机：赛博朋克虚线脉冲 (表示空中走廊)
              ? new Cesium.PolylineDashMaterialProperty({
                  color: Cesium.Color.CYAN,
                  dashLength: 20
                })
              // 救护车：高亮地面霓虹实线 (表示地面拥堵/特权通道)
              : new Cesium.PolylineGlowMaterialProperty({
                  glowPower: 0.15,
                  color: Cesium.Color.ORANGE
                }),

            // 🌟 灵魂属性：无人机悬空，救护车完美贴合地表起伏
            clampToGround: !isDrone,
          },
        })

        // 🌟 避障段高亮：当无人机出现明显抬升时，叠加一条洋红色高亮线用于解释“AI 正在绕障”
        if (isDrone && pathWithAltitude.length >= 2) {
          const altitudes = pathWithAltitude.map((p) => p[2] ?? 0)
          const minAlt = Math.min(...altitudes)
          const obstacleFlat = []

          pathWithAltitude.forEach((point) => {
            const [lng, lat, alt] = point
            // 抬升超过基础高度 60m 视为“避障段”
            if (alt > minAlt + 60) {
              obstacleFlat.push(lng, lat, alt)
            }
          })

          // 至少两个点才能成线
          if (obstacleFlat.length >= 6) {
            viewerRef.value.entities.add({
              polyline: {
                positions: Cesium.Cartesian3.fromDegreesArrayHeights(obstacleFlat),
                width: 6,
                material: new Cesium.PolylineGlowMaterialProperty({
                  glowPower: 0.35,
                  color: Cesium.Color.MAGENTA.withAlpha(0.95),
                }),
                clampToGround: false,
              },
            })
          }
        }

        // 启动模型运动
        createAndFly(isDrone, resource.id, pathWithAltitude)
        return result
      } else {
        alert('后端未返回有效路径！请检查路网配置。')
        return null
      }
    } catch (error) {
      console.error("资源调度路径规划请求失败:", error);
      alert("调度失败！路径规划接口异常，请检查后端服务是否正常运行");
      return null
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

    if (isCameraFollowing.value) {
      attachFollowCamera()
    }
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
      if (isCameraFollowing.value) attachFollowCamera()
    } else {
      alert("未找到该载具，可能尚未起飞或已结束任务！");
    }
  }

  // 🌟 新增：解除视角锁定，恢复自由移动
  const unlockCamera = () => {
    const viewer = viewerRef.value
    if (viewer) {
      viewer.trackedEntity = undefined // 恢复自由平移
      isCameraFollowing.value = false
      detachFollowCamera()
    }
  }

  const setCameraFollow = (enabled) => {
    isCameraFollowing.value = Boolean(enabled)
    const viewer = viewerRef.value
    if (!viewer) return
    if (!isCameraFollowing.value) {
      viewer.trackedEntity = undefined
      detachFollowCamera()
      return
    }
    attachFollowCamera()
  }

  const toggleCameraFollow = () => {
    setCameraFollow(!isCameraFollowing.value)
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
        if (isCameraFollowing.value) attachFollowCamera()
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
    isCameraFollowing,
    dispatch,
    viewVehicle,
    unlockCamera,
    setCameraFollow,
    toggleCameraFollow,
    closeCamera,
    clearAll,
    changeWeather,
    telemetry,
    activeFleetList,
    routeProfile,
  }
}