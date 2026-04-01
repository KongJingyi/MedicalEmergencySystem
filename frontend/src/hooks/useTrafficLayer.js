import { ref, shallowRef } from 'vue'
import * as Cesium from 'cesium'
import axios from 'axios'

export function useTrafficLayer(viewerRef) {
  const isTrafficVisible = ref(false) // 交通图层开关状态
  const trafficDataSource = shallowRef(null) // 统一管理交通线的容器

  // 生成不同拥堵程度的颜色和发光特效
  const getTrafficMaterial = (congestionIndex) => {
    let color;
    if (congestionIndex > 7) {
      color = Cesium.Color.fromCssColorString('#ff4d4f') // 红色：拥堵
    } else if (congestionIndex > 4) {
      color = Cesium.Color.fromCssColorString('#faad14') // 黄色：缓慢
    } else {
      color = Cesium.Color.fromCssColorString('#00ffaa') // 绿色：畅通
    }

    // 使用霓虹发光材质，赛博朋克感拉满
    return new Cesium.PolylineGlowMaterialProperty({
      glowPower: 0.2,
      taperPower: 1.0,
      color: color
    })
  }

  // 获取路网数据并绘制
  const renderTrafficLines = async () => {
    const viewer = viewerRef.value
    if (!viewer) return

    // 1. 初始化 DataSource
    if (!trafficDataSource.value) {
      trafficDataSource.value = new Cesium.CustomDataSource('traffic-layer')
      viewer.dataSources.add(trafficDataSource.value)
    } else {
      trafficDataSource.value.entities.removeAll()
    }

    try {
      // 尝试从前端 public/data 或后端 API 获取你们的路网拓扑数据
      // 注意：请确保你的 public 目录下有这两个文件，或者换成你的真实后端接口
      const nodesRes = await axios.get('http://127.0.0.1:8000/api/road_nodes').catch(() => null)
      const graphRes = await axios.get('http://127.0.0.1:8000/api/road_graph').catch(() => null)

      let nodes = nodesRes?.data || []
      let edges = graphRes?.data?.edges || []

      // 🚨 如果后端没有返回足够多的真实路网数据，启动【密集路网生成引擎】！
      if (nodes.length < 10 || edges.length < 10) {
        console.warn("未获取到足够的真实路网，正在生成高密度虚拟交通网...")
        nodes = []
        edges = []

        // 设定北京二环核心区的经纬度边界
        const minLng = 116.3300, maxLng = 116.4500
        const minLat = 39.8800, maxLat = 39.9500

        // 生成一个 12 x 12 的密集路网矩阵（总共 144 个路口，几百条路）
        const rows = 12
        const cols = 12

        // 1. 生成所有路口节点 (加入微小的随机偏移，让路网看起来更像真实街道，而不是死板的棋盘)
        for (let r = 0; r < rows; r++) {
          for (let c = 0; c < cols; c++) {
            const jitterLng = (Math.random() - 0.5) * 0.004 // 经度随机偏移
            const jitterLat = (Math.random() - 0.5) * 0.004 // 纬度随机偏移

            nodes.push({
              lng: minLng + (c / (cols - 1)) * (maxLng - minLng) + jitterLng,
              lat: minLat + (r / (rows - 1)) * (maxLat - minLat) + jitterLat
            })
          }
        }

        // 2. 将相邻的路口连成线（横向与纵向连接，并加入随机对角线斜街）
        for (let r = 0; r < rows; r++) {
          for (let c = 0; c < cols; c++) {
            const currentIndex = r * cols + c

            // 向右连接
            if (c < cols - 1) edges.push({ from: currentIndex, to: currentIndex + 1 })
            // 向下连接
            if (r < rows - 1) edges.push({ from: currentIndex, to: currentIndex + cols })

            // 随机加入一些北京常见的“斜街”（增加真实感）
            if (c < cols - 1 && r < rows - 1 && Math.random() > 0.8) {
              edges.push({ from: currentIndex, to: currentIndex + cols + 1 })
            }
          }
        }
      }

      // 2. 遍历所有边（Edges），画线
      edges.forEach(edge => {
        const fromNode = nodes[edge.from]
        const toNode = nodes[edge.to]

        if (fromNode && toNode) {
          // 🎲 调整拥堵比例：让大部分路是绿色(畅通)，少部分黄色(缓慢)，极少数红色(拥堵)
          // 这样视觉层次感最好，不然全红就假了
          let congestionIndex = Math.random() * 10
          if (Math.random() > 0.3) congestionIndex = Math.random() * 4 // 70% 概率强行变绿

          trafficDataSource.value.entities.add({
            polyline: {
              positions: Cesium.Cartesian3.fromDegreesArray([
                fromNode.lng, fromNode.lat,
                toNode.lng, toNode.lat
              ]),
              width: 4, // 🌟 关键修改：线宽从 8 改成 4，线条更细腻，科技感更强
              material: getTrafficMaterial(congestionIndex),
              clampToGround: true, // 让线贴合地表或 3D Tiles 建筑
              zIndex: 1 // 确保在线在地图之上
            }
          })
        }
      })

    } catch (error) {
      console.error("渲染交通路况图层失败:", error)
    }
  }

  // 控制图层显示/隐藏的开关函数
  const toggleTrafficLayer = () => {
    const viewer = viewerRef.value
    if (!viewer) return

    isTrafficVisible.value = !isTrafficVisible.value

    if (isTrafficVisible.value) {
      renderTrafficLines()
      trafficDataSource.value.show = true
    } else {
      if (trafficDataSource.value) {
        trafficDataSource.value.show = false
      }
    }
  }

  return {
    isTrafficVisible,
    toggleTrafficLayer
  }
}
