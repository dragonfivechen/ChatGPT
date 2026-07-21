#!/usr/bin/env python3
"""
🔥 燃期货 v0.1-LEGACY — 存档保留

状态: 🔒 FROZEN | 2026-07-21

此文件标记为 LEGACY，不继续堆功能。
期货验证环境请见 workspace/market_futures/ (Futures-Sim)。

原描述:
🔥 燃期货 v1.0 — 拟真期货交易模拟系统
龙哥的深夜交易 simulator 💹

Usage:
    python3 futures_sim.py

Commands (交互式):
    list/ls             查看所有品种行情
    view <code>         查看品种详情+K线
    buy <code> <手数>   开多
    sell <code> <手数>  开空
    close <code> <手数> 平多
    cover <code> <手数> 平空
    pos/positions       查看持仓
    acc/account         查看账户
    order <id>          查看订单详情
    history/hist        交易历史
    cancel <id>         撤销挂单
    sl <code> <价>      设置止损
    tp <code> <价>      设置止盈
    reset               重置账户(100万)
    help/?              帮助
    quit/q/exit         退出
"""

import os
import sys
import json
import time
import random
import math
import threading
from datetime import datetime
from collections import deque

# ─── 颜色定义 ───
C = {
    'R': '\033[91m',    # 红(跌)
    'G': '\033[92m',    # 绿(涨)
    'Y': '\033[93m',    # 黄
    'B': '\033[94m',    # 蓝
    'M': '\033[95m',    # 紫
    'C': '\033[96m',    # 青
    'W': '\033[97m',    # 白
    'N': '\033[0m',     # 重置
    'BOLD': '\033[1m',
    'DIM': '\033[2m',
}

# ─── 品种配置 ───
CONTRACTS = {
    'RB':  {'name': '螺纹钢', 'exchange': '上期所', 'mult': 10,   'margin': 0.10, 'tick': 1,    'tv': 10,   'comm': 0.00005, 'base': 3300, 'vol': 25,  'hour': '日盘+夜盘'},
    'I':   {'name': '铁矿石', 'exchange': '大商所', 'mult': 100,  'margin': 0.12, 'tick': 0.5,  'tv': 50,   'comm': 0.00005, 'base': 800,  'vol': 15,  'hour': '日盘+夜盘'},
    'SC':  {'name': '原油',   'exchange': '上期所', 'mult': 1000, 'margin': 0.10, 'tick': 0.1,  'tv': 100,  'comm': 0.00005, 'base': 520,  'vol': 8,   'hour': '日盘+夜盘'},
    'CU':  {'name': '沪铜',   'exchange': '上期所', 'mult': 5,    'margin': 0.08, 'tick': 10,   'tv': 50,   'comm': 0.00005, 'base': 68000,'vol': 500, 'hour': '日盘+夜盘'},
    'AU':  {'name': '沪金',   'exchange': '上期所', 'mult': 1000, 'margin': 0.08, 'tick': 0.02, 'tv': 20,   'comm': 0.00005, 'base': 450,  'vol': 3,   'hour': '日盘+夜盘'},
    'AG':  {'name': '沪银',   'exchange': '上期所', 'mult': 15,   'margin': 0.10, 'tick': 1,    'tv': 15,   'comm': 0.00005, 'base': 5800, 'vol': 40,  'hour': '日盘+夜盘'},
    'RU':  {'name': '橡胶',   'exchange': '上期所', 'mult': 10,   'margin': 0.10, 'tick': 5,    'tv': 50,   'comm': 0.00005, 'base': 13500,'vol': 120, 'hour': '日盘'},
    'M':   {'name': '豆粕',   'exchange': '大商所', 'mult': 10,   'margin': 0.08, 'tick': 1,    'tv': 10,   'comm': 0.00005, 'base': 3100, 'vol': 20,  'hour': '日盘+夜盘'},
    'P':   {'name': '棕榈油', 'exchange': '大商所', 'mult': 10,   'margin': 0.10, 'tick': 2,    'tv': 20,   'comm': 0.00005, 'base': 7800, 'vol': 50,  'hour': '日盘+夜盘'},
    'TA':  {'name': 'PTA',    'exchange': '郑商所', 'mult': 5,    'margin': 0.08, 'tick': 2,    'tv': 10,   'comm': 0.00005, 'base': 5200, 'vol': 40,  'hour': '日盘+夜盘'},
    'MA':  {'name': '甲醇',   'exchange': '郑商所', 'mult': 10,   'margin': 0.10, 'tick': 1,    'tv': 10,   'comm': 0.00005, 'base': 2200, 'vol': 18,  'hour': '日盘+夜盘'},
    'FG':  {'name': '玻璃',   'exchange': '郑商所', 'mult': 20,   'margin': 0.10, 'tick': 1,    'tv': 20,   'comm': 0.00005, 'base': 1400, 'vol': 12,  'hour': '日盘+夜盘'},
    'ZC':  {'name': '动力煤', 'exchange': '郑商所', 'mult': 100,  'margin': 0.12, 'tick': 0.2,  'tv': 20,   'comm': 0.00005, 'base': 750,  'vol': 10,  'hour': '日盘'},
    'HC':  {'name': '热卷',   'exchange': '上期所', 'mult': 10,   'margin': 0.10, 'tick': 1,    'tv': 10,   'comm': 0.00005, 'base': 3500, 'vol': 22,  'hour': '日盘+夜盘'},
    'SN':  {'name': '沪锡',   'exchange': '上期所', 'mult': 1,    'margin': 0.10, 'tick': 10,   'tv': 10,   'comm': 0.00005, 'base': 220000,'vol': 2000,'hour': '日盘+夜盘'},
}

