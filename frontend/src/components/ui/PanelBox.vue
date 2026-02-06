<template>
  <div class="sci-fi-panel">
    <div class="corner top-left"></div>
    <div class="corner top-right"></div>
    <div class="corner bottom-left"></div>
    <div class="corner bottom-right"></div>
    
    <div class="panel-header" v-if="title">
      <span class="header-deco">///</span> {{ title }}
    </div>
    
    <div class="panel-content">
      <slot></slot>
    </div>
  </div>
</template>

<script setup>
defineProps({ title: String })
</script>

<style scoped>
.sci-fi-panel {
  position: relative;
  background: var(--bg-glass);
  backdrop-filter: blur(10px); /* 毛玻璃核心 */
  border: 1px solid var(--border-color);
  padding: 15px;
  box-shadow: 0 0 20px rgba(0, 210, 255, 0.1);
}

.panel-header {
  color: var(--neon-blue);
  font-family: 'Orbitron', sans-serif;
  border-bottom: 1px solid rgba(0, 210, 255, 0.3);
  padding-bottom: 5px;
  margin-bottom: 10px;
  text-shadow: 0 0 5px var(--neon-blue);
}

.header-deco {
  margin-right: 6px;
  opacity: 0.8;
}

/* 角落装饰线 */
.corner {
  position: absolute;
  width: 10px;
  height: 10px;
  border: 2px solid var(--neon-blue);
  transition: all 0.3s;
}
.top-left { top: -1px; left: -1px; border-right: none; border-bottom: none; }
.top-right { top: -1px; right: -1px; border-left: none; border-bottom: none; }
.bottom-left { bottom: -1px; left: -1px; border-right: none; border-top: none; }
.bottom-right { bottom: -1px; right: -1px; border-left: none; border-top: none; }

.sci-fi-panel:hover .corner {
  width: 15px;
  height: 15px;
  box-shadow: 0 0 10px var(--neon-blue);
}
</style>

