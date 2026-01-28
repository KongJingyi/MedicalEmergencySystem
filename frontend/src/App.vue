<script setup>
import { onMounted, ref, shallowRef } from 'vue'
import axios from 'axios'
import * as Cesium from 'cesium' 
import "cesium/Build/Cesium/Widgets/widgets.css"
import Dashboard from './components/Dashboard.vue'
import DroneCam from './components/DroneCam.vue'

// ================= 1. 变量定义 =================
const resources = ref([]) 
const hospitalPressure = ref(0) // 模拟医院物资缺口缓解程度
const currentVehicle = ref(null) // 当前调度的载具实体（给 DroneCam 用）
const viewerRef = shallowRef(null) // 给模板传参用（Cesium Viewer 很大，用 shallowRef 更合适）

// 坐标定义 (北京大学人民医院 -> 积水潭医院)
const LOCATIONS = {
  START: { lng: 116.3538, lat: 39.9337, name: "北大人民医院", color: Cesium.Color.CORNFLOWERBLUE },
  END: { lng: 116.3725, lat: 39.9468, name: "积水潭医院", color: Cesium.Color.CRIMSON }
}

// ================= 2. 核心功能函数 =================

const fetchResources = async () => {
  try {
    const res = await axios.get('http://127.0.0.1:8000/api/resources')
    resources.value = res.data
  } catch (error) {
    console.error("后端连不上", error)
  }
}

const addMarkers = (viewer) => {
  // 起点
  viewer.entities.add({
    position: Cesium.Cartesian3.fromDegrees(LOCATIONS.START.lng, LOCATIONS.START.lat, 50),
    point: { pixelSize: 15, color: LOCATIONS.START.color },
    label: { 
      text: LOCATIONS.START.name, 
      font: '16px sans-serif',
      pixelOffset: new Cesium.Cartesian2(0, -20),
      fillColor: Cesium.Color.WHITE,
      showBackground: true,
      backgroundColor: new Cesium.Color(0, 0, 0, 0.7)
    }
  });
  // 终点
  viewer.entities.add({
    position: Cesium.Cartesian3.fromDegrees(LOCATIONS.END.lng, LOCATIONS.END.lat, 50),
    point: { pixelSize: 20, color: LOCATIONS.END.color },
    label: { 
      text: LOCATIONS.END.name, 
      font: '18px sans-serif',
      pixelOffset: new Cesium.Cartesian2(0, -20),
      fillColor: Cesium.Color.WHITE,
      showBackground: true,
      backgroundColor: new Cesium.Color(0.8, 0, 0, 0.7)
    }
  });
}

