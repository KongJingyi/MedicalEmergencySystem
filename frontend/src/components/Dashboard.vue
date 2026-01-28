<script setup>
import { onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps(['hospitalPressure']) // 接收父组件传来的“压力值”

// 定义图表容器的引用
const chartTempRef = ref(null)
const chartStockRef = ref(null)

// 1. 初始化左侧：冷链温度监控 (模拟实时跳动)
const initTempChart = () => {
  const myChart = echarts.init(chartTempRef.value)
  const option = {
    title: { text: '冷链箱实时温控', textStyle: { color: '#fff', fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: ['10:00', '10:05', '10:10', '10:15', '10:20'], axisLabel: { color: '#fff' } },
    yAxis: { type: 'value', min: -80, max: 10, axisLabel: { color: '#fff' }, splitLine: { show: false } },
    series: [{
      data: [-70, -71, -69, -70, -72], // 模拟辉瑞疫苗温度
      type: 'line',
      smooth: true,
      lineStyle: { color: '#00d2ff' },
      areaStyle: { color: 'rgba(0, 210, 255, 0.3)' }
    }]
  }
  myChart.setOption(option)
}

// 2. 初始化右侧：医院承载力/库存 (核心医疗数据)
const initStockChart = () => {
  const myChart = echarts.init(chartStockRef.value)
  const option = {
    title: { text: '目标医院物资缺口', textStyle: { color: '#fff', fontSize: 14 } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value', axisLabel: { show: false }, splitLine: { show: false } },
    yAxis: { 
      type: 'category', 
      data: ['防护服', '强心剂', 'O型血', 'mRNA疫苗'], 
      axisLabel: { color: '#fff' } 
    },
    series: [
      {
        name: '当前缺口',
        type: 'bar',
        data: [20, 50, 90, 80], // 红色代表缺口大
        itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: '#ff4d4f' }, { offset: 1, color: '#ff7875' }]) },
        label: { show: true, position: 'right', color: '#fff' }
      }
    ]
  }
  myChart.setOption(option)
  return myChart
}

onMounted(() => {
  initTempChart()
  const stockChart = initStockChart()

  // 监听父组件传来的压力变化，动态更新图表
  // 当无人机送达时，缺口会减少！
  watch(() => props.hospitalPressure, (newVal) => {
    // 模拟数据更新：O型血缺口从 90 降到 (90 - 减少的值)
    stockChart.setOption({
      series: [{ data: [20, 50, Math.max(0, 90 - newVal), 80] }]
    })
  })
})
</script>

<template>
  <div class="panel left-panel">
    <div ref="chartTempRef" class="chart-box"></div>
  </div>

  <div class="panel right-panel">
    <div ref="chartStockRef" class="chart-box"></div>
    <div class="status-box">
      <h4>🏥 积水潭医院状态</h4>
      <p>急救响应等级: <span style="color:red">Level 1</span></p>
      <p>ICU 占用率: <span style="color:orange">92%</span></p>
      <p>预计送达时间: <span style="color:#00d2ff">3分20秒</span></p>
    </div>
  </div>
</template>

<style scoped>
.panel {
  position: absolute;
  top: 80px; /* 留出顶部标题栏空间 */
  width: 300px;
  background: rgba(11, 17, 32, 0.85); /* 深色半透明 */
  border: 1px solid rgba(0, 210, 255, 0.3);
  box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
  border-radius: 8px;
  padding: 15px;
  z-index: 998; /* 在地图之上 */
}
.left-panel { left: 20px; bottom: 20px; top: auto; } /* 左下角 */
.right-panel { right: 20px; } /* 右上角 */

.chart-box {
  width: 100%;
  height: 200px;
}
.status-box {
  margin-top: 15px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding-top: 10px;
  color: white;
}
</style>