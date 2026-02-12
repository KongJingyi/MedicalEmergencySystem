<template>
  <div class="sci-fi-panel">
    <svg class="border-svg" width="100%" height="100%">
      <defs>
        <linearGradient id="borderGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:var(--neon-blue);stop-opacity:1" />
          <stop offset="50%" style="stop-color:var(--neon-blue);stop-opacity:0.5" />
          <stop offset="100%" style="stop-color:var(--neon-blue);stop-opacity:1" />
        </linearGradient>
        <filter id="glow">
          <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
          <feMerge>
            <feMergeNode in="coloredBlur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>
      
      <line x1="0" y1="0" x2="30" y2="0" stroke="var(--neon-blue)" stroke-width="2" filter="url(#glow)"/>
      <line x1="0" y1="0" x2="0" y2="30" stroke="var(--neon-blue)" stroke-width="2" filter="url(#glow)"/>
      
      <line x1="100%" y1="0" x2="calc(100% - 30px)" y2="0" stroke="var(--neon-blue)" stroke-width="2" filter="url(#glow)"/>
      <line x1="100%" y1="0" x2="100%" y2="30" stroke="var(--neon-blue)" stroke-width="2" filter="url(#glow)"/>
      
      <line x1="0" y1="100%" x2="30" y2="100%" stroke="var(--neon-blue)" stroke-width="2" filter="url(#glow)"/>
      <line x1="0" y1="100%" x2="0" y2="calc(100% - 30px)" stroke="var(--neon-blue)" stroke-width="2" filter="url(#glow)"/>
      
      <line x1="100%" y1="100%" x2="calc(100% - 30px)" y2="100%" stroke="var(--neon-blue)" stroke-width="2" filter="url(#glow)"/>
      <line x1="100%" y1="100%" x2="100%" y2="calc(100% - 30px)" stroke="var(--neon-blue)" stroke-width="2" filter="url(#glow)"/>
    </svg>

    <div class="corner top-left"></div>
    <div class="corner top-right"></div>
    <div class="corner bottom-left"></div>
    <div class="corner bottom-right"></div>
    
    <div class="panel-header" v-if="title || $slots['header-extra']">
      <div class="header-left">
        <span class="header-deco">///</span>
        <span class="header-title">{{ title }}</span>
      </div>
      <span class="header-line"></span>
      <slot name="header-extra"></slot>
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
  backdrop-filter: blur(10px);
  border: 1px solid var(--border-color);
  padding: 15px;
  box-shadow: 
    0 0 20px rgba(0, 210, 255, 0.1),
    inset 0 0 30px rgba(0, 210, 255, 0.05);
  border-radius: 4px;
  overflow: hidden;
}

.border-svg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}

.panel-header {
  position: relative;
  color: var(--neon-blue);
  font-family: 'Orbitron', 'Roboto Mono', monospace, sans-serif;
  font-size: 14px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 2px;
  border-bottom: 1px solid rgba(0, 210, 255, 0.3);
  padding-bottom: 8px;
  margin-bottom: 12px;
  text-shadow: 0 0 8px var(--neon-blue);
  display: flex;
  align-items: center;
  z-index: 2;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-deco {
  margin-right: 8px;
  opacity: 0.9;
  font-size: 12px;
}

.header-title {
  font-size: 14px;
}

.header-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(to right, var(--neon-blue), transparent);
  margin-left: 12px;
  opacity: 0.5;
}

.panel-content {
  position: relative;
  z-index: 2;
  height: calc(100% - 40px);
  overflow: hidden;
}

.corner {
  position: absolute;
  width: 12px;
  height: 12px;
  border: 2px solid var(--neon-blue);
  transition: all 0.3s ease;
  z-index: 2;
  box-shadow: 0 0 5px rgba(0, 210, 255, 0.5);
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

.sci-fi-panel:hover .corner {
  width: 18px;
  height: 18px;
  box-shadow: 0 0 15px rgba(0, 210, 255, 0.8);
}

.sci-fi-panel:hover {
  box-shadow: 
    0 0 30px rgba(0, 210, 255, 0.2),
    inset 0 0 40px rgba(0, 210, 255, 0.08);
  border-color: rgba(0, 210, 255, 0.6);
}
</style>

