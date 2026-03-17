#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风险自动检测模块
基于规则的风险检测（不依赖 AI）
"""

from datetime import datetime


def detect_risks(df, total_value):
    """
    基于规则的风险检测
    
    参数：
    - df: 持仓 DataFrame
    - total_value: 总市值
    
    返回：
    {
        'risk_level': '高风险 | 中风险 | 低风险',
        'risk_reason': '一句话原因（含数字）',
        'issues': [
            {
                'level': '高 | 中 | 低',
                'type': '集中度 | 止损 | 行业',
                'desc': '问题描述（含股票名和数字）',
                'action': '操作建议'
            }
        ]
    }
    """
    risks = []
    
    if df.empty or total_value <= 0:
        return {
            'risk_level': '低风险',
            'risk_reason': '持仓数据为空或无效',
            'issues': []
        }
    
    # ========== 规则 1：单只股票占比过高（>40%） ==========
    for _, row in df.iterrows():
        ratio = row['持仓市值'] / total_value
        if ratio > 0.4:
            risks.append({
                'level': '高',
                'type': '集中度',
                'desc': f"{row['名称']}占比{ratio*100:.1f}%，超过 40% 警戒线",
                'action': f"建议减持至 30% 以下（当前{row['持仓市值']:,.0f}元）",
                'stock': row['名称']
            })
        elif ratio > 0.25:
            risks.append({
                'level': '中',
                'type': '集中度',
                'desc': f"{row['名称']}占比{ratio*100:.1f}%，超过 25% 警戒线",
                'action': f"建议关注，避免继续加仓（当前{row['持仓市值']:,.0f}元）",
                'stock': row['名称']
            })
    
    # ========== 规则 2：行业过于集中（>60%） ==========
    if '行业' in df.columns:
        sector_concentration = df.groupby('行业')['持仓市值'].sum()
        for sector, value in sector_concentration.items():
            ratio = value / total_value
            if ratio > 0.6:
                risks.append({
                    'level': '高',
                    'type': '行业',
                    'desc': f"{sector}行业占比{ratio*100:.1f}%，行业集中度过高",
                    'action': f"建议分散到其他行业（当前{value:,.0f}元）",
                    'stock': sector
                })
    
    # ========== 规则 3：单只跌幅过大（<-20%） ==========
    for _, row in df.iterrows():
        pnl_pct = row.get('盈亏率', 0)
        # 注意：盈亏率字段是百分比形式（如 -9.55），不是小数（如 -0.0955）
        if pnl_pct < -30:
            risks.append({
                'level': '高',
                'type': '止损',
                'desc': f"{row['名称']}亏损{abs(pnl_pct):.1f}%，深度套牢",
                'action': "建议评估是否执行止损（30% 止损线）或补仓摊薄",
                'stock': row['名称']
            })
        elif pnl_pct < -20:
            risks.append({
                'level': '中',
                'type': '止损',
                'desc': f"{row['名称']}亏损{abs(pnl_pct):.1f}%",
                'action': "建议设置止损位，避免继续下跌",
                'stock': row['名称']
            })
    
    # ========== 规则 4：单日大亏（>-5%） ==========
    total_today_pnl = df.get('今日盈亏', 0).sum() if '今日盈亏' in df.columns else 0
    today_pnl_pct = total_today_pnl / total_value if total_value > 0 else 0
    
    if today_pnl_pct < -0.05:
        risks.append({
            'level': '高',
            'type': '单日',
            'desc': f"单日亏损{today_pnl_pct*100:.2f}%，亏损{total_today_pnl:,.0f}元",
            'action': "建议检查持仓，评估是否需要调仓",
            'stock': '全部持仓'
        })
    
    # ========== 确定整体风险等级 ==========
    if any(r['level'] == '高' for r in risks):
        risk_level = '高风险'
    elif any(r['level'] == '中' for r in risks):
        risk_level = '中风险'
    else:
        risk_level = '低风险'
    
    # ========== 生成风险原因 ==========
    if risks:
        # 取第一个高风险，或第一个中风险，或第一个低风险
        priority_risk = next((r for r in risks if r['level'] == '高'), risks[0])
        risk_reason = priority_risk['desc']
    else:
        risk_reason = '持仓分散合理，无明显风险'
    
    return {
        'risk_level': risk_level,
        'risk_reason': risk_reason,
        'issues': risks,
        'check_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


def should_send_alert(current_risks, last_risks):
    """
    判断是否应该发送告警（去重逻辑）
    
    返回：True/False
    """
    # 首次告警
    if not last_risks:
        return True
    
    # 风险等级变化
    if current_risks['risk_level'] != last_risks.get('risk_level'):
        return True
    
    # 新增高风险
    current_high = {r['desc'] for r in current_risks['issues'] if r['level'] == '高'}
    last_high = {r['desc'] for r in last_risks.get('issues', []) if r['level'] == '高'}
    
    if current_high - last_high:  # 有新的高风险
        return True
    
    return False


def get_alert_fingerprint(risk):
    """
    生成告警指纹（用于去重）
    """
    import hashlib
    content = f"{risk['risk_level']}:{risk['risk_reason']}"
    return hashlib.md5(content.encode()).hexdigest()[:8]
