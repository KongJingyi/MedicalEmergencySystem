<template>
  <div class="timeline-panel">
    <div class="header">
      <span class="title">🛰️ 指挥中心事件流</span>
      <button class="export-btn" @click="downloadCSV" title="导出 CSV">导出CSV</button>
    </div>
    <div class="log-list">
      <div v-for="(log, index) in logs" :key="index" class="log-item" :class="log.type.toLowerCase()">
        <span class="time">[{{ log.time }}]</span>
        <span class="type">{{ log.type }}</span>
        <span class="msg">{{ log.msg }}</span>
      </div>
      <div v-if="!logs || logs.length === 0" class="empty">暂无事件日志...</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  logs: {
    type: Array,
    default: () => [],
  },
})

const normalizedLogs = computed(() => (Array.isArray(props.logs) ? props.logs : []))

const escapeCsv = (v) => {
  const s = String(v ?? '')
  return `"${s.replace(/"/g, '""')}"`
}

const downloadCSV = () => {
  if (normalizedLogs.value.length === 0) return

  // Excel 友好：加 BOM，避免中文乱码
  const BOM = '\uFEFF'
  const header = ['Time', 'Type', 'Message']
  const rows = normalizedLogs.value.map((log) => [
    escapeCsv(log.time),
    escapeCsv(log.type),
    escapeCsv(log.msg),
  ])

  const csvContent = BOM + [header.join(','), ...rows.map((r) => r.join(','))].join('\n')
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.setAttribute('href', url)
  link.setAttribute(
    'download',
    `event-stream-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.csv`
  )
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.timeline-panel {
  width: 100%;
  height: 250px;
  background: rgba(0, 15, 30, 0.82);
  border: 1px solid #00d2ff;
  border-radius: 8px;
  overflow: hidden;
}
.header {
  height: 38px;
  padding: 0 12px;
  color: #00d2ff;
  font-weight: 700;
  border-bottom: 1px solid rgba(0, 210, 255, 0.25);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.title {
  line-height: 38px;
}
.export-btn {
  height: 26px;
  padding: 0 10px;
  border-radius: 6px;
  border: 1px solid rgba(0, 210, 255, 0.45);
  background: rgba(0, 210, 255, 0.12);
  color: #00d2ff;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}
.export-btn:hover {
  background: rgba(0, 210, 255, 0.22);
  box-shadow: 0 0 12px rgba(0, 210, 255, 0.25);
  transform: translateY(-1px);
}
.log-list {
  height: calc(100% - 38px);
  overflow-y: auto;
  padding: 8px 10px;
  font-size: 12px;
}
.log-item {
  margin-bottom: 6px;
  line-height: 1.4;
  color: #d5e7ff;
  word-break: break-all;
}
.log-item .time { color: #8ab4ff; margin-right: 6px; }
.log-item .type { font-weight: 700; margin-right: 6px; }
.log-item.info .type { color: #00d2ff; }
.log-item.success .type { color: #00ffaa; }
.log-item.warn .type { color: #faad14; }
.log-item.error .type { color: #ff4d4f; }
.empty { color: rgba(255,255,255,0.5); padding-top: 8px; }
</style>
