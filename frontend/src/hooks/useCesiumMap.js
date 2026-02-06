// src/hooks/useCesiumMap.js
import { shallowRef } from 'vue'
import * as Cesium from 'cesium'
import "cesium/Build/Cesium/Widgets/widgets.css"

// 关键位置定义（起点 -> 终点）
export const LOCATIONS = {
  START: { lng: 116.3538, lat: 39.9337, name: "调度中心", color: Cesium.Color.CORNFLOWERBLUE },
  END: { lng: 116.3725, lat: 39.9468, name: "目标医院", color: Cesium.Color.CRIMSON }
}

export function useCesiumMap() {
  // 使用 shallowRef 存储 viewer（Cesium 实例是复杂对象，浅响应足够）
  const viewerRef = shallowRef(null)

  // 向地图添加标记点
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

  // 对外暴露的添加标记方法（内部调用 addMarkers，保持接口统一）
  const addMarkersPublic = (viewer) => {
    addMarkers(viewer)
  }

  const initMap = async (containerId) => {
    // 1. 设置 Cesium Token
    Cesium.Ion.defaultAccessToken = import.meta.env.VITE_CESIUM_TOKEN || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJmZGE1OTk3Zi02Y2Y0LTQ0ZmUtYTk3NC03NTYyNmEzMzczNWQiLCJpZCI6MzI3MTAxLCJpYXQiOjE3NTc1ODIzNDZ9.abj8PxbfTVfqzWdS-UCCzMD5ROorrNd_-kX5gFTI-_Q'; 

    // 2. 加载地形数据（带异常处理）
    let terrainProvider;
    try {
      terrainProvider = await Cesium.createWorldTerrainAsync();
    } catch (error) {
      console.warn("⚠️ 地形数据加载失败，将使用默认地形", error);
      terrainProvider = undefined;
    }

    // 3. 初始化 Viewer（保留大气等效果，由 WeatherSystem 管理天气；这里只做性能相关配置）
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

      // 🔥 1. 性能优化：按需渲染
      requestRenderMode: true,
      maximumRenderTimeChange: Infinity,

      // 🔥 2. 画质与性能权衡
      contextOptions: {
        webgl: {
          alpha: false,
          antialias: true, // 主视图保留抗锯齿，观感更好
          powerPreference: 'high-performance',
        },
      },
    });

    // 🔥 3. 限制帧率，避免一直满帧渲染
    viewer.targetFrameRate = 45;
    // 🔥 4. 略微降低分辨率，给后期天气特效留出显卡空间
    viewer.resolutionScale = 0.8;

    // 4. 加载 3D 城市模型
    try {
      const tileset = await Cesium.Cesium3DTileset.fromIonAssetId(96188);
      viewer.scene.primitives.add(tileset);
      tileset.style = new Cesium.Cesium3DTileStyle({
        color: { conditions: [['true', 'color("white", 0.6)']] }
      });
    } catch (e) { 
      console.error("❌ 3D城市模型加载失败", e); 
    }

    // 5. 设置相机初始视角
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(116.363, 39.935, 2500), 
      orientation: {
        heading: Cesium.Math.toRadians(0.0), 
        pitch: Cesium.Math.toRadians(-40.0),  
        roll: 0.0
      },
      duration: 3 
    });

    // 6. 添加标记点到地图
    addMarkers(viewer);

    // 将实例挂载到 ref 并暴露到全局（方便调试）
    viewerRef.value = viewer;
    window.viewer = viewer; // 方便开发者调试
    
    return viewer;
  }

  return {
    viewerRef,
    initMap,
    addMarkers: addMarkersPublic // 对外暴露统一的添加标记方法
  }
}