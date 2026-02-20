<template>
  <PanelBox title="机队指挥中心">
    <div class="fleet-container">
      <div class="tab-header">
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

      <div class="fleet-list">
        <div 
          v-for="item in currentFleet" 
          :key="item.id"
          class="fleet-item"
          :class="{ selected: selectedItem && selectedItem.id === item.id }"
          @click="selectItem(item)"
        >
          <div class="item-header">
            <span class="item-id">[ID: {{ item.id }}]</span>
            <span class="item-type">{{ item.type }}</span>
          </div>
          <div class="item-status">
            <span 
              class="status-badge battery"
              :class="getBatteryClass(item.battery)"
            >
              [电量: {{ item.battery }}%]
            </span>
            <span 
              class="status-badge status"
              :class="getStatusClass(item.status)"
            >
              [状态: {{ item.status }}]
            </span>
          </div>
        </div>
      </div>

      <div class="fleet-summary">
        <span class="summary-item">总计: {{ currentFleet.length }}</span>
        <span class="summary-item">在线: {{ onlineCount }}</span>
        <span class="summary-item">任务中: {{ taskCount }}</span>
      </div>
    </div>
  </PanelBox>
</template>

<script setup>
import { ref, computed } from 'vue'
import PanelBox from './ui/PanelBox.vue'
import { useAudio } from '../hooks/useAudio'

const emit = defineEmits(['select'])
const { playClick } = useAudio()

const activeTab = ref('highway')

const tabs = [
  { id: 'highway', name: '京津干线' },
  { id: 'city', name: '市内配送' }
]

const highwayFleet = ref([
  { id: 'A-01', type: '救护车', battery: 85, status: '行驶中', position: { lon: 116.4, lat: 39.9 } },
  { id: 'A-02', type: '救护车', battery: 72, status: '待命', position: { lon: 116.5, lat: 39.8 } },
  { id: 'A-03', type: '救护车', battery: 91, status: '任务中', position: { lon: 116.3, lat: 39.7 } },
  { id: 'A-04', type: '救护车', battery: 45, status: '充电中', position: { lon: 116.6, lat: 39.85 } },
  { id: 'A-05', type: '救护车', battery: 68, status: '行驶中', position: { lon: 116.45, lat: 39.75 } }
])

const cityFleet = ref([
  { id: 'D-01', type: '无人机', battery: 92, status: '飞行中', position: { lon: 116.4, lat: 39.9 } },
  { id: 'D-02', type: '无人机', battery: 78, status: '待命', position: { lon: 116.42, lat: 39.88 } },
  { id: 'D-03', type: '无人机', battery: 65, status: '任务中', position: { lon: 116.38, lat: 39.92 } },
  { id: 'D-04', type: '无人机', battery: 88, status: '返航中', position: { lon: 116.44, lat: 39.86 } },
  { id: 'D-05', type: '无人机', battery: 54, status: '充电中', position: { lon: 116.46, lat: 39.84 } },
  { id: 'D-06', type: '无人机', battery: 97, status: '飞行中', position: { lon: 116.48, lat: 39.82 } }
])

const selectedItem = ref(null)

const currentFleet = computed(() => {
  return activeTab.value === 'highway' ? highwayFleet.value : cityFleet.value
})

const onlineCount = computed(() => {
  return currentFleet.value.filter(item => item.status !== '充电中').length
})

const taskCount = computed(() => {
  return currentFleet.value.filter(item => ['任务中', '行驶中', '飞行中'].includes(item.status)).length
})

const getBatteryClass = (battery) => {
  if (battery >= 70) return 'high'
  if (battery >= 40) return 'medium'
  return 'low'
}

const getStatusClass = (status) => {
  const statusMap = {
    '行驶中': 'active',
    '飞行中': 'active',
    '任务中': 'task',
    '待命': 'idle',
    '返航中': 'return',
    '充电中': 'charging'
  }
  return statusMap[status] || 'idle'
}

const selectItem = (item) => {
  playClick()
  selectedItem.value = item
  emit('select', item)
}

const switchTab = (tabId) => {
  playClick()
  activeTab.value = tabId
}