DATA_FILE = os.path.expanduser('~/.openclaw/workspace/.futures_data.json')

# ─── 行情引擎 ───
class MarketEngine:
    def __init__(self):
        self.prices = {}       # code -> current price
        self.opens = {}        # code -> today open
        self.highs = {}        # code -> today high
        self.lows = {}         # code -> today low
        self.prev_close = {}   # code -> yesterday close
        self.volume = {}       # code -> today volume
        self.oi = {}           # code -> open interest
        self.kline = {}        # code -> deque of (time, price, vol)
        self._running = True
        self._lock = threading.Lock()
        
        for code, cfg in CONTRACTS.items():
            base = cfg['base']
            noise = random.uniform(-cfg['vol'], cfg['vol'])
            self.prices[code] = base + noise
            self.opens[code] = self.prices[code]
            self.highs[code] = self.prices[code]
            self.lows[code] = self.prices[code]
            self.prev_close[code] = base
            self.volume[code] = 0
            self.oi[code] = random.randint(100000, 500000)
            self.kline[code] = deque(maxlen=240)  # 240 ticks
            self.kline[code].append((time.time(), self.prices[code], 0))
        
        # 启动行情线程
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
    
    def _run(self):
        """后台行情更新线程——每个品种随机波动"""
        while self._running:
            time.sleep(2 + random.random())  # 2-3秒更新一次
            with self._lock:
                for code, cfg in CONTRACTS.items():
                    vol_ratio = cfg['vol'] / cfg['base']
                    # 带趋势和均值回归的随机游走
                    center = self.prev_close[code]
                    drift = (center - self.prices[code]) * 0.002  # 均值回归力
                    shock = random.gauss(0, cfg['vol'] * 0.3)     # 随机冲击
                    change = drift + shock
                    
                    new_price = self.prices[code] + change
                    # 限制涨跌幅 (5%)
                    limit = self.prev_close[code] * 0.05
                    new_price = max(self.prev_close[code] - limit, min(self.prev_close[code] + limit, new_price))
                    # 保持在tick整数倍
                    tick = cfg['tick']
                    new_price = round(new_price / tick) * tick
                    
                    self.prices[code] = new_price
                    self.highs[code] = max(self.highs[code], new_price)
                    self.lows[code] = min(self.lows[code], new_price)
                    
                    # 模拟成交量
                    v = random.randint(100, 5000)
                    self.volume[code] += v
                    self.kline[code].append((time.time(), new_price, v))
    
    def get_price(self, code):
        with self._lock:
            return self.prices.get(code, 0)
    
    def get_snapshot(self, code):
        with self._lock:
            p = self.prices.get(code, 0)
            return {
                'price': p,
                'open': self.opens.get(code, p),
                'high': self.highs.get(code, p),
                'low': self.lows.get(code, p),
                'prev_close': self.prev_close.get(code, p),
                'volume': self.volume.get(code, 0),
                'oi': self.oi.get(code, 0),
                'change': p - self.prev_close.get(code, p),
                'change_pct': (p - self.prev_close.get(code, p)) / self.prev_close.get(code, p) * 100 if self.prev_close.get(code, p) else 0
            }
    
    def get_all_snapshots(self):
        return {code: self.get_snapshot(code) for code in CONTRACTS}
    
    def stop(self):
        self._running = False

