#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票新闻生成模块
模拟真实新闻 API，标注情绪值
"""

from datetime import datetime, timedelta
import random


def generate_stock_news(stock_name, stock_row):
    """
    生成持仓股票相关新闻（模拟）
    
    实际应接入：
    - 东方财富新闻 API
    - 新浪财经 API
    - 同花顺 API
    """
    news_templates = {
        '利好': [
            "{stock}业绩超预期，净利润增长{num}%",
            "{stock}中标重大项目，金额达{num}亿元",
            "{stock}获机构增持，目标价上调至{num}元",
            "{stock}新产品发布，市场反响热烈",
            "{stock}回购股份，金额达{num}亿元",
        ],
        '利空': [
            "{stock}业绩下滑，净利润减少{num}%",
            "{stock}股东减持计划实施中",
            "{stock}收到监管函，要求整改",
            "{stock}产品价格上涨，成本压力增大",
            "{stock}行业政策收紧，面临挑战",
        ],
        '中性': [
            "{stock}召开年度股东大会",
            "{stock}发布日常经营公告",
            "{stock}董事会审议通过年度报告",
            "{stock}发布投资者关系活动记录表",
            "{stock}行业展会参展，展示新产品",
        ]
    }
    
    news_list = []
    
    # 根据持仓盈亏生成相关新闻
    pnl_pct = stock_row.get('盈亏率', 0)
    
    # 盈利股票：多生成利好新闻
    if pnl_pct > 0.1:
        sentiment_weights = {'利好': 0.6, '中性': 0.3, '利空': 0.1}
    elif pnl_pct < -0.2:
        # 亏损股票：多生成利空新闻
        sentiment_weights = {'利好': 0.1, '中性': 0.3, '利空': 0.6}
    else:
        # 正常：均衡分布
        sentiment_weights = {'利好': 0.3, '中性': 0.5, '利空': 0.2}
    
    # 生成 3-5 条新闻
    num_news = random.randint(3, 5)
    
    for i in range(num_news):
        # 随机选择情绪
        sentiment = random.choices(
            list(sentiment_weights.keys()),
            weights=list(sentiment_weights.values())
        )[0]
        
        # 随机选择模板
        template = random.choice(news_templates[sentiment])
        title = template.format(stock=stock_name, num=random.randint(10, 50))
        
        # 计算情绪值（0-10）
        if sentiment == '利好':
            sentiment_score = random.uniform(7, 10)
        elif sentiment == '利空':
            sentiment_score = random.uniform(0, 3)
        else:
            sentiment_score = random.uniform(4, 6)
        
        # 生成时间（最近 7 天）
        days_ago = random.randint(0, 7)
        hours_ago = random.randint(1, 23)
        news_time = datetime.now() - timedelta(days=days_ago, hours=hours_ago)
        
        # 新闻源和对应链接模板
        sources = {
            '东方财富': 'https://quote.eastmoney.com/',
            '新浪财经': 'https://finance.sina.com.cn/',
            '同花顺': 'http://basic.10jqka.com.cn/',
            '财联社': 'https://www.cls.cn/',
            '证券时报': 'http://www.stcn.com/'
        }
        source_name = random.choice(list(sources.keys()))
        
        # 生成模拟链接（实际应使用真实新闻 URL）
        news_url = f"{sources[source_name]}news/{news_time.strftime('%Y%m%d')}/{random.randint(100000, 999999)}.html"
        
        news_list.append({
            'title': title,
            'sentiment': sentiment,
            'sentiment_score': round(sentiment_score, 1),
            'source': source_name,
            'time': news_time.strftime('%m-%d %H:%M'),
            'url': news_url
        })
    
    # 按情绪值排序（利好在前）
    news_list.sort(key=lambda x: x['sentiment_score'], reverse=True)
    
    return news_list


def fetch_real_news(stock_code, stock_name, limit=10):
    """
    获取真实新闻（待实现）
    
    可接入的 API：
    1. 东方财富：http://push2.eastmoney.com/api/qt/stock/news/get
    2. 新浪财经：https://feed.mix.sina.com.cn/
    3. 同花顺：http://basic.10jqka.com.cn/{code}/news.html
    
    参数：
    - stock_code: 股票代码
    - stock_name: 股票名称
    - limit: 返回数量
    
    返回：
    [
        {
            'title': '新闻标题',
            'sentiment': '利好 | 利空 | 中性',
            'sentiment_score': 7.5,
            'source': '东方财富',
            'time': '03-17 14:30',
            'url': 'https://...'
        }
    ]
    """
    # TODO: 实现真实新闻 API 调用
    # 这里先返回模拟数据
    return []
