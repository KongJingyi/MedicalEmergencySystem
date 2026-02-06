// src/hooks/useCesiumMap.js
import { shallowRef } from 'vue'
import * as Cesium from 'cesium'
import "cesium/Build/Cesium/Widgets/widgets.css"

// 坐标定义 (北京大学人民医院 -> 积水潭医院)
export const LOCATIONS = {
  START: { lng: 116.3538, lat: 39.9337, name: "北大人民医院", color: Cesium.Color.CORNFLOWERBLUE },
  END: { lng: 116.3725, lat: 39.9468, name: "积水潭医院", color: Cesium.Color.CRIMSON }
}

export function useCesiumMap() {
  // 使用 shallowRef 存储 viewer，Cesium对象太复杂，不要用深层响应式，否则卡顿
  const viewerRef = shallowRef(null)

  // 内部辅助函数：添加标记
  const addMarkers = (viewer) => {
    Object.values(LOCATIONS).forEach(loc => {
      const isEnd = loc === LOCATIONS.END
      viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(loc.lng, loc.lat, 50),
        point: { pixelSize: isEnd ? 20 : 15, color: loc.color },
        label: { 
          text: loc.name, 
          font: isEnd ? '18px sans-serif' : '16px sans-serif',
          pixelOffset: new Cesium.Cartesian2(0, -20),
          fillColor: Cesium.Color.WHITE,
          showBackground: true,
          backgroundColor: isEnd ? new Cesium.Color(0.8, 0, 0, 0.7) : new Cesium.Color(0, 0, 0, 0.7)
        }
      });
    });
  }

  // 导出 addMarkers 供外部使用（比如 drawRoute 清理后需要重新添加标记）
  const addMarkersPublic = (viewer) => {
    addMarkers(viewer)
  }

  const initMap = async (containerId) => {
    // 1. 设置 Token
    Cesium.Ion.defaultAccessToken = import.meta.env.VITE_CESIUM_TOKEN || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiIxOTJkMGQ1Yi02MDAzLTQ1ZmItYmE2OS03YjI4NTEyMDFhMTIiLCJpZCI6MzI0MjU4LCJpYXQiOjE3NTMyNjUzMTV9.q1G99hnGlMCEbM-QRVPlQukQYuXBad50VSHenwtlOoo'; 

    // 2. 加载地形 (带容错)
    let terrainProvider;
    try {
      terrainProvider = await Cesium.createWorldTerrainAsync();
    } catch (error) {
      console.warn("?? 地形加载失败，降级为默认椭球体", error);
      terrainProvider = undefined;
    }

    // 3. 初始化 Viewer
    const viewer = new Cesium.Viewer(containerId, {
      terrainProvider,
      infoBox: false, 
      selectionIndicator: false, 
      timeline: false, 
      animation: false, 
      baseLayerPicker: false, 
      homeButton: false, 
      geocoder: false, 
      navigationHelpButton: false, 
      sceneModePicker: false,
    });

    // 4. 加载 3D 建筑白膜
    try {
      const tileset = await Cesium.Cesium3DTileset.fromIonAssetId(96188);
      viewer.scene.primitives.add(tileset);
      tileset.style = new Cesium.Cesium3DTileStyle({
        color: { conditions: [['true', 'color("white", 0.6)']] }
      });
    } catch (e) { 
      console.error("? 建筑加载失败", e); 
    }

    // 5. 飞到北京初始视角
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(116.363, 39.935, 2500), 
      orientation: {
        heading: Cesium.Math.toRadians(0.0), 
        pitch: Cesium.Math.toRadians(-40.0),  
        roll: 0.0
      },
      duration: 3 
    });

    // 6. 添加起点终点标记
    addMarkers(viewer);

    // 赋值给 ref，供外部使用
    viewerRef.value = viewer;
    window.viewer = viewer; // 保留供调试
    
    return viewer;
  }

  return {
    viewerRef,
    initMap,
    addMarkers: addMarkersPublic // 导出供外部调用
  }
}
