<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import * as echarts from 'echarts'
import PanelBox from './ui/PanelBox.vue'

const props = defineProps(['hospitalPressure'])

const chartStockRef = ref(null)
const chartGaugeRef = ref(null)

let stockChart = null
let gaugeChart = null
let updateInterval = null

const stockData = ref([20, 50, 90, 80])
const icuOccupancy = ref(92)
const bloodStock = ref(75)

const initStockChart = () => {
  stockChart = echarts.init(chartStockRef.value)
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
        data: stockData.value,
        itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: '#ff4d4f' }, { offset: 1, color: '#ff7875' }]) },
        label: { show: true, position: 'right', color: '#fff', formatter: (params) => params.value.toFixed(2) }
      }
    ]
  }
  stockChart.setOption(option)
  return stockChart
}

const initGaugeChart = () => {
  gaugeChart = echarts.init(chartGaugeRef.value)
  const option = {
    series: [
      {
        type: 'gauge',
        startAngle: 180,
        endAngle: 0,
        min: 0,
        max: 100,
        splitNumber: 10,
        radius: '90%',
        center: ['50%', '70%'],
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#00d2ff' },
            { offset: 0.5, color: '#00ff88' },
            { offset: 1, color: '#ff4d4f' }
          ])
        },
        progress: {
          show: true,
          roundCap: true,
          width: 12
        },
        pointer: {
          show: false
        },
        axisLine: {
          roundCap: true,
          lineStyle: {
            width: 12,
            color: [[1, 'rgba(255, 255, 255, 0.1)']]
          }
        },
        axisTick: {
          show: false
        },
        splitLine: {
          show: false
        },
        axisLabel: {
          show: false
        },
        title: {
          show: true,
          offsetCenter: [0, '30%'],
          color: '#fff',
          fontSize: 14,
          fontFamily: 'Orbitron, Roboto Mono, monospace'
        },
        detail: {
          valueAnimation: true,
          fontSize: 24,
          offsetCenter: [0, '0%'],
          color: '#fff',
          fontFamily: 'Orbitron, Roboto Mono, monospace',
          formatter: (value) => value.toFixed(2) + '%'
        },
        data: [
          {
            value: icuOccupancy.value,
            name: 'ICU占用率'
          }
        ]
      }
    ]
  }
  gaugeChart.setOption(option)
}

const updateCharts = () => {
  stockData.value = stockData.value.map(val => Math.max(0, val + Math.random() * 4 - 2))
  stockChart.setOption({
    series: [{ data: stockData.value }]
  })
  
  icuOccupancy.value = Math.max(0, Math.min(100, icuOccupancy.value + Math.random() * 2 - 1))
  gaugeChart.setOption({
    series: [{ data: [{ value: icuOccupancy.value, name: 'ICU占用率' }] }]
  })
}

const handleResize = () => {
  if (stockChart) stockChart.resize()
  if (gaugeChart) gaugeChart.resize()
}

onMounted(() => {
  initStockChart()
  initGaugeChart()
  
  window.addEventListener('resize', handleResize)
  
  updateInterval = setInterval(updateCharts, 1000)
  
  watch(() => props.hospitalPressure, (newVal) => {
    stockData.value[2] = Math.max(0, 90 - newVal)
    stockChart.setOption({
      series: [{ data: stockData.value }]
    })
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (updateInterval) clearInterval(updateInterval)
  if (stockChart) stockChart.dispose()
  if (gaugeChart) gaugeChart.dispose()
})
</script>

<template>
  <PanelBox title="医院物资状态" class="right-panel">
    <div ref="chartStockRef" class="chart-box"></div>
    <div class="status-box">
      <h4>🏥 积水潭医院状态</h4>
      <p>急救响应等级: <span style="color:var(--neon-red)">Level 1</span></p>
      <p>血库余量: <span :style="{ color: bloodStock > 50 ? '#00d2ff' : '#ff4d4f' }">{{ bloodStock.toFixed(1) }}%</span></p>
      <p>预计送达时间: <span style="color:var(--neon-blue)">3分20秒</span></p>
    </div>
    <div ref="chartGaugeRef" class="gauge-box"></div>
  </PanelBox>
</template>

<style scoped>
.right-panel {
  position: absolute;
  right: 20px;
  top: 220px;
  width: 450px;
  z-index: 998;
}

.chart-box {
  width: 100%;
  height: 250px;
}

.gauge-box {
  width: 100%;
  height: 180px;
  margin-top: 15px;
}

.status-box {
  margin-top: 15px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding-top: 10px;
  color: white;
}

.status-box h4 {
  margin: 0 0 10px 0;
  color: var(--neon-blue);
  font-family: 'Orbitron', 'Roboto Mono', monospace, sans-serif;
  font-size: 14px;
}

.status-box p {
  margin: 5px 0;
  font-size: 13px;
}
</style>