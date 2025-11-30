# gui/positions_view.py
"""
倉位表格模組
負責顯示倉位、右鍵選單、雙擊切換、報價更新
"""
import tkinter as tk
from tkinter import ttk, messagebox

class PositionsView:
    def __init__(self, root, app):
        self.root = root
        self.app = app  # 主視窗的參考
        self.setup_ui()
    
    def setup_ui(self):
        """建立倉位表格 UI"""
        frame_mid = tk.LabelFrame(
            self.root, 
            text="庫存監控 (雙擊第一欄切換)", 
            padx=10, pady=10
        )
        frame_mid.pack(fill='both', expand=True, padx=10)
        
        # 建立表格
        cols = ("select", "code", "direction", "days", "quantity", "cost", 
                "last_price", "pnl", "margin", "delta", "net_delta", "weight")
        self.tree = ttk.Treeview(frame_mid, columns=cols, show='headings')
        
        # 設定欄位標題
        self.tree.heading("select", text="選")
        self.tree.heading("code", text="代碼")
        self.tree.heading("direction", text="方向")
        self.tree.heading("days", text="天數")
        self.tree.heading("quantity", text="口數")
        self.tree.heading("cost", text="成本")
        self.tree.heading("last_price", text="現價")
        self.tree.heading("pnl", text="損益")
        self.tree.heading("margin", text="保證金")
        self.tree.heading("delta", text="單位Δ")
        self.tree.heading("net_delta", text="淨Δ")
        self.tree.heading("weight", text="權重")
        
        # 設定欄位寬度
        self.tree.column("select", width=30, anchor='center')
        self.tree.column("code", width=90, anchor='center')
        self.tree.column("direction", width=50, anchor='center')
        self.tree.column("days", width=50, anchor='center')
        self.tree.column("quantity", width=50, anchor='center')
        self.tree.column("cost", width=70, anchor='center')
        self.tree.column("last_price", width=70, anchor='center')
        self.tree.column("pnl", width=80, anchor='center')
        self.tree.column("margin", width=80, anchor='center')
        self.tree.column("delta", width=60, anchor='center')
        self.tree.column("net_delta", width=70, anchor='center')
        self.tree.column("weight", width=80, anchor='center')
        
        self.tree.pack(fill='both', expand=True)
        
        # 綁定事件
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.on_right_click)
        
        # 設定顏色標籤
        self.tree.tag_configure('profit', foreground='red')
        self.tree.tag_configure('loss', foreground='green')
        self.tree.tag_configure('neutral', foreground='black')
        
        # 按鈕區
        btn_frame = tk.Frame(frame_mid)
        btn_frame.pack(pady=5)
        
        tk.Button(
            btn_frame, text="刷新現價與損益", 
            command=self.refresh_positions, 
            bg="#87CEEB"
        ).pack(side='left', padx=5)
        
        self.btn_subscribe = tk.Button(
            btn_frame, text="訂閱即時報價", 
            command=self.app.toggle_subscription, 
            bg="#FFD700"
        )
        self.btn_subscribe.pack(side='left', padx=5)
        
        tk.Button(
            btn_frame, text="檢查訂閱狀態", 
            command=self.app.check_subscription_status, 
            bg="#D3D3D3"
        ).pack(side='left', padx=5)
    
    def refresh_positions(self):
        """刷新倉位資料"""
        if not self.app.backend.connected:
            return
        
        # 清空表格
        for row in self.tree.get_children():
            self.tree.delete(row)
        
        # 取得倉位資料
        raw_data = self.app.backend.get_positions()
        self.app.positions_data = []
        
        underlying_price = self.app.backend.get_underlying_price()
        print(f"[GUI] 標的價格: {underlying_price}")
        
        # 計算總 Delta
        total_net_delta = sum(p['est_delta'] * float(p['quantity']) for p in raw_data)
        
        long_delta = sum(p['est_delta'] * float(p['quantity']) for p in raw_data 
                        if p['est_delta'] * float(p['quantity']) > 0)
        short_delta = sum(p['est_delta'] * float(p['quantity']) for p in raw_data 
                         if p['est_delta'] * float(p['quantity']) < 0)
        
        total_pnl_val = 0
        total_margin_val = 0
        
        # 處理每個倉位
        for p in raw_data:
            qty = float(p.get('quantity', 0))
            delta = float(p.get('est_delta', 0))
            pnl = int(p.get('calc_pnl', 0))
            total_pnl_val += pnl
            
            code = p.get('code', '')
            last_price = p.get('last_price', 0)
            
            print(f"[GUI] 計算 {code} 保證金: qty={qty}, last_price={last_price}, underlying={underlying_price}")
            
            # 計算保證金
            margin = self.app.margin_fetcher.calculate_margin(
                code,
                int(qty),
                last_price=last_price,
                underlying_price=underlying_price
            )
            total_margin_val += margin
            
            print(f"[GUI] {code} 保證金結果: {margin}")
            
            net_delta = delta * qty
            
            # 計算權重
            weight_str = "-"
            if abs(total_net_delta) > 0.01:
                weight_pct = (net_delta / total_net_delta) * 100
                weight_str = f"{weight_pct:+.1f}%"
            
            days_val = p.get('days_left', 0)
            days_str = str(days_val) if days_val > 0 else "-"
            
            # 決定顏色標籤
            tag = 'neutral'
            if pnl > 0:
                tag = 'profit'
            elif pnl < 0:
                tag = 'loss'
            
            # 建立項目
            item_entry = {'data': p, 'selected': True}
            
            row_id = self.tree.insert("", "end", values=(
                "X",
                code,
                p['dir_str'],
                days_str,
                int(qty),
                p.get('price', 0),
                p.get('last_price', 0),
                pnl,
                f"{margin:,}",
                f"{delta:.2f}",
                f"{net_delta:+.2f}",
                weight_str
            ), tags=(tag,))
            
            item_entry['id'] = row_id
            self.app.positions_data.append(item_entry)
        
        # 更新總計顯示
        self.app.lbl_total_pnl.config(
            text=f"{total_pnl_val:,}", 
            fg="red" if total_pnl_val > 0 else "green" if total_pnl_val < 0 else "black"
        )
        
        self.app.lbl_total_margin.config(text=f"{total_margin_val:,}", fg="blue")
        
        self.app.lbl_long_delta.config(text=f"{long_delta:+.2f}")
        self.app.lbl_short_delta.config(text=f"{short_delta:+.2f}")
        
        # 更新淨方向
        if abs(total_net_delta) < 0.1:
            direction_text = "中立"
            direction_color = "black"
        elif total_net_delta > 0:
            direction_text = f"偏多 {total_net_delta:+.2f}"
            direction_color = "red"
        else:
            direction_text = f"偏空 {total_net_delta:+.2f}"
            direction_color = "green"
        
        self.app.lbl_net_direction.config(text=direction_text, fg=direction_color)
        
        self.update_delta_display()
    
    def clear_all(self):
        """清空表格"""
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.app.positions_data = []
    
    def on_double_click(self, event):
        """雙擊切換選取"""
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        
        target = next((x for x in self.app.positions_data if x['id'] == item_id), None)
        if target:
            target['selected'] = not target['selected']
            new_symbol = "X" if target['selected'] else ""
            vals = self.tree.item(item_id, "values")
            self.tree.item(item_id, values=(new_symbol, *vals[1:]))
            self.update_delta_display()
    
    def on_right_click(self, event):
        """右鍵選單"""
        from .dialogs import show_right_click_menu
        show_right_click_menu(self, event)
    
    def update_delta_display(self):
        """更新 Delta 顯示"""
        total = 0.0
        for item in self.app.positions_data:
            if item['selected']:
                qty = float(item['data'].get('quantity', 0))
                delta = float(item['data'].get('est_delta', 0))
                total += (qty * delta)
        self.app.lbl_current_delta.config(text=f"{total:.2f}")
        return total
    
    def handle_quote_update(self, exchange, tick):
        """處理報價更新"""
        try:
            code = tick.code if hasattr(tick, 'code') else str(tick.get('code', ''))
            
            # 取得最新價格
            close = 0
            
            if hasattr(tick, 'close') and tick.close and tick.close > 0:
                close = float(tick.close)
            
            elif hasattr(tick, 'bid_price') and hasattr(tick, 'ask_price'):
                bid = float(tick.bid_price[0]) if tick.bid_price and len(tick.bid_price) > 0 and tick.bid_price[0] > 0 else 0
                ask = float(tick.ask_price[0]) if tick.ask_price and len(tick.ask_price) > 0 and tick.ask_price[0] > 0 else 0
                
                if bid > 0 and ask > 0:
                    close = (bid + ask) / 2
                elif bid > 0:
                    close = bid
                elif ask > 0:
                    close = ask
            
            elif hasattr(tick, 'buy_price') and hasattr(tick, 'sell_price'):
                buy = float(tick.buy_price) if tick.buy_price and tick.buy_price > 0 else 0
                sell = float(tick.sell_price) if tick.sell_price and tick.sell_price > 0 else 0
                
                if buy > 0 and sell > 0:
                    close = (buy + sell) / 2
                elif buy > 0:
                    close = buy
                elif sell > 0:
                    close = sell
            
            if close <= 0:
                return
            
            # 更新倉位資料
            updated = False
            
            for item in self.app.positions_data:
                if item['data']['code'] == code:
                    item['data']['last_price'] = close
                    
                    # 重新計算損益
                    qty = float(item['data'].get('quantity', 0))
                    cost = float(item['data'].get('price', 0))
                    direction = item['data'].get('direction', '')
                    multiplier = self.app.backend.contracts.get_multiplier(code)
                    
                    diff = (close - cost) if 'Buy' in str(direction) else (cost - close)
                    pnl = int(diff * qty * multiplier)
                    item['data']['calc_pnl'] = pnl
                    
                    # 重新計算保證金
                    if code.startswith('TXO'):
                        underlying_price = self.app.backend.get_underlying_price()
                        margin = self.app.margin_fetcher.calculate_margin(
                            code,
                            int(qty),
                            last_price=close,
                            underlying_price=underlying_price
                        )
                    else:
                        margin = self.app.margin_fetcher.calculate_margin(code, int(qty))
                    
                    # 更新表格顯示
                    vals = list(self.tree.item(item['id'], 'values'))
                    vals[6] = f"{close:.2f}"
                    vals[7] = pnl
                    vals[8] = f"{margin:,}"
                    
                    tag = 'neutral'
                    if pnl > 0:
                        tag = 'profit'
                    elif pnl < 0:
                        tag = 'loss'
                    
                    self.tree.item(item['id'], values=vals, tags=(tag,))
                    updated = True
                    break
            
            if updated:
                self.update_totals()
        
        except Exception as e:
            print(f"[報價更新錯誤] {e}")
            import traceback
            traceback.print_exc()
    
    def update_totals(self):
        """更新總損益和總保證金"""
        total_pnl = 0
        total_margin = 0
        
        for item in self.app.positions_data:
            pnl = item['data'].get('calc_pnl', 0)
            total_pnl += pnl
            
            vals = self.tree.item(item['id'], 'values')
            margin_str = str(vals[8]).replace(',', '')
            try:
                margin = int(margin_str) if margin_str.isdigit() else 0
                total_margin += margin
            except:
                pass
        
        self.app.lbl_total_pnl.config(
            text=f"{total_pnl:,}", 
            fg="red" if total_pnl > 0 else "green" if total_pnl < 0 else "black"
        )
        
        self.app.lbl_total_margin.config(text=f"{total_margin:,}", fg="blue")