// 【重点修改】画线函数：增加了避障拐点 (Waypoints) + 送达回调
const drawRoute = (viewer, isDrone) => {
  viewer.entities.removeAll(); // 清理
  addMarkers(viewer); // 补回图标

  // 时间设置
  const start = Cesium.JulianDate.now();
  const stop = Cesium.JulianDate.addSeconds(start, 40, new Cesium.JulianDate()); // 总共飞40秒
  
  viewer.clock.startTime = start.clone();
  viewer.clock.stopTime = stop.clone();
  viewer.clock.currentTime = start.clone();
  viewer.clock.clockRange = Cesium.ClockRange.CLAMPED; 
  viewer.clock.multiplier = 1; 
  viewer.clock.shouldAnimate = true; 

  // 定义飞行高度 (无人机更高，救护车略高于地形，避免钻地)
  const h = isDrone ? 150 : 50; 

  // === 规划路径 (这是手动设计的避障路线) ===
  const positionProperty = new Cesium.SampledPositionProperty();
  
  // 1. 起点
  positionProperty.addSample(start, Cesium.Cartesian3.fromDegrees(LOCATIONS.START.lng, LOCATIONS.START.lat, h));
  
  // 2. 拐点A (西直门立交桥东侧，避开高楼)
  positionProperty.addSample(
    Cesium.JulianDate.addSeconds(start, 10, new Cesium.JulianDate()), 
    Cesium.Cartesian3.fromDegrees(116.360, 39.938, h)
  );

  // 3. 拐点B (新街口北大街路口)
  positionProperty.addSample(
    Cesium.JulianDate.addSeconds(start, 25, new Cesium.JulianDate()), 
    Cesium.Cartesian3.fromDegrees(116.368, 39.942, h)
  );

  // 4. 终点
  positionProperty.addSample(stop, Cesium.Cartesian3.fromDegrees(LOCATIONS.END.lng, LOCATIONS.END.lat, h));

  // 创建运动物体 (加载 drone.glb 模型)
  const vehicle = viewer.entities.add({
    availability: new Cesium.TimeIntervalCollection([new Cesium.TimeInterval({ start: start, stop: stop })]),
    position: positionProperty,
    // 自动计算朝向 (让车头/机头朝前)
    orientation: new Cesium.VelocityOrientationProperty(positionProperty),
    
    // 加载模型
    model: {
      uri: '/models/drone.glb', // 你的模型路径 (位于 frontend/public/models/drone.glb)
      
      // --- 下面这些参数需要你根据实际效果微调 ---
      // 1. 大小调整
      minimumPixelSize: 64, // 保证缩小时也能看见
      scale: 1.0,           // 如果太小看不见，改成 10.0 或 100.0
      
      // 2. 动画
      runAnimations: true,  // 让螺旋桨转起来
    },
    
    // 保留轨迹线，方便调试
    path: {
      resolution: 1,
      material: new Cesium.PolylineGlowMaterialProperty({
        glowPower: 0.2,
        color: Cesium.Color.ORANGERED
      }),
      width: 6
    }
  });
  // 👇 保存出来，给 DroneCam 使用
  currentVehicle.value = vehicle

  // 相机追踪
  viewer.trackedEntity = vehicle;

  // 👇👇👇【核心修复】viewer.clock.onStop 是 Event，必须 addEventListener（不能用 = 覆盖）
  // 防止多次点击“调度”重复注册：先移除旧监听器
  if (window.__onStopCallback) {
    viewer.clock.onStop.removeEventListener(window.__onStopCallback);
    window.__onStopCallback = null;
  }

  const onStopCallback = () => {
    // 只有当时间真正走到终点时，才触发送达逻辑
    if (viewer.clock.currentTime.equals(viewer.clock.stopTime)) {
      alert("✅ 物资已送达！正在更新医院库存数据...");
      hospitalPressure.value = 30; // 缺口减少 30，驱动 Dashboard 图表更新

      // 触发一次后移除，避免下次调度复用旧逻辑
      viewer.clock.onStop.removeEventListener(onStopCallback);
      window.__onStopCallback = null;
    }
  };

  window.__onStopCallback = onStopCallback;
  viewer.clock.onStop.addEventListener(onStopCallback);
}

const dispatch = async (resource) => {
  try {
    const res = await axios.post('http://127.0.0.1:8000/api/plan_route', {
      resource_id: resource.id,
      start_node: "START", end_node: "END"
    });
    const result = res.data;
    const isDrone = result.analysis[0].recommend; 
    
    alert(`【系统决策】\n物资：${resource.name}\n推荐方案：${isDrone ? '🚁 无人机急送' : '🚑 地面救护车'}\n理由：${result.analysis[0].logs[0] || '综合评分最高'}`);

    if (window.viewer) {
      drawRoute(window.viewer, isDrone);
    }
  } catch (error) {
    console.error("调度失败:", error);
    alert("调度失败，请检查后端");
  }
}

