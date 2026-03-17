#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
决策日记与月度复盘模块
"""

import json
import os
from datetime import datetime

DECISION_DIARY_PATH = 'data/decision_diary.json'


def save_daily_snapshot(holdings_data, total_market_value, total_pnl, total_pnl_pct):
    """
    保存每日决策日记快照
    
    参数：
    - holdings_data: 持仓数据
    - total_market_value: 总市值
    - total_pnl: 总盈亏
    - total_pnl_pct: 总盈亏率
    """
    diary = load_diary()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 检查今天是否已保存
    if any(entry['date'] == today for entry in diary):
        print(f"📝 {today} 的快照已存在，跳过保存")
        return
    
    # 创建快照
    snapshot = {
        'date': today,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_market_value': total_market_value,
        'total_pnl': total_pnl,
        'total_pnl_pct': total_pnl_pct,
        'holdings': []
    }
    
    # 保存每只股票的快照
    for stock in holdings_data.get('stocks', []):
        snapshot['holdings'].append({
            'code': stock['code'],
            'name': stock['name'],
            'shares': stock['shares'],
            'cost': stock['cost'],
            'stop_profit': stock.get('stop_profit'),
            'stop_loss': stock.get('stop_loss'),
            'buy_reason': stock.get('buy_reason', '')
        })
    
    diary.append(snapshot)
    
    # 只保留最近 90 天
    if len(diary) > 90:
        diary = diary[-90:]
    
    # 保存
    os.makedirs(os.path.dirname(DECISION_DIARY_PATH), exist_ok=True)
    with open(DECISION_DIARY_PATH, 'w') as f:
        json.dump(diary, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 已保存 {today} 的决策日记快照")


def load_diary():
    """加载决策日记"""
    if not os.path.exists(DECISION_DIARY_PATH):
        return []
    
    try:
        with open(DECISION_DIARY_PATH, 'r') as f:
            return json.load(f)
    except:
        return []


def generate_monthly_report(diary, days=30):
    """
    生成月度复盘报告
    
    参数：
    - diary: 决策日记数据
    - days: 最近多少天
    
    返回：
    {
        'period': '时间段',
        'summary': '总体表现',
        'best_stock': '最成功持仓',
        'worst_stock': '最失败持仓',
        'trading_habits': '交易习惯特征',
        'suggestions': '下月建议'
    }
    """
    recent_entries = diary[-days:]
    
    if not recent_entries:
        return None
    
    # 计算月度表现
    start_value = recent_entries[0]['total_market_value']
    end_value = recent_entries[-1]['total_market_value']
    month_pnl = end_value - start_value
    month_pnl_pct = (month_pnl / start_value * 100) if start_value > 0 else 0
    
    # 找出最成功和最失败的持仓（简化版）
    all_holdings = {}
    for entry in recent_entries:
        for stock in entry['holdings']:
            name = stock['name']
            if name not in all_holdings:
                all_holdings[name] = []
            all_holdings[name].append(stock)
    
    # 简单分析：持仓次数最多的股票
    most_held = max(all_holdings.items(), key=lambda x: len(x[1]))[0] if all_holdings else '无'
    
    report = {
        'period': f"最近{days}天",
        'start_date': recent_entries[0]['date'],
        'end_date': recent_entries[-1]['date'],
        'start_value': start_value,
        'end_value': end_value,
        'month_pnl': month_pnl,
        'month_pnl_pct': month_pnl_pct,
        'total_days': len(recent_entries),
        'most_held_stock': most_held,
        'avg_market_value': sum(e['total_market_value'] for e in recent_entries) / len(recent_entries)
    }
    
    return report


def ai_generate_monthly_report(report_data):
    """
    调用 AI 生成个性化月报
    
    参数：
    - report_data: 月度报告基础数据
    
    返回：
    AI 生成的月报内容（Markdown 格式）
    """
    import os
    
    AI_API_KEY = os.getenv('AI_API_KEY', '')
    AI_MODEL = os.getenv('AI_MODEL', 'qwen-plus')
    AI_API_URL = os.getenv('AI_API_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions')
    
    if not AI_API_KEY:
        # 降级方案：返回基础报告
        return f"""## 📊 月度复盘报告

**时间段：** {report_data['period']}（{report_data['start_date']} ~ {report_data['end_date']}）

### 总体表现
- 起始市值：¥{report_data['start_value']:,.0f}
- 期末市值：¥{report_data['end_value']:,.0f}
- 月度盈亏：¥{report_data['month_pnl']:+,.0f} ({report_data['month_pnl_pct']:+.2f}%)
- 交易天数：{report_data['total_days']}天

### 持仓分析
- 持仓最久股票：{report_data['most_held_stock']}
- 平均市值：¥{report_data['avg_market_value']:,.0f}

### 建议
- 继续保持良好的交易习惯
- 注意风险控制，设置止盈止损
- 下月关注市场热点板块

*注：配置 AI_API_KEY 后可获得更详细的 AI 个性化分析*"""
    
    try:
        import requests
        
        prompt = f"""你是一位专业的投资顾问，请根据用户的交易数据生成一份个性化的月度复盘报告。

【月度数据】
时间段：{report_data['period']}
起始市值：¥{report_data['start_value']:,.0f}
期末市值：¥{report_data['end_value']:,.0f}
月度盈亏：¥{report_data['month_pnl']:+,.0f} ({report_data['month_pnl_pct']:+.2f}%)
交易天数：{report_data['total_days']}天
持仓最久股票：{report_data['most_held_stock']}
平均市值：¥{report_data['avg_market_value']:,.0f}

请生成一份月度复盘报告，包含：
1. 本月盈亏来源分析
2. 最成功和最失败的持仓分析
3. 用户交易习惯特征总结
4. 下月建议关注点

请用 Markdown 格式返回，包含表情符号和清晰的标题结构。"""
        
        headers = {'Authorization': f'Bearer {AI_API_KEY}', 'Content-Type': 'application/json'}
        payload = {
            'model': AI_MODEL,
            'messages': [
                {'role': 'system', 'content': '你是一位专业的投资顾问，擅长生成个性化的投资复盘报告。'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.5,
            'max_tokens': 1500
        }
        
        response = requests.post(AI_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        return result['choices'][0]['message']['content'].strip()
        
    except Exception as e:
        return f"""## 📊 月度复盘报告

**时间段：** {report_data['period']}

**生成失败：** {str(e)}

请检查 AI API 配置或网络连接。"""
