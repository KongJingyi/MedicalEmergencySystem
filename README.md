MedicalEmergencySystem/
│
├── backend/                  # 【核心大脑】Python + FastAPI
│   ├── main.py               # 入口文件（在这里启动后端）
│   ├── database.py           # 数据库配置 (SQLite连接)
│   ├── models.py             # 【医疗灵魂】定义数据模型 (血浆、疫苗的属性)
│   ├── algorithms.py         # 【深度来源】路径规划算法 (A* 或 评分函数)
│   ├── requirements.txt      # 依赖包列表
│   └── data/                 # 预置数据文件夹
│       └── seed_data.json    # 初始的假数据 (用于一键导入数据库)
│
├── frontend/                 # 【演示大屏】Vue3 + Cesium
│   ├── src/
│   │   ├── api/              # 专门存放与后端通信的代码
│   │   │   └── index.js      # axios 请求封装
│   │   ├── components/       # 组件
│   │   │   ├── CesiumMap.vue # 地图组件
│   │   │   ├── Dashboard.vue # 仪表盘组件
│   │   │   └── Warning.vue   # 报警弹窗
│   │   └── App.vue
│   ├── package.json
│   └── vite.config.js
│
└── README.md                 # 写给评委看的：系统部署说明