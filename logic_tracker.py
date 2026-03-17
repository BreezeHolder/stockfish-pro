#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
买入逻辑追踪模块
"""

import os

AI_API_KEY = os.getenv('AI_API_KEY', '')
AI_MODEL = os.getenv('AI_MODEL', 'qwen-plus')
AI_API_URL = os.getenv('AI_API_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions')


def analyze_buying_logic(stock_name, buy_reason, current_pnl_pct, current_price, cost_price):
    """
    分析买入逻辑是否成立
    
    返回：
    {
        'status': '逻辑成立 | 逻辑动摇 | 逻辑已失效',
        'reason': '判断依据（一句话）'
    }
    """
    if not AI_API_KEY or not buy_reason:
        # 降级方案：基于规则判断
        if current_pnl_pct > 0:
            return {'status': '逻辑成立', 'reason': '当前盈利，走势符合预期'}
        elif current_pnl_pct > -10:
            return {'status': '逻辑动摇', 'reason': '小幅亏损，需观察后续走势'}
        else:
            return {'status': '逻辑已失效', 'reason': '亏损超过 10%，建议重新评估'}
    
    try:
        import requests
        
        prompt = f"""你是一位专业的投资顾问，请分析用户的买入逻辑是否仍然成立。

【股票名称】{stock_name}
【买入理由】{buy_reason}
【当前价格】{current_price}元
【成本价】{cost_price}元
【当前盈亏率】{current_pnl_pct:.1f}%

请判断买入逻辑是否成立，返回：
1. 状态：逻辑成立 / 逻辑动摇 / 逻辑已失效
2. 一句话判断依据

只返回 JSON 格式：
{{
    "status": "逻辑成立 | 逻辑动摇 | 逻辑已失效",
    "reason": "判断依据"
}}"""
        
        headers = {'Authorization': f'Bearer {AI_API_KEY}', 'Content-Type': 'application/json'}
        payload = {
            'model': AI_MODEL,
            'messages': [
                {'role': 'system', 'content': '你是一位专业的投资顾问，擅长分析买入逻辑和市场走势。'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.3,
            'max_tokens': 200
        }
        
        response = requests.post(AI_API_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        result = response.json()
        
        import json
        ai_content = result['choices'][0]['message']['content'].strip()
        if ai_content.startswith('```json'):
            ai_content = ai_content[7:]
        if ai_content.endswith('```'):
            ai_content = ai_content[:-3]
        
        return json.loads(ai_content.strip())
        
    except Exception as e:
        return {'status': '逻辑动摇', 'reason': f'AI 分析失败：{str(e)[:50]}'}
