<script setup>
import PanelBox from './ui/PanelBox.vue'
import HospitalNeedsChart from './charts/HospitalNeedsChart.vue'

defineProps({
  hospitalName: {
    type: String,
    default: '',
  },
  needsData: {
    type: Object,
    default: () => ({}),
  },
})
</script>

<template>
  <PanelBox title="医院物资状态" class="right-panel">
    <HospitalNeedsChart
      :hospitalName="hospitalName"
      :needsData="needsData"
    />
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
</style>