// ================= 3. 生命周期 =================
onMounted(async () => {
  // 填入你的 Token
  Cesium.Ion.defaultAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJhYWFlNTlhNi1kMjA1LTRmNmUtOGU5Mi00MTNiYmU4NjQzNDAiLCJpZCI6MzI3MTAxLCJpYXQiOjE3Njk1NzkzMjh9.urt5EDHgyCAJVzppAaz4IOZS4PcTRxHiawrq4qH2BiU'; 

  fetchResources()
  
  // 👇👇👇【保险丝】地形加载失败(401/网络)时自动降级，不让 onMounted 夭折
  let terrainProvider;
  try {
    terrainProvider = await Cesium.createWorldTerrainAsync();
  } catch (error) {
    console.warn("⚠️ 地形加载失败(可能是Token权限/网络问题)，已降级为默认地球。", error);
    terrainProvider = undefined;
  }

  const viewer = new Cesium.Viewer('cesiumContainer', {
    terrainProvider,
    infoBox: false,       
    selectionIndicator: false,
    timeline: false,      
    animation: false,     
    baseLayerPicker: false, 
    homeButton: false,
    geocoder: false,
    navigationHelpButton: false,
    sceneModePicker: false,
  });

  // 👇👇👇 【核心修复】建筑加载放回 onMounted，保证一开机就显示
  try {
    const tileset = await Cesium.Cesium3DTileset.fromIonAssetId(96188);
    viewer.scene.primitives.add(tileset);
    
    // 给建筑调色
    tileset.style = new Cesium.Cesium3DTileStyle({
      color: { conditions: [['true', 'color("white", 0.6)']] }
    });
    
    // 如果加了地形还是有点悬空，可以在这里微调高度 (可选)
    // 一般加了 createWorldTerrain 后就不需要这步了
  } catch (e) {
    console.error("❌ 建筑加载失败，请检查网络或Token", e);
  }

  // 飞到北京 (调整了视角，让你能看清路线)
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(116.363, 39.935, 2500), 
    orientation: {
      heading: Cesium.Math.toRadians(0.0), 
      pitch: Cesium.Math.toRadians(-40.0),  
      roll: 0.0
    },
    duration: 3 
  });

  addMarkers(viewer);
  window.viewer = viewer;
  viewerRef.value = viewer;
})
</script>

<template>
  <div id="cesiumContainer"></div>
  
  <div class="header-bar">
    <h2>🚑 城市医疗应急资源联运指挥中心</h2>
  </div>

  <Dashboard :hospitalPressure="hospitalPressure" />

  <DroneCam 
    v-if="currentVehicle && viewerRef" 
    :mainViewer="viewerRef" 
    :vehicle="currentVehicle" 
  />

  <div class="test-panel" style="top: 80px;">
    <h3>🏥 医疗资源应急调度台</h3>
    <ul>
      <li v-for="item in resources" :key="item.id" class="resource-item">
        <div class="info">
          <b>{{ item.name }}</b> 
          <span class="tag" v-if="item.urgency_level >= 4">急救</span>
          <br>
          <small>温控: {{ item.min_temp }}~{{ item.max_temp }}°C</small>
        </div>
        <button @click="dispatch(item)" class="btn-dispatch">🚀 调度</button>
      </li>
    </ul>
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
  color: #00d2ff;
  font-family: "Microsoft YaHei", sans-serif;
  text-shadow: 0 0 10px #00d2ff;
  letter-spacing: 2px;
  margin: 0;
}
.test-panel {
  position: absolute; top: 20px; left: 20px; width: 300px;
  background: rgba(11, 17, 32, 0.85);
  padding: 20px; border: 1px solid #00d2ff; border-radius: 8px; z-index: 999; color: white;
  box-shadow: 0 0 15px rgba(0, 210, 255, 0.3);
}
.resource-item { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px; }
.tag { background: #ff4d4f; color: white; padding: 2px 5px; border-radius: 4px; font-size: 12px; margin-left: 5px; }
.btn-dispatch { background: linear-gradient(45deg, #ff4d4f, #ff7875); border: none; color: white; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-weight: bold; }
.btn-dispatch:hover { transform: scale(1.05); }
</style>