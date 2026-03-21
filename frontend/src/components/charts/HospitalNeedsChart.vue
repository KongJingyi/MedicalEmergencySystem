<template>
    <div class="chart-container">
      <div class="chart-header">
        <span class="pulse-dot"></span>
        <h3>{{ hospitalName || '全市' }} 实时物资缺口</h3>
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
      // 🌟 1. 增加 Tooltip，鼠标放上去可以看到完整长名字
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' }
      },
      grid: {
        left: '3%',
        right: '12%',
        bottom: '5%',
        top: '5%',
        containLabel: true
      },
      xAxis: {
        type: 'value',
        splitLine: { show: false }, // 隐藏网格线
        axisLabel: { show: false }, // 隐藏 X 轴刻度
        axisLine: { show: false },
        axisTick: { show: false }
      },
      yAxis: {
        type: 'category',
        data: categories,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          color: 'rgba(255, 255, 255, 0.85)',
          fontSize: 12,
          fontWeight: 'bold',
          fontFamily: "'Rajdhani', sans-serif",
          // 🌟 2. 核心修改：截断过长的名字
          formatter: function (value) {
            // 如果名字超过 10 个字，就截断并加上省略号
            return value.length > 10 ? value.substring(0, 10) + '...' : value;
          }
        }
      },
      series: [
        {
          type: 'bar',
          data: values,
          barWidth: '40%', // 柱子宽度
          showBackground: true, // 开启背景槽
          backgroundStyle: {
            color: 'rgba(0, 210, 255, 0.05)', // 科技感背景槽
            borderRadius: [0, 10, 10, 0]
          },
          itemStyle: {
            borderRadius: [0, 10, 10, 0],
            // 炫酷的霓虹红渐变色
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: '#ff4d4f' }, // 危险红
              { offset: 1, color: '#ff7875' }  // 亮红
            ]),
            shadowBlur: 10,
            shadowColor: 'rgba(255, 77, 79, 0.5)'
          },
          label: {
            show: true,
            position: 'right', // 数字显示在柱子右侧
            color: '#ff7875',
            fontSize: 14,
            fontWeight: 'bold',
            fontFamily: "'Orbitron', monospace",
            formatter: '{c}' // 显示具体数值
          },
          animationDuration: 1000,
          animationEasing: 'cubicOut'
        }
      ]
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
    background: rgba(0, 0, 0, 0.4);
    border: 1px solid rgba(0, 210, 255, 0.2);
    border-radius: 8px;
    padding: 15px;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
  }
  
  .chart-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
  }
  
  .pulse-dot {
    width: 8px;
    height: 8px;
    background-color: #ff4d4f;
    border-radius: 50%;
    box-shadow: 0 0 8px #ff4d4f;
    animation: pulse 1.5s infinite;
  }
  
  .chart-header h3 {
    margin: 0;
    color: #00d2ff;
    font-size: 15px;
    font-family: 'Rajdhani', sans-serif;
    letter-spacing: 1px;
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