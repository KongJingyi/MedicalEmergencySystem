// src/classes/Drone.js
import * as Cesium from 'cesium'
import { VEHICLE_TYPES } from '../config/VehicleConfig' // 引入配置

export class Drone {
  /**
   * 构造函数：�? new 一次，就诞生一架新飞机
   * @param {Cesium.Viewer} viewer - 地图对象
   * @param {String} id - 唯一编号 (�? "drone-001")
   */
  constructor(viewer, id) {
    this.viewer = viewer;
    this.id = id;
    this.entity = null; // 它是 Cesium 的实�?
    this.status = 'IDLE'; // IDLE, FLYING, ARRIVED
    this.onArrivedCallback = null; // 到达后的回调
    this._onStopListener = null; // 保存监听器引用，方便清理
    this.typeConfig = null; // 存储当前是哪种载�?
  }

  /**
   * 核心方法：执行飞行任�?
   * @param {Object} routeData - 包含起点、终点、拐点的路径数据
   * @param {String} type - 载具类型 ('DRONE' �? 'AMBULANCE')
   */
  flyTo(routeData, type = 'DRONE') {
    this.status = 'FLYING';
    
    // 1. 读取配置
    this.typeConfig = VEHICLE_TYPES[type] || VEHICLE_TYPES.DRONE;

    // 2. 计算路径 (传入配置的高�?)
    const { start, stop, waypoints } = this._calculatePath(routeData, this.typeConfig.flyHeight);

    // 3. 【核心算法】计算修正后的朝�?
    const orientationProperty = this._getCorrectedOrientation(waypoints, this.typeConfig.fixHeading);

    // 4. 创建实体
    this.entity = this.viewer.entities.add({
      id: this.id, // 给实体绑�? ID
      availability: new Cesium.TimeIntervalCollection([new Cesium.TimeInterval({ start: start, stop: stop })]),
      position: waypoints,
      // 使用修正后的朝向
      orientation: orientationProperty,
      
      // 模型配置（从配置读取�?
      model: {
        uri: this.typeConfig.modelUri,
        minimumPixelSize: this.typeConfig.minimumPixelSize,
        scale: this.typeConfig.scale,
        runAnimations: true,
      },
      
      // 路径线（从配置读取颜色）
      path: {
        resolution: 1,
        material: new Cesium.PolylineGlowMaterialProperty({
          glowPower: 0.2,
          color: this.typeConfig.pathColor
        }),
        width: 6
      }
    });

    // 5. 监听是否到达 (私有方法)
    this._listenArrival(stop);
  }

  /**
   * 销毁自�? (从地图上移除)
   */
  remove() {
    if (this.entity) {
      this.viewer.entities.remove(this.entity);
      this.entity = null;
    }
    // 移除监听�?
    if (this._onStopListener) {
      this.viewer.clock.onStop.removeEventListener(this._onStopListener);
      this._onStopListener = null;
    }
    this.status = 'IDLE';
  }

  // ================= 私有辅助方法 =================

  // 内部计算路径 (支持动态高�?)
  _calculatePath(routeData, height) {
    const start = Cesium.JulianDate.now();
    const duration = 40; // 飞行40�?
    const stop = Cesium.JulianDate.addSeconds(start, duration, new Cesium.JulianDate());
    
    // 设置地图时钟 (注意：多机协同如果强行改全局时钟可能会有冲突�?
    // 完美方案是后端计算好绝对时间，Day 3-4 我们先假设以第一架飞机的时间为准)
    if (!this.viewer.clock.shouldAnimate) {
        this.viewer.clock.startTime = start.clone();
        this.viewer.clock.stopTime = stop.clone();
        this.viewer.clock.currentTime = start.clone();
        this.viewer.clock.clockRange = Cesium.ClockRange.CLAMPED;
        this.viewer.clock.shouldAnimate = true;
    }

    const property = new Cesium.SampledPositionProperty();
    
    // 使用传入�? height 参数
    property.addSample(start, Cesium.Cartesian3.fromDegrees(routeData.START.lng, routeData.START.lat, height));
    property.addSample(
      Cesium.JulianDate.addSeconds(start, 10, new Cesium.JulianDate()), 
      Cesium.Cartesian3.fromDegrees(116.360, 39.938, height)
    );
    property.addSample(
      Cesium.JulianDate.addSeconds(start, 25, new Cesium.JulianDate()), 
      Cesium.Cartesian3.fromDegrees(116.368, 39.942, height)
    );
    property.addSample(stop, Cesium.Cartesian3.fromDegrees(routeData.END.lng, routeData.END.lat, height));

    return { start, stop, waypoints: property };
  }

  // ?���ռ��޸��桿��̬�����㷨 ?
  _getCorrectedOrientation(positionProperty, fixHeadingDegrees) {
    const velocityOrientation = new Cesium.VelocityOrientationProperty(positionProperty);
    
    // 1. Ԥ������ȷ�� fixHeadingDegrees �Ǹ���Ч�����֣����û������0��ֱ�ӷ���ԭ������
    const degrees = Number(fixHeadingDegrees);
    if (Number.isNaN(degrees) || degrees === 0) {
      return velocityOrientation;
    }

    // 2. 预计算修正四元数
    let correctionQuat = Cesium.Quaternion.IDENTITY;
    try {
      correctionQuat = Cesium.Quaternion.fromHeadingPitchRoll(
        new Cesium.HeadingPitchRoll(Cesium.Math.toRadians(degrees), 0, 0)
      );
    } catch (e) {
      console.warn("修正四元数计算失败，使用默认值");
    }

    // 3. 返回回调
    return new Cesium.CallbackProperty((time, result) => {
      // 安全获取原生朝向
      const originalQuat = velocityOrientation.getValue(time);

      // 🚨【绝对防御】�?
      // 只要 originalQuat 不是一个有效的对象，立刻返回默认值（不旋转）
      // 不要�? undefined 进入 multiply 计算�?
      if (!originalQuat) {
        return Cesium.Quaternion.clone(Cesium.Quaternion.IDENTITY, result);
      }

      // 只有�? originalQuat �? correctionQuat 都是对象时，才进行乘�?
      if (!result) {
        result = new Cesium.Quaternion();
      }
      return Cesium.Quaternion.multiply(originalQuat, correctionQuat, result);
    }, false);
  }

  // 内部监听�?
  _listenArrival(stopTime) {
    this._onStopListener = () => {
      // 只有当时间匹配且自己还没到达�?
      if (this.viewer.clock.currentTime.equals(this.viewer.clock.stopTime) && this.status === 'FLYING') {
        this.status = 'ARRIVED';
        console.log(`Drone ${this.id} 已送达`);
        
        // 执行回调 (通知 UI 更新)
        if (this.onArrivedCallback) {
          this.onArrivedCallback(this.id);
        }
        
        // 移除监听器，避免重复触发
        if (this._onStopListener) {
          this.viewer.clock.onStop.removeEventListener(this._onStopListener);
          this._onStopListener = null;
        }
      }
    };
    this.viewer.clock.onStop.addEventListener(this._onStopListener);
  }
}
