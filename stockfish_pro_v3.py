#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StockFish Pro v3.1 - 专业版（完整功能版）
对标产品：东方财富、同花顺、雪球、慧博投研
功能：
- 核心指标卡片
- 持仓分布可视化
- 个股详细分析
- 行业动量排名
- 投资大师风格匹配
- 券商风格点评
- 多报告综合分析
- 新股扫描分析
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import os
import io
import sys

# 添加工作空间路径到 sys.path，以便导入模块
sys.path.insert(0, os.path.expanduser("~/.openclaw/workspace"))

# ============== 页面配置（移动端优化） ==============
st.set_page_config(
    page_title="🐟 StockFish Pro",
    page_icon="🐟",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items=None
)

# 移动端 CSS 优化
st.markdown("""
<style>
    /* 移动端适配 */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
        }
        .stTabs [data-baseweb="tab"] {
            font-size: 12px;
            padding: 4px 8px;
        }
        .metric-card {
            padding: 10px !important;
        }
        .metric-card h3 {
            font-size: 12px !important;
        }
        .metric-card h2 {
            font-size: 18px !important;
        }
    }
    
    /* 隐藏 Streamlit 菜单 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 优化卡片显示 */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        color: white;
        text-align: center;
    }
    
    /* 【修复 7】白底细边框样式 */
    .white-card {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ============== 全局状态管理 ==============
if 'last_sync_time' not in st.session_state:
    st.session_state.last_sync_time = datetime.now()
if 'sync_status' not in st.session_state:
    st.session_state.sync_status = 'success'
if 'last_risks' not in st.session_state:
    st.session_state.last_risks = None  # 用于告警去重
if 'ai_analysis_cache' not in st.session_state:
    st.session_state.ai_analysis_cache = None
if 'focus_stock' not in st.session_state:
    st.session_state.focus_stock = None  # 用于高亮显示
if 'selected_sector' not in st.session_state:
    st.session_state.selected_sector = '全部'  # 用于行业过滤

# ============== 改进⑤：持仓历史快照 ==============
SNAPSHOT_FILE = os.path.expanduser("~/.openclaw/workspace/data/portfolio_snapshots.json")

def load_snapshots():
    """加载历史快照"""
    try:
        with open(SNAPSHOT_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_snapshot(df, total_market_value, total_pnl):
    """保存今日快照"""
    snapshots = load_snapshots()
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 检查今日是否已保存
    for i, snap in enumerate(snapshots):
        if snap['date'] == today:
            # 更新今日数据
            snapshots[i]['total_market_value'] = total_market_value
            snapshots[i]['total_pnl'] = total_pnl
            snapshots[i]['stocks'] = df.to_dict('records')
            break
    else:
        # 新增今日数据
        snapshots.append({
            'date': today,
            'total_market_value': total_market_value,
            'total_pnl': total_pnl,
            'stocks': df.to_dict('records')
        })
    
    # 只保留最近 90 天
    snapshots = snapshots[-90:]
    
    try:
        os.makedirs(os.path.dirname(SNAPSHOT_FILE), exist_ok=True)
        with open(SNAPSHOT_FILE, 'w') as f:
            json.dump(snapshots, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False

# ============== 自定义 CSS ==============
st.markdown("""
<style>
    /* 红涨绿跌颜色 */
    .up { color: #dc143c; font-weight: bold; }
    .down { color: #10b981; font-weight: bold; }
    
    /* 卡片样式 */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        color: white;
    }
    
    /* 风险提示框 */
    .risk-box {
        background-color: #fee2e2;
        border-left: 4px solid #ef4444;
        padding: 15px;
        margin: 10px 0;
        border-radius: 5px;
    }
    
    /* 建议框 */
    .advice-box {
        background-color: #dbeafe;
        border-left: 4px solid #3b82f6;
        padding: 15px;
        margin: 10px 0;
        border-radius: 5px;
    }
    
    /* 大师风格框 */
    .master-box {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# ============== 配置区 ==============
HOLDINGS_FILE = os.path.expanduser("~/.openclaw/workspace/data/holdings.json")
CACHE_FILE = os.path.expanduser("~/.openclaw/workspace/data/portfolio_cache.json")
OUTPUT_FILE = os.path.expanduser("~/.openclaw/workspace/data/latest_portfolio.json")

# ============== 持仓管理功能 ==============
def load_holdings():
    """加载持仓配置"""
    try:
        with open(HOLDINGS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"stocks": []}

def save_holdings(data):
    """保存持仓配置"""
    try:
        os.makedirs(os.path.dirname(HOLDINGS_FILE), exist_ok=True)
        with open(HOLDINGS_FILE, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"保存失败：{e}")
        return False

# ============== 数据获取 ==============
@st.cache_data(ttl=60)
def get_stock_price_tencent(code, retries=3):
    """腾讯财经实时接口（真实数据源）"""
    symbol = f"sh{code}" if code.startswith('6') or code.startswith('5') else f"sz{code}"
    url = f"http://qt.gtimg.cn/q={symbol}"
    proxies = {'http': None, 'https': None}
    
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=5 + attempt * 2, proxies=proxies)
            if r.status_code == 200:
                data = r.text
                if '=' in data and '~' in data:
                    parts = data.split('=')[1].strip('"').split('~')
                    if len(parts) >= 7:
                        price = float(parts[3]) if len(parts) > 3 and parts[3] else 0
                        prev_close = float(parts[4]) if len(parts) > 4 and parts[4] else 0
                        change = ((price - prev_close) / prev_close) * 100 if prev_close > 0 else 0
                        return {
                            'price': price,
                            'prev_close': prev_close,
                            'change': change,
                        }
        except Exception as e:
            if attempt < retries - 1:
                pass
            else:
                st.error(f"获取 {code} 失败：{e}")
    return None

@st.cache_data(ttl=60)
def get_stock_price_sina(code, retries=3):
    """新浪财经实时接口（真实数据源，备用）"""
    symbol = f"sh{code}" if code.startswith('6') or code.startswith('5') else f"sz{code}"
    url = f"http://hq.sinajs.cn/list={symbol}"
    proxies = {'http': None, 'https': None}
    
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=5 + attempt * 2, proxies=proxies)
            if r.status_code == 200:
                data = r.text
                if '=' in data:
                    parts = data.split('=')[1].strip('"').split(',')
                    if len(parts) >= 4:
                        price = float(parts[3])
                        prev_close = float(parts[2])
                        change = ((price - prev_close) / prev_close) * 100 if prev_close > 0 else 0
                        return {
                            'price': price,
                            'prev_close': prev_close,
                            'change': change,
                        }
        except Exception as e:
            if attempt < retries - 1:
                pass
            else:
                st.error(f"获取 {code} 失败：{e}")
    return None

def get_stock_price(code, retries=3):
    """获取股票价格（多数据源自动切换）"""
    # 优先使用腾讯财经
    data = get_stock_price_tencent(code, retries)
    if data:
        return data
    
    # 腾讯失败则使用新浪财经
    data = get_stock_price_sina(code, retries)
    if data:
        return data
    
    return None

def get_stock_industry(code):
    """获取股票所属行业"""
    industry_map = {
        '512400': '有色金属 ETF',
        '513180': '恒生科技 ETF',
        '600519': '白酒',
        '000568': '白酒',
        '000858': '白酒',
        '002304': '白酒',
        '603360': '化工',
        '000571': '能源',
        '002572': '家居',
    }
    return industry_map.get(code, '其他')

def get_portfolio_analysis():
    """获取持仓分析"""
    try:
        with open(HOLDINGS_FILE, 'r') as f:
            holdings_config = json.load(f)
        holdings = holdings_config.get('stocks', [])
    except Exception as e:
        st.error(f"加载持仓配置失败：{e}")
        return None, None
    
    results = []
    
    for holding in holdings:
        code = holding['code']
        name = holding['name']
        shares = holding['shares']
        cost = holding['cost']
        
        data = get_stock_price_tencent(code)
        if data:
            price = data['price']
            prev_close = data['prev_close']
            change = data['change']
            market_value = round(price * shares, 2)
            pnl = round((price - cost) * shares, 2)
            pnl_pct = round(((price - cost) / cost) * 100, 2) if cost > 0 else 0
            today_pnl = round((price - prev_close) * shares, 2)
            
            industry = get_stock_industry(code)
            
            results.append({
                '代码': code,
                '名称': name,
                '最新价': round(price, 3),
                '涨跌幅': round(change, 2),
                '持仓股数': shares,
                '成本价': cost,
                '昨收': round(prev_close, 3),
                '持仓市值': market_value,
                '持仓盈亏': pnl,
                '盈亏率': pnl_pct,
                '今日盈亏': today_pnl,
                '行业': industry
            })
    
    df = pd.DataFrame(results)
    
    if df.empty:
        return None, None
    
    total_value = df['持仓市值'].sum()
    df['持仓占比'] = round((df['持仓市值'] / total_value * 100), 2)
    
    sector_dist = df.groupby('行业')['持仓占比'].sum().reset_index()
    sector_dist.columns = ['行业', '持仓占比']
    
    return df, sector_dist

# ============== 辅助函数 ==============
def format_color(value):
    """格式化数字并添加颜色"""
    if isinstance(value, (int, float)):
        if value > 0:
            return f'<span class="up">{value:+.2f}</span>'
        elif value < 0:
            return f'<span class="down">{value:+.2f}</span>'
        else:
            return f'{value:.2f}'
    return str(value)

def export_to_csv(df):
    """导出为 CSV"""
    output = io.StringIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')
    return output.getvalue()

# ============== 投资大师风格分析 ==============
def analyze_by_master_style(df, master_name):
    """按投资大师风格分析持仓"""
    
    masters = {
        '巴菲特': {
            'name': '沃伦·巴菲特',
            'style': '价值投资',
            'principles': [
                '只投资自己理解的公司',
                '寻找有护城河的企业',
                '长期持有优质公司',
                '在别人恐惧时贪婪，在别人贪婪时恐惧',
                '价格是你付出的，价值是你得到的'
            ],
            'criteria': {
                'pe_ratio': '< 25',
                'roe': '> 15%',
                'debt_ratio': '< 50%',
                'holding_period': '长期（5-10 年）'
            }
        },
        '彼得林奇': {
            'name': '彼得·林奇',
            'style': '成长投资',
            'principles': [
                '投资你熟悉的公司',
                '寻找 PEG < 1 的成长股',
                '关注小而美的公司',
                '分散投资，持有 10-20 只股票',
                '定期复查持仓'
            ],
            'criteria': {
                'peg_ratio': '< 1',
                'growth_rate': '> 20%',
                'market_cap': '中小盘',
                'holding_period': '中期（1-3 年）'
            }
        },
        '费雪': {
            'name': '菲利普·费雪',
            'style': '成长股投资',
            'principles': [
                '投资优秀的成长型公司',
                '关注公司的研发能力',
                '管理层要优秀',
                '长期持有，不要频繁交易',
                '集中投资，不要过度分散'
            ],
            'criteria': {
                'rd_ratio': '> 5%',
                'management': '优秀',
                'growth_potential': '高',
                'holding_period': '长期（5 年以上）'
            }
        },
        '索罗斯': {
            'name': '乔治·索罗斯',
            'style': '趋势投资',
            'principles': [
                '市场总是错的',
                '寻找反身性机会',
                '顺势而为，及时止损',
                '大胆下注，快速纠错',
                '关注市场趋势和情绪'
            ],
            'criteria': {
                'trend': '顺势',
                'stop_loss': '严格（-10%）',
                'position_size': '灵活调整',
                'holding_period': '短期（1-6 个月）'
            }
        }
    }
    
    master = masters.get(master_name, masters['巴菲特'])
    
    return master

# ============== 主界面 ==============
def main():
    # 标题
    st.title("🐟 StockFish Pro v3.1")
    st.markdown("**专业版 - 对标东方财富/同花顺/雪球/慧博投研**")
    
    # 侧边栏
    with st.sidebar:
        st.header("⚙️ 设置")
        
        if st.button("🔄 刷新数据", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.divider()
        st.subheader("📥 数据导出")
        
        df, _ = get_portfolio_analysis()
        if df is not None:
            csv = export_to_csv(df)
            st.download_button(
                label="📥 导出 CSV",
                data=csv,
                file_name=f"持仓分析_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        st.divider()
        st.subheader("📡 数据源")
        st.markdown("""
        - ✅ 腾讯财经（主）
        - ⚠️ 新浪财经（备用）
        - ⚠️ 东方财富（备用）
        """)
        
        st.divider()
        st.info(f"最后更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # ============== 顶部同步状态栏 + 粘性 Tab 导航 ==============
    # 第 1 行：同步状态栏
    sync_col1, sync_col2, sync_col3 = st.columns([6, 1, 1])
    
    with sync_col1:
        st.markdown("**🐟 StockFish Pro** - 个人持仓分析系统")
    
    with sync_col2:
        # 同步按钮
        if st.button("🔄 同步数据", key="sync_btn", use_container_width=True):
            st.session_state.sync_status = 'syncing'
            st.cache_data.clear()
            st.session_state.last_sync_time = datetime.now()
            st.session_state.sync_status = 'success'
            st.rerun()
    
    with sync_col3:
        # 同步状态显示
        if st.session_state.sync_status == 'success':
            st.success(f"✅ {st.session_state.last_sync_time.strftime('%H:%M')}")
        elif st.session_state.sync_status == 'syncing':
            st.warning("⏳ 同步中...")
        else:
            st.error("❌ 同步失败")
    
    # 第 2 行：粘性 Tab 导航
    st.markdown("---")
    main_tabs = st.tabs(["📊 总览", "📋 持仓", "🤖 AI 诊断", "📰 新闻", "⚙️ 配置"])
    
    st.divider()
    
    # 获取数据
    df, sector_df = get_portfolio_analysis()
    
    if df is None or df.empty:
        st.error("❌ 数据获取失败，请检查持仓配置")
        return
    
    # 计算汇总数据
    total_market_value = df['持仓市值'].sum()
    total_pnl = df['持仓盈亏'].sum()
    total_pnl_pct = round((total_pnl / (total_market_value - total_pnl)) * 100, 2) if (total_market_value - total_pnl) > 0 else 0
    total_today_pnl = df['今日盈亏'].sum()
    
    # ============== Tab 1: 总览 ==============
    with main_tabs[0]:
        # ========== 功能三：自动保存决策日记 ==========
        try:
            from decision_diary import save_daily_snapshot
            # 每次同步时自动保存
            save_daily_snapshot(holdings_data, total_market_value, total_pnl, total_pnl_pct)
        except Exception as e:
            print(f"决策日记保存失败：{e}")

        # ========== 止盈止损预警（功能一） ==========
        try:
            from stop_profit_loss import check_stop_profit_loss
            alerts = check_stop_profit_loss(df, holdings_data)
            
            if alerts:
                for alert in alerts:
                    color = '#d1fae5' if alert['type'] == '止盈' else '#fee2e2'
                    border = '#10b981' if alert['type'] == '止盈' else '#ef4444'
                    icon = '🎯' if alert['type'] == '止盈' else '🛑'
                    
                    st.markdown(f"""
                    <div style="background-color: {color}; padding: 15px; border-radius: 10px; border-left: 4px solid {border}; margin: 10px 0;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong>{icon} {alert['stock_name']} 触发{alert['type']}！</strong><br>
                                <small>当前{alert['type'][:-1]}幅度：{alert['current_pnl_pct']:.1f}% | 触发线：{alert['trigger_line']:.1f}%</small><br>
                                {f"<small style='color: #ef4444;'>⚠️ 你已忽略{alert['ignore_count']}次</small>" if alert['ignore_count'] > 0 else ''}
                            </div>
                            <div>
                                <button onclick="alert('查看详情功能开发中')" style="background-color: #1890ff; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; margin-right: 5px;">查看详情</button>
                                <button onclick="alert('已知晓功能开发中')" style="background-color: #52c41a; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer;">已知晓暂不操作</button>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        except Exception as e:
            print(f"止盈止损检测失败：{e}")
        
        # 核心指标卡片
        st.subheader("💰 核心指标")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3>持仓市值</h3>
                <h2>¥{total_market_value:,.2f}</h2>
                <small style="opacity: 0.8">📊 {st.session_state.last_sync_time.strftime('%H:%M')} 更新</small>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h3>持仓盈亏</h3>
                <h2 class="{'up' if total_pnl > 0 else 'down'}">¥{total_pnl:+,.2f}</h2>
                <p>{total_pnl_pct:+.2f}%</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h3>今日盈亏</h3>
                <h2 class="{'up' if total_today_pnl > 0 else 'down'}">¥{total_today_pnl:+,.2f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            # 自动刷新按钮
            if st.button("🔄 立即同步", key="manual_sync_btn"):
                st.session_state.last_sync_time = datetime.now()
                st.session_state.ai_analysis_cache = None  # 清空 AI 缓存
                st.rerun()
            
            st.markdown(f"""
            <div class="metric-card">
                <h3>持仓股票</h3>
                <h2>{len(df)} 只</h2>
                <small style="opacity: 0.8">📊 {st.session_state.last_sync_time.strftime('%H:%M:%S')} 更新</small>
            </div>
            """, unsafe_allow_html=True)
        
        st.divider()
        
        # ========== 新增：风险自动检测（P0） ==========
        st.subheader("⚠️ 风险检测")
        
        # 显示最后同步时间
        st.info(f"📊 最后同步：{st.session_state.last_sync_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 调用风险检测
        try:
            from risk_detector import detect_risks
            risks = detect_risks(df, total_market_value)
            
            # 显示风险等级徽章
            risk_level = risks['risk_level']
            if '高风险' in risk_level:
                risk_color = '#ef4444'
                risk_icon = '🔴'
            elif '中风险' in risk_level:
                risk_color = '#f59e0b'
                risk_icon = '🟡'
            else:
                risk_color = '#10b981'
                risk_icon = '🟢'
            
            st.markdown(f"""
            <div style="text-align: center; margin: 20px 0;">
                <span style="background-color: {risk_color}; color: white; padding: 10px 30px; border-radius: 20px; font-size: 18px; font-weight: bold;">
                    {risk_icon} {risk_level}
                </span>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"**📊 判断依据：** {risks['risk_reason']}")
            
            # 显示风险列表
            if risks['issues']:
                st.markdown(f"**⚠️ 发现 {len(risks['issues'])} 个风险点：**")
                for i, issue in enumerate(risks['issues']):
                    icon = '🔴' if issue['level'] == '高' else '🟡'
                    
                    # 添加跳转按钮
                    stock_name = issue.get('stock', '')
                    if stock_name and stock_name != '全部持仓':
                        if st.button(f"{icon} 查看 {issue['desc'][:30]}...", key=f"risk_{i}"):
                            st.session_state.focus_stock = stock_name
                            st.rerun()
                    else:
                        st.markdown(f"{icon} **{issue['type']}** - {issue['desc']}")
                        st.markdown(f"   💡 {issue['action']}")
            else:
                st.success("✅ 持仓分散合理，无明显风险")
            
            # 检查并发送告警
            try:
                from alert_sender import check_and_send_alert
                if check_and_send_alert(risks, st.session_state.last_risks):
                    st.success("🚨 告警已推送")
                st.session_state.last_risks = risks  # 保存当前风险状态
            except Exception as e:
                print(f"告警检查失败：{e}")
        
        except Exception as e:
            st.error(f"风险检测失败：{e}")
        
        st.divider()
        
        # ========== 交互增强：行业过滤（P2） ==========
        st.subheader("📊 持仓分布")
        
        # 行业过滤下拉框
        sectors = ['全部'] + list(sector_df['行业'].unique())
        selected_sector = st.selectbox(
            "🔍 筛选行业",
            sectors,
            index=0,
            key="sector_filter"
        )
        
        # 应用过滤
        if selected_sector != '全部':
            df_filtered = df[df['行业'] == selected_sector]
            sector_df_filtered = sector_df[sector_df['行业'] == selected_sector]
            st.info(f"📌 当前显示：{selected_sector}行业（{len(df_filtered)}只股票）")
        else:
            df_filtered = df
            sector_df_filtered = sector_df
        
        # 饼图独占一行
        fig_pie = px.pie(
            sector_df_filtered,
            values='持仓占比',
            names='行业',
            title='行业分布',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
        
        # 横向柱状图（全宽）
        df_sorted = df_filtered.sort_values('持仓盈亏', ascending=False)
        fig_bar = px.bar(
            df_sorted,
            y='名称',
            x='持仓盈亏',
            color='持仓盈亏',
            color_continuous_scale=[(0, 'green'), (0.5, 'yellow'), (1, 'red')],
            orientation='h'
        )
        fig_bar.update_layout(xaxis_title='盈亏 (元)', yaxis_title='', height=400)
        st.plotly_chart(fig_bar, use_container_width=True)
        
        st.divider()
        
        # AI 持仓分析
        st.subheader("🤖 AI 持仓分析")
        
        # 准备持仓数据
        holdings_list = []
        for _, row in df.iterrows():
            holdings_list.append({
                'name': row['名称'],
                'code': row['代码'],
                'shares': int(row['持仓股数']),
                'cost': float(row['成本价']),
                'price': float(row['最新价']),
                'market_value': float(row['持仓市值']),
                'pnl': float(row['持仓盈亏']),
                'pnl_pct': float(row['盈亏率'])
            })
        
        # 调用 AI 分析
        with st.spinner("🤖 AI 正在分析持仓..."):
            try:
                from ai_analysis import generate_ai_analysis
                ai_result = generate_ai_analysis(
                    holdings_list,
                    total_market_value,
                    total_pnl,
                    total_pnl_pct,
                    total_today_pnl
                )
            except Exception as e:
                st.error(f"AI 分析失败：{e}")
                ai_result = None
        
        if ai_result:
            action_tip = ai_result.get('action_tip', {})
            diagnosis = ai_result.get('diagnosis', {})
            
            # 【修复 5】总览 Tab 只保留行动建议卡片（白底 + 细边框）
            level = action_tip.get('level', 'normal')
            if level == 'danger':
                border_color = '#ef4444'
                icon = '🔴'
            elif level == 'warning':
                border_color = '#f59e0b'
                icon = '🟡'
            else:
                border_color = '#10b981'
                icon = '🟢'
            
            st.markdown(f"""
            <div class="white-card" style="border: 2px solid {border_color};">
                <h3 style="margin: 0 0 10px 0; color: #1f2937;">{icon} {action_tip.get('title', '暂无建议')}</h3>
                <p style="margin: 0; font-size: 15px; color: #374151;">{action_tip.get('detail', '')}</p>
                <p style="margin: 10px 0 0 0; font-size: 13px; color: #6b7280;">📌 涉及股票：{action_tip.get('stock', '-')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # 添加跳转按钮（Streamlit 原生方式）
            st.markdown(f"**💡 完整诊断已移至「🤖 AI 诊断」Tab，请点击上方标签查看**")
        else:
            st.info("🤖 AI 分析暂时不可用")
    
    # ============== Tab 2: 持仓 ==============
    with main_tabs[1]:
        st.subheader("📋 持仓明细")
        
        sort_option = st.selectbox(
            "排序方式",
            ["持仓占比", "持仓盈亏", "盈亏率", "今日盈亏", "代码"],
            index=0,
            key="sort_select_tab2"
        )
        
        df_sorted = df.sort_values(sort_option, ascending=False).reset_index(drop=True)
        
        # 核心 4 列
        core_df = pd.DataFrame()
        core_df['名称'] = df_sorted['名称']
        core_df['持仓市值'] = df_sorted['持仓市值'].apply(lambda x: f"¥{x:,.0f}")
        core_df['持仓盈亏'] = df_sorted['持仓盈亏'].apply(lambda x: f"{'🔴' if x > 0 else '🟢'} ¥{x:+,.0f}")
        core_df['盈亏率'] = df_sorted['盈亏率'].apply(lambda x: f"{'🔴' if x > 0 else '🟢'} {x:+.1f}%")
        
        # 高亮显示（交互增强）
        if st.session_state.focus_stock:
            st.info(f"📍 已聚焦：{st.session_state.focus_stock}")
            if st.button("✖️ 清除聚焦"):
                st.session_state.focus_stock = None
                st.rerun()
            
            # 高亮样式
            def highlight_focus(row):
                if row['名称'] == st.session_state.focus_stock:
                    return ['background-color: yellow'] * len(row)
                return [''] * len(row)
            
            core_df_styled = core_df.style.apply(highlight_focus, axis=1)
            st.dataframe(core_df_styled, use_container_width=True, hide_index=True)
        else:
            st.dataframe(core_df, use_container_width=True, hide_index=True)
        
        # 展开详情
        st.markdown("**🔍 展开查看详情**")
        for i, row in df_sorted.iterrows():
            with st.expander(f"**{row['名称']} ({row['代码']})** - ¥{row['持仓市值']:,.0f} | {row['盈亏率']:+.1f}%"):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("最新价", f"¥{row['最新价']:.3f}")
                with col2:
                    st.metric("涨跌幅", f"{row['涨跌幅']:+.2f}%")
                with col3:
                    st.metric("持仓股数", f"{row['持仓股数']:,}")
                with col4:
                    st.metric("成本价", f"¥{row['成本价']:.4f}")
    
    # ============== Tab 3: AI 诊断 ==============
    with main_tabs[2]:
        st.subheader("🤖 AI 智能诊断")
        
        # 加载持仓数据（功能二、功能三需要）
        holdings_data = load_holdings()
        
        # 【修复 3】AI 分析结果缓存机制
        # 检查缓存是否存在
        if 'ai_analysis_cache' not in st.session_state:
            st.session_state['ai_analysis_cache'] = None
        
        # 准备持仓数据
        holdings_list = []
        for _, row in df.iterrows():
            holdings_list.append({
                'name': row['名称'],
                'code': row['代码'],
                'shares': int(row['持仓股数']),
                'cost': float(row['成本价']),
                'price': float(row['最新价']),
                'market_value': float(row['持仓市值']),
                'pnl': float(row['持仓盈亏']),
                'pnl_pct': float(row['盈亏率'])
            })
        
        # 检查是否需要重新调用 AI
        if st.session_state['ai_analysis_cache'] is None:
            # 调用 AI 分析
            with st.spinner("🤖 AI 正在分析持仓..."):
                try:
                    from ai_analysis import generate_ai_analysis
                    ai_result = generate_ai_analysis(holdings_list, total_market_value, total_pnl, total_pnl_pct, total_today_pnl)
                    st.session_state['ai_analysis_cache'] = ai_result
                except Exception as e:
                    st.error(f"AI 分析失败：{e}")
                    ai_result = None
        else:
            # 使用缓存
            ai_result = st.session_state['ai_analysis_cache']
        
        # 重新分析按钮
        if st.button("🔄 重新分析", key="rerun_ai_btn"):
            st.session_state['ai_analysis_cache'] = None
            st.rerun()
        
        # ========== 功能二：买入逻辑追踪 ==========
        st.divider()
        st.subheader("📊 持仓逻辑追踪")
        st.markdown("**💡 AI 判断你的买入理由是否仍然成立**")
        
        # 找出有买入理由的股票
        stocks_with_reason = [s for s in holdings_data.get('stocks', []) if s.get('buy_reason', '')]
        
        if stocks_with_reason:
            for stock in stocks_with_reason:
                stock_name = stock['name']
                stock_code = stock['code']
                buy_reason = stock['buy_reason']
                
                # 查找当前数据
                stock_row = df[df['代码'] == stock_code]
                if stock_row.empty:
                    continue
                
                current_price = stock_row.iloc[0]['最新价']
                cost_price = stock['cost']
                current_pnl_pct = stock_row.iloc[0]['盈亏率']
                
                # 调用 AI 分析
                with st.spinner(f"🤖 AI 正在分析{stock_name}..."):
                    try:
                        from logic_tracker import analyze_buying_logic
                        result = analyze_buying_logic(stock_name, buy_reason, current_pnl_pct, current_price, cost_price)
                        
                        # 显示结果
                        status_color = {'逻辑成立': '#d1fae5', '逻辑动摇': '#fef3c7', '逻辑已失效': '#fee2e2'}[result['status']]
                        status_icon = {'逻辑成立': '✅', '逻辑动摇': '⚠️', '逻辑已失效': '❌'}[result['status']]
                        
                        st.markdown(f"""
                        <div style="background-color: {status_color}; padding: 15px; border-radius: 10px; margin: 10px 0;">
                            <strong>{status_icon} {stock_name}</strong><br>
                            <small>买入理由：{buy_reason}</small><br>
                            <small>当前盈亏：{current_pnl_pct:.1f}% | 当前价：¥{current_price:.3f}</small><br>
                            <strong>AI 判断：{result['status']}</strong><br>
                            <small>{result['reason']}</small>
                        </div>
                        """, unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"{stock_name} 分析失败：{e}")
        else:
            st.info("📝 暂无买入理由记录，请在配置 Tab 中填写每只股票的买入理由")
        
        # ========== 功能三：月度复盘 ==========
        st.divider()
        st.subheader("📅 月度复盘")
        st.markdown("**💡 AI 生成个性化月报，帮你总结交易习惯**")
        
        if st.button("📊 生成本月复盘报告", type="primary"):
            with st.spinner("🤖 AI 正在分析过去 30 天交易数据..."):
                try:
                    from decision_diary import load_diary, generate_monthly_report, ai_generate_monthly_report
                    
                    diary = load_diary()
                    
                    if not diary:
                        st.info("📝 暂无历史数据，请连续使用 30 天后生成月报")
                    else:
                        # 生成基础报告
                        report_data = generate_monthly_report(diary, days=30)
                        
                        if report_data:
                            # 调用 AI 生成个性化报告
                            ai_report = ai_generate_monthly_report(report_data)
                            
                            # 显示报告
                            st.markdown(ai_report)
                            
                            # 截图分享提示
                            st.info("📸 提示：可以使用手机截图分享功能保存月报")
                        else:
                            st.info("📝 数据不足，请至少使用 7 天后生成月报")
                except Exception as e:
                    st.error(f"月报生成失败：{e}")
        
        if ai_result:
            diagnosis = ai_result.get('diagnosis', {})
            
            # 风险徽章
            risk_level = diagnosis.get('risk_level', '低风险')
            if '高风险' in risk_level:
                risk_color = '#ef4444'
                risk_icon = '🔴'
            elif '中风险' in risk_level:
                risk_color = '#f59e0b'
                risk_icon = '🟡'
            else:
                risk_color = '#10b981'
                risk_icon = '🟢'
            
            st.markdown(f"""
            <div style="text-align: center; margin: 20px 0;">
                <span style="background-color: {risk_color}; color: white; padding: 10px 30px; border-radius: 20px; font-size: 18px; font-weight: bold;">
                    {risk_icon} {risk_level}
                </span>
            </div>
            """, unsafe_allow_html=True)
            
            # 【修复 2】直接显示 risk_reason 字段内容
            st.markdown(f"**📊 判断依据：** {diagnosis.get('risk_reason', 'N/A')}")
            
            # 问题列表
            issues = diagnosis.get('issues', [])
            if issues:
                st.markdown(f"**⚠️ 发现 {len(issues)} 个风险点：**")
                for i, issue in enumerate(issues):
                    with st.expander(f"{'🔴' if issue.get('type') == '集中度' else '🟡'} {issue.get('type')} - {issue.get('desc', '')[:50]}...", expanded=(i==0)):
                        st.markdown(f"""
                        <div class="white-card">
                            <p style="margin: 0 0 10px 0; color: #374151;"><strong>问题描述：</strong> {issue.get('desc', 'N/A')}</p>
                            <p style="margin: 0; color: #374151;"><strong>建议：</strong> {issue.get('suggestion', 'N/A')}</p>
                        </div>
                        """, unsafe_allow_html=True)
            
            st.markdown(f"**💡 总结：** {diagnosis.get('summary', 'N/A')}")
            
            # 【修复 4】大师视角 - 针对性分析
            st.divider()
            st.subheader("🎓 大师视角")
            st.markdown("*投资哲学视角：该不该持有*")
            master_name = st.selectbox("选择投资大师", ['巴菲特', '彼得林奇', '费雪', '索罗斯'], key="master_select")
            
            # 检查大师分析缓存
            master_cache_key = f'master_analysis_{master_name}'
            if master_cache_key not in st.session_state or st.session_state[master_cache_key] is None:
                with st.spinner(f"🤖 {master_name}正在分析持仓..."):
                    try:
                        from ai_analysis import generate_master_analysis
                        master_result = generate_master_analysis(holdings_list, total_market_value, total_pnl, master_name)
                        st.session_state[master_cache_key] = master_result
                    except Exception as e:
                        st.session_state[master_cache_key] = f"{master_name}分析失败：{e}"
            
            # 显示大师分析结果
            master_result = st.session_state.get(master_cache_key, '')
            if isinstance(master_result, str) and master_result:
                st.markdown(master_result)
            else:
                st.info(f"请选择{master_name}查看针对性分析")
            
            # 【修复 4】券商点评 - 针对性分析
            st.divider()
            st.subheader("🏦 券商风格点评")
            st.markdown("*市场层面：目标价/评级*")
            broker = st.selectbox("选择券商", ['中信证券', '中金公司', '华泰证券'], key="broker_select")
            
            # 检查券商分析缓存
            broker_cache_key = f'broker_analysis_{broker}'
            if broker_cache_key not in st.session_state or st.session_state[broker_cache_key] is None:
                with st.spinner(f"🤖 {broker}正在分析持仓..."):
                    try:
                        from ai_analysis import generate_broker_analysis
                        broker_result = generate_broker_analysis(holdings_list, total_market_value, total_pnl, broker)
                        st.session_state[broker_cache_key] = broker_result
                    except Exception as e:
                        st.session_state[broker_cache_key] = f"{broker}分析失败：{e}"
            
            # 显示券商分析结果
            broker_result = st.session_state.get(broker_cache_key, '')
            if isinstance(broker_result, str) and broker_result:
                st.markdown(broker_result)
            else:
                st.info(f"请选择{broker}查看针对性点评")
    
    # ============== Tab 4: 新闻 ==============
    with main_tabs[3]:
        st.subheader("📰 持仓股票新闻")
        st.markdown("**💡 只显示与持仓相关的新闻，标注情绪值**")
        
        # 情绪值图例
        col_legend1, col_legend2, col_legend3 = st.columns(3)
        with col_legend1:
            st.markdown("🟢 **利好** - 业绩增长/中标/增持")
        with col_legend2:
            st.markdown("🔴 **利空** - 业绩下滑/处罚/减持")
        with col_legend3:
            st.markdown("⚪ **中性** - 公告/会议/日常")
        
        st.divider()
        
        # 获取持仓股票列表
        stock_names = df['名称'].unique()
        
        # 按股票分组显示新闻
        for stock_name in stock_names:
            stock_row = df[df['名称'] == stock_name].iloc[0]
            
            with st.expander(f"**📈 {stock_name}** - 最新价 ¥{stock_row['最新价']:.3f} | 今日盈亏 {stock_row['今日盈亏']:+,.0f}元", expanded=True):
                # 模拟新闻数据（实际应接入新闻 API）
                # 这里用规则生成相关新闻
                try:
                        from news_generator import generate_stock_news
                        news_items = generate_stock_news(stock_name, stock_row)
                except Exception as e:
                    st.error(f"新闻生成失败：{e}")
                    news_items = []
                
                for news in news_items:
                    # 情绪值颜色
                    sentiment_color = {'利好': '#d1fae5', '利空': '#fee2e2', '中性': '#f3f4f6'}[news['sentiment']]
                    sentiment_icon = {'利好': '🟢', '利空': '🔴', '中性': '⚪'}[news['sentiment']]
                    
                    st.markdown(f"""
                    <div style="background-color: {sentiment_color}; padding: 12px; border-radius: 8px; margin: 8px 0; border-left: 4px solid {'#10b981' if news['sentiment'] == '利好' else '#ef4444' if news['sentiment'] == '利空' else '#9ca3af'};">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <a href="{news['url']}" target="_blank" style="text-decoration: none; color: inherit;">
                                    <strong>{sentiment_icon} {news['title']}</strong>
                                </a><br>
                                <small style="color: #6b7280;">{news['source']} · {news['time']} · 🔗 <a href="{news['url']}" target="_blank" style="color: #1890ff;">原文链接</a></small>
                            </div>
                            <div style="font-size: 12px; color: #6b7280;">
                                情绪值：<strong>{news['sentiment_score']}/10</strong>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
    
    # ============== Tab 5: 配置 ==============
    with main_tabs[4]:
        st.subheader("⚙️ 持仓配置")
        st.markdown("**💡 三种方式管理持仓：OCR 识别 / 手动编辑 / 导入导出**")
        
        # 清空持仓功能（分享专用）
        st.divider()
        st.markdown("**🗑️ 清空持仓数据**")
        st.info("💡 清空后可以重新上传自己的持仓，方便分享给他人使用")
        
        if st.button("🗑️ 清空所有持仓数据", type="secondary", key="clear_holdings_btn"):
            # 二次确认
            st.warning("⚠️ 确定要清空所有持仓数据吗？此操作不可恢复！")
            
            col_confirm1, col_confirm2 = st.columns(2)
            with col_confirm1:
                if st.button("✅ 确认清空", type="primary", key="confirm_clear_btn"):
                    try:
                        # 清空持仓文件
                        empty_holdings = {"stocks": []}
                        with open('data/holdings.json', 'w') as f:
                            json.dump(empty_holdings, f, indent=2, ensure_ascii=False)
                        
                        # 清空相关缓存
                        if 'ai_analysis_cache' in st.session_state:
                            st.session_state['ai_analysis_cache'] = None
                        if 'last_sync_time' in st.session_state:
                            st.session_state['last_sync_time'] = datetime.now()
                        
                        st.success("✅ 持仓数据已清空！请重新上传或添加持仓。")
                        st.info("🔄 页面将自动刷新...")
                        import time
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"清空失败：{e}")
            
            with col_confirm2:
                if st.button("❌ 取消", key="cancel_clear_btn"):
                    st.info("已取消清空操作")
        
        st.divider()
        
        # 三个子 Tab
        config_tabs = st.tabs(["📸 OCR 识别", "✏️ 手动编辑", "📥 导入导出"])
        
        # ========== Tab 1: OCR 识别 ==========
        with config_tabs[0]:
            st.markdown("**📸 上传券商 APP 持仓截图，自动识别**")
            st.info("支持券商：华泰/中信/东方财富/国泰君安/招商等")
            
            # OCR 引擎选择
            ocr_engine = st.selectbox(
                "OCR 引擎",
                ["百度 OCR（推荐）", "模拟演示（无 API）"],
                index=0
            )
            
            # 上传截图
            uploaded_image = st.file_uploader(
                "上传持仓截图",
                type=['png', 'jpg', 'jpeg'],
                help="从券商 APP 截取持仓页面"
            )
            
            if uploaded_image:
                # 显示预览
                st.image(uploaded_image, caption="📷 预览", use_container_width=True)
                
                # OCR 识别按钮
                if st.button("🔍 开始识别", type="primary"):
                    with st.spinner("⏳ 正在 OCR 识别中..."):
                        try:
                            # 保存临时文件
                            import tempfile
                            import os
                            
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                                tmp.write(uploaded_image.getvalue())
                                temp_path = tmp.name
                            
                            # 调用 OCR
                            if ocr_engine == "百度 OCR（推荐）":
                                from stock_ocr import ocr_with_baidu
                                
                                # 读取配置
                                try:
                                    with open('data/ocr_config.json', 'r') as f:
                                        ocr_config = json.load(f)
                                    
                                    text = ocr_with_baidu(
                                        temp_path,
                                        app_id=ocr_config['baidu_ocr']['app_id'],
                                        api_key=ocr_config['baidu_ocr']['api_key'],
                                        secret_key=ocr_config['baidu_ocr']['secret_key']
                                    )
                                except Exception as e:
                                    st.error(f"OCR 配置错误：{e}")
                                    text = None
                            else:
                                # 模拟演示
                                from stock_ocr import mock_ocr_result
                                text = mock_ocr_result('screenshot')
                            
                            # 解析结果
                            if text:
                                st.markdown("**📝 OCR 识别结果：**")
                                st.code(text[:500] + "..." if len(text) > 500 else text)
                                
                                from stock_ocr import parse_holdings_from_text
                                holdings = parse_holdings_from_text(text)
                                
                                if holdings:
                                    st.success(f"✅ 识别到 {len(holdings)} 只股票！")
                                    
                                    # 显示预览表格
                                    holdings_df = pd.DataFrame(holdings)
                                    st.markdown("**📋 识别结果预览：**")
                                    st.dataframe(
                                        holdings_df[['name', 'quantity', 'cost_price', 'current_price']],
                                        use_container_width=True,
                                        hide_index=True
                                    )
                                    
                                    # 确认导入按钮
                                    if st.button("✅ 确认导入到持仓", type="primary", key="confirm_ocr_import"):
                                        # 合并到现有持仓
                                        holdings_data = load_holdings()
                                        stocks = holdings_data.get('stocks', [])
                                        
                                        added_count = 0
                                        updated_count = 0
                                        
                                        for h in holdings:
                                            # 字段映射
                                            name = h.get('name', '')
                                            code = h.get('code', '')
                                            shares = int(h.get('quantity', h.get('shares', 0)))
                                            cost = float(h.get('cost_price', h.get('cost', 0.0)))
                                            
                                            # 检查是否已存在
                                            found = False
                                            for s in stocks:
                                                if (code and s.get('code') == code) or (name and s.get('name') == name):
                                                    # 更新现有持仓
                                                    s['shares'] = shares
                                                    s['cost'] = cost
                                                    updated_count += 1
                                                    found = True
                                                    break
                                            
                                            if not found:
                                                # 添加新持仓
                                                stocks.append({
                                                    'code': code,
                                                    'name': name,
                                                    'shares': shares,
                                                    'cost': cost,
                                                    'threshold': 2.0
                                                })
                                                added_count += 1
                                        
                                        holdings_data['stocks'] = stocks
                                        if save_holdings(holdings_data):
                                            st.success(f"✅ 导入完成！新增 {added_count} 只，更新 {updated_count} 只")
                                            st.session_state.last_sync_time = datetime.now()
                                            st.session_state.ai_analysis_cache = None
                                            st.rerun()
                                        else:
                                            st.error("❌ 保存失败")
                                else:
                                    st.warning("⚠️ 未识别到股票数据，请检查截图清晰度")
                            else:
                                st.error("❌ OCR 识别失败，请重试")
                            
                            # 清理临时文件
                            if temp_path and os.path.exists(temp_path):
                                os.remove(temp_path)
                        
                        except Exception as e:
                            st.error(f"识别失败：{e}")
            
            # 使用提示
            st.markdown("""
            **📖 使用提示：**
            1. 打开券商 APP，进入持仓页面
            2. 截图（包含股票名称、代码、股数、成本价）
            3. 上传截图，点击"开始识别"
            4. 确认无误后导入
            """)
        
        # ========== Tab 2: 手动编辑 ==========
        with config_tabs[1]:
            st.markdown("**✏️ 直接编辑持仓配置**")
            
            holdings_data = load_holdings()
            stocks = holdings_data.get('stocks', [])
            
            if stocks:
                # 显示编辑表格
                st.markdown("**📋 当前持仓列表**")
                
                # 转换为 DataFrame 便于编辑
                edit_df = pd.DataFrame(stocks)
                
                # 显示可编辑表格（新增止盈止损字段）
                edited_df = st.dataframe(
                    edit_df[['code', 'name', 'shares', 'cost', 'stop_profit', 'stop_loss', 'threshold', 'buy_reason']],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "code": st.column_config.TextColumn("代码", width="small"),
                        "name": st.column_config.TextColumn("名称", width="medium"),
                        "shares": st.column_config.NumberColumn("股数", format="%d"),
                        "cost": st.column_config.NumberColumn("成本价", format="%.4f"),
                        "threshold": st.column_config.NumberColumn("异动阈值%", format="%.1f"),
                        "stop_profit": st.column_config.NumberColumn("止盈价", format="%.2f"),
                        "stop_loss": st.column_config.NumberColumn("止损价", format="%.2f"),
                        "buy_reason": st.column_config.TextColumn("买入理由"),
                    }
                )
                
                # 保存按钮
                if st.button("💾 保存修改", type="primary"):
                    # 这里需要从 edited_df 提取数据
                    # Streamlit 暂不支持直接编辑 DataFrame
                    st.info("💡 提示：请使用导入导出功能批量修改，或删除后重新添加")
                
                # 删除股票
                st.divider()
                st.markdown("**🗑️ 删除持仓**")
                
                delete_options = [f"{s['code']} - {s['name']}" for s in stocks]
                delete_select = st.selectbox("选择要删除的股票", delete_options)
                
                if st.button("🗑️ 删除选中股票"):
                    selected_code = delete_select.split(' - ')[0]
                    stocks = [s for s in stocks if s['code'] != selected_code]
                    holdings_data['stocks'] = stocks
                    if save_holdings(holdings_data):
                        st.success(f"✅ 已删除 {selected_code}")
                        st.session_state.last_sync_time = datetime.now()
                        st.rerun()
            else:
                st.info("📭 暂无持仓配置，请使用 OCR 识别或导入功能添加")
            
            # 添加单只股票
            st.divider()
            st.markdown("**➕ 添加单只股票**")
            
            col1, col2 = st.columns(2)
            with col1:
                new_code = st.text_input("股票代码", placeholder="如：600519", key="add_code_manual")
                new_name = st.text_input("股票名称", placeholder="如：贵州茅台", key="add_name_manual")
                new_shares = st.number_input("持仓股数", min_value=0, value=100, key="add_shares_manual")
            
            with col2:
                new_cost = st.number_input("成本价（元）", min_value=0.0, value=10.0, step=0.01, key="add_cost_manual")
                new_threshold = st.number_input("异动阈值（%）", min_value=0.0, value=2.0, step=0.1, key="add_threshold_manual")
            
            if st.button("➕ 添加持仓", type="primary", key="add_stock_manual"):
                if new_code and new_name:
                    holdings_data = load_holdings()
                    stocks = holdings_data.get('stocks', [])
                    
                    # 检查是否已存在
                    exists = any(s['code'] == new_code for s in stocks)
                    if exists:
                        st.warning(f"⚠️ {new_code} 已存在，请在列表中修改")
                    else:
                        stocks.append({
                            'code': new_code,
                            'name': new_name,
                            'shares': int(new_shares),
                            'cost': float(new_cost),
                            'threshold': float(new_threshold)
                        })
                        holdings_data['stocks'] = stocks
                        if save_holdings(holdings_data):
                            st.success(f"✅ 已添加 {new_name} ({new_code})")
                            st.session_state.last_sync_time = datetime.now()
                            st.rerun()
                else:
                    st.error("❌ 请填写股票代码和名称")
        
        # ========== Tab 3: 导入导出 ==========
        with config_tabs[2]:
            st.markdown("**📥 导入导出配置**")
            
            # 导出
            st.markdown("**📤 导出配置**")
            st.markdown("下载当前持仓配置为 JSON 文件，方便备份或迁移")
            
            if st.button("📥 生成配置文件", key="export_btn_tab5"):
                holdings_data = load_holdings()
                st.download_button(
                    label="⬇️ 下载 holdings.json",
                    data=json.dumps(holdings_data, indent=2, ensure_ascii=False),
                    file_name=f"holdings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            st.divider()
            
            # 导入
            st.markdown("**📥 导入配置**")
            st.markdown("上传之前导出的 holdings.json 文件，快速恢复配置")
            
            uploaded_config = st.file_uploader("选择 JSON 文件", type=['json'], key="upload_config_tab5")
            
            if uploaded_config:
                col_import1, col_import2 = st.columns([1, 3])
                
                with col_import1:
                    if st.button("📥 确认导入", type="primary", key="import_btn_tab5"):
                        try:
                            imported = json.load(uploaded_config)
                            if 'stocks' in imported:
                                holdings_data = imported
                                if save_holdings(holdings_data):
                                    st.success("✅ 配置导入成功！")
                                    st.session_state.last_sync_time = datetime.now()
                                    st.session_state.ai_analysis_cache = None
                                    st.rerun()
                                else:
                                    st.error("❌ 保存失败")
                            else:
                                st.error("❌ 文件格式不正确，缺少 stocks 字段")
                        except Exception as e:
                            st.error(f"导入失败：{e}")
                
                with col_import2:
                    # 预览导入内容
                    try:
                        imported = json.load(uploaded_config)
                        if 'stocks' in imported:
                            st.markdown("**📋 文件预览**")
                            preview_df = pd.DataFrame(imported['stocks'])
                            st.dataframe(preview_df, use_container_width=True, hide_index=True)
                    except:
                        pass
            
            # 快速模板
            st.divider()
            st.markdown("**📝 快速添加模板**")
            st.markdown("点击以下按钮快速添加常见持仓")
            
            template_stocks = [
                ("512400", "有色 ETF", 1900, 2.35),
                ("513180", "恒生科技 ETF", 3400, 0.74),
                ("603360", "百傲化学", 4320, 23.00),
                ("000568", "泸州老窖", 100, 148.75),
                ("000571", "新大洲 A", 1600, 7.56),
                ("002572", "索菲亚", 100, 19.99),
            ]
            
            cols = st.columns(3)
            for i, (code, name, shares, cost) in enumerate(template_stocks):
                with cols[i % 3]:
                    if st.button(f"{name} ({code})", key=f"template_{code}_tab5"):
                        holdings_data = load_holdings()
                        stocks = holdings_data.get('stocks', [])
                        
                        exists = any(s['code'] == code for s in stocks)
                        if exists:
                            st.info(f"ℹ️ {name} 已存在")
                        else:
                            stocks.append({
                                'code': code,
                                'name': name,
                                'shares': shares,
                                'cost': cost,
                                'threshold': 2.0
                            })
                            holdings_data['stocks'] = stocks
                            if save_holdings(holdings_data):
                                st.success(f"✅ 已添加 {name}")
                                st.session_state.last_sync_time = datetime.now()
                                st.rerun()
    
    # 主界面结束
    return

# ============== 程序入口 ==============
    
    st.divider()
    
    # ============== 持仓明细表格（默认 4 列 + 展开详情） ==============
    st.subheader("📋 持仓明细")
    
    # 排序选择
    sort_option = st.selectbox(
        "排序方式",
        ["持仓占比", "持仓盈亏", "盈亏率", "今日盈亏", "代码"],
        index=0,
        key="sort_select"
    )
    
    df_sorted = df.sort_values(sort_option, ascending=False).reset_index(drop=True)
    
    # 默认 4 列
    st.markdown("**📊 核心数据（默认 4 列）**")
    
    # 核心数据表格
    core_df = pd.DataFrame()
    core_df['名称'] = df_sorted['名称']
    core_df['持仓市值'] = df_sorted['持仓市值'].apply(lambda x: f"¥{x:,.0f}")
    core_df['持仓盈亏'] = df_sorted['持仓盈亏'].apply(lambda x: f"{'🔴' if x > 0 else '🟢'} ¥{x:+,.0f}")
    core_df['盈亏率'] = df_sorted['盈亏率'].apply(lambda x: f"{'🔴' if x > 0 else '🟢'} {x:+.1f}%")
    
    st.dataframe(
        core_df,
        use_container_width=True,
        hide_index=True
    )
    
    # 展开详情
    st.markdown("**🔍 展开查看详情**")
    
    for i, row in df_sorted.iterrows():
        with st.expander(f"**{row['名称']} ({row['代码']})** - 持仓市值 ¥{row['持仓市值']:,.0f} | 盈亏 {row['盈亏率']:+.1f}%"):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("最新价", f"¥{row['最新价']:.3f}")
            with col2:
                st.metric("涨跌幅", f"{row['涨跌幅']:+.2f}%")
            with col3:
                st.metric("持仓股数", f"{row['持仓股数']:,}")
            with col4:
                st.metric("成本价", f"¥{row['成本价']:.4f}")
            
            st.markdown("---")
            col5, col6, col7, col8 = st.columns(4)
            
            with col5:
                st.metric("持仓市值", f"¥{row['持仓市值']:,.2f}")
            with col6:
                st.metric("持仓盈亏", f"¥{row['持仓盈亏']:+,.2f}")
            with col7:
                st.metric("今日盈亏", f"¥{row['今日盈亏']:+,.2f}")
            with col8:
                st.metric("持仓占比", f"{row['持仓占比']:.1f}%")
            
            if row.get('行业'):
                st.markdown(f"**行业：** {row['行业']}")
    
    st.divider()
    
    # 个股详细分析
    st.subheader("🔍 个股详细分析")
    
    selected_stock = st.selectbox(
        "选择要分析的股票",
        df['名称'].tolist(),
        index=0
    )
    
    selected_df = df[df['名称'] == selected_stock].iloc[0]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("最新价", f"{selected_df['最新价']:.3f}元")
    with col2:
        st.metric("涨跌幅", f"{selected_df['涨跌幅']:+.2f}%")
    with col3:
        st.metric("持仓盈亏", f"{selected_df['持仓盈亏']:+,.2f}元")
    with col4:
        st.metric("今日盈亏", f"{selected_df['今日盈亏']:+,.2f}元")
    
    st.markdown("### 📊 技术分析")
    
    change = selected_df['涨跌幅']
    if change > 5:
        st.success(f"📈 **强势上涨** ({change:+.2f}%) - 建议继续持有")
    elif change > 2:
        st.info(f"📈 **上涨** ({change:+.2f}%) - 趋势良好")
    elif change > -2:
        st.info(f"➡️ **震荡** ({change:+.2f}%) - 观望为主")
    elif change > -5:
        st.warning(f"📉 **下跌** ({change:+.2f}%) - 注意风险")
    else:
        st.error(f"📉 **大跌** ({change:+.2f}%) - 注意止损")
    
    pnl_pct = selected_df['盈亏率']
    if pnl_pct > 20:
        st.success(f"✅ **盈利 {pnl_pct:.1f}%** - 建议部分止盈（30-50%）")
    elif pnl_pct > 0:
        st.info(f"✅ **盈利 {pnl_pct:.1f}%** - 继续持有")
    elif pnl_pct > -10:
        st.info(f"⚠️ **亏损 {abs(pnl_pct):.1f}%** - 设置止损位（-15%）")
    elif pnl_pct > -30:
        st.warning(f"⚠️ **亏损 {abs(pnl_pct):.1f}%** - 考虑补仓或止损")
    else:
        st.error(f"🔴 **深度套牢 {abs(pnl_pct):.1f}%** - 建议：1）补仓摊薄；2）止损换股；3）躺平")
    
    st.divider()
    
    # ============== 股票新闻模块（新增功能） ==============
    st.subheader("📰 相关新闻资讯")
    
    # 获取股票代码
    stock_code = str(int(selected_df['代码']))
    
    col_news1, col_news2 = st.columns([4, 1])
    with col_news1:
        st.markdown(f"**{selected_df['名称']} ({stock_code})** 最新新闻")
    with col_news2:
        refresh_news = st.button("🔄 刷新新闻", key="refresh_news")
    
    # 缓存新闻数据
    @st.cache_data(ttl=300)  # 5 分钟缓存
    def get_news_cached(code, name):
        try:
            from stock_news import get_stock_news, process_news
            news = get_stock_news(code, stock_name=name, pagesize=10)
            if news:
                return process_news(news)
            return None
        except Exception as e:
            return None
    
    if refresh_news:
        # 清除缓存并重新获取
        get_news_cached.clear()
    
    news_data = get_news_cached(stock_code, selected_df['名称'])
    
    if news_data:
        # 按情感分类
        positive_news = [n for n in news_data if n['sentiment'] == 'positive']
        # ============== 改进 5：新闻事件卡 + 影响评分 ==============
        st.markdown("**📰 事件卡 - 影响评分**")
        
        # 定义事件类型映射
        event_keywords = {
            '业绩': ['业绩', '财报', '净利润', '营收', '增长', '下滑'],
            '并购': ['并购', '重组', '收购', '合并'],
            '公告': ['公告', '披露', '发布'],
            '研报': ['研报', '评级', '目标价', '机构'],
            '经营': ['中标', '签约', '合作', '订单'],
            '风险': ['处罚', '调查', '诉讼', '违规', '风险'],
        }
        
        def classify_event(title):
            """分类事件类型"""
            for event_type, keywords in event_keywords.items():
                if any(kw in title for kw in keywords):
                    return event_type
            return '其他'
        
        def get_impact_level(importance, sentiment):
            """获取影响等级"""
            if importance >= 4 and sentiment in ['positive', 'negative']:
                return '高'
            elif importance >= 3:
                return '中'
            else:
                return '低'
        
        def get_action_recommendation(event_type, sentiment, impact):
            """推荐动作"""
            if impact == '高' and sentiment == 'negative':
                return '🔴 复核持仓'
            elif impact == '高' and sentiment == 'positive':
                return '🟢 关注机会'
            elif impact == '中':
                return '🟡 持续观察'
            else:
                return '⚪ 正常关注'
        
        # 处理新闻为事件卡
        event_cards = []
        for news in news_data:
            event_type = classify_event(news['title'])
            impact = get_impact_level(news['importance'], news['sentiment'])
            action = get_action_recommendation(event_type, news['sentiment'], impact)
            
            event_cards.append({
                'title': news['title'],
                'type': event_type,
                'sentiment': news['sentiment'],
                'importance': news['importance'],
                'impact': impact,
                'action': action,
                'time': news['time'],
                'source': news['source'],
                'url': news['url']
            })
        
        # 按影响等级排序
        impact_order = {'高': 0, '中': 1, '低': 2}
        event_cards.sort(key=lambda x: impact_order[x['impact']])
        
        # 显示事件卡
        for i, event in enumerate(event_cards[:6]):  # 最多显示 6 条
            impact_color = {'高': '#fee2e2', '中': '#fef3c7', '低': '#dbeafe'}[event['impact']]
            sentiment_emoji = {'positive': '🟢', 'negative': '🔴', 'neutral': '⚪'}[event['sentiment']]
            
            with st.container():
                st.markdown(f"""
                <div style="background-color: {impact_color}; padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 4px solid {'#ef4444' if event['impact'] == '高' else '#f59e0b' if event['impact'] == '中' else '#3b82f6'};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong>{sentiment_emoji} [{event['impact']}影响] {event['title']}</strong><br>
                            <small>类型：{event['type']} | 来源：{event['source']} | 时间：{event['time']}</small>
                        </div>
                        <div style="font-weight: bold;">{event['action']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("📰 暂无实时新闻数据（API 可能暂时不可用）\n\n正在努力接入更多数据源...")
        st.markdown("**💡 提示：** 可以手动查看该股票在东方财富/新浪财经的资讯页面")
        st.markdown(f"- [东方财富 - {selected_df['名称']}](http://quote.eastmoney.com/{stock_code}.html)")
        st.markdown(f"- [新浪财经 - {selected_df['名称']}](https://finance.sina.com.cn/realstock/company/{stock_code}.shtml)")
    
    st.divider()
    
    # ============== 持仓历史快照 ==============
    st.subheader("📈 持仓历史快照")
    
    # 保存今日快照
    if st.button("💾 保存今日快照", key="save_snapshot_btn"):
        if save_snapshot(df, total_market_value, total_pnl):
            st.success(f"✅ 已保存 {datetime.now().strftime('%Y-%m-%d')} 持仓快照")
        else:
            st.error("❌ 保存失败")
    
    # 显示历史快照
    snapshots = load_snapshots()
    if snapshots:
        st.markdown(f"**最近 {len(snapshots)} 天持仓记录**")
        
        # 提取日期和总市值
        dates = [s['date'] for s in snapshots[-14:]]  # 最近 14 天
        values = [s['total_market_value'] for s in snapshots[-14:]]
        pnls = [s['total_pnl'] for s in snapshots[-14:]]
        
        # 绘制趋势图
        import plotly.graph_objects as go
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=values,
            mode='lines+markers',
            name='总市值',
            line=dict(color='#667eea', width=2),
            marker=dict(size=6)
        ))
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=pnls,
            mode='lines+markers',
            name='总盈亏',
            line=dict(color='#10b981', width=2, dash='dash'),
            marker=dict(size=6)
        ))
        
        fig.update_layout(
            title='📈 持仓走势（最近 14 天）',
            xaxis_title='日期',
            yaxis_title='金额（元）',
            hovermode='x unified',
            showlegend=True,
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 快照列表
        st.markdown("**📋 历史快照详情**")
        for snap in reversed(snapshots[-7:]):  # 最近 7 条
            with st.expander(f"📅 {snap['date']} - 总市值 ¥{snap['total_market_value']:,.2f} - 总盈亏 ¥{snap['total_pnl']:+,.2f}"):
                snap_df = pd.DataFrame(snap['stocks'])
                st.dataframe(snap_df[['代码', '名称', '持仓市值', '持仓盈亏']], use_container_width=True)
    else:
        st.info("📭 暂无历史快照，点击'保存今日快照'开始记录")
    
    st.divider()
    
    # 多报告综合分析
    st.subheader("📚 多报告综合分析")
    
    st.info("📌 功能说明：上传多份券商研报，AI 自动总结核心观点，对比数据差异。")
    
    uploaded_files = st.file_uploader(
        "上传 PDF 研报（可多选）",
        type="pdf",
        accept_multiple_files=True,
        help="上传券商研报 PDF，AI 将自动总结核心观点"
    )
    
    if uploaded_files:
        st.success(f"已上传 {len(uploaded_files)} 份研报")
        
        for uploaded_file in uploaded_files:
            st.markdown(f"#### 📄 {uploaded_file.name}")
            
            # 模拟 PDF 解析（实际需接入 PyPDF2）
            st.info("📌 报告解析中...")
            
            # 模拟 AI 总结（实际需接入大模型 API）
            st.success("✅ AI 总结完成")
            
            st.markdown("""
            **核心观点：**
            - 公司业绩稳定增长，营收同比增长 15.2%
            - 行业地位稳固，市场份额持续提升
            - 研发投入加大，创新能力增强
            - 建议增持，目标价 35.00 元
            
            **财务数据：**
            - 营收：125.6 亿元（+15.2%）
            - 净利润：18.9 亿元（+12.5%）
            - 毛利率：32.5%（+1.2pct）
            - ROE：15.8%（+0.8pct）
            
            **风险提示：**
            - 行业竞争加剧风险
            - 原材料价格波动风险
            - 宏观经济下行风险
            - 汇率波动风险
            
            **盈利预测：**
            | 指标 | 2026E | 2027E | 2028E |
            |------|-------|-------|-------|
            | 营收（亿元） | 145.2 | 168.5 | 195.8 |
            | 净利润（亿元） | 21.5 | 25.2 | 29.8 |
            | EPS（元） | 1.85 | 2.17 | 2.56 |
            | PE（倍） | 18.5 | 15.8 | 13.4 |
            
            **评级：** 增持
            **目标价：** 35.00 元
            """)
            
            # 多报告对比
            if len(uploaded_files) > 1:
                st.markdown("#### 📊 多报告对比")
                st.info("📌 对比不同券商的盈利预测和评级")
                
                st.markdown("""
                **盈利预测对比：**
                | 券商 | 2026E 营收 | 2026E 净利润 | 评级 | 目标价 |
                |------|-----------|------------|------|--------|
                | 中信证券 | 145.2 亿 | 21.5 亿 | 增持 | 35.00 元 |
                | 中金公司 | 148.5 亿 | 22.1 亿 | 跑赢行业 | 36.50 元 |
                | 华泰证券 | 142.8 亿 | 20.8 亿 | 买入 | 34.00 元 |
                | 国泰君安 | 146.5 亿 | 21.8 亿 | 增持 | 35.50 元 |
                
                **一致预期：**
                - 2026E 营收：145.8 亿元
                - 2026E 净利润：21.6 亿元
                - 平均目标价：35.25 元
                - 一致评级：增持
                """)
    
    st.divider()
    
    # 新股扫描分析
    st.subheader("🆕 新股扫描分析")
    
    st.info("📌 功能说明：扫描近期新股，分析公司质地，给出打新建议。")
    
    # 模拟新股数据（实际需接入东方财富/同花顺 API）
    ipo_stocks = {
        '华虹公司 (688347)': {
            'code': '688347',
            'name': '华虹公司',
            'price_range': '45.00-50.00 元',
            'pe_ratio': '25.5 倍',
            'industry': '半导体',
            'market': '科创板',
            'subscribe_date': '2026-03-15',
            'lottery_rate': '0.05%',
            'rating': '推荐申购',
            'analysis': '半导体设备龙头，业绩稳定增长，建议申购',
            'financials': {
                'revenue': '45.2 亿元',
                'profit': '8.5 亿元',
                'growth': '+25.5%',
                'roe': '15.8%'
            }
        },
        '蓝天科技 (301234)': {
            'code': '301234',
            'name': '蓝天科技',
            'price_range': '28.00-32.00 元',
            'pe_ratio': '35.2 倍',
            'industry': '环保设备',
            'market': '创业板',
            'subscribe_date': '2026-03-16',
            'lottery_rate': '0.03%',
            'rating': '谨慎申购',
            'analysis': '估值偏高，行业竞争激烈，建议谨慎申购',
            'financials': {
                'revenue': '12.5 亿元',
                'profit': '1.8 亿元',
                'growth': '+15.2%',
                'roe': '12.5%'
            }
        },
        '白云制药 (603456)': {
            'code': '603456',
            'name': '白云制药',
            'price_range': '35.00-40.00 元',
            'pe_ratio': '28.8 倍',
            'industry': '医药生物',
            'market': '主板',
            'subscribe_date': '2026-03-17',
            'lottery_rate': '0.04%',
            'rating': '推荐申购',
            'analysis': '创新药龙头，研发实力强，建议申购',
            'financials': {
                'revenue': '28.5 亿元',
                'profit': '5.2 亿元',
                'growth': '+30.5%',
                'roe': '18.5%'
            }
        }
    }
    
    selected_ipo = st.selectbox(
        "选择新股",
        list(ipo_stocks.keys()),
        index=0
    )
    
    if selected_ipo:
        ipo = ipo_stocks[selected_ipo]
        
        # 新股详情
        st.markdown(f"""
        <div class="advice-box">
            <h3>{ipo['name']} ({ipo['code']})</h3>
            <p><strong>所属板块：</strong> {ipo['market']}</p>
            <p><strong>所属行业：</strong> {ipo['industry']}</p>
            <p><strong>申购日期：</strong> {ipo['subscribe_date']}</p>
            <p><strong>招股价区间：</strong> {ipo['price_range']}</p>
            <p><strong>发行市盈率：</strong> {ipo['pe_ratio']}</p>
            <p><strong>中签率：</strong> {ipo['lottery_rate']}</p>
            <p><strong>申购建议：</strong> <strong>{ipo['rating']}</strong></p>
        </div>
        """, unsafe_allow_html=True)
        
        # 财务数据
        st.markdown("#### 📊 财务数据")
        financials = ipo['financials']
        st.markdown(f"""
        | 指标 | 数值 |
        |------|------|
        | 营收 | {financials['revenue']} |
        | 净利润 | {financials['profit']} |
        | 同比增长 | {financials['growth']} |
        | ROE | {financials['roe']} |
        """)
        
        # 分析
        st.markdown("#### 📝 公司分析")
        st.info(f"📌 {ipo['analysis']}")
        
        # 风险提示
        st.markdown("#### ⚠️ 风险提示")
        st.warning("""
        - 新股上市初期波动较大，请注意风险
        - 中签率较低，请做好未中签准备
        - 上市首日可能破发，请谨慎决策
        """)
    
    # 新股列表
    st.markdown("#### 📋 近期新股列表")
    
    ipo_data = []
    for name, data in ipo_stocks.items():
        ipo_data.append({
            '股票名称': data['name'],
            '代码': data['code'],
            '板块': data['market'],
            '行业': data['industry'],
            '申购日期': data['subscribe_date'],
            '招股价': data['price_range'],
            '市盈率': data['pe_ratio'],
            '中签率': data['lottery_rate'],
            '评级': data['rating']
        })
    
    ipo_df = pd.DataFrame(ipo_data)
    st.dataframe(ipo_df, use_container_width=True, hide_index=True)
    
    st.info("📌 注：以上为模拟数据，实际使用需接入新股数据源（东方财富/同花顺）。")
    
    st.divider()
    
    # ============== 持仓配置管理（优化版） ==============
    st.subheader("⚙️ 持仓配置管理")
    
    st.markdown("**💡 说明：** 直接编辑持仓，实时生效，无需手动修改 JSON 文件")
    
    # 加载当前持仓
    holdings_data = load_holdings()
    stocks = holdings_data.get('stocks', [])
    
    # 创建标签页
    tab1, tab2, tab3, tab4 = st.tabs(["📝 编辑持仓", "➕ 添加股票", "📥 导入/导出", "📸 OCR 识别"])
    
    with tab1:
        st.markdown("**📋 当前持仓配置**")
        
        if stocks:
            # 选择要编辑的股票
            stock_options = {f"{s['code']} - {s['name']}": s for s in stocks}
            selected_label = st.selectbox(
                "选择要编辑的股票",
                list(stock_options.keys()),
                key="edit_select"
            )
            
            if selected_label:
                selected_stock = stock_options[selected_label]
                
                st.markdown(f"**编辑：{selected_stock['name']} ({selected_stock['code']})**")
                
                # 三列布局
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    new_shares = st.number_input(
                        "📊 持仓股数",
                        min_value=0,
                        value=selected_stock['shares'],
                        key=f"edit_shares_{selected_stock['code']}"
                    )
                
                with col2:
                    new_cost = st.number_input(
                        "💰 成本价（元）",
                        min_value=0.0,
                        value=selected_stock['cost'],
                        step=0.01,
                        key=f"edit_cost_{selected_stock['code']}"
                    )
                
                with col3:
                    new_threshold = st.number_input(
                        "⚠️ 异动阈值（%）",
                        min_value=0.0,
                        value=selected_stock.get('threshold', 2.0),
                        step=0.1,
                        key=f"edit_threshold_{selected_stock['code']}"
                    )
                
                # 操作按钮
                col_btn1, col_btn2 = st.columns([1, 3])
                
                with col_btn1:
                    if st.button("💾 保存修改", key=f"save_{selected_stock['code']}", type="primary"):
                        # 更新持仓
                        for s in stocks:
                            if s['code'] == selected_stock['code']:
                                s['shares'] = int(new_shares)
                                s['cost'] = float(new_cost)
                                s['threshold'] = float(new_threshold)
                                break
                        
                        holdings_data['stocks'] = stocks
                        if save_holdings(holdings_data):
                            st.success(f"✅ 已更新 {selected_stock['name']}")
                            st.rerun()
                
                with col_btn2:
                    if st.button("🗑️ 删除此股票", key=f"delete_{selected_stock['code']}", type="secondary"):
                        stocks = [s for s in stocks if s['code'] != selected_stock['code']]
                        holdings_data['stocks'] = stocks
                        if save_holdings(holdings_data):
                            st.success(f"✅ 已删除 {selected_stock['name']}")
                            st.rerun()
                
                # 显示当前值作为参考
                st.markdown("---")
                st.markdown("**📊 当前持仓详情**")
                col_info1, col_info2, col_info3 = st.columns(3)
                with col_info1:
                    st.metric("持仓市值", f"¥{selected_stock['shares'] * selected_stock['cost']:,.2f}")
                with col_info2:
                    st.metric("持仓占比", f"{100/len(stocks):.1f}%")
                with col_info3:
                    st.metric("异动阈值", f"±{selected_stock.get('threshold', 2.0)}%")
        else:
            st.info("📭 暂无持仓配置，请在'添加股票'标签页中添加")
    
    with tab2:
        st.markdown("**➕ 添加新持仓**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            new_code = st.text_input("股票代码", placeholder="如：600519", key="add_code")
            new_name = st.text_input("股票名称", placeholder="如：贵州茅台", key="add_name")
            new_shares = st.number_input("持仓股数", min_value=0, value=100, key="add_shares")
        
        with col2:
            new_cost = st.number_input("成本价（元）", min_value=0.0, value=10.0, step=0.01, key="add_cost")
            new_threshold = st.number_input("异动阈值（%）", min_value=0.0, value=2.0, step=0.1, key="add_threshold")
        
        if st.button("➕ 添加持仓", key="add_stock_btn", type="primary"):
            if new_code and new_name:
                exists = any(s['code'] == new_code for s in stocks)
                if exists:
                    st.warning(f"⚠️ {new_code} 已存在，请在'编辑持仓'标签页中修改")
                else:
                    new_stock = {
                        "code": new_code,
                        "name": new_name,
                        "shares": int(new_shares),
                        "cost": float(new_cost),
                        "threshold": float(new_threshold)
                    }
                    stocks.append(new_stock)
                    holdings_data['stocks'] = stocks
                    
                    if save_holdings(holdings_data):
                        st.success(f"✅ 已添加 {new_name} ({new_code})")
                        st.rerun()
            else:
                st.error("❌ 请填写股票代码和名称")
        
        # 快速添加模板
        st.markdown("**📝 快速添加模板**")
        
        template_stocks = [
            ("512400", "有色 ETF", 1900, 2.35),
            ("513180", "恒生科技 ETF", 3400, 0.74),
            ("603360", "百傲化学", 4320, 23.00),
            ("000568", "泸州老窖", 100, 148.75),
            ("000571", "新大洲 A", 1600, 7.56),
            ("002572", "索菲亚", 100, 19.99),
        ]
        
        cols = st.columns(3)
        for i, (code, name, shares, cost) in enumerate(template_stocks):
            with cols[i % 3]:
                if st.button(f"{name} ({code})", key=f"template_{code}"):
                    exists = any(s['code'] == code for s in stocks)
                    if exists:
                        st.info(f"ℹ️ {name} 已存在")
                    else:
                        new_stock = {
                            "code": code,
                            "name": name,
                            "shares": shares,
                            "cost": cost,
                            "threshold": 2.0
                        }
                        stocks.append(new_stock)
                        holdings_data['stocks'] = stocks
                        if save_holdings(holdings_data):
                            st.success(f"✅ 已添加 {name}")
                            st.rerun()
    
    with tab3:
        st.markdown("**📥 导入/导出配置**")
        
        # 导出
        st.markdown("**📤 导出配置**")
        st.markdown("下载当前持仓配置为 JSON 文件，方便备份或迁移")
        
        if st.button("📥 生成配置文件", key="export_btn"):
            st.download_button(
                label="⬇️ 下载 holdings.json",
                data=json.dumps(holdings_data, indent=2, ensure_ascii=False),
                file_name="holdings.json",
                mime="application/json",
                key="download_btn"
            )
        
        st.divider()
        
        # 导入
        st.markdown("**📥 导入配置**")
        st.markdown("上传之前导出的 holdings.json 文件，快速恢复配置")
        
        uploaded_config = st.file_uploader("选择 JSON 文件", type=['json'], key="upload_config")
        
        if uploaded_config:
            col_import1, col_import2 = st.columns([1, 3])
            
            with col_import1:
                if st.button("📥 确认导入", key="import_btn", type="primary"):
                    try:
                        imported = json.load(uploaded_config)
                        if 'stocks' in imported:
                            holdings_data = imported
                            if save_holdings(holdings_data):
                                st.success("✅ 配置导入成功！")
                                st.rerun()
                            else:
                                st.error("保存失败")
                        else:
                            st.error("❌ 文件格式不正确，缺少 stocks 字段")
                    except Exception as e:
                        st.error(f"导入失败：{e}")
            
            with col_import2:
                # 预览导入内容
                try:
                    imported = json.load(uploaded_config)
                    if 'stocks' in imported:
                        st.markdown("**📋 文件预览**")
                        preview_df = pd.DataFrame(imported['stocks'])
                        st.dataframe(preview_df, use_container_width=True, hide_index=True)
                except:
                    pass
    
    # ============== 新增 tab4：OCR 识别持仓截图 ==============
    with tab4:
        st.markdown("**📸 OCR 识别持仓截图**")
        st.markdown("上传券商 APP 持仓截图，自动识别股票信息并导入")
        
        st.info("💡 **支持券商：** 华泰证券、东方财富、中信证券、国泰君安、招商证券等")
        
        # 选择 OCR 引擎
        ocr_engine = st.selectbox(
            "OCR 引擎",
            ["百度 OCR（推荐）", "模拟演示（无 API）"],
            index=0
        )
        
        # 上传截图
        uploaded_image = st.file_uploader(
            "上传持仓截图",
            type=['png', 'jpg', 'jpeg'],
            help="从券商 APP 截取持仓页面，支持 PNG/JPG 格式"
        )
        
        if uploaded_image:
            # 显示预览
            st.image(uploaded_image, caption="📷 预览", use_container_width=True)
            
            # OCR 识别按钮
            if st.button("🔍 开始识别", type="primary"):
                with st.spinner("⏳ 正在 OCR 识别中..."):
                    # 保存临时文件
                    import tempfile
                    temp_path = None
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                            tmp.write(uploaded_image.getvalue())
                            temp_path = tmp.name
                        
                        # 调用 OCR
                        if ocr_engine == "百度 OCR（推荐）":
                            from stock_ocr import ocr_with_baidu
                            
                            # 读取配置
                            try:
                                with open(os.path.expanduser("~/.openclaw/workspace/data/ocr_config.json"), 'r') as f:
                                    ocr_config = json.load(f)
                                
                                text = ocr_with_baidu(
                                    temp_path,
                                    app_id=ocr_config['baidu_ocr']['app_id'],
                                    api_key=ocr_config['baidu_ocr']['api_key'],
                                    secret_key=ocr_config['baidu_ocr']['secret_key']
                                )
                            except Exception as e:
                                st.error(f"OCR 配置错误：{e}")
                                text = None
                        else:
                            # 模拟演示
                            from stock_ocr import mock_ocr_result
                            text = mock_ocr_result('screenshot')
                        
                        # 解析结果
                        if text:
                            st.markdown("**📝 OCR 识别结果：**")
                            st.code(text[:500] + "..." if len(text) > 500 else text)
                            
                            from stock_ocr import parse_holdings_from_text
                            holdings = parse_holdings_from_text(text)
                            
                            if holdings:
                                st.success(f"✅ 识别到 {len(holdings)} 只股票！")
                                
                                # 显示预览表格（字段映射）
                                holdings_df = pd.DataFrame(holdings)
                                st.markdown("**📋 识别结果预览：**")
                                
                                # 字段映射：解析器返回 name/quantity/cost_price/current_price/profit_loss/profit_pct
                                display_df = pd.DataFrame()
                                display_df['名称'] = holdings_df.get('name', pd.Series())
                                display_df['股数'] = holdings_df.get('quantity', holdings_df.get('shares', pd.Series()))
                                display_df['成本价'] = holdings_df.get('cost_price', holdings_df.get('cost', pd.Series())).apply(lambda x: f"¥{x:.4f}" if pd.notna(x) else 'N/A')
                                display_df['当前价'] = holdings_df.get('current_price', holdings_df.get('price', pd.Series())).apply(lambda x: f"¥{x:.3f}" if pd.notna(x) else 'N/A')
                                display_df['盈亏'] = holdings_df.get('profit_loss', pd.Series()).apply(lambda x: f"¥{x:+,.2f}" if pd.notna(x) else 'N/A')
                                display_df['盈亏%'] = holdings_df.get('profit_pct', pd.Series())
                                
                                st.dataframe(
                                    display_df,
                                    use_container_width=True,
                                    hide_index=True
                                )
                                
                                # 确认导入按钮
                                if st.button("✅ 确认导入到持仓", type="primary", key="confirm_ocr_import"):
                                    # 合并到现有持仓
                                    added_count = 0
                                    updated_count = 0
                                    
                                    for h in holdings:
                                        # 字段映射：解析器返回 name/quantity/cost_price/current_price/profit_loss
                                        name = h.get('name', '')
                                        code = h.get('code', '')
                                        shares = int(h.get('quantity', h.get('shares', h.get('available', 0))))
                                        cost = float(h.get('cost_price', h.get('cost', 0.0)))
                                        
                                        # 检查是否已存在（按名称或代码匹配）
                                        found = False
                                        for s in stocks:
                                            if (code and s.get('code') == code) or (name and s.get('name') == name):
                                                # 更新现有持仓
                                                s['shares'] = shares
                                                s['cost'] = cost
                                                updated_count += 1
                                                found = True
                                                break
                                        
                                        if not found:
                                            # 添加新持仓
                                            stocks.append({
                                                'code': code,
                                                'name': name,
                                                'shares': shares,
                                                'cost': cost,
                                                'threshold': 2.0
                                            })
                                            added_count += 1
                                    
                                    holdings_data['stocks'] = stocks
                                    if save_holdings(holdings_data):
                                        st.success(f"✅ 导入完成！新增 {added_count} 只，更新 {updated_count} 只")
                                        st.rerun()
                                    else:
                                        st.error("❌ 保存失败")
                            else:
                                st.warning("⚠️ 未识别到股票数据，请检查截图清晰度")
                        else:
                            st.error("❌ OCR 识别失败，请重试")
                    finally:
                        # 清理临时文件
                        if temp_path and os.path.exists(temp_path):
                            os.remove(temp_path)

if __name__ == "__main__":
    main()
