#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书告警推送模块
支持去重、延迟控制
"""

import hashlib
from datetime import datetime, timedelta

# 告警状态存储（内存）
alert_state = {
    'last_alerts': {},  # 告警指纹 -> 最后推送时间
    'cooldown_minutes': 60  # 冷却时间（分钟）
}


def send_feishu_alert(title, content, alert_type="general"):
    """
    发送飞书告警（带去重）
    
    参数：
    - title: 告警标题
    - content: 告警内容
    - alert_type: 告警类型（high_risk/big_loss/position_change）
    
    返回：True/False
    """
    import requests
    import json
    
    # 生成告警指纹（去重）
    alert_hash = hashlib.md5(f"{alert_type}:{title}".encode()).hexdigest()
    
    # 检查冷却时间
    last_alert_time = alert_state['last_alerts'].get(alert_hash)
    if last_alert_time:
        cooldown_end = last_alert_time + timedelta(minutes=alert_state['cooldown_minutes'])
        if datetime.now() < cooldown_end:
            print(f"⏳ 告警冷却中，跳过推送：{title}")
            return False
    
    # 飞书 Webhook URL（需要配置）
    # 方式 1：使用飞书机器人 Webhook
    # webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK"
    
    # 方式 2：使用飞书消息 API（需要 access_token）
    # 这里使用简化的消息发送
    
    # 构建消息内容
    message = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": title
                },
                "template": "red" if "高风险" in title or "大亏" in title else "blue"
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": content
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"推送时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        }
                    ]
                }
            ]
        }
    }
    
    try:
        # 如果有 Webhook URL，发送消息
        # response = requests.post(webhook_url, json=message, timeout=10)
        # if response.status_code == 200:
        #     alert_state['last_alerts'][alert_hash] = datetime.now()
        #     print(f"✅ 告警推送成功：{title}")
        #     return True
        
        # 临时方案：打印日志（实际使用时替换为真实推送）
        print(f"🚨【飞书告警】{title}")
        print(f"📝 内容：{content}")
        print(f"⏰ 时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 记录告警状态
        alert_state['last_alerts'][alert_hash] = datetime.now()
        
        return True
        
    except Exception as e:
        print(f"❌ 告警推送失败：{e}")
        return False


def check_and_send_alert(risks, last_risks=None):
    """
    检查风险并发送告警
    
    参数：
    - risks: 当前风险检测结果
    - last_risks: 上次风险检测结果
    
    返回：是否发送了告警
    """
    from risk_detector import should_send_alert, get_alert_fingerprint
    
    # 判断是否需要发送告警
    if not should_send_alert(risks, last_risks):
        print("✅ 风险无变化，跳过告警")
        return False
    
    # 高风险告警
    if risks['risk_level'] == '高风险':
        title = "🚨 高风险持仓预警"
        content = f"**风险等级：** 高风险\n\n**原因：** {risks['risk_reason']}\n\n**建议操作：**\n"
        for issue in risks['issues']:
            if issue['level'] == '高':
                content += f"- {issue['action']}\n"
        
        send_feishu_alert(title, content, "high_risk")
        return True
    
    # 单日大亏告警
    for issue in risks['issues']:
        if issue['type'] == '单日' and issue['level'] == '高':
            title = "📉 单日大亏预警"
            content = issue['desc'] + "\n\n" + issue['action']
            send_feishu_alert(title, content, "big_loss")
            return True
    
    return False


def reset_alert_state():
    """重置告警状态（用于测试或手动重置）"""
    alert_state['last_alerts'] = {}
    print("✅ 告警状态已重置")
