import * as Cesium from 'cesium'

export const VEHICLE_TYPES = {
  // 1. 无人机配置
  DRONE: {
    modelUri: '/models/drone.glb',
    scale: 1.0,         // 如果模型太小，这里改大，比如 10.0
    minimumPixelSize: 64,
    fixHeading: 0,      // 修正角度：如果模型歪了90度，这里填 90
    pathColor: Cesium.Color.ORANGERED,
    flyHeight: 150      // 飞行高度
  },
  
  // 2. 救护车配置
  AMBULANCE: {
    modelUri: '/models/drone.glb', // 暂时用 drone.glb 代替，等有 ambulance.glb 再改
    scale: 20.0,        // 汽车模型通常比飞机模型小，可能需要放大
    minimumPixelSize: 64,
    fixHeading: 90,     // 假设下载的车头是朝向 +X 的，可能需要转 90 度
    pathColor: Cesium.Color.YELLOW,
    flyHeight: 50       // 贴地（但略高于地形，避免钻地）
  }
}
