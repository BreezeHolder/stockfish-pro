#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 持仓分析模块 v2
功能：
1. generate_ai_analysis - 通用持仓分析
2. generate_master_analysis - 大师视角针对性分析
3. generate_broker_analysis - 券商点评针对性分析
"""

import json
import os

# AI 配置
AI_API_KEY = os.getenv('AI_API_KEY', '')
AI_MODEL = os.getenv('AI_MODEL', 'qwen-plus')
AI_API_URL = os.getenv('AI_API_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions')


def generate_ai_analysis(holdings, total_value, total_profit, total_profit_pct, today_profit):
    """通用持仓分析"""
    holdings_json = json.dumps([
        {
            'name': h.get('name', ''),
            'code': h.get('code', ''),
            'shares': h.get('shares', h.get('quantity', 0)),
            'cost': h.get('cost', h.get('cost_price', 0)),
            'price': h.get('price', h.get('current_price', 0)),
            'market_value': h.get('market_value', 0),
            'pnl': h.get('pnl', h.get('profit_loss', 0)),
            'pnl_pct': h.get('pnl_pct', h.get('profit_pct', 0))
        }
        for h in holdings
    ], ensure_ascii=False)
    
    prompt = f"""你是一位专业的 A 股投资顾问，请根据以下真实持仓数据进行分析。

【当前持仓】
{holdings_json}

【账户概览】
- 总市值：{total_value:,.2f}元
- 总盈亏：{total_profit:+,.2f}元 ({total_profit_pct*100:+.2f}%)
- 今日盈亏：{today_profit:+,.2f}元

请返回严格的 JSON 格式，不要有任何多余文字：

{{
  "action_tip": {{
    "level": "danger | warning | normal",
    "title": "一句话点明今日最需要关注的问题（15 字以内，必须包含具体股票名）",
    "detail": "具体建议（30 字以内，包含具体数字）",
    "stock": "涉及的股票名称"
  }},
  "diagnosis": {{
    "risk_level": "高风险 | 中风险 | 低风险",
    "risk_reason": "风险等级判断依据（一句话，含具体数字）",
    "issues": [
      {{
        "type": "集中度 | 止损 | 行业 | 仓位",
        "desc": "具体问题描述（含股票名和数字）",
        "suggestion": "具体操作建议"
      }}
    ],
    "summary": "整体持仓一句话总结（20 字以内）"
  }}
}}"""
    
    try:
        import requests
        headers = {'Authorization': f'Bearer {AI_API_KEY}', 'Content-Type': 'application/json'}
        payload = {'model': AI_MODEL, 'messages': [
            {'role': 'system', 'content': '你是一位专业的 A 股投资顾问，擅长风险控制和仓位管理。'},
            {'role': 'user', 'content': prompt}
        ], 'temperature': 0.3, 'max_tokens': 1000}
        
        response = requests.post(AI_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        ai_content = result['choices'][0]['message']['content'].strip()
        if ai_content.startswith('```json'): ai_content = ai_content[7:]
        if ai_content.endswith('```'): ai_content = ai_content[:-3]
        return json.loads(ai_content.strip())
    except Exception as e:
        print(f"AI 调用失败：{e}")
        return generate_fallback_analysis(holdings, total_value, total_profit, total_profit_pct, today_profit)


def generate_master_analysis(holdings, total_value, total_profit, master_name):
    """
    大师视角针对性分析
    根据大师的投资风格，分析用户当前持仓
    """
    # 检查 API 配置
    if not AI_API_KEY:
        # 返回通用的大师投资理念（基于规则）
        master_philosophy = {
            '巴菲特': """**🎓 巴菲特视角分析**

**投资理念：**
- 长期价值投资，持有优质龙头 5 年以上
- 关注护城河和 ROE（净资产收益率）
- 不建议频繁交易

**当前市场建议：**
1. 检查持仓股票是否有持续竞争优势
2. 关注 ROE > 15% 的优质公司
3. 避免追涨杀跌，长期持有""",
            '彼得林奇': """**🎓 彼得·林奇视角分析**

**投资理念：**
- 成长股投资，关注 PEG < 1
- 寻找被低估的成长股
- 分散投资，持有 10-20 只股票

