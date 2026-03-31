<template>
  <div class="chart-container">
    <div class="chart-header">
      <span class="pulse-dot"></span>
      <div class="header-text">
        <h3 class="title">{{ hospitalName || '全市' }} 物资缺口</h3>
        <div class="subtitle">数据源：后端实时缺口矩阵</div>
      </div>
      <div class="header-chip">NEEDS</div>
    </div>
    <div ref="chartRef" class="echarts-box"></div>
  </div>
  </template>
  
  <script setup>
  import { ref, onMounted, onBeforeUnmount, watch, shallowRef } from 'vue'
  import * as echarts from 'echarts'
  
  // 接收父组件传来的数据
  const props = defineProps({
    hospitalName: {
      type: String,
      default: '未选择医院'
    },
    needsData: {
      type: Object,
      default: () => ({})
    }
  })
  
  const chartRef = ref(null)
  const myChart = shallowRef(null)
  
  // 渲染/更新图表的核心方法
  const updateChart = () => {
    if (!myChart.value) return
  
    // 解析传入的数据，例如 {'O型血': 106, 'mRNA疫苗': 123}
    const dataMap = props.needsData || {}
    
    // 过滤掉缺口为 0 的物资，并按缺口数量降序排序
    const sortedData = Object.entries(dataMap)
      .filter(([_, val]) => val > 0)
      .sort((a, b) => a[1] - b[1]) // Echarts 横向柱状图是从下往上画的，所以这里升序
  
    const categories = sortedData.map(item => item[0])
    const values = sortedData.map(item => item[1])
  
    const option = {
      backgroundColor: 'transparent',
      // 🌟 Tooltip：悬浮展示完整名称与缺口
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow',
          shadowStyle: { color: 'rgba(0, 210, 255, 0.10)' },
        },
        backgroundColor: 'rgba(0, 8, 18, 0.92)',
        borderColor: 'rgba(0, 210, 255, 0.35)',
        borderWidth: 1,
        textStyle: { color: 'rgba(255,255,255,0.92)', fontFamily: "'Rajdhani', sans-serif" },
        extraCssText: 'box-shadow: 0 0 18px rgba(0,210,255,0.20);',
        formatter: (params) => {
          const p = Array.isArray(params) ? params[0] : params
          const name = p?.name ?? ''
          const v = p?.value ?? 0
          return `<div style="font-weight:700; color:#00d2ff; margin-bottom:6px;">${name}</div>
                  <div style="display:flex; gap:10px; align-items:baseline;">
                    <span style="color:rgba(255,255,255,0.75);">缺口</span>
                    <span style="font-family:Orbitron, monospace; font-weight:800; color:#ff7875;">${v}</span>
                  </div>`
        },
      },
      grid: {
        left: 10,
        right: 18,
        bottom: 8,
        top: 10,
        containLabel: true,
      },
      xAxis: {
        type: 'value',
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { show: false },
        splitNumber: 4,
        splitLine: {
          show: true,
          lineStyle: { color: 'rgba(0, 210, 255, 0.10)', type: 'dashed' },
        },
      },
      yAxis: {
        type: 'category',
        data: categories,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          color: 'rgba(255, 255, 255, 0.86)',
          fontSize: 12,
          fontWeight: 600,
          fontFamily: "'Rajdhani', sans-serif",
          margin: 14,
          // 🌟 截断过长名称（悬浮 tooltip 看全名）
          formatter: (value) => (value.length > 12 ? value.substring(0, 12) + '…' : value),
        },
      },
      series: [
        {
          name: '缺口',
          type: 'bar',
          data: values,
          barWidth: values.length >= 8 ? 10 : 14,
          barCategoryGap: '45%',
          showBackground: true,
          backgroundStyle: {
            color: 'rgba(0, 210, 255, 0.06)',
            borderRadius: [0, 10, 10, 0],
          },
          itemStyle: {
            borderRadius: [0, 10, 10, 0],
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: 'rgba(255, 77, 79, 0.40)' },
              { offset: 0.35, color: '#ff4d4f' },
              { offset: 1, color: '#ffb3b5' },
            ]),
            shadowBlur: 18,
            shadowColor: 'rgba(255, 77, 79, 0.28)',
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 28,
              shadowColor: 'rgba(255, 77, 79, 0.55)',
            },
          },
          label: {
            show: true,
            position: 'right',
            distance: 8,
            color: 'rgba(255, 190, 190, 0.95)',
            fontSize: 12,
            fontWeight: 800,
            fontFamily: "'Orbitron', monospace",
            formatter: '{c}',
          },
          animationDuration: 900,
          animationEasing: 'cubicOut',
          animationDelay: (idx) => idx * 40,
        },
      ],
    }
  
    myChart.value.setOption(option)
  }
  
  // 监听窗口大小变化，图表自适应
  const handleResize = () => {
    if (myChart.value) myChart.value.resize()
  }
  
  onMounted(() => {
    if (chartRef.value) {
      myChart.value = echarts.init(chartRef.value)
      updateChart()
    }
    window.addEventListener('resize', handleResize)
  })
  
  onBeforeUnmount(() => {
    window.removeEventListener('resize', handleResize)
    if (myChart.value) {
      myChart.value.dispose()
    }
  })
  
  // 🌟 核心：监听数据变化，实现扣减时的动态动画
  watch(
    () => props.needsData,
    () => {
      updateChart()
    },
    { deep: true }
  )
  
  // 监听医院名字切换
  watch(
    () => props.hospitalName,
    () => {
      updateChart()
    }
  )
  </script>
  
  <style scoped>
  .chart-container {
    width: 100%;
    height: 300px;
    background:
      radial-gradient(900px 240px at 12% 0%, rgba(0, 210, 255, 0.08), transparent 55%),
      radial-gradient(800px 220px at 90% 20%, rgba(255, 77, 79, 0.06), transparent 60%);
    border-radius: 8px;
    padding: 10px 12px 12px;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
  }
  
  .chart-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
  }
  
  .pulse-dot {
    width: 8px;
    height: 8px;
    background-color: #ff4d4f;
    border-radius: 50%;
    box-shadow: 0 0 8px #ff4d4f;
    animation: pulse 1.5s infinite;
  }
  
  .header-text { display: flex; flex-direction: column; gap: 2px; }
  .title {
    margin: 0;
    color: rgba(255,255,255,0.92);
    font-size: 14px;
    font-family: 'Orbitron', 'Rajdhani', sans-serif;
    letter-spacing: 1px;
    text-shadow: 0 0 14px rgba(0,210,255,0.25);
  }
  .subtitle {
    color: rgba(0,210,255,0.65);
    font-size: 11px;
    font-family: 'Rajdhani', sans-serif;
    letter-spacing: 0.5px;
  }
  .header-chip{
    margin-left: auto;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 10px;
    letter-spacing: 2px;
    font-family: 'Orbitron', monospace;
    color: rgba(0,210,255,0.95);
    border: 1px solid rgba(0,210,255,0.28);
    background: rgba(0, 210, 255, 0.10);
    box-shadow: 0 0 14px rgba(0, 210, 255, 0.18);
  }
  
  .echarts-box {
    flex: 1;
    width: 100%;
  }
  
  @keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(255, 77, 79, 0.7); }
    70% { box-shadow: 0 0 0 6px rgba(255, 77, 79, 0); }
    100% { box-shadow: 0 0 0 0 rgba(255, 77, 79, 0); }
  }
  </style>