# ─── 交易系统 ───
class TradeEngine:
    def __init__(self, market):
        self.market = market
        self.balance = 1_000_000.0
        self.positions = {}    # code -> {direction, qty, avg_price}
        self.orders = []       # 挂单
        self.trades = []       # 已成交历史
        self.order_id = 0
        self.stops = {}        # code -> {sl_price, tp_price} (per position)
    
    @property
    def margin_used(self):
        total = 0.0
        for code, pos in self.positions.items():
            if code in CONTRACTS:
                cfg = CONTRACTS[code]
                price = self.market.get_price(code)
                total += price * cfg['mult'] * pos['qty'] * cfg['margin']
        return total
    
    @property
    def floating_pnl(self):
        total = 0.0
        for code, pos in self.positions.items():
            if code in CONTRACTS:
                cfg = CONTRACTS[code]
                price = self.market.get_price(code)
                if pos['direction'] == 'long':
                    total += (price - pos['avg_price']) * cfg['mult'] * pos['qty']
                else:
                    total += (pos['avg_price'] - price) * cfg['mult'] * pos['qty']
        return total
    
    @property
    def equity(self):
        return self.balance + self.floating_pnl
    
    @property
    def available(self):
        return self.equity - self.margin_used
    
    def open_position(self, code, direction, qty):
        """开仓"""
        if code not in CONTRACTS:
            return False, f"未知品种: {code}"
        cfg = CONTRACTS[code]
        price = self.market.get_price(code)
        
        # 计算保证金
        margin_needed = price * cfg['mult'] * qty * cfg['margin']
        commission = price * cfg['mult'] * qty * cfg['comm']
        
        total_cost = margin_needed + commission
        if total_cost > self.equity:
            return False, f"权益不足！需 ¥{total_cost:.2f}(保证金¥{margin_needed:.2f}+手续费¥{commission:.2f})，当前权益 ¥{self.equity:.2f}"
        
        # 执行开仓
        self.balance -= commission
        
        if code in self.positions:
            pos = self.positions[code]
            if pos['direction'] == direction:
                # 同向加仓，加权均价
                old_cost = pos['avg_price'] * pos['qty']
                new_cost = price * qty
                pos['qty'] += qty
                pos['avg_price'] = (old_cost + new_cost) / pos['qty']
            else:
                # 反向——先平再开
                return self._reverse_position(code, direction, qty, price, cfg)
        else:
            self.positions[code] = {
                'direction': direction,
                'qty': qty,
                'avg_price': price
            }
        
        self.order_id += 1
        trade = {
            'id': self.order_id,
            'time': datetime.now().strftime('%H:%M:%S'),
            'code': code,
            'action': f'开{direction}',
            'qty': qty,
            'price': price,
            'commission': commission,
            'pnl': 0
        }
        self.trades.append(trade)
        
        return True, f"✅ 开仓成功！{cfg['name']}({code}) 开{'多' if direction == 'long' else '空'} {qty}手 @ ¥{price:.2f}，手续费 ¥{commission:.2f}"
    
    def _reverse_position(self, code, direction, qty, price, cfg):
        """反向开仓：先平现有仓位，多余部分开新仓"""
        pos = self.positions[code]
        
        if pos['qty'] > qty:
            # 部分平仓
            pnl = (price - pos['avg_price']) * cfg['mult'] * qty if pos['direction'] == 'long' else (pos['avg_price'] - price) * cfg['mult'] * qty
            commission = price * cfg['mult'] * qty * cfg['comm']
            self.balance += pnl - commission
            pos['qty'] -= qty
            
            self.order_id += 1
            self.trades.append({
                'id': self.order_id,
                'time': datetime.now().strftime('%H:%M:%S'),
                'code': code,
                'action': f'平{pos["direction"]}',
                'qty': qty,
                'price': price,
                'commission': commission,
                'pnl': pnl
            })
            return True, f"🔄 反向平仓 {qty}手 @ ¥{price:.2f}，盈亏 ¥{pnl:.2f}，手续费 ¥{commission:.2f}"
        
        elif pos['qty'] == qty:
            # 全部平仓
            pnl = (price - pos['avg_price']) * cfg['mult'] * qty if pos['direction'] == 'long' else (pos['avg_price'] - price) * cfg['mult'] * qty
            commission = price * cfg['mult'] * qty * cfg['comm']
            self.balance += pnl - commission
            del self.positions[code]
            
            self.order_id += 1
            self.trades.append({
                'id': self.order_id,
                'time': datetime.now().strftime('%H:%M:%S'),
                'code': code,
                'action': f'平{pos["direction"]}',
                'qty': qty,
                'price': price,
                'commission': commission,
                'pnl': pnl
            })
            return True, f"🔄 全部平仓 {qty}手 @ ¥{price:.2f}，盈亏 ¥{pnl:.2f}，手续费 ¥{commission:.2f}"
        
        else:
            # 平掉全部，多余开新仓
            pnl = (price - pos['avg_price']) * cfg['mult'] * pos['qty'] if pos['direction'] == 'long' else (pos['avg_price'] - price) * cfg['mult'] * pos['qty']
            close_comm = price * cfg['mult'] * pos['qty'] * cfg['comm']
            self.balance += pnl - close_comm
            
            remaining = qty - pos['qty']
            open_comm = price * cfg['mult'] * remaining * cfg['comm']
            self.balance -= open_comm
            
            self.positions[code] = {
                'direction': direction,
                'qty': remaining,
                'avg_price': price
            }
            
            self.order_id += 1
            self.trades.append({
                'id': self.order_id,
                'time': datetime.now().strftime('%H:%M:%S'),
                'code': code,
                'action': f'平{pos["direction"]}+开{direction}',
                'qty': pos['qty'],
                'price': price,
                'commission': close_comm + open_comm,
                'pnl': pnl
            })
            return True, f"🔄 平仓 {pos['qty']}手(盈亏¥{pnl:.2f})，开仓 {remaining}手 @ ¥{price:.2f}"
    
    def close_position(self, code, qty=None):
        """平多仓"""
        if code not in self.positions:
            return False, f"无 {code} 持仓"
        pos = self.positions[code]
        if pos['direction'] != 'long':
            return False, f"{CONTRACTS[code]['name']}({code}) 当前为空仓，请用 cover 平空"
        
        cfg = CONTRACTS[code]
        price = self.market.get_price(code)
        close_qty = qty if qty and qty <= pos['qty'] else pos['qty']
        
        pnl = (price - pos['avg_price']) * cfg['mult'] * close_qty
        commission = price * cfg['mult'] * close_qty * cfg['comm']
        self.balance += pnl - commission
        
        if close_qty >= pos['qty']:
            del self.positions[code]
        else:
            pos['qty'] -= close_qty
        
        self.order_id += 1
        self.trades.append({
            'id': self.order_id,
            'time': datetime.now().strftime('%H:%M:%S'),
            'code': code,
            'action': '平多',
            'qty': close_qty,
            'price': price,
            'commission': commission,
            'pnl': pnl
        })
        
        emoji = '💰' if pnl >= 0 else '💸'
        return True, f"{emoji} 平多 {close_qty}手 @ ¥{price:.2f}，盈亏 ¥{pnl:.2f}，手续费 ¥{commission:.2f}"
    
    def cover_position(self, code, qty=None):
        """平空仓"""
        if code not in self.positions:
            return False, f"无 {code} 持仓"
        pos = self.positions[code]
        if pos['direction'] != 'short':
            return False, f"{CONTRACTS[code]['name']}({code}) 当前为多仓，请用 close 平多"
        
        cfg = CONTRACTS[code]
        price = self.market.get_price(code)
        close_qty = qty if qty and qty <= pos['qty'] else pos['qty']
        
        pnl = (pos['avg_price'] - price) * cfg['mult'] * close_qty
        commission = price * cfg['mult'] * close_qty * cfg['comm']
        self.balance += pnl - commission
        
        if close_qty >= pos['qty']:
            del self.positions[code]
        else:
            pos['qty'] -= close_qty
        
        self.order_id += 1
        self.trades.append({
            'id': self.order_id,
            'time': datetime.now().strftime('%H:%M:%S'),
            'code': code,
            'action': '平空',
            'qty': close_qty,
            'price': price,
            'commission': commission,
            'pnl': pnl
        })
        
        emoji = '💰' if pnl >= 0 else '💸'
        return True, f"{emoji} 平空 {close_qty}手 @ ¥{price:.2f}，盈亏 ¥{pnl:.2f}，手续费 ¥{commission:.2f}"
    
    def check_stops(self):
        """检查止损止盈"""
        triggered = []
        for code in list(self.stops.keys()):
            if code not in self.positions:
                del self.stops[code]
                continue
            pos = self.positions[code]
            price = self.market.get_price(code)
            stop = self.stops[code]
            cfg = CONTRACTS[code]
            
            should_close = False
            reason = ''
            
            if pos['direction'] == 'long':
                if 'sl' in stop and price <= stop['sl']:
                    should_close = True
                    reason = f'止损触发(¥{stop["sl"]:.2f})'
                elif 'tp' in stop and price >= stop['tp']:
                    should_close = True
                    reason = f'止盈触发(¥{stop["tp"]:.2f})'
            else:
                if 'sl' in stop and price >= stop['sl']:
                    should_close = True
                    reason = f'止损触发(¥{stop["sl"]:.2f})'
                elif 'tp' in stop and price <= stop['tp']:
                    should_close = True
                    reason = f'止盈触发(¥{stop["tp"]:.2f})'
            
            if should_close:
                pnl = 0
                if pos['direction'] == 'long':
                    pnl = (price - pos['avg_price']) * cfg['mult'] * pos['qty']
                else:
                    pnl = (pos['avg_price'] - price) * cfg['mult'] * pos['qty']
                commission = price * cfg['mult'] * pos['qty'] * cfg['comm']
                self.balance += pnl - commission
                
                self.order_id += 1
                self.trades.append({
                    'id': self.order_id,
                    'time': datetime.now().strftime('%H:%M:%S'),
                    'code': code,
                    'action': f'强平({reason})',
                    'qty': pos['qty'],
                    'price': price,
                    'commission': commission,
                    'pnl': pnl
                })
                
                triggered.append((code, pos['qty'], reason, pnl))
                del self.positions[code]
                del self.stops[code]
        
        return triggered
    
    def check_liquidation(self):
        """检查强平"""
        if self.available < 0:
            # 找个持仓最大的强平
            max_pos = None
            max_val = 0
            for code, pos in self.positions.items():
                cfg = CONTRACTS[code]
                price = self.market.get_price(code)
                val = price * cfg['mult'] * pos['qty']
                if val > max_val:
                    max_val = val
                    max_pos = (code, pos)
            
            if max_pos:
                code, pos = max_pos
                cfg = CONTRACTS[code]
                price = self.market.get_price(code)
                pnl = 0
                if pos['direction'] == 'long':
                    pnl = (price - pos['avg_price']) * cfg['mult'] * pos['qty']
                else:
                    pnl = (pos['avg_price'] - price) * cfg['mult'] * pos['qty']
                commission = price * cfg['mult'] * pos['qty'] * cfg['comm']
                self.balance += pnl - commission
                
                self.order_id += 1
                self.trades.append({
                    'id': self.order_id,
                    'time': datetime.now().strftime('%H:%M:%S'),
                    'code': code,
                    'action': '⚠️强平',
                    'qty': pos['qty'],
                    'price': price,
                    'commission': commission,
                    'pnl': pnl
                })
                
                name = CONTRACTS[code]['name']
                del self.positions[code]
                if code in self.stops:
                    del self.stops[code]
                
                return True, f"🚨 强平！{name}({code}) {pos['qty']}手，盈亏 ¥{pnl:.2f}"
        return False, None
    
    def set_stop(self, code, price, stop_type='sl'):
        """设置止损止盈"""
        if code not in self.positions:
            return False, f"无 {code} 持仓"
        if code not in self.stops:
            self.stops[code] = {}
        self.stops[code][stop_type] = price
        
        name = CONTRACTS[code]['name']
        label = '止损' if stop_type == 'sl' else '止盈'
        return True, f"📌 {name}({code}) {label} 已设置 @ ¥{price:.2f}"
    
    def reset(self):
        self.balance = 1_000_000.0
        self.positions.clear()
        self.orders.clear()
        self.stops.clear()
        return "🔄 账户已重置，初始资金 ¥1,000,000"

