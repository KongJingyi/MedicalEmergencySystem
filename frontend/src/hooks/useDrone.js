// src/hooks/useDrone.js
import { ref } from 'vue'
import axios from 'axios'
import * as Cesium from 'cesium'
import { LOCATIONS } from './useCesiumMap' // 复用坐标

export function useDrone(viewerRef, hospitalPressure, addMarkers) {
  const currentVehicle = ref(null) // 暴露给 DroneCam 用

  // 处理到达逻辑
  const handleArrival = (viewer) => {
    // 清理旧监听
    if (window.__onStopCallback) {
      viewer.clock.onStop.removeEventListener(window.__onStopCallback);
      window.__onStopCallback = null;
    }

    const onStopCallback = () => {
      if (viewer.clock.currentTime.equals(viewer.clock.stopTime)) {
        alert("? 物资已送达！正在更新医院库存数据...");
        hospitalPressure.value = 30; // 更新外部传进来的响应式数据
        viewer.clock.onStop.removeEventListener(onStopCallback);
        window.__onStopCallback = null;
      }
    };
    
    window.__onStopCallback = onStopCallback;
    viewer.clock.onStop.addEventListener(onStopCallback);
  }

  // 画线并飞行 (私有函数，不对外暴露)
  const drawRoute = (isDrone) => {
    const viewer = viewerRef.value;
    if (!viewer) return;

    // 清理旧实体
    viewer.entities.removeAll(); 
    // 重新添加标记点
    if (addMarkers) {
      addMarkers(viewer);
    }
    
    // 时间设置
    const start = Cesium.JulianDate.now();
    const stop = Cesium.JulianDate.addSeconds(start, 40, new Cesium.JulianDate());
    
    viewer.clock.startTime = start.clone();
    viewer.clock.stopTime = stop.clone();
    viewer.clock.currentTime = start.clone();
    viewer.clock.clockRange = Cesium.ClockRange.CLAMPED; 
    viewer.clock.multiplier = 1; 
    viewer.clock.shouldAnimate = true; 

    // 飞行高度
    const h = isDrone ? 150 : 50; 

    // === 路径规划 ===
    const positionProperty = new Cesium.SampledPositionProperty();
    positionProperty.addSample(start, Cesium.Cartesian3.fromDegrees(LOCATIONS.START.lng, LOCATIONS.START.lat, h));
    positionProperty.addSample(
      Cesium.JulianDate.addSeconds(start, 10, new Cesium.JulianDate()), 
      Cesium.Cartesian3.fromDegrees(116.360, 39.938, h)
    );
    positionProperty.addSample(
      Cesium.JulianDate.addSeconds(start, 25, new Cesium.JulianDate()), 
      Cesium.Cartesian3.fromDegrees(116.368, 39.942, h)
    );
    positionProperty.addSample(stop, Cesium.Cartesian3.fromDegrees(LOCATIONS.END.lng, LOCATIONS.END.lat, h));

    // 创建实体
    const vehicle = viewer.entities.add({
      availability: new Cesium.TimeIntervalCollection([new Cesium.TimeInterval({ start: start, stop: stop })]),
      position: positionProperty,
      orientation: new Cesium.VelocityOrientationProperty(positionProperty),
      model: {
        uri: '/models/drone.glb', // 确保 public 目录下有这个文件
        minimumPixelSize: 64,
        scale: 1.0,
        runAnimations: true,
      },
      path: {
        resolution: 1,
        material: new Cesium.PolylineGlowMaterialProperty({ 
          glowPower: 0.2, 
          color: Cesium.Color.ORANGERED 
        }),
        width: 6
      }
    });

    currentVehicle.value = vehicle;
    viewer.trackedEntity = vehicle;

    // 监听到达
    handleArrival(viewer);
  }

  // 对外暴露的调度函数
  const dispatch = async (resource) => {
    try {
      const res = await axios.post('http://127.0.0.1:8000/api/plan_route', {
        resource_id: resource.id, 
        start_node: "START", 
        end_node: "END"
      });
      const result = res.data;
      const isDrone = result.analysis[0].recommend; 
      
      alert(`【系统决策】\n物资：${resource.name}\n推荐方案：${isDrone ? '? 无人机急送' : '? 地面救护车'}\n理由：${result.analysis[0].logs[0] || '综合评分最高'}`);

      if (viewerRef.value) {
        drawRoute(isDrone);
      }
    } catch (error) {
      console.error("调度失败:", error);
      alert("调度失败，请检查后端");
    }
  }

  return {
    currentVehicle,
    dispatch
  }
}
