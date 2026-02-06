import * as Cesium from 'cesium'

export class WeatherSystem {
  constructor(viewer) {
    this.viewer = viewer
    this.rainStage = null
    this.snowStage = null
    this.fogStage = null
  }

  // ================= ☀️ 晴天 =================
  setSunny() {
    this._removeStages()
    this.viewer.scene.fog.density = 0.0002 // 恢复默认薄雾
    this.viewer.scene.skyAtmosphere.hueShift = 0.0
    this.viewer.scene.skyAtmosphere.saturationShift = 0.0
    this.viewer.scene.globe.enableLighting = true
    console.log('☀️ 天气切换：晴天')
  }

  // ================= 🌧️ 下雨 (物理 shader 实现) =================
  setRain() {
    this._removeStages()

    // 1. 调整天空氛围 (变蓝、变暗)
    this.viewer.scene.skyAtmosphere.hueShift = -0.8
    this.viewer.scene.skyAtmosphere.saturationShift = -0.7
    this.viewer.scene.fog.density = 0.001 // 增加雾气模拟雨中朦胧感

    // 2. 加载下雨着色器
    const fsRain = `
      uniform sampler2D colorTexture;
      in vec2 v_textureCoordinates;
      uniform float tiltAngle;
      uniform float rainSize;
      uniform float rainSpeed;
      
      float hash(float x) { return fract(sin(x * 133.3) * 13.13); }
      
      void main(void) {
        float time = czm_frameNumber / 60.0;
        vec2 resolution = czm_viewport.zw;
        vec2 uv = (gl_FragCoord.xy * 2.0 - resolution.xy) / min(resolution.x, resolution.y);
        vec3 c = vec3(0.6, 0.7, 0.8);
        float a = tiltAngle;
        float si = sin(a), co = cos(a);
        uv *= mat2(co, -si, si, co);
        uv *= length(uv + vec2(0, 4.9)) * rainSize + 1.0;
        float v = 1.0 - sin(hash(floor(uv.x * 100.0)) * 2.0);
        float b = clamp(abs(sin(20.0 * time * v + uv.y * (5.0 / (2.0 + v)))) - 0.95, 0.0, 1.0) * 20.0;
        c *= v * b;
        out_FragColor = mix(texture(colorTexture, v_textureCoordinates), vec4(c, 1), 0.3);
      }
    `

    this.rainStage = new Cesium.PostProcessStage({
      name: 'czm_rain',
      fragmentShader: fsRain,
      uniforms: {
        tiltAngle: 0.6, // 雨滴倾斜角度
        rainSize: 0.6, // 雨滴大小
        rainSpeed: 120.0,
      },
    })

    this.viewer.scene.postProcessStages.add(this.rainStage)
    console.log('🌧️ 天气切换：大雨')
  }

  // ================= ❄️ 下雪 =================
  setSnow() {
    this._removeStages()

    // 1. 调整天空 (变白、雾气变浓)
    this.viewer.scene.skyAtmosphere.hueShift = -0.1
    this.viewer.scene.skyAtmosphere.saturationShift = -0.3
    this.viewer.scene.fog.density = 0.003

    // 2. 加载下雪着色器
    const fsSnow = `
      uniform sampler2D colorTexture;
      in vec2 v_textureCoordinates;
      uniform float snowSpeed;
      
      float snow(vec2 uv, float scale) {
        float time = czm_frameNumber / 60.0;
        float w = smoothstep(1.0, 0.0, -uv.y * (scale/10.0));
        if (w < 0.1) return 0.0;
        uv += time / scale;
        uv.y += time * 2.0 / scale;
        uv.x += sin(uv.y + time * 0.5) / scale;
        uv *= scale;
        vec2 s = floor(uv), f = fract(uv), p;
        float k = 3.0, d = 0.0, t;
        p = vec2(0.5) + vec2(sin(time * 0.5) * 0.5, 0.0); // 简单风力
        d = length(f - p);
        k = min(d, k);
        // 重要提醒：第一个参数必须是float，否则 WebGL 会报 smoothstep 重载匹配错误
        k = smoothstep(0.0, k, sin(f.x + f.y) * 0.01);
        return k * w;
      }

      void main(void) {
        vec2 resolution = czm_viewport.zw;
        vec2 uv = (gl_FragCoord.xy * 2.0 - resolution.xy) / min(resolution.x, resolution.y);
        vec3 finalColor = vec3(0);
        float c = 0.0;
        c += snow(uv, 30.0) * 0.0;
        c += snow(uv, 20.0) * 0.4;
        c += snow(uv, 15.0) * 0.3;
        c += snow(uv, 10.0) * 0.2;
        c += snow(uv, 5.0) * 0.1;
        vec4 baseColor = texture(colorTexture, v_textureCoordinates);
        out_FragColor = mix(baseColor, vec4(1, 1, 1, 1), c); // 混合白色雪花
      }
    `

    this.snowStage = new Cesium.PostProcessStage({
      name: 'czm_snow',
      fragmentShader: fsSnow,
      uniforms: {
        snowSpeed: 1.0,
      },
    })

    this.viewer.scene.postProcessStages.add(this.snowStage)
    console.log('❄️ 天气切换：大雪')
  }

  // ================= 🌫️ 大雾 =================
  setFog() {
    this._removeStages()

    // Cesium 自带雾效，直接调参数即可
    this.viewer.scene.fog.enabled = true
    this.viewer.scene.fog.density = 0.005 // 高密度雾，伸手不见五指
    this.viewer.scene.fog.screenSpaceErrorFactor = 2.0

    // 把大气层变得灰蒙蒙
    this.viewer.scene.skyAtmosphere.hueShift = -0.1
    this.viewer.scene.skyAtmosphere.saturationShift = -1.0 // 去色
    this.viewer.scene.skyAtmosphere.brightnessShift = -0.2

    console.log('🌫️ 天气切换：大雾')
  }

  // 私有方法：清理所有后期特效
  _removeStages() {
    if (this.rainStage) {
      this.viewer.scene.postProcessStages.remove(this.rainStage)
      this.rainStage = null
    }
    if (this.snowStage) {
      this.viewer.scene.postProcessStages.remove(this.snowStage)
      this.snowStage = null
    }
    // 重置雾和大气
    this.viewer.scene.fog.density = 0.0002
    this.viewer.scene.skyAtmosphere.hueShift = 0.0
    this.viewer.scene.skyAtmosphere.saturationShift = 0.0
    this.viewer.scene.skyAtmosphere.brightnessShift = 0.0
  }
}