# ─── UI 渲染 ───
class UI:
    def __init__(self, market, trade):
        self.market = market
        self.trade = trade
    
    def color_pct(self, pct):
        return f"{C['G']}{pct:+.2f}%{C['N']}" if pct >= 0 else f"{C['R']}{pct:+.2f}%{C['N']}"
    
    def color_price(self, change):
        return C['G'] if change >= 0 else C['R']
    
    def arrow(self, change):
        return '↑' if change >= 0 else '↓'
    
    def render_header(self):
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lines = [
            f"{C['BOLD']}{C['Y']}╔══════════════════════════════════════════════════╗{C['N']}",
            f"{C['BOLD']}{C['Y']}║{C['N']}    🔥 燃期货 v1.0 — 模拟交易系统 {C['DIM']}{now}{C['N']}    {C['BOLD']}{C['Y']}║{C['N']}",
            f"{C['BOLD']}{C['Y']}╚══════════════════════════════════════════════════╝{C['N']}",
        ]
        return '\n'.join(lines)
    
    def render_account(self):
        eq = self.trade.equity
        bal = self.trade.balance
        mg = self.trade.margin_used
        avail = self.trade.available
        fl = self.trade.floating_pnl
        init = 1_000_000
        total_pnl = eq - init
        total_pnl_pct = (eq - init) / init * 100
        
        eq_color = C['G'] if eq >= init else C['R']
        fl_color = C['G'] if fl >= 0 else C['R']
        avail_color = C['G'] if avail >= 0 else C['R']
        
        lines = [
            f"\n{C['BOLD']}📊 账户概览{C['N']}",
            f"{'─' * 50}",
            f"  期初权益:  ¥{init:<10,.2f}  │  当前权益:  {eq_color}¥{eq:<10,.2f}{C['N']}",
            f"  余额:      ¥{bal:<10,.2f}  │  浮动盈亏:  {fl_color}¥{fl:<10,.2f}{C['N']}",
            f"  保证金:    ¥{mg:<10,.2f}  │  可用资金:  {avail_color}¥{avail:<10,.2f}{C['N']}",
            f"  总盈亏:    {self.color_pct(total_pnl_pct)} ({'💰' if total_pnl >= 0 else '💸'}¥{total_pnl:,.2f})",
            f"  持仓品种:  {len(self.trade.positions)} 个",
        ]
        return '\n'.join(lines)
    
    def render_positions(self):
        if not self.trade.positions:
            return f"\n{C['DIM']}暂无持仓{C['N']}"
        
        lines = [f"\n{C['BOLD']}📋 当前持仓{C['N']}", f"{'─' * 70}"]
        lines.append(f"  {'品种':<8} {'方向':<6} {'手数':<6} {'开仓价':<10} {'现价':<10} {'盈亏':<12} {'盈亏%':<8}")
        lines.append(f"  {'─' * 8} {'─' * 6} {'─' * 6} {'─' * 10} {'─' * 10} {'─' * 12} {'─' * 8}")
        
        for code, pos in self.trade.positions.items():
            cfg = CONTRACTS.get(code)
            if not cfg: continue
            price = self.market.get_price(code)
            
            if pos['direction'] == 'long':
                pnl = (price - pos['avg_price']) * cfg['mult'] * pos['qty']
            else:
                pnl = (pos['avg_price'] - price) * cfg['mult'] * pos['qty']
            
            pnl_pct = (price - pos['avg_price']) / pos['avg_price'] * 100 if pos['direction'] == 'long' else (pos['avg_price'] - price) / pos['avg_price'] * 100
            pnl_c = C['G'] if pnl >= 0 else C['R']
            dir_s = f"{C['R']}空{C['N']}" if pos['direction'] == 'short' else f"{C['G']}多{C['N']}"
            
            # 止损止盈标记
            sltp = ''
            if code in self.trade.stops:
                s = self.trade.stops[code]
                if 'sl' in s: sltp += f" SL¥{s['sl']:.0f}"
                if 'tp' in s: sltp += f" TP¥{s['tp']:.0f}"
            
            lines.append(f"  {cfg['name']:<8} {dir_s:<6} {pos['qty']:<6} ¥{pos['avg_price']:<8,.2f} ¥{price:<8,.2f} {pnl_c}¥{pnl:<+8,.0f}{C['N']} {pnl_c}{pnl_pct:<+7.2f}%{C['N']}{C['DIM']}{sltp}{C['N']}")
        
        return '\n'.join(lines)
    
    def render_market(self, codes=None):
        snaps = self.market.get_all_snapshots()
        if codes:
            snaps = {c: snaps[c] for c in codes if c in snaps}
        
        lines = [f"\n{C['BOLD']}📈 实时行情{C['N']}", f"{'─' * 75}"]
        lines.append(f"  {'代码':<6} {'品种':<8} {'最新价':<10} {'涨跌':<12} {'涨幅':<9} {'最高':<10} {'最低':<10} {'成交量':<8}")
        lines.append(f"  {'─' * 6} {'─' * 8} {'─' * 10} {'─' * 12} {'─' * 9} {'─' * 10} {'─' * 10} {'─' * 8}")
        
        for code, s in snaps.items():
            cfg = CONTRACTS[code]
            chg = s['change']
            color = self.color_price(chg)
            arrow = self.arrow(chg)
            vol_str = f"{s['volume'] / 10000:.0f}万" if s['volume'] > 10000 else str(s['volume'])
            lines.append(f"  {code:<6} {cfg['name']:<8} {color}¥{s['price']:<8,.2f}{C['N']} {color}{arrow} ¥{abs(chg):<8.2f}{C['N']} {self.color_pct(s['change_pct']):<9} ¥{s['high']:<8,.2f} ¥{s['low']:<8,.2f} {vol_str:<8}")
        
        return '\n'.join(lines)
    
    def render_history(self, limit=20):
        if not self.trade.trades:
            return f"\n{C['DIM']}暂无交易记录{C['N']}"
        
        lines = [f"\n{C['BOLD']}📜 交易历史 (最近{limit}条){C['N']}", f"{'─' * 65}"]
        lines.append(f"  {'#':<4} {'时间':<8} {'品种':<8} {'操作':<14} {'手数':<6} {'价格':<10} {'盈亏':<12}")
        lines.append(f"  {'─' * 4} {'─' * 8} {'─' * 8} {'─' * 14} {'─' * 6} {'─' * 10} {'─' * 12}")
        
        for t in self.trades[-limit:]:
            pnl = t.get('pnl', 0)
            pnl_c = C['G'] if pnl >= 0 else C['R']
            pnl_str = f"{pnl_c}¥{pnl:<+8,.0f}{C['N']}" if pnl != 0 else f"{C['DIM']}¥0{C['N']}"
            lines.append(f"  {t['id']:<4} {t['time']:<8} {CONTRACTS.get(t['code'], {}).get('name', t['code']):<8} {t['action']:<14} {t['qty']:<6} ¥{t['price']:<8.2f} {pnl_str}")
        
        return '\n'.join(lines)
    
    def render_help(self):
        return f"""
{C['BOLD']}{C['Y']}🔥 燃期货 命令帮助{C['N']}
{'─' * 50}

{C['BOLD']}📈 行情{C['N']}
  list/ls                   查看所有品种行情
  view <代码>               查看品种详情

{C['BOLD']}💹 交易{C['N']}
  buy <代码> <手数>         开多（例: buy RB 2）
  sell <代码> <手数>        开空（例: sell SC 1）
  close <代码> <手数>       平多（例: close RB 1）
  cover <代码> <手数>       平空（例: cover I 1）

{C['BOLD']}📊 持仓/账户{C['N']}
  pos/positions             查看持仓
  acc/account               查看账户
  history/hist              交易历史

{C['BOLD']}🎯 风控{C['N']}
  sl <代码> <价格>          设置止损（例: sl RB 3200）
  tp <代码> <价格>          设置止盈（例: tp RB 3400）

{C['BOLD']}🔧 其他{C['N']}
  reset                     重置账户(100万)
  help/?                    帮助
  quit/q/exit               退出
"""