**当前市场建议：**
1. 计算持仓股票的 PEG（市盈率/增长率）
2. 关注市值 50-500 亿的中小盘成长股
3. 避免过度集中单一股票""",
            '费雪': """**🎓 菲利普·费雪视角分析**

**投资理念：**
- 集中投资，深度研究后重仓
- 关注研发能力和管理层
- 长期持有，不轻易卖出

**当前市场建议：**
1. 深入研究持仓公司的研发实力
2. 关注管理层是否诚信有能力
3. 集中持仓 3-5 只最看好的股票""",
            '索罗斯': """**🎓 索罗斯视角分析**

**投资理念：**
- 趋势投资，顺势而为
- 及时止损，不固执己见
- 关注市场情绪和反身性

**当前市场建议：**
1. 判断当前市场趋势（上涨/下跌/震荡）
2. 设置止损位（建议 -10%）
3. 趋势反转时果断调仓"""
        }
        return master_philosophy.get(master_name, f"**🎓 {master_name}视角**\n\n投资理念请参考相关书籍和资料。")
    
    holdings_json = json.dumps([
        {'name': h.get('name', ''), 'code': h.get('code', ''), 'pnl_pct': h.get('pnl_pct', 0)}
        for h in holdings
    ], ensure_ascii=False)
    
    master_styles = {
        '巴菲特': '长期价值投资，持有优质龙头 5 年以上，关注护城河和 ROE',
        '彼得林奇': '成长股投资，关注 PEG<1，寻找被低估的成长股',
        '费雪': '集中投资，深度研究后重仓，关注研发能力和管理层',
        '索罗斯': '趋势投资，顺势而为，及时止损，关注市场情绪'
    }
    
    prompt = f"""你是一位专业的投资顾问，现在请扮演{master_name}。

【{master_name}投资风格】
{master_styles.get(master_name, '')}

【用户当前持仓】
{holdings_json}

【账户概览】
- 总市值：{total_value:,.2f}元
- 总盈亏：{total_profit:+,.2f}元

请以{master_name}的视角和语气，针对用户当前持有的这些股票，给出：
1. 对当前持仓的整体评价（1-2 句话）
2. 具体哪些股票符合/不符合你的投资理念
3. 操作建议（买入/卖出/持有）

请用 Markdown 格式返回，包含标题和列表，语气要像{master_name}本人说话。"""
    
    try:
        import requests
        headers = {'Authorization': f'Bearer {AI_API_KEY}', 'Content-Type': 'application/json'}
        payload = {'model': AI_MODEL, 'messages': [
            {'role': 'system', 'content': f'你是{master_name}，一位传奇投资者。请用你的投资理念和语气分析用户持仓。'},
            {'role': 'user', 'content': prompt}
        ], 'temperature': 0.5, 'max_tokens': 800}
        
        response = requests.post(AI_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"**🎓 {master_name}视角**\n\nAI 分析暂时不可用：{str(e)[:100]}...\n\n**{master_name}投资理念：**\n- {master_styles.get(master_name, '')}"


def generate_broker_analysis(holdings, total_value, total_profit, broker_name):
    """
    券商点评针对性分析
    根据券商的研究风格，分析用户当前持仓
    """
    # 检查 API 配置
    if not AI_API_KEY:
        # 返回通用的券商研究风格（基于规则）
        broker_philosophy = {
            '中信证券': """**🏦 中信证券点评**

**研究风格：**
- 稳健价值，关注行业龙头和蓝筹股
- 基本面分析为主
- 长期持有优质资产

**当前市场建议：**
1. 超配行业龙头股票
2. 关注低估值蓝筹股
3. 避免追高题材股""",
            '中金公司': """**🏦 中金公司点评**

**研究风格：**
- 国际视野，深度研报
- 关注 A 股核心资产
- 注重全球配置视角

**当前市场建议：**
1. 关注 A 股核心资产（沪深 300 成分股）
2. 对比港股/A 股估值差异
3. 长期持有优质核心资产""",
            '华泰证券': """**🏦 华泰证券点评**

**研究风格：**
- 科技成长，创新视角
- 关注科技股和成长股
- 注重产业趋势分析

