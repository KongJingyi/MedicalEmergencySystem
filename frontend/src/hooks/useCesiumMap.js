// src/hooks/useCesiumMap.js
import { shallowRef } from 'vue'
import * as Cesium from 'cesium'
import "cesium/Build/Cesium/Widgets/widgets.css"

// 关键位置定义（起点 -> 终点）
export const LOCATIONS = {
  START: { lng: 116.3538, lat: 39.9337, name: "调度中心", color: Cesium.Color.CORNFLOWERBLUE },
  END: { lng: 116.3725, lat: 39.9468, name: "目标医院", color: Cesium.Color.CRIMSON }
}

// 🛠️ 升级版辅助函数：同时调整经纬度和高度
// longitudeOffset / latitudeOffset 单位：弧度；heightOffset 单位：米
function updateTilesetLocation(tileset, longitudeOffset, latitudeOffset, heightOffset) {
  const center = tileset.boundingSphere.center;
  const cartographic = Cesium.Cartographic.fromCartesian(center);
  
  const surface = Cesium.Cartesian3.fromRadians(
    cartographic.longitude,
    cartographic.latitude,
    cartographic.height
  );
  
  const offset = Cesium.Cartesian3.fromRadians(
    cartographic.longitude + longitudeOffset, // 经度偏移 (弧度)
    cartographic.latitude + latitudeOffset,   // 纬度偏移 (弧度)
    cartographic.height + heightOffset        // 高度偏移 (米)
  );
  
  const translation = Cesium.Cartesian3.subtract(
    offset,
    surface,
    new Cesium.Cartesian3()
  );
  
  tileset.modelMatrix = Cesium.Matrix4.fromTranslation(translation);
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

    // 4. 🌟 加载本地购买的真实北京 3D Tiles
    try {
      console.log("正在加载本地 3D 北京模型...");

      // 关键 1：开启地球 (作为地基，否则模型会悬浮在黑洞里)
      viewer.scene.globe.show = true;

      // 关键 2：加载 tileset.json
      // 这里的路径 '/Beijing3D/tileset.json' 对应你 public 下的文件夹名
      const cityTileset = await Cesium.Cesium3DTileset.fromUrl(
        '/Beijing3D/tileset.json',
        {
          maximumScreenSpaceError: 10, // 数值越小越精细，但越吃显卡（默认16）
          maximumMemoryUsage: 2048,    // 允许最大显存 2GB
          skipLevelOfDetail: true,     // 优化加载速度
          baseScreenSpaceError: 1024,
          skipScreenSpaceErrorFactor: 16,
          skipLevels: 1
        }
      );

      // ⭐ CustomShader：在保留原始纹理的基础上叠加“全息蓝光扫描 + 呼吸边缘光”效果
      const hologramShader = new Cesium.CustomShader({
        // 使用 PBR/光照，但通过 emissive 叠加高科技光效
        lightingModel: Cesium.LightingModel.PBR,
        fragmentShaderText: `
        void fragmentMain(FragmentInput fsInput, inout czm_modelMaterial material) {
          // 世界坐标高度（近似用于竖直方向渐变）
          float height = fsInput.attributes.positionWC.z;

          // 归一化高度（用于从底部到高层渐变），这里做一个简单的缩放
          float hNorm = clamp((height - 0.0) / 200.0, 0.0, 1.0);

          // 全局时间（使用帧号近似，避免传 uniform）
          float t = float(czm_frameNumber) * 0.02;

          // === 1. 底部全息扫描带 ===
          // 利用高度 + 时间做一条向上移动的扫描带
          float band = fract(hNorm * 4.0 + t);
          float scan = smoothstep(0.0, 0.15, band) * (1.0 - smoothstep(0.7, 1.0, band));

          // === 2. 高层建筑边缘呼吸光 ===
          // 根据法线与竖直方向的夹角，提取“边缘”区域
          vec3 n = normalize(fsInput.attributes.normalEC);
          float edge = 1.0 - abs(dot(n, vec3(0.0, 0.0, 1.0)));
          // 高层区域权重
          float highLayer = smoothstep(0.4, 1.0, hNorm);
          // 呼吸节奏
          float breathing = 0.5 + 0.5 * sin(t * 6.28318);

          // 全息蓝色
          vec3 holoColor = vec3(0.0, 0.8, 1.2);

          // 底部扫描：主要增强建筑下半部分的发光
          float scanIntensity = scan * (1.0 - hNorm);
          // 边缘呼吸：主要作用在高层轮廓
          float edgeGlow = edge * highLayer * breathing;

          // 通过 emissive 叠加，不修改原始 diffuse/纹理
          material.emissive += holoColor * (scanIntensity * 1.2 + edgeGlow * 0.5);

          // 轻微提高整体发光，让画面偏“赛博蓝”
          material.emissive += holoColor * 0.05;
        }`
      });

      cityTileset.customShader = hologramShader;

      // 关键 3：添加到场景
      viewer.scene.primitives.add(cityTileset);

      // 关键 4：飞过去看看！
      // 这一步很重要，因为有时候买的数据坐标系不对，用 zoomTo 能直接定位到模型位置
      viewer.zoomTo(cityTileset);

      // 关键 5：位置对齐：经度 / 纬度 / 高度 三个维度（初始值，可用键盘再微调）
      updateTilesetLocation(
        cityTileset,
        0.0,  // longitudeOffset 经度偏移（弧度）
        0.0,  // latitudeOffset  纬度偏移（弧度）
        0.0   // heightOffset    高度偏移（米）
      );

      console.log("✅ 真实北京城加载成功！");
    } catch (error) {
      console.error("❌ 加载 3D 模型失败，请检查 public 路径:", error);
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