# ─── 主循环 ───
def main():
    os.system('clear' if os.name == 'posix' else 'cls')
    
    market = MarketEngine()
    trade = TradeEngine(market)
    ui = UI(market, trade)
    
    # 启动止损检查线程
    def stop_checker():
        while True:
            time.sleep(3)
            try:
                triggered = trade.check_stops()
                for code, qty, reason, pnl in triggered:
                    name = CONTRACTS[code]['name']
                    emoji = '💰' if pnl >= 0 else '💸'
                    print(f"\n{C['Y']}⚡ {reason}：{name}({code}) {qty}手 {emoji} ¥{pnl:+.2f}{C['N']}")
                
                liq, msg = trade.check_liquidation()
                if liq:
                    print(f"\n{C['R']}{msg}{C['N']}")
            except:
                pass
    
    t = threading.Thread(target=stop_checker, daemon=True)
    t.start()
    
    print(ui.render_header())
    print(ui.render_account())
    print(ui.render_market())
    print(f"\n{C['DIM']}输入 help 查看命令帮助{C['N']}")
    print(f"{C['DIM']}{'─' * 50}{C['N']}")
    
    while True:
        try:
            cmd = input(f"\n{C['BOLD']}{C['C']}🔥{C['N']} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        
        if not cmd:
            continue
        
        parts = cmd.split()
        action = parts[0].lower()
        
        if action in ('q', 'quit', 'exit'):
            print(f"\n{C['Y']}👋 龙哥，交易愉快！下次再来玩～{C['N']}")
            break
        
        elif action in ('help', '?'):
            print(ui.render_help())
        
        elif action in ('list', 'ls'):
            print(ui.render_market())
        
        elif action == 'view':
            if len(parts) < 2:
                print(f"{C['R']}用法: view <品种代码>{C['N']}")
                continue
            code = parts[1].upper()
            if code not in CONTRACTS:
                print(f"{C['R']}未知品种: {code}{C['N']}")
                continue
            s = market.get_snapshot(code)
            cfg = CONTRACTS[code]
            color = ui.color_price(s['change'])
            arrow = ui.arrow(s['change'])
            print(f"""
{C['BOLD']}📊 {cfg['name']}({code}) 行情详情{C['N']}
{'─' * 40}
  交易所:   {cfg['exchange']}
  合约乘数: {cfg['mult']}
  保证金:   {cfg['margin']*100:.0f}%
  最小变动: ¥{cfg['tick']} (每跳 ¥{cfg['tv']})
  交易时间: {cfg['hour']}
{'─' * 40}
  最新价:   {color}¥{s['price']:<10,.2f}{C['N']}
  开盘价:   ¥{s['open']:<10,.2f}
  最高价:   ¥{s['high']:<10,.2f}
  最低价:   ¥{s['low']:<10,.2f}
  昨收价:   ¥{s['prev_close']:<10,.2f}
  涨  跌:   {color}{arrow} ¥{abs(s['change']):<8.2f}{C['N']}
  涨跌幅:   {ui.color_pct(s['change_pct'])}
  成交量:   {s['volume']:<10,}
  持仓量:   {s['oi']:<10,}
{'─' * 40}
  开一手保证金: {color}¥{s['price'] * cfg['mult'] * cfg['margin']:<.2f}{C['N']}
  一手手续费:   ¥{s['price'] * cfg['mult'] * cfg['comm']:<.4f}
""")
        
        elif action in ('buy', 'b'):
            if len(parts) < 3:
                print(f"{C['R']}用法: buy <代码> <手数>{C['N']}")
                continue
            code = parts[1].upper()
            try:
                qty = int(parts[2])
            except:
                print(f"{C['R']}手数必须为整数{C['N']}")
                continue
            success, msg = trade.open_position(code, 'long', qty)
            print(f"\n  {msg}")
        
        elif action in ('sell', 's'):
            if len(parts) < 3:
                print(f"{C['R']}用法: sell <代码> <手数>{C['N']}")
                continue
            code = parts[1].upper()
            try:
                qty = int(parts[2])
            except:
                print(f"{C['R']}手数必须为整数{C['N']}")
                continue
            success, msg = trade.open_position(code, 'short', qty)
            print(f"\n  {msg}")
        
        elif action == 'close':
            if len(parts) < 2:
                print(f"{C['R']}用法: close <代码> [手数]{C['N']}")
                continue
            code = parts[1].upper()
            qty = int(parts[2]) if len(parts) > 2 else None
            success, msg = trade.close_position(code, qty)
            print(f"\n  {msg}")
        
        elif action == 'cover':
            if len(parts) < 2:
                print(f"{C['R']}用法: cover <代码> [手数]{C['N']}")
                continue
            code = parts[1].upper()
            qty = int(parts[2]) if len(parts) > 2 else None
            success, msg = trade.cover_position(code, qty)
            print(f"\n  {msg}")
        
        elif action in ('pos', 'positions'):
            print(ui.render_positions())
        
        elif action in ('acc', 'account'):
            print(ui.render_account())
        
        elif action in ('history', 'hist'):
            print(ui.render_history())
        
        elif action == 'sl':
            if len(parts) < 3:
                print(f"{C['R']}用法: sl <代码> <止损价>{C['N']}")
                continue
            code = parts[1].upper()
            try:
                price = float(parts[2])
            except:
                print(f"{C['R']}价格必须为数字{C['N']}")
                continue
            success, msg = trade.set_stop(code, price, 'sl')
            print(f"\n  {msg}")
        
        elif action == 'tp':
            if len(parts) < 3:
                print(f"{C['R']}用法: tp <代码> <止盈价>{C['N']}")
                continue
            code = parts[1].upper()
            try:
                price = float(parts[2])
            except:
                print(f"{C['R']}价格必须为数字{C['N']}")
                continue
            success, msg = trade.set_stop(code, price, 'tp')
            print(f"\n  {msg}")
        
        elif action == 'reset':
            print(f"\n  {trade.reset()}")
        
        else:
            print(f"{C['DIM']}未知命令: {action}  输入 help 查看帮助{C['N']}")
    
    market.stop()
    print()

if __name__ == '__main__':
    main()
