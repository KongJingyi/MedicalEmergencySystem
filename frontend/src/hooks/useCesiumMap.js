// src/hooks/useCesiumMap.js
import { shallowRef } from 'vue'
import * as Cesium from 'cesium'
import axios from 'axios'
import "cesium/Build/Cesium/Widgets/widgets.css"

// 关键位置定义（起点 -> 终点）
export const LOCATIONS = {
  START: { lng: 116.3538, lat: 39.9337, name: "调度中心", color: Cesium.Color.CORNFLOWERBLUE },
  END: { lng: 116.3725, lat: 39.9468, name: "目标医院", color: Cesium.Color.CRIMSON }
}

// 使用 CustomDataSource 管理医院和路网图层，便于一键显隐
const hospitalSource = new Cesium.CustomDataSource('hospitals')
const roadNodeSource = new Cesium.CustomDataSource('roadNodes')

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

  // 加载医院点位
  const loadHospitals = async (viewer) => {
    if (!viewer) return
    if (!viewer.dataSources.contains(hospitalSource)) {
      viewer.dataSources.add(hospitalSource)
    }
    try {
      const res = await axios.get('http://127.0.0.1:8000/api/hospitals')
      hospitalSource.entities.removeAll()
      res.data.forEach((hosp) => {
        hospitalSource.entities.add({
          position: Cesium.Cartesian3.fromDegrees(hosp.lng, hosp.lat, 10),
          point: {
            pixelSize: 10,
            color: Cesium.Color.RED.withAlpha(0.9),
            outlineColor: Cesium.Color.WHITE.withAlpha(0.9),
            outlineWidth: 2,
          },
          label: {
            text: hosp.name,
            font: '14px sans-serif',
            pixelOffset: new Cesium.Cartesian2(0, -30),
            fillColor: Cesium.Color.WHITE,
            showBackground: true,
            backgroundColor: new Cesium.Color(0, 0, 0, 0.6),
          },
        })
      })
    } catch (e) {
      console.error('医院加载失败', e)
    }
  }

  // 加载路网关键节点
  const loadRoadNodes = async (viewer) => {
    if (!viewer) return
    if (!viewer.dataSources.contains(roadNodeSource)) {
      viewer.dataSources.add(roadNodeSource)
    }
    try {
      const res = await axios.get('http://127.0.0.1:8000/api/road_nodes')
      roadNodeSource.entities.removeAll()
      res.data.forEach((node) => {
        roadNodeSource.entities.add({
          position: Cesium.Cartesian3.fromDegrees(node.lng, node.lat, 2),
          point: {
            pixelSize: 6,
            color: Cesium.Color.YELLOW,
            outlineColor: Cesium.Color.BLACK,
            outlineWidth: 1,
          },
        })
      })
    } catch (e) {
      console.error('路网加载失败', e)
    }
  }

  // 图层显示/隐藏控制
  const toggleLayer = (layerName, isShow) => {
    if (layerName === 'hospital') hospitalSource.show = isShow
    if (layerName === 'road') roadNodeSource.show = isShow
  }

  const initMap = async (containerId) => {
    // 1. 设置 Cesium Token
    Cesium.Ion.defaultAccessToken = import.meta.env.VITE_CESIUM_TOKEN || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJmZGE1OTk3Zi02Y2Y0LTQ0ZmUtYTk3NC03NTYyNmEzMzczNWQiLCJpZCI6MzI3MTAxLCJpYXQiOjE3NTc1ODIzNDZ9.abj8PxbfTVfqzWdS-UCCzMD5ROorrNd_-kX5gFTI-_Q'; 

    // 2. 加载地形数据（带异常处理）
    let terrainProvider;
    try {
      // ❌ 不再使用真实地形，避免不可控的高差
      // terrainProvider = await Cesium.createWorldTerrainAsync();

      // ✅ 使用椭球体地形：把地球当作光滑的圆球，方便和 3D Tiles 对齐
      terrainProvider = new Cesium.EllipsoidTerrainProvider();
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

    // 💡 开启 Bloom 泛光（城市霓虹 + 无人机轨迹会有光晕）
    const bloom = viewer.scene.postProcessStages.bloom;
    if (bloom) {
      bloom.enabled = true;
      bloom.uniforms.glowOnly = false;
      bloom.uniforms.contrast = 128.0;
      bloom.uniforms.brightness = -0.3;
      bloom.uniforms.delta = 1.0;
      bloom.uniforms.sigma = 2.0;
      bloom.uniforms.stepSize = 1.0;
    }

    // 💡 MSAA 抗锯齿（在支持 WebGL2 的环境下叠加多重采样）
    if (viewer.scene.msaaSamples !== undefined) {
      viewer.scene.msaaSamples = 4; // 典型值：2 或 4
    }
    // 同时禁用 FXAA，避免和 MSAA 叠加造成过度模糊
    if (viewer.scene.postProcessStages.fxaa) {
      viewer.scene.postProcessStages.fxaa.enabled = false;
    }

    // 🔍 性能监控：在左上角显示 FPS，方便观察 30+ 载具场景下的帧率表现
    viewer.scene.debugShowFramesPerSecond = true;

    // 4. 城市 3D Tiles 由 App.vue 中的 useTilesetManager 统一加载，避免重复添加模型

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

    // 7. 加载医院与路网图层（默认开启）
    await Promise.all([loadHospitals(viewer), loadRoadNodes(viewer)])

    // 将实例挂载到 ref 并暴露到全局（方便调试）
    viewerRef.value = viewer;
    window.viewer = viewer; // 方便开发者调试
    
    return viewer;
  }

  return {
    viewerRef,
    initMap,
    addMarkers: addMarkersPublic, // 对外暴露统一的添加标记方法
    toggleLayer,
  }
}