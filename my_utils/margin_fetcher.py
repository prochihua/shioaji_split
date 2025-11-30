# margin_fetcher.py
import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import re

class MarginFetcher:
    def __init__(self, cache_file='margin_data.json'):
        self.cache_file = cache_file
        self.margin_data = {}
        self.load_from_cache()
        
    def fetch_and_save(self):
        """從期交所抓取保證金資料並存檔"""
        try:
            # 正確的期交所保證金網址
            url = "https://www.taifex.com.tw/cht/5/indexMarging"
            
            print("正在抓取期交所保證金資料...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                return False, f"無法連接期交所網站 (HTTP {response.status_code})"
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 尋找表格 - 期交所使用多種可能的 class
            table = None
            for table_class in ['table_f', 'table_c', 'table', None]:
                if table_class:
                    table = soup.find('table', {'class': table_class})
                else:
                    # 嘗試找任何 table
                    tables = soup.find_all('table')
                    if tables:
                        # 找包含「保證金」的表格
                        for t in tables:
                            if '保證金' in t.get_text() or '契約' in t.get_text():
                                table = t
                                break
                if table:
                    break
            
            if not table:
                # 儲存 HTML 供除錯
                with open('debug_margin.html', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                return False, "找不到保證金表格，已儲存 debug_margin.html 供檢查"
            
            self.margin_data = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'contracts': {}
            }
            
            # 解析表格
            rows = table.find_all('tr')
            print(f"找到 {len(rows)} 行資料")
            
            # 先找出表頭，確定欄位順序
            header_row = rows[0] if rows else None
            col_indices = {}
            
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
                print(f"表頭: {headers}")
                
                # 找出各欄位的索引
                for idx, header in enumerate(headers):
                    if '商品' in header or '契約' in header:
                        col_indices['product'] = idx
                    elif '原始保證金' in header:
                        col_indices['original'] = idx
                    elif '維持保證金' in header:
                        col_indices['maintenance'] = idx
                    elif '結算保證金' in header:
                        col_indices['settlement'] = idx
                
                print(f"欄位索引: {col_indices}")
            
            for i, row in enumerate(rows):
                # 跳過表頭
                if i == 0:
                    continue
                    
                cols = row.find_all(['td', 'th'])
                if len(cols) < 2:
                    continue
                    
                try:
                    # 提取文字並清理
                    texts = [col.get_text(strip=True) for col in cols]
                    
                    # 跳過空行或標題行
                    if not texts[0] or '商品名稱' in texts[0]:
                        continue
                    
                    # 根據表頭索引取得欄位
                    product_name = texts[col_indices.get('product', 0)]
                    
                    original_margin = 0
                    maintenance_margin = 0
                    
                    # 使用正確的欄位索引
                    if 'original' in col_indices and col_indices['original'] < len(texts):
                        text = texts[col_indices['original']].replace(',', '').replace('元', '').replace(' ', '')
                        if text.isdigit():
                            original_margin = int(text)
                    
                    if 'maintenance' in col_indices and col_indices['maintenance'] < len(texts):
                        text = texts[col_indices['maintenance']].replace(',', '').replace('元', '').replace(' ', '')
                        if text.isdigit():
                            maintenance_margin = int(text)
                    
                    # 如果沒有找到欄位索引，使用預設邏輯（但避開結算保證金）
                    if original_margin == 0 and 'original' not in col_indices:
                        # 假設順序：商品名稱、原始保證金、維持保證金、結算保證金
                        # 所以原始保證金在索引 1，維持保證金在索引 2
                        if len(texts) >= 3:
                            # 第一個數字是原始保證金
                            text1 = texts[1].replace(',', '').replace('元', '').replace(' ', '')
                            if text1.isdigit():
                                original_margin = int(text1)
                            
                            # 第二個數字是維持保證金
                            text2 = texts[2].replace(',', '').replace('元', '').replace(' ', '')
                            if text2.isdigit():
                                maintenance_margin = int(text2)
                    
                    if original_margin > 0:
                        # 使用商品名稱作為 key
                        self.margin_data['contracts'][product_name] = {
                            'name': product_name,
                            'original_margin': original_margin,
                            'maintenance_margin': maintenance_margin if maintenance_margin > 0 else int(original_margin * 0.75)
                        }
                        
                        print(f"  載入: {product_name:<20s} - 原始: {original_margin:>8,}, 維持: {maintenance_margin:>8,}")
                        
                except Exception as e:
                    print(f"  解析第 {i} 行失敗: {e}, 資料: {texts[:3] if 'texts' in locals() else 'N/A'}")
                    continue
            
            if not self.margin_data['contracts']:
                return False, "未能解析任何保證金資料"
            
            # 儲存到檔案
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.margin_data, f, ensure_ascii=False, indent=2)
            
            count = len(self.margin_data['contracts'])
            return True, f"成功載入 {count} 個商品的保證金資料"
            
        except requests.Timeout:
            return False, "連線逾時，請檢查網路"
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"抓取失敗: {str(e)}"
    
    def load_from_cache(self):
        """從檔案載入保證金資料"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.margin_data = json.load(f)
                print(f"已載入保證金資料: {self.margin_data.get('timestamp', '未知時間')}")
            except Exception as e:
                print(f"載入保證金資料失敗: {e}")
                self.margin_data = {}
    
    def has_data(self):
        """檢查是否有保證金資料"""
        return bool(self.margin_data.get('contracts'))
    
    def get_data_timestamp(self):
        """取得資料時間戳記"""
        return self.margin_data.get('timestamp', '未知')
    
    # ==========================================================
    # [修正] 新增缺失的方法 get_margin_info 和 _get_multiplier
    # ==========================================================
    def _get_multiplier(self, code):
        """ 根據合約代碼回傳乘數 """
        code = code.strip().upper()
        if code.startswith('TXO'):
            return 50.0  # 臺指選擇權
        elif code.startswith('TX') or code.startswith('MTX'):
            return 200.0  # 臺股期貨/大台
        elif code.startswith('MXF'):
            return 50.0  # 小型臺指期貨
        elif code.startswith('TMF'):
            return 10.0  # 微型臺指期貨
        elif code.startswith('TE'):
            return 4000.0 # 電子期貨
        elif code.startswith('TF'):
            return 1000.0 # 金融期貨
        return 1.0 # 預設值
    
    def get_margin_info(self, code, last_price, underlying_price=None):
        """
        [修復] 提供給 gui.py 呼叫以取得保證金和乘數資訊
        - margin: 單口原始保證金
        - multiplier: 合約乘數
        """
        code = code.strip().upper()

        if not self.has_data():
            # 無資料時提供預設值，避免程式崩潰
            multiplier = self._get_multiplier(code)
            if 'TXO' in code:
                # 選擇權使用權利金市值估算一個最低保證金
                margin = max(1000.0, last_price * multiplier * 0.1) 
            elif 'MXF' in code:
                margin = 20000.0 # 預設小台保證金
            elif 'TX' in code:
                margin = 83000.0 # 預設大台保證金
            else:
                margin = 1000.0
            
            print(f"[警告] 保證金資料未載入，使用預設值: {code} -> {margin}/{multiplier}")
            return margin, multiplier

        # 1. 取得乘數
        multiplier = self._get_multiplier(code)

        # 2. 計算單口保證金 (quantity=1)
        # 注意: TXO 需要 underlying_price
        margin = self.calculate_margin(code, 1, last_price, underlying_price)
        
        return margin, multiplier
    # ==========================================================
    
    def calculate_margin(self, code, quantity, last_price=None, underlying_price=None):
        """
        計算保證金
        - 期貨：使用固定原始保證金
        - TXO 選擇權：使用期交所公式
        """
        if not self.has_data():
            return 0

        contracts = self.margin_data.get("contracts", {})
        code = code.strip().upper()

        product_name = self._map_code_to_product(code)

        # =============== TXO 選擇權 ========================
        if product_name == "臺指選擇權":

            if last_price is None or underlying_price is None:
                print(f"[警告] TXO {code} 缺 last_price 或 underlying_price")
                return 0

            # -------- 解析履約價 --------
            # 找前方連續數字
            m = re.search(r'^TXO(\d{3,5})', code)
            if not m:
                print(f"[警告] 無法解析履約價: {code}")
                return 0
            strike = int(m.group(1))

            # -------- 判斷 C/P --------
            # 倒數第二個字母
            cp_flag = code[-2]
            is_put = cp_flag in ("P", "X")
            is_call = not is_put

            MULTIPLIER = 50

            # -------- 計算價外值 OTM --------
            if is_put:
                # Put 價外 = max(標的 - 履約, 0)
                otm_value = max(underlying_price - strike, 0) * MULTIPLIER
            else:
                # Call 價外 = max(履約 - 標的, 0)
                otm_value = max(strike - underlying_price, 0) * MULTIPLIER

            # 權利金市值
            premium_value = last_price * MULTIPLIER

            # -------- 讀 A / B / C 值 --------
            A = contracts.get("臺指選擇權風險保證金(A)值", {}).get("original_margin", 86000)
            B = contracts.get("臺指選擇權風險保證金(B)值", {}).get("original_margin", 43000)
            C = contracts.get("臺指選擇權風險保證金(C)值", {}).get("original_margin", 8600)

            # -------- TAIFEX 正式公式 --------
            original_margin = premium_value + max(A - otm_value, B)

            return original_margin * abs(quantity)

        # =============== 期貨（維持原本） ===================
        if product_name in contracts:
            margin_per_contract = contracts[product_name]['original_margin']
            return margin_per_contract * abs(quantity)

        # 模糊匹配
        for contract_name, data in contracts.items():
            if self._fuzzy_match(product_name, contract_name):
                return data['original_margin'] * abs(quantity)

        print(f"[警告] 找不到商品: {code} ({product_name})")
        return 0

    
    
    def _map_code_to_product(self, code):
        """
        將實際合約代碼對應到期交所的商品名稱
        
        對照表（根據期交所官網）:
        - 臺股期貨 (TX)
        - 小型臺指期貨 (MTX/MXF)
        - 微型臺指期貨 (TMF)
        - 臺指選擇權 (TXO)
        - 電子期貨 (TE)
        - 小型電子期貨 (ZEF)
        - 金融期貨 (TF)
        - 小型金融期貨 (ZFF)
        """
        mapping = {
            'TX': '臺股期貨',
            'TXF': '臺股期貨',
            'MTX': '小型臺指期貨',
            'MXF': '小型臺指期貨',
            'TMF': '微型臺指期貨',
            'TXO': '臺指選擇權',
            'TE': '電子期貨',
            'ZEF': '小型電子期貨',
            'TF': '金融期貨',
            'ZFF': '小型金融期貨',
        }
        
        # 檢查代碼前綴
        for prefix in sorted(mapping.keys(), key=len, reverse=True):
            if code.startswith(prefix):
                return mapping[prefix]
        
        return code
    
    def _fuzzy_match(self, code_name, contract_name):
        """模糊匹配商品名稱"""
        # 移除空格和特殊字元
        code_clean = re.sub(r'[^A-Z\u4e00-\u9fff]', '', code_name.upper())
        contract_clean = re.sub(r'[^A-Z\u4e00-\u9fff]', '', contract_name.upper())
        
        # 檢查是否包含
        return code_clean in contract_clean or contract_clean in code_clean
    
    def get_all_contracts(self):
        """取得所有合約的保證金資料"""
        if not self.has_data():
            return []
        
        contracts = self.margin_data.get('contracts', {})
        result = []
        
        for name, data in contracts.items():
            result.append({
                'name': name,
                'original_margin': data['original_margin'],
                'maintenance_margin': data['maintenance_margin']
            })
        
        return result
    
    def print_summary(self):
        """印出保證金資料摘要"""
        if not self.has_data():
            print("沒有保證金資料")
            return
        
        print(f"\n保證金資料時間: {self.get_data_timestamp()}")
        print("=" * 70)
        print(f"{'商品名稱':<25s} {'原始保證金':>12s} {'維持保證金':>12s}")
        print("-" * 70)
        
        for contract in self.get_all_contracts():
            print(f"{contract['name']:<25s} {contract['original_margin']:>12,} {contract['maintenance_margin']:>12,}")


if __name__ == "__main__":
    # 測試用
    fetcher = MarginFetcher()
    
    # 嘗試更新資料
    success, message = fetcher.fetch_and_save()
    print(f"\n結果: {message}")
    
    if success:
        fetcher.print_summary()
        
        # 測試計算
        print("\n" + "=" * 70)
        print("測試保證金計算:")
        print("-" * 70)
        test_cases = [
            ('MXFL5', 2),
            ('TMFL5', 5),
            ('TXO26500X5', 10),
            ('TXFL5', 1),
        ]
        
        for code, qty in test_cases:
            margin = fetcher.calculate_margin(code, qty)
            print(f"{code:<15s} x {qty:>2d}口 = NT$ {margin:>12,}")