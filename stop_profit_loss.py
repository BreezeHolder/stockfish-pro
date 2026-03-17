#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
止盈止损检测模块
"""


def check_stop_profit_loss(df, holdings_data):
    """
    检查止盈止损触发情况
    
    返回：
    [
        {
            'stock_name': '股票名',
            'type': '止盈 | 止损',
            'current_pnl_pct': 当前盈亏率，
            'trigger_line': 触发线，
            'ignore_count': 忽略次数
        }
    ]
    """
    alerts = []
    
    stocks = holdings_data.get('stocks', [])
    
    for _, row in df.iterrows():
        stock_name = row['名称']
        current_pnl_pct = row.get('盈亏率', 0)
        
        # 查找对应持仓配置
        stock_config = next((s for s in stocks if s['code'] == row['代码']), None)
        if not stock_config:
            continue
        
        stop_profit = stock_config.get('stop_profit')
        stop_loss = stock_config.get('stop_loss')
        ignore_count = stock_config.get('ignore_count', 0)
        
        # 检查止盈
        if stop_profit and current_pnl_pct >= stop_profit:
            alerts.append({
                'stock_name': stock_name,
                'type': '止盈',
                'current_pnl_pct': current_pnl_pct,
                'trigger_line': stop_profit,
                'ignore_count': ignore_count
            })
        
        # 检查止损
        if stop_loss and current_pnl_pct <= stop_loss:
            alerts.append({
                'stock_name': stock_name,
                'type': '止损',
                'current_pnl_pct': current_pnl_pct,
                'trigger_line': stop_loss,
                'ignore_count': ignore_count
            })
    
    return alerts


def reset_ignore_count(holdings_data, stock_code):
    """重置忽略次数"""
    import json
    
    for stock in holdings_data['stocks']:
        if stock['code'] == stock_code:
            stock['ignore_count'] = 0
            break
    
    with open('data/holdings.json', 'w') as f:
        json.dump(holdings_data, f, indent=2, ensure_ascii=False)
