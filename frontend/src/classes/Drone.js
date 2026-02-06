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
   * 核心方法：执行飞行任务
   * @param {Array<[number, number]>} pathPoints - 后端返回的路径数组 [[lng, lat], [lng, lat], ...]
   * @param {String} type - 载具类型 ('DRONE' 或 'AMBULANCE')
   */
  flyTo(pathPoints, type = 'DRONE') {
    this.status = 'FLYING'

    // 1. 读取配置
    this.typeConfig = VEHICLE_TYPES[type] || VEHICLE_TYPES.DRONE

    // 2. 调用新的路径计算方法，传入数组
    const { start, stop, waypoints } = this._calculatePath(
      pathPoints,
      this.typeConfig.flyHeight
    )

    // 3. 计算姿态（保持之前的防弹版代码不变）
    const orientationProperty = this._getCorrectedOrientation(
      waypoints,
      this.typeConfig.fixHeading
    )

    // 4. 创建实体
    this.entity = this.viewer.entities.add({
      id: this.id,
      availability: new Cesium.TimeIntervalCollection([
        new Cesium.TimeInterval({ start, stop }),
      ]),
      position: waypoints,
      orientation: orientationProperty,
      model: {
        uri: this.typeConfig.modelUri,
        minimumPixelSize: this.typeConfig.minimumPixelSize,
        scale: this.typeConfig.scale,
        runAnimations: true,
      },
      path: {
        resolution: 1,
        material: new Cesium.PolylineGlowMaterialProperty({
          glowPower: 0.2,
          color: this.typeConfig.pathColor,
        }),
        width: 6,
      },
    })

    // 5. 监听到达
    this._listenArrival(stop)
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

  /**
   * 根据坐标数组计算平滑轨迹
   */
  _calculatePath(pathPoints, height) {
    const start = Cesium.JulianDate.now()
    const property = new Cesium.SampledPositionProperty()

    // 设定速度 (米/秒)：高度高的认为是无人机（快），高度低的是救护车（慢）
    const speed = height > 10 ? 30 : 15

    let currentTime = start.clone()

    // 遍历每一个坐标点
    for (let i = 0; i < pathPoints.length; i++) {
      const pt = pathPoints[i] // [lng, lat]
      const position = Cesium.Cartesian3.fromDegrees(pt[0], pt[1], height)

      if (i === 0) {
        // 起点
        property.addSample(currentTime, position)
      } else {
        // 计算与上一个点的距离
        const prevPt = pathPoints[i - 1]
        const prevPos = Cesium.Cartesian3.fromDegrees(prevPt[0], prevPt[1], height)
        const distance = Cesium.Cartesian3.distance(prevPos, position)

        // 时间 = 距离 / 速度，防止距离为 0 导致时间停滞
        const duration = distance / speed > 0 ? distance / speed : 0.1

        // 累加时间
        currentTime = Cesium.JulianDate.addSeconds(
          currentTime,
          duration,
          new Cesium.JulianDate()
        )

        property.addSample(currentTime, position)
      }
    }

    // 最后一个点的时间就是结束时间
    const stop = currentTime.clone()

    // 如果只有一个点（异常情况），强行加 1 秒防止报错
    if (Cesium.JulianDate.equals(start, stop)) {
      Cesium.JulianDate.addSeconds(stop, 1, stop)
    }

    // 确保场景时钟覆盖本次任务的时间区间，否则实体不会显示/运动
    if (!this.viewer.clock.shouldAnimate) {
      this.viewer.clock.startTime = start.clone()
      this.viewer.clock.stopTime = stop.clone()
      this.viewer.clock.currentTime = start.clone()
      this.viewer.clock.clockRange = Cesium.ClockRange.CLAMPED
      this.viewer.clock.shouldAnimate = true
    }

    return { start, stop, waypoints: property }
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
