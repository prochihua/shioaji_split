# config/config_loader.py
"""
設定檔載入模組
負責從 opds.ini 載入認證資訊
"""
import configparser
import os

def load_credentials(config_file='opds.ini'):
    """
    從設定檔載入認證資訊
    
    Args:
        config_file: 設定檔路徑,預設為 'opds.ini'
    
    Returns:
        dict: 包含 api_key, secret_key, ca_path, ca_passwd, person_id
              如果檔案不存在或讀取失敗,返回空字典
    """
    credentials = {
        'api_key': '',
        'secret_key': '',
        'ca_path': '',
        'ca_passwd': '',
        'person_id': ''
    }
    
    if not os.path.exists(config_file):
        print(f"警告: 找不到設定檔 {config_file}")
        return credentials
    
    try:
        opds = configparser.ConfigParser()
        opds.read(config_file, encoding='utf-8')
        
        if 'user_pw' in opds:
            credentials['api_key'] = opds['user_pw'].get('API_KEY', '')
            credentials['secret_key'] = opds['user_pw'].get('SECRET_KEY', '')
            credentials['ca_path'] = opds['user_pw'].get('ca_path', '')
            credentials['ca_passwd'] = opds['user_pw'].get('ca_passwd', '')
            credentials['person_id'] = opds['user_pw'].get('person_id', '')
        else:
            print("警告: 設定檔中找不到 [user_pw] 區段")
    
    except Exception as e:
        print(f"載入設定檔失敗: {e}")
    
    return credentials


def save_credentials(api_key='', secret_key='', ca_path='', 
                    ca_passwd='', person_id='', config_file='opds.ini'):
    """
    儲存認證資訊到設定檔
    
    Args:
        api_key: API Key
        secret_key: Secret Key
        ca_path: CA 憑證路徑
        ca_passwd: CA 憑證密碼
        person_id: 身分證字號
        config_file: 設定檔路徑
    
    Returns:
        bool: 是否儲存成功
    """
    try:
        opds = configparser.ConfigParser()
        
        # 如果檔案已存在,先讀取
        if os.path.exists(config_file):
            opds.read(config_file, encoding='utf-8')
        
        # 確保 [user_pw] 區段存在
        if 'user_pw' not in opds:
            opds['user_pw'] = {}
        
        # 更新資訊(只更新非空值)
        if api_key:
            opds['user_pw']['API_KEY'] = api_key
        if secret_key:
            opds['user_pw']['SECRET_KEY'] = secret_key
        if ca_path:
            opds['user_pw']['ca_path'] = ca_path
        if ca_passwd:
            opds['user_pw']['ca_passwd'] = ca_passwd
        if person_id:
            opds['user_pw']['person_id'] = person_id
        
        # 寫入檔案
        with open(config_file, 'w', encoding='utf-8') as f:
            opds.write(f)
        
        return True
    
    except Exception as e:
        print(f"儲存設定檔失敗: {e}")
        return False


def get_ca_config(config_file='opds.ini'):
    """
    取得 CA 憑證設定
    
    Returns:
        tuple: (ca_path, ca_passwd, person_id) 或 (None, None, None)
    """
    credentials = load_credentials(config_file)
    
    ca_path = credentials.get('ca_path', '')
    ca_passwd = credentials.get('ca_passwd', '')
    person_id = credentials.get('person_id', '')
    
    if ca_path and ca_passwd and person_id:
        return ca_path, ca_passwd, person_id
    
    return None, None, None


# 使用範例
if __name__ == "__main__":
    # 測試載入
    creds = load_credentials()
    print("載入的認證資訊:")
    print(f"API Key: {'*' * 10 if creds['api_key'] else '(空)'}")
    print(f"Secret Key: {'*' * 10 if creds['secret_key'] else '(空)'}")
    print(f"CA Path: {creds['ca_path'] if creds['ca_path'] else '(空)'}")
    
    # 測試 CA 設定
    ca_path, ca_passwd, person_id = get_ca_config()
    if ca_path:
        print("\nCA 憑證設定已找到")
    else:
        print("\n未找到 CA 憑證設定")