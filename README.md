# Nuitka 高级打包工具

![NuitkaGUI Logo](resources/icons/nuitka_icon.svg)

## 项目介绍

NuitkaGUI 是一个基于 PyQt5 的图形界面工具，用于简化 Nuitka 编译器的使用流程。它提供了直观的界面来配置和运行 Nuitka 打包命令，特别适合需要将 Python 代码打包为独立可执行文件的开发者。

## 主要功能

- 可视化配置 Nuitka 打包参数
- 支持单文件和目录两种打包模式
- 自动检测 Nuitka 版本和 Python 环境
- 实时显示打包进度和日志输出
- 保存和加载常用配置
- 内置美观的界面主题

## 系统要求

- Python 3.7+
- PyQt5
- Nuitka

## 安装指南

1. 克隆本仓库或下载源代码
2. 安装依赖：
   ```
   pip install PyQt5 nuitka
   ```
3. 运行主程序：
   ```
   python nuitka_packager/main.py
   ```

## 使用说明

1. 在"基本设置"选项卡中选择要打包的 Python 脚本
2. 配置输出目录和打包选项
3. 使用"高级设置"选项卡进行更精细的配置
4. 点击"开始打包"按钮启动编译过程
5. 在控制台中查看实时输出

## 界面截图

![image](https://github.com/user-attachments/assets/aaffc8aa-c253-4344-98c1-2113f3ec891d)
Nuitka显示未知版本为bug，将在下个版本修复


## 贡献指南

欢迎提交 Pull Request 或报告 Issues。

## 许可证

MIT License

## 联系方式

如有问题请联系项目维护者。
