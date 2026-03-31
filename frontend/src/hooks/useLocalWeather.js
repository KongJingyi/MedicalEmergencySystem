// frontend/src/hooks/useLocalWeather.js
import * as Cesium from 'cesium'
import { ref, markRaw, shallowRef } from 'vue'

export function useLocalWeather(viewerRef) {
  const isSettingLocation = ref(false) // 是否正在激活“点击设置天气”
  const currentRainZone = ref(null)
  const currentWeatherEntity = shallowRef(null) // 当前存在的天气区域标识（圆柱）
  const currentRainSystem = shallowRef(null) // 当前存在的粒子系统
  const rainColor = ref(Cesium.Color.LIGHTCYAN.withAlpha(0.5)) // 雨滴颜色

  const RAIN_RADIUS = 300.0 // 雨区半径 (米)
  const RAIN_HEIGHT = 200.0 // 雨区高度 (米)

  // 1. 核心：创建粒子系统 (雨滴)
  const _createRainParticleSystem = (centerDegrees, radius, height) => {
    // 雨滴图片 (使用 Cesium 自带的圆点图片)
    const particleImage = Cesium.buildModuleUrl('Assets/Textures/circular_particle.png');
    
    // 随机雨滴发射器的起始位置 (圆柱体内随机)
    const rainEmitter = new Cesium.CylinderEmitter({
        radius: radius,
        height: height,
        innerRadius: radius * 0.1
    });

    const rainParticleSystem = new Cesium.ParticleSystem({
        image: particleImage,
        color: rainColor.value,
        startScale: 1.0,
        endScale: 0.5,
        particleLife: 1.5, // 粒子生命周期 (秒)
        speed: 80.0, // 雨滴下落速度 (米/秒)
        emissionRate: 2000, // 每秒发射粒子数 (越多越密)
        loop: true,
        imageSize: new Cesium.Cartesian2(4, 4), // 雨滴大小
        bursts: [],
        lifeTime: 16.0, // 系统生命周期
        emitter: rainEmitter,
        modelMatrix: Cesium.Matrix4.IDENTITY, // 初始位置
    });

    // 动态调整粒子的矩阵 (使其始终垂直向地心下落)
    const gravityScratch = new Cesium.Cartesian3();
    rainParticleSystem.updateCallback = (particle, dt) => {
        // 定义下落速度
        const fallSpeed = 80.0; 
        // 计算向下的重力向量
        Cesium.Cartesian3.normalize(particle.position, gravityScratch);
        Cesium.Cartesian3.multiplyByScalar(gravityScratch, -fallSpeed * dt, gravityScratch);
        // 更新粒子位置
        particle.position = Cesium.Cartesian3.add(particle.position, gravityScratch, particle.position);
    }
    
    return rainParticleSystem
  }

  // 2. 🌟 激活“天气炸弹”模式：点击地图任何位置
  const activateWeatherSetter = () => {
    isSettingLocation.value = true;
    const viewer = viewerRef.value;
    if (!viewer) return;
    
    // 改变鼠标样式
    viewer._element.style.cursor = 'crosshair';

    const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
    handler.setInputAction((click) => {
      // 获取点击位置的笛卡尔坐标
      const cartesian = viewer.camera.pickEllipsoid(click.position, viewer.scene.globe.ellipsoid);
      if (cartesian) {
        setLocalRain(cartesian);
        
        // 点击后取消模式
        viewer._element.style.cursor = 'default';
        isSettingLocation.value = false;
        handler.destroy(); // 销毁监听器
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  }

  // 3. 核心：在特定笛卡尔坐标设置降雨
  const setLocalRain = (cartesian) => {
    const viewer = viewerRef.value;
    if (!viewer) return;

    // 清除旧天气
    clearWeather();

    // 将笛卡尔坐标转换为经纬度 (用于生成乌云)
    const cartographic = Cesium.Cartographic.fromCartesian(cartesian);
    const lng = Cesium.Math.toDegrees(cartographic.longitude);
    const lat = Cesium.Math.toDegrees(cartographic.latitude);

    const centerDegrees = [lng, lat];
    currentRainZone.value = { lng, lat }
    
    // 1. 创建乌云的实体 (用半透明的黑灰色圆柱体模拟乌云阴影)
    currentWeatherEntity.value = viewer.entities.add({
      name: `局部降雨区 [${lng.toFixed(3)}, ${lat.toFixed(3)}]`,
      position: cartesian,
      cylinder: {
        length: RAIN_HEIGHT * 2,
        topRadius: RAIN_RADIUS,
        bottomRadius: RAIN_RADIUS,
        // 🌟 使用纯色半透明材质，作为科幻风的天气禁飞区背景
        material: Cesium.Color.fromCssColorString('#00d2ff').withAlpha(0.1),
        outline: true,
        outlineColor: Cesium.Color.fromCssColorString('#00d2ff').withAlpha(0.8), // 亮蓝色边框
        outlineWidth: 2,
      },
      // 🌟 新增：在天上加一朵“乌云” Primitive (黑灰色半透明椭圆)
      ellipse: {
          semiMinorAxis: RAIN_RADIUS * 1.2,
          semiMajorAxis: RAIN_RADIUS * 1.2,
          height: RAIN_HEIGHT + 20, // 稍微飘在粒子系统上面
          material: new Cesium.Color.fromCssColorString('#1a1a1a').withAlpha(0.8), // 黑灰色乌云
          stitch: true,
      }
    });

    // 2. 创建并添加粒子系统
    currentRainSystem.value = _createRainParticleSystem(centerDegrees, RAIN_RADIUS, RAIN_HEIGHT);
    viewer.scene.primitives.add(currentRainSystem.value);

    // 3. 🌟 核心：计算粒子系统的位置矩阵 (使其位于点击点)
    const modelMatrix = Cesium.Transforms.eastNorthUpToFixedFrame(cartesian);
    currentRainSystem.value.modelMatrix = modelMatrix;

    // 4. 让相机飞过去看一眼
    viewer.flyTo(currentWeatherEntity.value, {
      duration: 1.5,
      offset: new Cesium.HeadingPitchRange(
        Cesium.Math.toRadians(30), 
        Cesium.Math.toRadians(-20), 
        RAIN_RADIUS * 6
      )
    });
  }

  // 4. 清除天气
  const clearWeather = () => {
    const viewer = viewerRef.value;
    if (!viewer) return;

    currentRainZone.value = null

    if (currentWeatherEntity.value) {
      viewer.entities.remove(currentWeatherEntity.value);
      currentWeatherEntity.value = null;
    }
    if (currentRainSystem.value) {
      viewer.scene.primitives.remove(currentRainSystem.value);
      currentRainSystem.value = null;
    }
  }

  return {
    isSettingLocation,
    currentRainZone, // 🌟 导出来
    activateWeatherSetter,
    setLocalRain,
    clearWeather
  }
}