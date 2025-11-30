# gui/main_window.py
"""
主視窗模組
負責 UI 框架、登入/登出、按鈕事件處理
"""
import tkinter as tk
from tkinter import messagebox
from backend import TradingBackend
from my_utils import MarginFetcher
from config import load_credentials
from .positions_view import PositionsView
from .dialogs import (
    FuturesRollDialog, 
    OptionsChangeDialog, 
    NewPositionDialog, 
    MonitorWindow
)

class TradingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python 程式交易中控台 (P&L Ver.)")
        self.root.geometry("1400x800")
        
        self.backend = TradingBackend(simulation=False)
        self.margin_fetcher = MarginFetcher()
        self.positions_data = []
        self.is_subscribed = False
        self.subscribed_contracts = []
        self.spread_monitors = []  # 價差監測列表
        
        self.setup_ui()
        self.load_credentials()
        self.update_margin_status()
    
    def setup_ui(self):
        """建立 UI 框架"""
        # ===== 1. Top Frame - 登入區 =====
        frame_top = tk.Frame(self.root, pady=10)
        frame_top.pack(fill='x')
        
        tk.Label(frame_top, text="API Key:").pack(side='left', padx=5)
        self.entry_api = tk.Entry(frame_top, width=20)
        self.entry_api.pack(side='left')
        
        tk.Label(frame_top, text="Secret:").pack(side='left', padx=5)
        self.entry_secret = tk.Entry(frame_top, width=20, show="*")
        self.entry_secret.pack(side='left')
        
        self.btn_auth = tk.Button(
            frame_top, text="登入 Shioaji", 
            command=self.toggle_auth, 
            bg="#add8e6", width=20
        )
        self.btn_auth.pack(side='left', padx=20)
        
        self.lbl_status = tk.Label(frame_top, text="狀態: 未連線", fg="red")
        self.lbl_status.pack(side='left', padx=10)
        
        self.lbl_margin_status = tk.Label(frame_top, text="保證金資料: 未載入", fg="orange")
        self.lbl_margin_status.pack(side='left', padx=10)
        
        tk.Button(
            frame_top, text="更新保證金", 
            command=self.fetch_margin_data, 
            bg="#90EE90"
        ).pack(side='left', padx=5)
        
        # ===== 2. Middle Frame - 倉位表格 =====
        self.positions_view = PositionsView(self.root, self)
        
        # ===== 3. Bottom Frame - 策略與風險 =====
        frame_btm = tk.LabelFrame(self.root, text="策略與風險", padx=10, pady=10)
        frame_btm.pack(fill='x', padx=10, pady=10)
        
        # Delta 顯示
        f1 = tk.Frame(frame_btm)
        f1.pack(fill='x')
        
        tk.Label(f1, text="Net Delta:", font=("Arial", 10)).pack(side='left')
        self.lbl_current_delta = tk.Label(f1, text="0.0", fg="blue", font=("Arial", 12, "bold"))
        self.lbl_current_delta.pack(side='left', padx=10)
        
        tk.Label(f1, text="總損益:", font=("Arial", 10)).pack(side='left', padx=10)
        self.lbl_total_pnl = tk.Label(f1, text="0", font=("Arial", 12, "bold"))
        self.lbl_total_pnl.pack(side='left')
        
        tk.Label(f1, text="總保證金:", font=("Arial", 10)).pack(side='left', padx=10)
        self.lbl_total_margin = tk.Label(f1, text="0", font=("Arial", 12, "bold"))
        self.lbl_total_margin.pack(side='left')
        
        # 多空 Delta 分析
        f2 = tk.Frame(frame_btm)
        f2.pack(fill='x', pady=5)
        
        tk.Label(f2, text="多方Delta:", font=("Arial", 9)).pack(side='left', padx=5)
        self.lbl_long_delta = tk.Label(f2, text="0.0", fg="red", font=("Arial", 10, "bold"))
        self.lbl_long_delta.pack(side='left', padx=5)
        
        tk.Label(f2, text="空方Delta:", font=("Arial", 9)).pack(side='left', padx=5)
        self.lbl_short_delta = tk.Label(f2, text="0.0", fg="green", font=("Arial", 10, "bold"))
        self.lbl_short_delta.pack(side='left', padx=5)
        
        tk.Label(f2, text="淨方向:", font=("Arial", 9)).pack(side='left', padx=5)
        self.lbl_net_direction = tk.Label(f2, text="中立", font=("Arial", 10, "bold"))
        self.lbl_net_direction.pack(side='left', padx=5)
        
        # 目標 Delta 計算
        f3 = tk.Frame(frame_btm)
        f3.pack(fill='x', pady=5)
        
        tk.Label(f3, text="目標 Delta:").pack(side='left', padx=(0, 0))
        self.entry_target = tk.Entry(f3, width=8)
        self.entry_target.insert(0, "0.0")
        self.entry_target.pack(side='left')
        
        tk.Button(f3, text="計算建議", command=self.on_calculate, bg="orange").pack(side='left', padx=10)
        
        self.txt_result = tk.Text(frame_btm, height=5, bg="#f0f0f0")
        self.txt_result.pack(fill='x', pady=5)
    
    def load_credentials(self):
        """載入認證資訊"""
        creds = load_credentials()
        if creds.get('api_key'):
            self.entry_api.insert(0, creds['api_key'])
        if creds.get('secret_key'):
            self.entry_secret.insert(0, creds['secret_key'])
    
    # ===== 保證金相關 =====
    def update_margin_status(self):
        """更新保證金狀態顯示"""
        if self.margin_fetcher.has_data():
            timestamp = self.margin_fetcher.get_data_timestamp()
            self.lbl_margin_status.config(text=f"保證金資料: {timestamp}", fg="green")
        else:
            self.lbl_margin_status.config(text="保證金資料: 未載入", fg="orange")
    
    def fetch_margin_data(self):
        """抓取保證金資料"""
        try:
            self.lbl_margin_status.config(text="正在更新保證金資料...", fg="blue")
            self.root.update()
            
            success, message = self.margin_fetcher.fetch_and_save()
            
            if success:
                messagebox.showinfo("成功", message)
                self.update_margin_status()
                if self.backend.connected:
                    self.positions_view.refresh_positions()
            else:
                messagebox.showerror("錯誤", message)
                self.update_margin_status()
        except Exception as e:
            messagebox.showerror("錯誤", f"更新保證金失敗: {str(e)}")
            self.update_margin_status()
    
    # ===== 登入/登出 =====
    def toggle_auth(self):
        """切換登入/登出"""
        if self.backend.connected:
            # 登出
            if self.is_subscribed:
                self.unsubscribe_quotes()
            
            self.backend.logout()
            self.btn_auth.config(text="登入 Shioaji", bg="#add8e6")
            self.lbl_status.config(text="狀態: 已登出", fg="red")
            
            # 清空顯示
            self.positions_view.clear_all()
            self.lbl_total_pnl.config(text="0", fg="black")
            self.lbl_total_margin.config(text="0", fg="black")
            self.lbl_long_delta.config(text="0.0")
            self.lbl_short_delta.config(text="0.0")
            self.lbl_net_direction.config(text="中立")
            self.lbl_current_delta.config(text="0.0")
        else:
            # 登入
            success, msg = self.backend.login(
                self.entry_api.get(), 
                self.entry_secret.get()
            )
            if success:
                self.btn_auth.config(text="已登入 (點擊登出)", bg="#ffcccb")
                self.lbl_status.config(text="狀態: 已連線", fg="green")
                self.positions_view.refresh_positions()
            else:
                messagebox.showerror("錯誤", msg)
    
    # ===== 訂閱相關 =====
    def toggle_subscription(self):
        """切換訂閱狀態"""
        if not self.backend.connected:
            messagebox.showwarning("警告", "請先登入 Shioaji")
            return
        
        if not self.positions_data:
            messagebox.showwarning("警告", "沒有庫存部位")
            return
        
        if self.is_subscribed:
            self.unsubscribe_quotes()
        else:
            self.subscribe_quotes()
    
    def subscribe_quotes(self):
        """訂閱報價"""
        codes = [item['data']['code'] for item in self.positions_data]
        success = self.backend.start_subscribing(
            codes, 
            self.on_quote_update, 
            self.on_order_update
        )
        
        if success:
            self.is_subscribed = True
            self.subscribed_contracts = codes.copy()
            self.positions_view.btn_subscribe.config(
                text="已訂閱報價 (點擊取消)", 
                bg="#FF4444"
            )
            messagebox.showinfo("成功", f"已成功訂閱 {len(codes)} 檔即時報價!\n報價將即時更新損益")
        else:
            messagebox.showerror("失敗", "訂閱失敗,請檢查 console 輸出")
    
    def unsubscribe_quotes(self):
        """取消訂閱"""
        if not self.is_subscribed and not self.subscribed_contracts:
            print("[提示] 目前沒有訂閱")
            self.positions_view.btn_subscribe.config(text="訂閱即時報價", bg="#FFD700")
            return
        
        try:
            if self.subscribed_contracts:
                self.backend.subscription.unsubscribe(self.subscribed_contracts)
        except Exception as e:
            print(f"取消訂閱錯誤: {e}")
        finally:
            self.is_subscribed = False
            self.subscribed_contracts = []
            self.positions_view.btn_subscribe.config(text="訂閱即時報價", bg="#FFD700")
            print("[狀態] 訂閱已完全取消")
    
    def check_subscription_status(self):
        """檢查訂閱狀態"""
        from datetime import datetime
        
        info = []
        info.append(f"GUI 訂閱狀態: {'已訂閱' if self.is_subscribed else '未訂閱'}")
        info.append(f"已訂閱合約數: {len(self.subscribed_contracts)}")
        
        if self.subscribed_contracts:
            info.append(f"合約列表: {', '.join(self.subscribed_contracts[:5])}")
        
        now = datetime.now()
        info.append(f"\n當前時間: {now.strftime('%H:%M:%S')}")
        
        hour = now.hour
        minute = now.minute
        
        if (hour == 8 and minute >= 45) or (9 <= hour < 13) or (hour == 13 and minute <= 45):
            session = "日盤交易時段"
        elif (hour == 15) or (16 <= hour <= 23) or (0 <= hour < 5):
            session = "夜盤交易時段"
        else:
            session = "休市時段"
        
        info.append(f"交易時段: {session}")
        
        if session == "休市時段":
            info.append("\n⚠️ 目前是休市時段,不會有報價更新!")
            info.append("日盤: 08:45-13:45")
            info.append("夜盤: 15:00-05:00")
        
        messagebox.showinfo("訂閱狀態", "\n".join(info))
    
    # ===== 報價更新回調 =====
    def on_quote_update(self, exchange, tick):
        """處理報價更新"""
        self.positions_view.handle_quote_update(exchange, tick)
    
    def on_order_update(self, stat, msg):
        """處理委託更新"""
        print(f"委託更新: {stat}, {msg}")
    
    # ===== 計算建議 =====
    def on_calculate(self):
        """計算部位調整建議"""
        try:
            curr = self.positions_view.update_delta_display()
            target = float(self.entry_target.get())
            suggestion = self.backend.calculate_suggestion(curr, target)
            self.txt_result.delete("1.0", tk.END)
            self.txt_result.insert(tk.END, suggestion)
        except ValueError:
            messagebox.showerror("錯誤", "目標 Delta 格式錯誤")
    
    # ===== 價差監測相關 =====
    def start_spread_monitoring(self, code, qty, direction, target_spread, is_逆價差, auto_execute):
        """啟動價差監測"""
        monitor = {
            'code': code,
            'qty': qty,
            'direction': direction,
            'target_spread': target_spread,
            'is_逆價差': is_逆價差,
            'auto_execute': auto_execute,
            'active': True
        }
        
        self.spread_monitors.append(monitor)
        
        spread_type = "逆價差" if is_逆價差 else "正價差"
        auto_text = "自動下單" if auto_execute else "需確認"
        msg = f"已啟動價差監測\n\n"
        msg += f"商品: {code}\n"
        msg += f"類型: {spread_type}\n"
        msg += f"目標: {target_spread:.0f} 點\n"
        msg += f"模式: {auto_text}\n\n"
        msg += f"系統將每30秒檢查一次價差"
        
        messagebox.showinfo("監測已啟動", msg)
        
        # 顯示監測視窗
        MonitorWindow(self.root, self)
        
        # 開始檢查
        self.check_spread_monitors()
    
    def check_spread_monitors(self):
        """定期檢查價差監測任務"""
        if not hasattr(self, 'spread_monitors'):
            return
        
        for monitor in self.spread_monitors[:]:
            if not monitor['active']:
                continue
            
            is_sell = 'Sell' in str(monitor['direction'])
            should_roll, msg, spread = self.backend.check_and_roll_if_spread_met(
                monitor['code'],
                monitor['qty'],
                monitor['direction'],
                monitor['target_spread'],
                monitor['is_逆價差'],
                is_sell_position=is_sell
            )
            
            if should_roll:
                auto_exec = monitor.get('auto_execute', False)
                
                if auto_exec:
                    # 自動執行
                    result_msg = f"價差監測觸發!\n\n{msg}\n\n自動執行轉倉..."
                    print(result_msg)
                    
                    success, roll_msg = self.backend.roll_futures(
                        monitor['code'],
                        monitor['qty'],
                        monitor['direction'],
                        is_sell_position=is_sell
                    )
                    
                    if success:
                        messagebox.showinfo("自動轉倉成功", roll_msg)
                        self.positions_view.refresh_positions()
                    else:
                        messagebox.showerror("自動轉倉失敗", roll_msg)
                else:
                    # 需要確認
                    result_msg = f"價差監測觸發!\n\n{msg}\n\n即將執行轉倉..."
                    if messagebox.askyesno("確認轉倉", result_msg):
                        success, roll_msg = self.backend.roll_futures(
                            monitor['code'],
                            monitor['qty'],
                            monitor['direction'],
                            is_sell_position=is_sell
                        )
                        
                        if success:
                            messagebox.showinfo("轉倉成功", roll_msg)
                            self.positions_view.refresh_positions()
                        else:
                            messagebox.showerror("轉倉失敗", roll_msg)
                
                # 移除已觸發的監測
                self.spread_monitors.remove(monitor)
        
        # 如果還有活躍監測,繼續檢查
        if any(m['active'] for m in self.spread_monitors):
            self.root.after(30000, self.check_spread_monitors)