defineExpose({ activeTab, currentFleet })
</script>

<style scoped>
.fleet-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.tab-header {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(0, 210, 255, 0.2);
}

.tab-btn {
  flex: 1;
  background: rgba(0, 210, 255, 0.1);
  border: 1px solid rgba(0, 210, 255, 0.3);
  color: rgba(255, 255, 255, 0.7);
  padding: 8px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-family: 'Rajdhani', 'Roboto Mono', monospace;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
  transition: all 0.3s;
}

.tab-btn:hover {
  background: rgba(0, 210, 255, 0.2);
  border-color: rgba(0, 210, 255, 0.5);
  color: var(--neon-blue);
}

.tab-btn.active {
  background: rgba(0, 210, 255, 0.3);
  border-color: var(--neon-blue);
  color: var(--neon-blue);
  box-shadow: 0 0 10px rgba(0, 210, 255, 0.3);
}

.fleet-list {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}

.fleet-item {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(0, 210, 255, 0.2);
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.3s;
  animation: slideIn 0.3s ease-out;
}

.fleet-item:hover {
  background: rgba(0, 210, 255, 0.1);
  border-color: rgba(0, 210, 255, 0.4);
  transform: translateX(4px);
}

.fleet-item.selected {
  background: rgba(0, 210, 255, 0.2);
  border-color: var(--neon-blue);
  box-shadow: 0 0 15px rgba(0, 210, 255, 0.3);
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.item-id {
  color: var(--neon-blue);
  font-family: 'Orbitron', 'Roboto Mono', monospace;
  font-size: 14px;
  font-weight: 600;
  text-shadow: 0 0 8px rgba(0, 210, 255, 0.5);
}

.item-type {
  color: rgba(255, 255, 255, 0.6);
  font-size: 11px;
  background: rgba(0, 210, 255, 0.1);
  padding: 2px 6px;
  border-radius: 2px;
  text-transform: uppercase;
}

.item-status {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.status-badge {
  font-size: 10px;
  padding: 3px 8px;
  border-radius: 3px;
  font-family: 'Roboto Mono', monospace;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border: 1px solid;
}

.battery.high {
  color: #00ff88;
  background: rgba(0, 255, 136, 0.1);
  border-color: rgba(0, 255, 136, 0.3);
}

.battery.medium {
  color: #ffd700;
  background: rgba(255, 215, 0, 0.1);
  border-color: rgba(255, 215, 0, 0.3);
}

.battery.low {
  color: #ff4d4f;
  background: rgba(255, 77, 79, 0.1);
  border-color: rgba(255, 77, 79, 0.3);
}

.status.active {
  color: #00ff88;
  background: rgba(0, 255, 136, 0.1);
  border-color: rgba(0, 255, 136, 0.3);
}

.status.task {
  color: #00d2ff;
  background: rgba(0, 210, 255, 0.1);
  border-color: rgba(0, 210, 255, 0.3);
}

.status.idle {
  color: rgba(255, 255, 255, 0.6);
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.2);
}

.status.return {
  color: #ffd700;
  background: rgba(255, 215, 0, 0.1);
  border-color: rgba(255, 215, 0, 0.3);
}

.status.charging {
  color: #ff4d4f;
  background: rgba(255, 77, 79, 0.1);
  border-color: rgba(255, 77, 79, 0.3);
}

.fleet-summary {
  display: flex;
  justify-content: space-between;
  padding-top: 10px;
  border-top: 1px solid rgba(0, 210, 255, 0.2);
  margin-top: 10px;
}

.summary-item {
  color: rgba(255, 255, 255, 0.6);
  font-size: 11px;
  font-family: 'Roboto Mono', monospace;
  text-transform: uppercase;
}

.fleet-list::-webkit-scrollbar {
  width: 4px;
}

.fleet-list::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.5);
}

.fleet-list::-webkit-scrollbar-thumb {
  background: var(--neon-blue);
  border-radius: 2px;
}

.fleet-list::-webkit-scrollbar-thumb:hover {
  background: #00cc6e;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
</style>
