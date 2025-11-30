# main.py
"""
Python 程式交易中控台 - 主程式入口
"""
import tkinter as tk
from gui import TradingApp

def main():
    """主程式"""
    root = tk.Tk()
    app = TradingApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()