<template>
  <div class="attitude-indicator">
    <div class="indicator-header">
      <span class="header-deco">///</span>
      <span class="header-title">飞行姿态</span>
    </div>
    
    <div class="indicator-body">
      <div class="attitude-gauge" ref="pitchGaugeRef"></div>
      
      <div class="attitude-values">
        <div class="value-row">
          <span class="value-label">PITCH</span>
          <span class="value-number" :class="getValueClass(pitch)">{{ pitch.toFixed(1) }}°</span>
        </div>
        <div class="value-row">
          <span class="value-label">ROLL</span>
          <span class="value-number" :class="getValueClass(roll)">{{ roll.toFixed(1) }}°</span>
        </div>
        <div class="value-row">
          <span class="value-label">YAW</span>
          <span class="value-number">{{ yaw.toFixed(1) }}°</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  pitch: {
    type: Number,
    default: 0
  },
  roll: {
    type: Number,
    default: 0
  },
  yaw: {
    type: Number,
    default: 0
  }
})

const pitchGaugeRef = ref(null)
let pitchChart = null

const getValueClass = (value) => {
  const absValue = Math.abs(value)
  if (absValue > 30) return 'danger'
  if (absValue > 15) return 'warning'
  return 'normal'
}

const initPitchGauge = () => {
  if (!pitchGaugeRef.value) return
  
  pitchChart = echarts.init(pitchGaugeRef.value)
  
  const option = {
    series: [
      {
        type: 'gauge',
        center: ['50%', '70%'],
        radius: '90%',
        startAngle: 180,
        endAngle: 0,
        min: -90,
        max: 90,
        splitNumber: 6,
        axisLine: {
          lineStyle: {
            width: 15,
            color: [
              [0.33, '#ff4d4f'],
              [0.44, '#ffd700'],
              [0.56, '#00ff88'],
              [0.67, '#ffd700'],
              [1, '#ff4d4f']
            ]
          }
        },
        pointer: {
          icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
          length: '60%',
          width: 8,
          offsetCenter: [0, '-10%'],
          itemStyle: {
            color: 'rgba(0, 210, 255, 0.9)',
            shadowColor: 'rgba(0, 210, 255, 0.5)',
            shadowBlur: 10
          }
        },
        axisTick: {
          length: 8,
          lineStyle: {
            color: 'rgba(0, 210, 255, 0.6)',
            width: 1
          }
        },
        splitLine: {
          length: 15,
          lineStyle: {
            color: 'rgba(0, 210, 255, 0.8)',
            width: 2
          }
        },
        axisLabel: {
          distance: -35,
          color: 'rgba(255, 255, 255, 0.7)',
          fontSize: 10,
          fontFamily: 'Orbitron, monospace',
          formatter: (value) => {
            if (value === 0) return '0'
            return value
          }
        },
        title: {
          show: false
        },
        detail: {
          show: false
        },
        data: [
          {
            value: props.pitch
          }
        ]
      },
      {
        type: 'gauge',
        center: ['50%', '70%'],
        radius: '75%',
        startAngle: 180,
        endAngle: 0,
        min: -90,
        max: 90,
        axisLine: {
          show: false
        },
        pointer: {
          show: false
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
          show: false
        },
        detail: {
          show: true,
          offsetCenter: [0, '20%'],
          fontSize: 20,
          fontFamily: 'Orbitron, monospace',
          fontWeight: 'bold',
          color: '#00ff88',
          formatter: (value) => value.toFixed(1) + '°',
          textShadowColor: 'rgba(0, 255, 136, 0.5)',
          textShadowBlur: 10
        },
        data: [
          {
            value: props.pitch,
            name: 'PITCH'
          }
        ]
      }
    ]
  }
  
  pitchChart.setOption(option)
}

const updatePitchGauge = () => {
  if (!pitchChart) return
  
  pitchChart.setOption({
    series: [
      {
        data: [{ value: props.pitch }]
      },
      {
        data: [{ value: props.pitch }]
      }
    ]
  })
}

const handleResize = () => {
  if (pitchChart) {
    pitchChart.resize()
  }
}

watch(() => props.pitch, updatePitchGauge)

onMounted(() => {
  initPitchGauge()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  if (pitchChart) {
    pitchChart.dispose()
    pitchChart = null
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.attitude-indicator {
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(15px);
  border: 1px solid rgba(0, 210, 255, 0.4);
  border-radius: 8px;
  padding: 12px;
  box-shadow: 
    0 0 30px rgba(0, 210, 255, 0.15),
    inset 0 0 40px rgba(0, 210, 255, 0.05);
  min-width: 200px;
}

.indicator-header {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(0, 210, 255, 0.2);
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
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 2px;
  text-shadow: 0 0 10px rgba(0, 210, 255, 0.5);
}

.indicator-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.attitude-gauge {
  width: 100%;
  height: 120px;
}

.attitude-values {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.value-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 8px;
  background: rgba(0, 210, 255, 0.05);
  border-radius: 4px;
  border-left: 2px solid rgba(0, 210, 255, 0.3);
}

.value-label {
  font-family: 'Orbitron', monospace;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.5);
  letter-spacing: 1px;
}

.value-number {
  font-family: 'Orbitron', monospace;
  font-size: 14px;
  font-weight: 600;
  color: #00d2ff;
  text-shadow: 0 0 8px rgba(0, 210, 255, 0.4);
}

.value-number.normal {
  color: #00ff88;
  text-shadow: 0 0 8px rgba(0, 255, 136, 0.4);
}

.value-number.warning {
  color: #ffd700;
  text-shadow: 0 0 8px rgba(255, 215, 0, 0.4);
}

.value-number.danger {
  color: #ff4d4f;
  text-shadow: 0 0 8px rgba(255, 77, 79, 0.4);
  animation: blink 0.5s infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
