// src/hooks/useDrone.js
import { ref, reactive, markRaw } from 'vue'
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

  // 调度无人机/车辆执行配送任务（入参为待配送资源）
  const dispatch = async (resource) => {
    try {
      // 调用后端路径规划接口，获取配送方式推荐（无人机/车辆）
      const res = await axios.post('http://127.0.0.1:8000/api/plan_route', {
        resource_id: resource.id,
        // 这里必须传「路网节点」里存在的名字，才能算出路径
        // 对应 backend/data/road_nodes.json 里的 name 字段
        start_node: '西直门桥',
        end_node: '东直门桥',
      })

      const result = res.data
      const isDrone = result.recommend
      const rawPath = result.path

      if (viewerRef.value && rawPath && rawPath.length > 0) {
        // 关键：把 GCJ02 转为 WGS84，适配 Cesium
        const wgs84Path = rawPath.map((pt) =>
          gcoord.transform(pt, gcoord.GCJ02, gcoord.WGS84)
        )

        // 调试用：在地面画一条绿色细线，看路径是否沿着马路
        const viewer = viewerRef.value
        const flat = []
        for (const [lng, lat] of wgs84Path) {
          flat.push(lng, lat, 0)
        }
        viewer.entities.add({
          polyline: {
            positions: Cesium.Cartesian3.fromDegreesArrayHeights(flat),
            width: 2,
            material: Cesium.Color.LIME.withAlpha(0.8),
            clampToGround: true,
          },
        })

        // 创建并起飞
        createAndFly(isDrone, resource.id, wgs84Path)
      } else {
        alert('后端未返回有效路径！')
      }
    } catch (error) {
      console.error("资源调度路径规划请求失败:", error);
      alert("调度失败！路径规划接口异常，请检查后端服务是否正常运行");
    }
  }

  // 根据后端推荐结果，创建无人机/车辆并执行飞行/行驶逻辑
  const createAndFly = (isDrone, resourceId, pathData) => {
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

    // 执行载体的飞行/行驶方法：直接吃经过纠偏的路径数组
    newVehicle.flyTo(pathData, type);

    // 将新载体加入机队统一管理
    droneFleet.set(id, newVehicle);

    // 【原代码注释保留】关联第一视角（当前注释掉，可根据业务开启）
    // activeDroneEntity.value = markRaw(newVehicle.entity);
    // showCamera.value = true;
  }

  // 根据资源ID，查找对应配送载体并打开第一视角
  const viewVehicle = (resourceId) => {
    let targetVehicle = null;
    // 遍历机队，匹配包含当前资源ID的载体
    for (const [key, val] of droneFleet) {
      if (key.includes(String(resourceId))) {
        targetVehicle = val;
        break;
      }
    }

    // 找到载体则关联视角，否则弹窗提示
    if (targetVehicle) {
      activeDroneEntity.value = markRaw(targetVehicle.entity);
      showCamera.value = true;
    } else {
      alert("未找到该资源对应的配送无人机！请先调度无人机执行配送任务");
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
  }

  return {
    droneFleet,
    activeDroneEntity,
    showCamera,
    dispatch,
    viewVehicle,
    closeCamera,
    clearAll,
    changeWeather,
  }
}