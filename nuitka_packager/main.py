import sys
import os
from PyQt5.QtWidgets import QApplication
from ui import NuitkaPackager

def main():
    # 创建应用程序
    app = QApplication(sys.argv)
    
    # 设置应用程序字体
    font = app.font()
    font.setPointSize(10)
    app.setFont(font)
    
    # 创建主窗口
    window = NuitkaPackager()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()