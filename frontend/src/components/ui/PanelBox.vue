<template>
  <div class="panel-box">
    <div class="panel-border">
      <svg class="border-svg" width="100%" height="100%">
        <defs>
          <linearGradient id="panelGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:#00d2ff;stop-opacity:1" />
            <stop offset="50%" style="stop-color:#00d2ff;stop-opacity:0.5" />
            <stop offset="100%" style="stop-color:#00d2ff;stop-opacity:1" />
          </linearGradient>
          <filter id="panelGlow">
            <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        
        <line x1="0" y1="0" x2="30" y2="0" stroke="#00d2ff" stroke-width="2" filter="url(#panelGlow)"/>
        <line x1="0" y1="0" x2="0" y2="30" stroke="#00d2ff" stroke-width="2" filter="url(#panelGlow)"/>
        
        <line x1="100%" y1="0" x2="calc(100% - 30px)" y2="0" stroke="#00d2ff" stroke-width="2" filter="url(#panelGlow)"/>
        <line x1="100%" y1="0" x2="100%" y2="30" stroke="#00d2ff" stroke-width="2" filter="url(#panelGlow)"/>
        
        <line x1="0" y1="100%" x2="30" y2="100%" stroke="#00d2ff" stroke-width="2" filter="url(#panelGlow)"/>
        <line x1="0" y1="100%" x2="0" y2="calc(100% - 30px)" stroke="#00d2ff" stroke-width="2" filter="url(#panelGlow)"/>
        
        <line x1="100%" y1="100%" x2="calc(100% - 30px)" y2="100%" stroke="#00d2ff" stroke-width="2" filter="url(#panelGlow)"/>
        <line x1="100%" y1="100%" x2="100%" y2="calc(100% - 30px)" stroke="#00d2ff" stroke-width="2" filter="url(#panelGlow)"/>
      </svg>
      
      <div class="corner top-left"></div>
      <div class="corner top-right"></div>
      <div class="corner bottom-left"></div>
      <div class="corner bottom-right"></div>
    </div>
    
    <div class="panel-header" v-if="title || $slots['header-extra']">
      <div class="header-left">
        <span class="header-deco">///</span>
        <span class="header-title">{{ title }}</span>
      </div>
      <div class="header-line"></div>
      <slot name="header-extra"></slot>
    </div>
    
    <div class="panel-content">
      <slot></slot>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.panel-box {
  position: relative;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(15px);
  -webkit-backdrop-filter: blur(15px);
  border: 1px solid rgba(0, 210, 255, 0.3);
  border-radius: 6px;
  padding: 10px;
  box-shadow: 
    0 0 25px rgba(0, 210, 255, 0.15),
    0 0 50px rgba(0, 210, 255, 0.05),
    inset 0 0 40px rgba(0, 210, 255, 0.03);
  overflow: hidden;
  transition: all 0.3s ease;
}

.panel-box:hover {
  border-color: rgba(0, 210, 255, 0.5);
  box-shadow: 
    0 0 35px rgba(0, 210, 255, 0.25),
    0 0 70px rgba(0, 210, 255, 0.1),
    inset 0 0 50px rgba(0, 210, 255, 0.05);
}

.panel-border {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}

.border-svg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.corner {
  position: absolute;
  width: 14px;
  height: 14px;
  border: 2px solid #00d2ff;
  transition: all 0.3s ease;
  z-index: 2;
  box-shadow: 0 0 8px rgba(0, 210, 255, 0.6);
}

.top-left { 
  top: -1px; 
  left: -1px; 
  border-right: none; 
  border-bottom: none; 
}
.top-right { 
  top: -1px; 
  right: -1px; 
  border-left: none; 
  border-bottom: none; 
}
.bottom-left { 
  bottom: -1px; 
  left: -1px; 
  border-right: none; 
  border-top: none; 
}
.bottom-right { 
  bottom: -1px; 
  right: -1px; 
  border-left: none; 
  border-top: none; 
}

.panel-box:hover .corner {
  width: 20px;
  height: 20px;
  box-shadow: 0 0 20px rgba(0, 210, 255, 0.8);
}

.panel-header {
  position: relative;
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(0, 210, 255, 0.25);
  z-index: 2;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-deco {
  color: rgba(0, 210, 255, 0.9);
  font-family: 'Orbitron', 'Roboto Mono', monospace;
  font-size: 11px;
  letter-spacing: 1px;
}

.header-title {
  color: #00d2ff;
  font-family: 'Orbitron', 'Roboto Mono', monospace;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  text-shadow: 
    0 0 10px rgba(0, 210, 255, 0.6),
    0 0 20px rgba(0, 210, 255, 0.3);
}

.header-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(to right, rgba(0, 210, 255, 0.5), transparent);
  margin-left: 12px;
}

.panel-content {
  position: relative;
  z-index: 2;
  height: calc(100% - 40px);
  overflow: hidden;
}
</style>
