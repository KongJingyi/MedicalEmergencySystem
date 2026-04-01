import * as Cesium from 'cesium'

export function useTilesetManager(viewerRef) {

  // 加载 3D Tiles 城市/医院模型，并注入极限性能优化参数
  const loadOptimizedCityModel = async (urlOrAssetId, isLocal = false) => {
    const viewer = viewerRef.value
    if (!viewer) return null

    try {
      let tilesetUrl = urlOrAssetId;
      
      // 如果是用 Cesium ion 云端转换的，传入 AssetId
      if (!isLocal) {
        tilesetUrl = await Cesium.IonResource.fromAssetId(urlOrAssetId)
      }

      // 🌟 核心：3D Tiles 极限性能配置参数
      const tileset = await Cesium.Cesium3DTileset.fromUrl(tilesetUrl, {
        // 1. 动态 LOD 核心：屏幕空间误差。数值越大，越容易加载低精度模型，性能越好（默认 16，大城市建议改 32-64）
        maximumScreenSpaceError: 32, 
        
        // 2. 内存优化：最大内存使用量（MB），到达后会卸载视野外的模型
        maximumMemoryUsage: 1024,   

        // 3. 跳过中间层级优化：极大地加快镜头快速拉近时的加载速度
        skipLevelOfDetail: true,
        baseScreenSpaceError: 1024,
        skipScreenSpaceErrorFactor: 16,
        skipLevels: 1,
        immediatelyLoadDesiredLevelOfDetail: false,

        // 4. 剔除优化：不渲染相机背面和被遮挡的子节点
        loadSiblings: false,
        cullWithChildrenBounds: true,

        // 5. 动态降级：相机运动时自动降低渲染精度，停止时恢复（防掉帧神器）
        dynamicScreenSpaceError: true,
        dynamicScreenSpaceErrorDensity: 0.00278,
        dynamicScreenSpaceErrorFactor: 4.0,
        dynamicScreenSpaceErrorHeightFalloff: 0.25
      })

      viewer.scene.primitives.add(tileset)

      // 可选：加载完成后，镜头自动飞到模型位置
      viewer.zoomTo(tileset)

      return tileset
    } catch (error) {
      console.error(`加载 3D Tiles 模型失败: ${error}`)
    }
  }

  return {
    loadOptimizedCityModel
  }
}
