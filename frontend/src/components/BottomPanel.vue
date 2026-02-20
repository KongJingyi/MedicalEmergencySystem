<template>
  <PanelBox title="监控面板">
    <div class="tab-container">
      <button 
        v-for="tab in tabs" 
        :key="tab.id"
        class="tab-btn"
        :class="{ active: activeTab === tab.id }"
        @click="switchTab(tab.id)"
      >
        {{ tab.name }}
      </button>
    </div>

    <div class="tab-content">
      <div v-show="activeTab === 'coldchain'" class="coldchain-panel">
        <div ref="chartTempRef" class="chart-box"></div>
      </div>

      <div v-show="activeTab === 'logs'" class="logs-panel">
        <SystemLog ref="logRef" />
      </div>
    </div>
  </PanelBox>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'
import * as echarts from 'echarts'
import PanelBox from './ui/PanelBox.vue'
import SystemLog from './ui/SystemLog.vue'
import { useAudio } from '../hooks/useAudio'

const { playClick } = useAudio()

const activeTab = ref('coldchain')
const chartTempRef = ref(null)
const logRef = ref(null)

let tempChart = null
let updateInterval = null

const tempData = ref([-70, -72, -68, -73, -69])

const tabs = [
  { id: 'coldchain', name: '冷链监控' },
  { id: 'logs', name: '系统日志' }
]

const initTempChart = () => {
  tempChart = echarts.init(chartTempRef.value)
  const option = {
    title: { text: '冷链箱实时温控', textStyle: { color: '#fff', fontSize: 14 } },
    tooltip: {
      trigger: 'axis',
      formatter: function(params) {
        let result = params[0].name + '<br/>';
        params.forEach(item => {
          result += item.marker + item.seriesName + ': ' + item.value.toFixed(2) + '℃<br/>';
        });
        return result;
      }
    },
    xAxis: { type: 'category', data: ['10:00', '10:05', '10:10', '10:15', '10:20'], axisLabel: { color: '#fff' } },
    yAxis: { type: 'value', min: -75, max: -65, axisLabel: { color: '#fff' }, splitLine: { show: false } },
    series: [{
      data: tempData.value,
      type: 'line',
      smooth: true,
      lineStyle: { color: '#00d2ff' },
      areaStyle: { color: 'rgba(0, 210, 255, 0.3)' },
      symbol: 'circle',
      symbolSize: 6,
      itemStyle: { color: '#00d2ff' }
    }]
  }
  tempChart.setOption(option)
}

const updateTempData = () => {
  const newValue = -70 + (Math.random() * 10 - 5)
  tempData.value.shift()
  tempData.value.push(newValue)
  
  if (tempChart) {
    tempChart.setOption({
      series: [{
        data: tempData.value
      }]
    })
  }
}

const switchTab = (tabId) => {
  playClick()
  activeTab.value = tabId
  if (tabId === 'coldchain') {
    setTimeout(() => {
      if (chartTempRef.value && !tempChart) {
        initTempChart()
      } else if (tempChart) {
        tempChart.resize()
      }
    }, 100)
  }
}

onMounted(() => {
  initTempChart()
  updateInterval = setInterval(updateTempData, 3000)
  
  window.addEventListener('resize', () => {
    if (tempChart) tempChart.resize()
  })
})

onBeforeUnmount(() => {
  if (tempChart) tempChart.dispose()
  if (updateInterval) clearInterval(updateInterval)
})

defineExpose({ logRef })
</script>

<style scoped>
.tab-container {
  display: flex;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(0, 255, 136, 0.2);
  margin-bottom: 10px;
}

.tab-btn {
  flex: 1;
  padding: 8px 16px;
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(0, 255, 136, 0.3);
  border-radius: 4px;
  color: rgba(0, 255, 136, 0.6);
  font-family: 'Rajdhani', 'Roboto Mono', monospace;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  transition: all 0.3s;
}

.tab-btn:hover {
  background: rgba(0, 255, 136, 0.1);
  color: #00ff88;
  border-color: rgba(0, 255, 136, 0.5);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 255, 136, 0.2);
}

.tab-btn.active {
  background: rgba(0, 255, 136, 0.2);
  color: #00ff88;
  border-color: #00ff88;
  box-shadow: 0 0 15px rgba(0, 255, 136, 0.3);
}

.tab-content {
  min-height: 250px;
}

.coldchain-panel,
.logs-panel {
  width: 100%;
}

.chart-box {
  width: 100%;
  height: 250px;
}
</style>
