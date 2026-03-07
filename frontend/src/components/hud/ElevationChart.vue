<template>
  <div class="elevation-chart" v-if="visible">
    <div class="chart-header">
      <div class="header-left">
        <span class="header-deco">///</span>
        <span class="header-title">高度剖面图</span>
      </div>
      <div class="header-info">
        <span class="info-item">
          <span class="info-label">起点:</span>
          <span class="info-value">{{ startAlt.toFixed(0) }}m</span>
        </span>
        <span class="info-item">
          <span class="info-label">终点:</span>
          <span class="info-value">{{ endAlt.toFixed(0) }}m</span>
        </span>
        <span class="info-item">
          <span class="info-label">最高:</span>
          <span class="info-value highlight">{{ maxAlt.toFixed(0) }}m</span>
        </span>
        <span class="info-item">
          <span class="info-label">最低:</span>
          <span class="info-value">{{ minAlt.toFixed(0) }}m</span>
        </span>
      </div>
      <button class="close-btn" @click="$emit('close')">×</button>
    </div>
    
    <div class="chart-body" ref="chartRef"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  pathData: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['close'])

const chartRef = ref(null)
let chart = null

const startAlt = computed(() => props.pathData[0]?.altitude || 0)
const endAlt = computed(() => props.pathData[props.pathData.length - 1]?.altitude || 0)
const maxAlt = computed(() => Math.max(...props.pathData.map(p => p.altitude || 0)))
const minAlt = computed(() => Math.min(...props.pathData.map(p => p.altitude || 0)))

const initChart = () => {
  if (!chartRef.value) return
  
  chart = echarts.init(chartRef.value)
  updateChart()
}

const updateChart = () => {
  if (!chart || !props.pathData.length) return
  
  const distances = props.pathData.map((p, i) => (p.distance || i * 0.5).toFixed(1))
  const altitudes = props.pathData.map(p => p.altitude || 0)
  
  const option = {
    backgroundColor: 'transparent',
    grid: {
      top: 20,
      right: 40,
      bottom: 30,
      left: 50
    },
    xAxis: {
      type: 'category',
      data: distances,
      axisLine: {
        lineStyle: {
          color: 'rgba(0, 210, 255, 0.3)'
        }
      },
      axisLabel: {
        color: 'rgba(255, 255, 255, 0.6)',
        fontSize: 10,
        fontFamily: 'Orbitron, monospace',
        formatter: (value) => value + 'km'
      },
      axisTick: {
        lineStyle: {
          color: 'rgba(0, 210, 255, 0.3)'
        }
      },
      splitLine: {
        show: true,
        lineStyle: {
          color: 'rgba(0, 210, 255, 0.1)'
        }
      }
    },
    yAxis: {
      type: 'value',
      axisLine: {
        lineStyle: {
          color: 'rgba(0, 210, 255, 0.3)'
        }
      },
      axisLabel: {
        color: 'rgba(255, 255, 255, 0.6)',
        fontSize: 10,
        fontFamily: 'Orbitron, monospace',
        formatter: (value) => value + 'm'
      },
      axisTick: {
        lineStyle: {
          color: 'rgba(0, 210, 255, 0.3)'
        }
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(0, 210, 255, 0.1)'
        }
      }
    },
    series: [
      {
        type: 'line',
        data: altitudes,
        smooth: true,
        symbol: 'none',
        lineStyle: {
          color: '#00ff88',
          width: 2,
          shadowColor: 'rgba(0, 255, 136, 0.5)',
          shadowBlur: 10
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(0, 255, 136, 0.4)' },
              { offset: 0.5, color: 'rgba(0, 210, 255, 0.2)' },
              { offset: 1, color: 'rgba(0, 210, 255, 0.05)' }
            ]
          }
        },
        emphasis: {
          lineStyle: {
            width: 3
          }
        }
      },
      {
        type: 'line',
        data: altitudes.map(alt => alt + 50),
        smooth: true,
        symbol: 'none',
        lineStyle: {
          color: 'rgba(0, 210, 255, 0.3)',
          width: 1,
          type: 'dashed'
        }
      }
    ],
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      borderColor: 'rgba(0, 210, 255, 0.5)',
      borderWidth: 1,
      textStyle: {
        color: '#00ff88',
        fontFamily: 'Orbitron, monospace',
        fontSize: 12
      },
      formatter: (params) => {
        const data = params[0]
        return `
          <div style="padding: 4px 8px;">
            <div style="color: rgba(255,255,255,0.6); font-size: 10px;">距离: ${data.name}km</div>
            <div style="color: #00ff88; font-size: 14px; font-weight: bold;">海拔: ${data.value.toFixed(1)}m</div>
          </div>
        `
      }
    }
  }
  
  chart.setOption(option)
}

const handleResize = () => {
  if (chart) {
    chart.resize()
  }
}

watch(() => props.pathData, updateChart, { deep: true })

watch(() => props.visible, (newVal) => {
  if (newVal && !chart) {
    setTimeout(initChart, 100)
  }
})

onMounted(() => {
  if (props.visible) {
    setTimeout(initChart, 100)
  }
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  if (chart) {
    chart.dispose()
    chart = null
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.elevation-chart {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 80%;
  max-width: 900px;
  background: rgba(0, 0, 0, 0.9);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(0, 210, 255, 0.4);
  border-bottom: none;
  border-radius: 12px 12px 0 0;
  box-shadow: 
    0 0 40px rgba(0, 210, 255, 0.2),
    inset 0 0 60px rgba(0, 210, 255, 0.05);
  animation: slideUp 0.3s ease-out;
  z-index: 1400;
}

@keyframes slideUp {
  from {
    transform: translateX(-50%) translateY(100%);
    opacity: 0;
  }
  to {
    transform: translateX(-50%) translateY(0);
    opacity: 1;
  }
}

.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(0, 210, 255, 0.2);
}

.header-left {
  display: flex;
  align-items: center;
}

.header-deco {
  color: rgba(0, 210, 255, 0.8);
  font-family: 'Orbitron', monospace;
  font-size: 12px;
  margin-right: 8px;
}

.header-title {
  color: #00d2ff;
  font-family: 'Orbitron', monospace;
  font-size: 14px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 2px;
  text-shadow: 0 0 10px rgba(0, 210, 255, 0.5);
}

.header-info {
  display: flex;
  gap: 20px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.info-label {
  font-family: 'Rajdhani', monospace;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
}

.info-value {
  font-family: 'Orbitron', monospace;
  font-size: 12px;
  color: #00d2ff;
  text-shadow: 0 0 8px rgba(0, 210, 255, 0.4);
}

.info-value.highlight {
  color: #00ff88;
  text-shadow: 0 0 8px rgba(0, 255, 136, 0.4);
}

.close-btn {
  background: rgba(255, 77, 79, 0.2);
  border: 1px solid rgba(255, 77, 79, 0.4);
  color: #ff4d4f;
  font-size: 20px;
  width: 28px;
  height: 28px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s;
}

.close-btn:hover {
  background: rgba(255, 77, 79, 0.3);
  box-shadow: 0 0 15px rgba(255, 77, 79, 0.4);
}

.chart-body {
  height: 180px;
  padding: 10px;
}
</style>
