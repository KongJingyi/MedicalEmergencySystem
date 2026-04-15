<script setup>
import PanelBox from './ui/PanelBox.vue'

defineProps({
  shortageHistory: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['go-dispatch'])
</script>

<template>
  <PanelBox title="急缺发布记录" class="right-panel">
    <div class="records-wrap">
      <div v-if="!shortageHistory.length" class="empty">暂无急缺发布记录</div>
      <div v-else class="records-list">
        <div class="record-item" v-for="item in shortageHistory" :key="item.id">
          <div class="line1">
            <span class="hospital">{{ item.hospital }}</span>
            <span class="time">{{ item.time }}</span>
          </div>
          <div class="line2">
            急缺：{{ item.resourceName }} × {{ item.qty }}
          </div>
          <div class="line3">
            <span class="status" :class="item.status === 'dispatched' ? 'ok' : 'pending'">
              {{ item.status === 'dispatched' ? '已调度' : '待调度' }}
            </span>
            <button
              v-if="item.status !== 'dispatched'"
              class="dispatch-btn"
              @click="emit('go-dispatch', item.id)"
            >
              去调度
            </button>
          </div>
        </div>
      </div>
    </div>
  </PanelBox>
</template>

<style scoped>
.right-panel {
  position: absolute;
  right: 20px;
  top: 250px;
  width: clamp(320px, 22vw, 400px);
  z-index: 998;
}

.records-wrap {
  min-height: 220px;
  max-height: 340px;
}

.records-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 330px;
  overflow-y: auto;
  padding-right: 2px;
}

.record-item {
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  padding: 8px 10px;
}

.line1 {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.hospital {
  color: #ffffff;
  font-weight: 700;
  font-size: 13px;
}

.time {
  color: #9adfff;
  font-size: 11px;
}

.line2 {
  margin-top: 4px;
  color: rgba(255, 255, 255, 0.84);
  font-size: 12px;
}

.line3 {
  margin-top: 6px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status {
  font-size: 11px;
  font-weight: 700;
}

.status.pending {
  color: #fbbf24;
}

.status.ok {
  color: #34d399;
}

.dispatch-btn {
  border: 1px solid rgba(0, 210, 255, 0.52);
  background: rgba(0, 210, 255, 0.16);
  color: #9defff;
  border-radius: 6px;
  padding: 3px 10px;
  font-size: 11px;
  cursor: pointer;
}

.empty {
  color: rgba(255, 255, 255, 0.65);
  font-size: 13px;
  text-align: center;
  padding: 22px 8px;
}
</style>