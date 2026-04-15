<template>
  <transition name="cyber-fade">
    <div v-if="visible" class="decision-modal">
      <div class="modal-header">
        <h3>🧠 智能调度决策报告</h3>
        <button class="close-btn" @click="close">×</button>
      </div>

      <div class="modal-content" v-if="reportData">
        <div class="winner-banner">
          <span class="badge">最优推荐</span>
          <span class="winner-text">系统已自动指派：{{ reportData.recommend ? '🛸 无人机空运' : '🚑 地面救护车' }}</span>
        </div>

        <div class="analysis-container">
          <div
            v-for="(item, index) in reportData.analysis"
            :key="index"
            class="analysis-card"
            :class="{ 'is-winner': item.recommend }"
          >
            <div class="card-title">
              {{ item.type }}
              <span class="score">{{ item.score.toFixed(1) }} 分</span>
            </div>
            <ul class="log-list">
              <li
                v-for="(log, idx) in item.logs"
                :key="idx"
                :class="{ 'text-red': log.includes('扣分') || log.includes('降至') || log.includes('-') }"
              >
                {{ log }}
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref } from 'vue'

const visible = ref(false)
const reportData = ref(null)

// 暴露给父组件的方法
const showReport = (data) => {
  reportData.value = data
  visible.value = true
}
const close = () => { visible.value = false }

defineExpose({ showReport, close })
</script>

<style scoped>
.decision-modal {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 500px;
  background: rgba(0, 15, 30, 0.85);
  border: 1px solid #00d2ff;
  border-radius: 8px;
  box-shadow: 0 0 30px rgba(0, 210, 255, 0.3);
  z-index: 9999;
  backdrop-filter: blur(10px);
  color: #fff;
  font-family: 'Rajdhani', sans-serif;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  padding: 15px 20px;
  border-bottom: 1px solid rgba(0, 210, 255, 0.3);
}
.modal-header h3 { margin: 0; color: #00d2ff; font-weight: bold; }
.close-btn { background: none; border: none; color: #fff; font-size: 24px; cursor: pointer; }
.modal-content { padding: 20px; }
.winner-banner {
  background: rgba(0, 255, 170, 0.1);
  border-left: 4px solid #00ffaa;
  padding: 10px;
  margin-bottom: 20px;
}
.badge { background: #00ffaa; color: #000; padding: 2px 6px; font-size: 12px; font-weight: bold; border-radius: 3px; margin-right: 10px; }
.winner-text { font-size: 16px; font-weight: bold; }

.analysis-container { display: flex; gap: 15px; }
.analysis-card {
  flex: 1;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  padding: 15px;
}
.analysis-card.is-winner {
  border-color: #00ffaa;
  box-shadow: 0 0 15px rgba(0, 255, 170, 0.1);
}
.card-title { font-size: 16px; font-weight: bold; margin-bottom: 10px; display: flex; justify-content: space-between; border-bottom: 1px dashed rgba(255,255,255,0.2); padding-bottom: 5px; }
.score { color: #ffcc00; }
.log-list { margin: 0; padding-left: 15px; font-size: 12px; color: #ccc; line-height: 1.6; }
.text-red { color: #ff4d4f; font-weight: bold; }

/* 炫酷的淡入弹出动画 */
.cyber-fade-enter-active, .cyber-fade-leave-active { transition: all 0.3s ease; }
.cyber-fade-enter-from, .cyber-fade-leave-to { opacity: 0; transform: translate(-50%, -40%) scale(0.95); }
</style>
