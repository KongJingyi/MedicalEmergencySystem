// src/classes/PolylineTrailLinkMaterialProperty.js
// 自定义“流光轨迹线”材质，用于替换普通 Polyline 实线，让路径看起来像有光子在流动

import * as Cesium from 'cesium'

// 1. 注册自定义材质类型
const MaterialType = 'PolylineTrailLink'

if (!Cesium.Material._materialCache.getMaterial(MaterialType)) {
  Cesium.Material.PolylineTrailLinkType = MaterialType

  Cesium.Material.PolylineTrailLinkSource = `
    czm_material czm_getMaterial(czm_materialInput materialInput)
    {
        czm_material material = czm_getDefaultMaterial(materialInput);

        // 线段上的纹理坐标 (s: 沿线方向, t: 垂直线方向)
        float s = materialInput.st.s;

        // 时间推进
        float time = fract(czm_frameNumber * speed);

        // 生成一个 0~1 的流动条纹
        // 让高亮区域在 s 方向循环移动
        float alpha = smoothstep(0.0, 0.2, fract(s - time)) *
                      (1.0 - smoothstep(0.6, 0.8, fract(s - time)));

        // 增加一点渐隐边缘
        alpha *= gradient;

        vec4 baseColor = vec4(color.rgb, color.a * alpha);
        material.diffuse = baseColor.rgb;
        material.alpha = baseColor.a;
        return material;
    }
  `

  Cesium.Material._materialCache.addMaterial(MaterialType, {
    fabric: {
      type: MaterialType,
      uniforms: {
        color: new Cesium.Color(0.0, 1.0, 1.0, 1.0),
        speed: 0.02,   // 数值越大，流光移动越快
        gradient: 1.0, // 渐隐系数
      },
      source: Cesium.Material.PolylineTrailLinkSource,
    },
    translucent: () => true,
  })
}

// 2. 封装成 Property，支持随时间更新（这里 uniforms 固定不随时间变化）
export class PolylineTrailLinkMaterialProperty {
  constructor(color, speed = 0.02, gradient = 1.0) {
    this._definitionChanged = new Cesium.Event()
    this.color = color || Cesium.Color.CYAN
    this.speed = speed
    this.gradient = gradient
  }

  get isConstant() {
    return false
  }

  get definitionChanged() {
    return this._definitionChanged
  }

  getType(time) {
    return MaterialType
  }

  getValue(time, result) {
    if (!result) {
      result = {}
    }
    result.color = this.color
    result.speed = this.speed
    result.gradient = this.gradient
    return result
  }

  equals(other) {
    return (
      other instanceof PolylineTrailLinkMaterialProperty &&
      Cesium.Color.equals(this.color, other.color) &&
      this.speed === other.speed &&
      this.gradient === other.gradient
    )
  }
}