**当前市场建议：**
1. 关注科技成长股（半导体/新能源/AI）
2. 关注产业趋势向上的行业
3. 适当配置成长股，平衡价值/成长"""
        }
        return broker_philosophy.get(broker_name, f"**🏦 {broker_name}点评**\n\n研究风格请参考相关研报。")
    
    holdings_json = json.dumps([
        {'name': h.get('name', ''), 'code': h.get('code', ''), 'pnl_pct': h.get('pnl_pct', 0)}
        for h in holdings
    ], ensure_ascii=False)
    
    broker_styles = {
        '中信证券': '稳健价值，关注行业龙头和蓝筹股，基本面分析为主',
        '中金公司': '国际视野，深度研报，关注 A 股核心资产',
        '华泰证券': '科技成长，创新视角，关注科技股和成长股'
    }
    
    prompt = f"""你是一位专业的券商分析师，现在请代表{broker_name}。

【{broker_name}研究风格】
{broker_styles.get(broker_name, '')}

【用户当前持仓】
{holdings_json}

【账户概览】
- 总市值：{total_value:,.2f}元
- 总盈亏：{total_profit:+,.2f}元

请以{broker_name}的视角，针对用户当前持有的这些股票，给出：
1. 对当前持仓的整体评价
2. 重点股票的目标价和评级建议
3. 调仓建议

请用 Markdown 格式返回，包含标题和列表，语气要像专业券商研报。"""
    
    try:
        import requests
        headers = {'Authorization': f'Bearer {AI_API_KEY}', 'Content-Type': 'application/json'}
        payload = {'model': AI_MODEL, 'messages': [
            {'role': 'system', 'content': f'你是{broker_name}的资深分析师。请用专业券商研报的风格分析用户持仓。'},
            {'role': 'user', 'content': prompt}
        ], 'temperature': 0.5, 'max_tokens': 800}
        
        response = requests.post(AI_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"**🏦 {broker_name}点评**\n\nAI 分析暂时不可用：{str(e)[:100]}...\n\n**{broker_name}研究风格：**\n- {broker_styles.get(broker_name, '')}"


def generate_fallback_analysis(holdings, total_value, total_profit, total_profit_pct, today_profit):
    """降级方案：基于规则的简单分析"""
    issues = []
    if holdings:
        max_stock = max(holdings, key=lambda x: x.get('market_value', 0))
        max_stock_ratio = max_stock.get('market_value', 0) / total_value if total_value > 0 else 0
        if max_stock_ratio > 0.4:
            issues.append({'type': '集中度', 'desc': f"{max_stock.get('name', '某股票')}占比{max_stock_ratio*100:.1f}%，超过 40% 警戒线", 'suggestion': '建议分散投资，单一股票不超过 30%'})
        for h in holdings:
            pnl_pct = h.get('pnl_pct', 0)
            # 注意：pnl_pct 是百分比形式（如 -9.55），不是小数（如 -0.0955）
            if pnl_pct < -30:
                issues.append({'type': '止损', 'desc': f"{h.get('name', '某股票')}亏损{abs(pnl_pct):.1f}%", 'suggestion': '评估是否执行止损（建议 30% 止损线）'})
            elif pnl_pct < -20:
                issues.append({'type': '止损', 'desc': f"{h.get('name', '某股票')}亏损{abs(pnl_pct):.1f}%", 'suggestion': '评估是否执行止损（建议 30% 止损线）'})
    
    risk_level = '高风险' if len(issues) >= 2 else ('中风险' if len(issues) == 1 else '低风险')
    action_level = 'danger' if len(issues) >= 2 else ('warning' if len(issues) == 1 else 'normal')
    
    if issues:
        first_issue = issues[0]
        stock_name = first_issue['desc'].split('占比')[0] if '占比' in first_issue['desc'] else first_issue['desc'].split('亏损')[0]
        action_tip = {'level': action_level, 'title': f"{stock_name}{first_issue['desc'].split(stock_name)[1][:20]}...", 'detail': first_issue['suggestion'], 'stock': stock_name}
    else:
        action_tip = {'level': 'normal', 'title': '持仓健康，安心持有', 'detail': '暂无特别操作建议', 'stock': '-'}
    
    return {'action_tip': action_tip, 'diagnosis': {'risk_level': risk_level, 'risk_reason': f'发现{len(issues)}个风险点' if issues else '持仓分散合理，无明显风险', 'issues': issues, 'summary': f'需关注{len(issues)}个风险点' if issues else '持仓健康'}}
