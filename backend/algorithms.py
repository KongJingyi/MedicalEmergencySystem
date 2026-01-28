# backend/algorithms.py
import random

def calculate_medical_score(resource, route_type):
    """
    核心算法：根据【物资属性】计算【路径得分】
    resource: 数据库里查出来的那个 MedicalResource 对象
    route_type: 'DRONE'(无人机) 或 'AMBULANCE'(救护车)
    """
    
    score = 100 # 初始分
    logs = []   # 决策日志 (用来给评委看“算法是怎么思考的”)
    
    # 1. 温度检查
    # 假设无人机没有超低温冷柜，只有普通保温箱
    if resource.max_temp < -20 and route_type == 'DRONE':
        score -= 50
        logs.append(f"❌ 警告：无人机缺乏超低温设备，无法满足 {resource.name} 的温控需求")
    
    # 2. 震动检查
    # 假设无人机震动大(系数8)，救护车平稳(系数2)
    vehicle_shock = 8 if route_type == 'DRONE' else 2
    if vehicle_shock > resource.shock_sensitivity:
        penalty = (vehicle_shock - resource.shock_sensitivity) * 10
        score -= penalty
        logs.append(f"⚠️ 风险：运输震动({vehicle_shock}) 超过物资耐受度({resource.shock_sensitivity})，扣除 {penalty} 分")
    
    # 3. 时效性加分
    # 无人机快，救护车慢
    if resource.urgency_level >= 4 and route_type == 'DRONE':
        score += 20
        logs.append(f"✅ 优势：物资极度紧急(Lv{resource.urgency_level})，无人机时效性加分")
        
    return {"score": score, "logs": logs}