<script setup>
import { onMounted, ref } from 'vue'
import axios from 'axios'
import Dashboard from './components/Dashboard.vue'
import DroneCam from './components/DroneCam.vue'

// 引入我们刚才写的 Hooks
import { useCesiumMap } from './hooks/useCesiumMap'
import { useDrone } from './hooks/useDrone'

// 1. 业务数据状态
const resources = ref([]) 
const hospitalPressure = ref(0) 

// 2. 初始化地图 Hook
const { viewerRef, initMap, addMarkers } = useCesiumMap()

// 3. 初始化无人机 Hook (把 viewerRef 和 压力值 传进去)
const { currentVehicle, dispatch } = useDrone(viewerRef, hospitalPressure, addMarkers)

// 获取物资列表 (这个很简单，可以先留在这里，以后也可以抽离)
const fetchResources = async () => {
  try {
    const res = await axios.get('http://127.0.0.1:8000/api/resources')
    resources.value = res.data
  } catch (e) { 
    console.error("后端连不上", e) 
  }
}

onMounted(() => {
  // 一行代码启动地图
  initMap('cesiumContainer')
  fetchResources()
})
</script>

<template>
  <div id="cesiumContainer"></div>
  
  <div class="header-bar">
    <h2>? 城市医疗应急资源联运指挥中心</h2>
  </div>

  <Dashboard :hospitalPressure="hospitalPressure" />

  <DroneCam 
    v-if="currentVehicle && viewerRef" 
    :mainViewer="viewerRef" 
    :vehicle="currentVehicle" 
  />

  <div class="test-panel" style="top: 80px;">
    <h3>? 医疗资源应急调度台</h3>
    <ul>
      <li v-for="item in resources" :key="item.id" class="resource-item">
        <div class="info">
          <b>{{ item.name }}</b> 
          <span class="tag" v-if="item.urgency_level >= 4">急救</span>
          <br>
          <small>温控: {{ item.min_temp }}~{{ item.max_temp }}°C</small>
        </div>
        <button @click="dispatch(item)" class="btn-dispatch">? 调度</button>
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
