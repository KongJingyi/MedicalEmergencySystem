<template>
  <div ref="chartRef" style="width: 100%; height: 100%; min-height: 350px;"></div>
</template>

<script setup>
import * as echarts from 'echarts'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({ data: Object }) // 接收父组件传来的物资数据
const chartRef = ref(null)
let myChart = null
let updateInterval = null

const clamp = (v, min, max) => Math.max(min, Math.min(max, v))

const toRadarValues = (resource) => {
  // 后端字段（MedicalResource）：
  // - weight_kg, volume_L, urgency_level(1-5), shock_sensitivity(1-10), min_temp, max_temp
  // 雷达图指标：重量(0-100)、急迫(0-10)、易碎(0-10)、体积(0-100)、温控(0-100)

  if (!resource) return [50, 8, 4, 60, 60]

  const weightKg = Number(resource.weight_kg ?? resource.weight ?? 0)
  const volumeL = Number(resource.volume_L ?? resource.volume ?? 0)
  const urgency = Number(resource.urgency_level ?? resource.urgency ?? 1)
  const shock = Number(resource.shock_sensitivity ?? resource.fragile ?? 10)
  const minTemp = Number(resource.min_temp ?? 0)
  const maxTemp = Number(resource.max_temp ?? 0)

  // 归一化策略（演示用，易理解、可调整）
  const weight = clamp((weightKg / 2) * 100, 0, 100) // 0~2kg 映射到 0~100
  const volume = clamp((volumeL / 10) * 100, 0, 100) // 0~10L 映射到 0~100
  const urgent = clamp(urgency * 2, 0, 10) // 1~5 -> 2~10
  const fragile = clamp(11 - shock, 0, 10) // shock 越低越脆（1->10, 10->1）
  const range = Math.abs(maxTemp - minTemp)
  const tempControl = clamp(100 - range * 2, 0, 100) // 温控范围越窄越“苛刻”

  return [weight, urgent, fragile, volume, tempControl]
}

const updateOption = () => {
  if (!myChart) return

  const values = toRadarValues(props.data)

  const option = {
    tooltip: {
      backgroundColor: 'rgba(0, 8, 18, 0.92)',
      borderColor: 'rgba(0, 210, 255, 0.35)',
      borderWidth: 1,
      textStyle: { color: 'rgba(255,255,255,0.92)', fontFamily: "'Rajdhani', sans-serif" },
      extraCssText: 'box-shadow: 0 0 18px rgba(0,210,255,0.20);',
    },
    radar: {
      indicator: [
        { name: '重量', max: 100 },
        { name: '急迫', max: 10 },
        { name: '易碎', max: 10 },
        { name: '体积', max: 100 },
        { name: '温控', max: 100 },
      ],
      splitArea: { show: false },
      splitLine: { lineStyle: { color: 'rgba(0, 210, 255, 0.16)' } },
      axisLine: { lineStyle: { color: 'rgba(0, 210, 255, 0.32)' } },
      axisName: { color: 'rgba(255,255,255,0.86)', fontFamily: "'Rajdhani', sans-serif", fontSize: 12, fontWeight: 600 },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: values,
            name: '物资属性',
            areaStyle: { color: 'rgba(0, 210, 255, 0.22)' },
            lineStyle: { color: '#00d2ff', width: 2, shadowBlur: 18, shadowColor: 'rgba(0, 210, 255, 0.35)' },
            itemStyle: { color: '#00d2ff', shadowBlur: 12, shadowColor: 'rgba(0, 210, 255, 0.35)' },
          },
        ],
      },
    ],
    animation: true,
  }

  myChart.setOption(option)
}

const initChart = () => {
  if (!chartRef.value) return
  myChart = echarts.init(chartRef.value)
  updateOption()
}

const animateChart = () => {
  if (!myChart) return

  const baseValues = toRadarValues(props.data)
  const animatedValues = baseValues.map(val => {
    const variation = Math.random() * 10 - 5
    return clamp(val + variation, 0, val > 10 ? 100 : 10)
  })

  myChart.setOption({
    series: [
      {
        data: [
          {
            value: animatedValues,
          },
        ],
      },
    ],
  })
}

const handleResize = () => {
  if (myChart) myChart.resize()
}

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
  updateInterval = setInterval(animateChart, 500)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (updateInterval) clearInterval(updateInterval)
  if (myChart) {
    myChart.dispose()
    myChart = null
  }
})

watch(
  () => props.data,
  () => updateOption(),
  { deep: true }
)
</script>

