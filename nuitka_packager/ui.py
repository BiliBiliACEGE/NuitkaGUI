import os
import sys
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog,
                            QGroupBox, QCheckBox, QComboBox, QSpinBox, QProgressBar,
                            QMessageBox, QTabWidget, QStyleFactory, QMenuBar, QMenu,
                            QAction, QListWidget, QListWidgetItem, QDialog, QFormLayout,
                            QInputDialog, QStatusBar)
from PyQt5.QtCore import Qt, QProcess, QTimer, QDateTime, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QTextCursor, QColor, QTextCharFormat
from config_manager import ConfigManager

class NuitkaPackager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nuitka 高级打包工具")
        self.setWindowIcon(QIcon(self.get_resource_path("resources/icons/nuitka_icon.svg")))
        self.setGeometry(100, 100, 900, 700)
        
        self.config_manager = ConfigManager(self)
        self.init_ui()
        self.load_stylesheet()
        
        self.process = None
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self.update_progress)
        self.current_stage = 0
        self.stage_progress = 0
        self.stages = [
            {"name": "初始化", "weight": 5, "pattern": "Initializing"},
            {"name": "编译主模块", "weight": 30, "pattern": "Compiling module"},
            {"name": "分析依赖", "weight": 15, "pattern": "Doing module dependency"},
            {"name": "包含数据文件", "weight": 10, "pattern": "Including data files"},
            {"name": "生成C代码", "weight": 15, "pattern": "Generating C source"},
            {"name": "编译二进制", "weight": 20, "pattern": "Compiling C source"},
            {"name": "最终打包", "weight": 5, "pattern": "Creating binary"}
        ]
        
        self.console_colors = {
            "INFO": QColor(0, 0, 255),
            "WARNING": QColor(255, 165, 0),
            "ERROR": QColor(255, 0, 0),
            "STAGE": QColor(0, 100, 0),
            "COMMAND": QColor(128, 0, 128)
        }
        
        self.init_statusbar()
        self.load_history()
        self.included_files = []
        self.detect_nuitka_version()

    def load_stylesheet(self):
        qss = """
        /* 主窗口样式 */
        QMainWindow {
            background-color: #f5f7fa;
        }

        /* 按钮样式 */
        QPushButton {
            background-color: #4a6fa5;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            min-width: 80px;
        }

        QPushButton:hover {
            background-color: #3a5a80;
        }

        QPushButton:pressed {
            background-color: #2c4a6e;
        }

        /* 特殊按钮样式 */
        QPushButton#run_button {
            background-color: #4caf50;
        }

        QPushButton#run_button:hover {
            background-color: #3d8b40;
        }

        QPushButton#stop_button {
            background-color: #f44336;
        }

        QPushButton#stop_button:hover {
            background-color: #d32f2f;
        }

        /* 标签样式 */
        QLabel {
            color: #333333;
            font-size: 25px;
        }

        /* 输入框样式 */
        QLineEdit, QComboBox, QSpinBox {
            border: 1px solid #d1d5db;
            border-radius: 4px;
            padding: 6px;
            background: white;
        }

        QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
            border: 1px solid #4a6fa5;
        }

        /* 复选框样式 */
        QCheckBox {
            spacing: 5px;
        }

        QCheckBox::indicator {
            width: 16px;
            height: 16px;
        }

        /* 分组框样式 */
        QGroupBox {
            border: 1px solid #d1d5db;
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 20px;
            background: white;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px;
        }

        /* 标签页样式 */
        QTabWidget::pane {
            border: 1px solid #d1d5db;
            border-radius: 4px;
            background: white;
        }

        QTabBar::tab {
            background: #e5e7eb;
            border: 1px solid #d1d5db;
            padding: 8px 16px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }

        QTabBar::tab:selected {
            background: white;
            border-bottom-color: white;
        }

        /* 进度条样式 */
        QProgressBar {
            border: 1px solid #d1d5db;
            border-radius: 4px;
            text-align: center;
            background: white;
        }

        QProgressBar::chunk {
            background-color: #4a6fa5;
            border-radius: 2px;
        }

        /* 状态栏样式 */
        QStatusBar {
            background: #e5e7eb;
            border-top: 1px solid #d1d5db;
        }

        /* 列表样式 */
        QListWidget {
            border: 1px solid #d1d5db;
            border-radius: 4px;
            background: white;
        }

        /* 控制台样式 */
        QTextEdit {
            font-family: 'Consolas', 'Courier New', monospace;
            background-color: #1e1e1e;
            color: #d4d4d4;
            border: 1px solid #d1d5db;
            border-radius: 4px;
        }
        """
        self.setStyleSheet(qss)

    def init_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.nuitka_version_label = QLabel("Nuitka: 检测中...")
        self.status_bar.addPermanentWidget(self.nuitka_version_label)
        
        self.python_env_label = QLabel(f"Python: {sys.prefix}")
        self.status_bar.addPermanentWidget(self.python_env_label)

    def detect_nuitka_version(self):
        """更健壮的版本检测方法"""
        try:
            nuitka_path = self.get_nuitka_path()
            if not nuitka_path:
                self.nuitka_version_label.setText("Nuitka: 未找到")
                return

            # 使用QProcess替代subprocess实现后台运行
            self.version_process = QProcess(self)
            self.version_process.readyReadStandardOutput.connect(self.handle_version_output)
            self.version_process.finished.connect(self.handle_version_finished)
            self.version_process.start(nuitka_path, ["--version"])
            
        except Exception as e:
            self.nuitka_version_label.setText("Nuitka: 检测异常")
            error_msg = f"检测异常: {str(e)}\n"
            error_msg += f"请尝试在命令行执行: {self.get_nuitka_path() or 'nuitka'} --version\n"
            error_msg += "并将结果截图反馈给开发者"
            
    def handle_version_output(self):
        """处理版本检测输出"""
        output = self.version_process.readAllStandardOutput().data().decode().strip()
        if output:
            version = "未知版本"
            for line in output.split('\n'):
                if line.startswith("Nuitka") or line.startswith("nuitka"):
                    # 更健壮的版本号提取逻辑
                    version_match = re.search(r'(\d+\.\d+\.\d+)', line)
                    if version_match:
                        version = version_match.group(1)
                        break
                    # 处理不同格式的版本号输出
                    version_match = re.search(r'version\s*([\d\.]+)', line, re.IGNORECASE)
                    if version_match:
                        version = version_match.group(1)
                        break
                    # 处理类似 "Nuitka v1.2.3" 格式
                    version_match = re.search(r'v(\d+\.\d+\.\d+)', line, re.IGNORECASE)
                    if version_match:
                        version = version_match.group(1)
                        break
                    parts = line.split()
                    if len(parts) >= 2:
                        version = parts[1].lstrip('v')
                        break
            
            self.version_info = output
            self.detected_version = version
            
    def handle_version_finished(self, exit_code):
        """处理版本检测完成"""
        if exit_code == 0:
            self.nuitka_version_label.setText(f"Nuitka: {self.detected_version}")
            self.append_to_console("\n=== Nuitka版本信息 ===\n", level="STAGE")
            self.append_to_console(self.version_info + "\n", level="INFO")
        else:
            error = self.version_process.readAllStandardError().data().decode()
            self.nuitka_version_label.setText("Nuitka: 检测失败")
            self.append_to_console(f"版本检测失败:\n{error}", level="ERROR")
            # 避免使用colorama的ANSI转义序列
            if hasattr(self, 'console') and self.console:
                self.append_to_console(error_msg, level="ERROR")
                cursor = self.console.textCursor()
                cursor.movePosition(QTextCursor.End)
                
                if "ERROR" in self.console_colors:
                    char_format = QTextCharFormat()
                    char_format.setForeground(self.console_colors["ERROR"])
                    cursor.setCharFormat(char_format)
                
                cursor.insertText(error_msg)
                self.console.setTextCursor(cursor)

    def get_resource_path(self, relative_path, custom_path=None):
        """将相对路径转换为绝对路径
        
        参数:
            relative_path: 相对于项目根目录或自定义路径的相对路径
            custom_path: 可选的自定义基础路径，如果提供则优先使用
        """
        # 如果提供了自定义路径，优先使用
        if custom_path and os.path.isdir(custom_path):
            resource_path = os.path.join(custom_path, relative_path)
            if os.path.exists(resource_path):
                return os.path.abspath(resource_path)
        
        # 获取当前脚本所在目录的绝对路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 检查是否是打包后的环境
        if getattr(sys, 'frozen', False):
            # 如果是打包后的环境，从临时目录中查找资源
            base_path = sys._MEIPASS
            resource_path = os.path.join(base_path, relative_path)
            if os.path.exists(resource_path):
                return os.path.abspath(resource_path)
        
        # 获取项目根目录的绝对路径
        project_root = os.path.dirname(script_dir)
        # 构建完整资源路径
        resource_path = os.path.join(project_root, relative_path)
        
        # 检查路径是否存在，如果不存在则尝试从当前工作目录查找
        if not os.path.exists(resource_path):
            cwd_path = os.path.join(os.getcwd(), relative_path)
            if os.path.exists(cwd_path):
                return os.path.abspath(cwd_path)
        
        return os.path.abspath(resource_path)
        
    def get_nuitka_path(self):
        """获取nuitka可执行文件路径"""
        # 尝试标准路径
        if sys.platform == "win32":
            possible_paths = [
                os.path.join(sys.prefix, "Scripts", "nuitka.exe"),
                os.path.join(sys.prefix, "Scripts", "nuitka.cmd"),
                os.path.join(sys.prefix, "Scripts", "nuitka-script.py"),
                os.path.join(os.environ.get("APPDATA", ""), "Python", "Scripts", "nuitka.cmd"),
                os.path.join(os.path.dirname(sys.executable), "Scripts", "nuitka.cmd")
            ]
        else:
            possible_paths = [
                os.path.join(sys.prefix, "bin", "nuitka"),
                "/usr/local/bin/nuitka",
                "/usr/bin/nuitka"
            ]
        
        # 检查可能的路径
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # 尝试通过where/which命令查找
        try:
            cmd = "where nuitka" if sys.platform == "win32" else "which nuitka"
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except:
            pass
        
            # 最后尝试直接调用nuitka（假设在PATH中）
            return "nuitka"

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        main_layout = QVBoxLayout(main_widget)
        self.create_menubar()
        
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        basic_tab = QWidget()
        tabs.addTab(basic_tab, "基本设置")
        self.setup_basic_tab(basic_tab)
        
        advanced_tab = QWidget()
        tabs.addTab(advanced_tab, "高级设置")
        self.setup_advanced_tab(advanced_tab)
        
        history_tab = QWidget()
        tabs.addTab(history_tab, "历史记录")
        self.setup_history_tab(history_tab)
        
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Courier New", 10))
        main_layout.addWidget(self.console)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        main_layout.addWidget(self.progress)
        
        button_layout = QHBoxLayout()
        
        self.run_button = QPushButton("开始打包")
        self.run_button.setObjectName("run_button")
        self.run_button.setIcon(QIcon("resources/icons/run.svg"))
        self.run_button.clicked.connect(self.start_packaging)
        
        self.preview_button = QPushButton("预览命令")
        self.preview_button.setObjectName("preview_button")
        self.preview_button.setIcon(QIcon("resources/icons/preview.svg"))
        self.preview_button.clicked.connect(self.show_command_preview)
        
        self.stop_button = QPushButton("停止")
        self.stop_button.setObjectName("stop_button")
        self.stop_button.setIcon(QIcon("resources/icons/stop.svg"))
        self.stop_button.clicked.connect(self.stop_packaging)
        self.stop_button.setEnabled(False)
        
        self.clear_button = QPushButton("清空输出")
        self.clear_button.setIcon(QIcon("resources/icons/clear.svg"))
        self.clear_button.clicked.connect(self.clear_console)
        
        button_layout.addWidget(self.run_button)
        button_layout.addWidget(self.preview_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)

    def create_menubar(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("文件")
        
        new_action = QAction("新建配置", self)
        new_action.triggered.connect(self.new_config)
        file_menu.addAction(new_action)
        
        save_action = QAction("保存配置", self)
        save_action.triggered.connect(self.save_current_config)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("另存为...", self)
        save_as_action.triggered.connect(self.save_config_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        export_action = QAction("导出配置", self)
        export_action.triggered.connect(self.export_config)
        file_menu.addAction(export_action)
        
        import_action = QAction("导入配置", self)
        import_action.triggered.connect(self.import_config)
        file_menu.addAction(import_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        tools_menu = menubar.addMenu("工具")
        
        update_nuitka_action = QAction("检查Nuitka更新", self)
        update_nuitka_action.triggered.connect(self.check_nuitka_update)
        tools_menu.addAction(update_nuitka_action)
        
        diagnosis_action = QAction("环境诊断", self)
        diagnosis_action.triggered.connect(self.show_environment_diagnosis)
        tools_menu.addAction(diagnosis_action)
        
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_basic_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        file_group = QGroupBox("文件设置")
        file_layout = QVBoxLayout()
        
        script_layout = QHBoxLayout()
        script_layout.addWidget(QLabel("Python脚本:"))
        self.script_path = QLineEdit()
        self.script_path.setPlaceholderText("选择要打包的Python脚本")
        script_layout.addWidget(self.script_path)
        script_browse = QPushButton("浏览...")
        script_browse.clicked.connect(lambda: self.browse_file(self.script_path, "Python文件 (*.py)"))
        script_layout.addWidget(script_browse)
        file_layout.addLayout(script_layout)
        
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("输出目录:"))
        self.output_dir = QLineEdit()
        self.output_dir.setPlaceholderText("选择打包输出目录")
        output_layout.addWidget(self.output_dir)
        output_browse = QPushButton("浏览...")
        output_browse.clicked.connect(lambda: self.browse_directory(self.output_dir))
        output_layout.addWidget(output_browse)
        file_layout.addLayout(output_layout)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        options_group = QGroupBox("基本选项")
        options_layout = QVBoxLayout()
        
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("打包模式:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["单文件", "目录"])
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        options_layout.addLayout(mode_layout)
        
        platform_layout = QHBoxLayout()
        platform_layout.addWidget(QLabel("目标平台:"))
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["自动检测", "Windows", "Linux", "macOS"])
        platform_layout.addWidget(self.platform_combo)
        platform_layout.addStretch()
        options_layout.addLayout(platform_layout)
        
        self.standalone_check = QCheckBox("独立打包 (--standalone)")
        self.standalone_check.setChecked(True)
        options_layout.addWidget(self.standalone_check)
        
        self.onefile_check = QCheckBox("单文件模式 (--onefile)")
        options_layout.addWidget(self.onefile_check)
        
        self.remove_output_check = QCheckBox("打包后删除临时文件 (--remove-output)")
        options_layout.addWidget(self.remove_output_check)
        
        self.show_progress_check = QCheckBox("显示进度 (--show-progress)")
        self.show_progress_check.setChecked(True)
        options_layout.addWidget(self.show_progress_check)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        layout.addStretch()

    def setup_advanced_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        optimize_group = QGroupBox("优化选项")
        optimize_layout = QVBoxLayout()
        
        self.follow_imports_check = QCheckBox("包含所有导入 (--follow-imports)")
        optimize_layout.addWidget(self.follow_imports_check)
        
        self.include_packages_check = QCheckBox("包含指定包 (--include-package)")
        self.include_packages_check.setChecked(True)
        optimize_layout.addWidget(self.include_packages_check)
        
        self.include_packages_edit = QLineEdit()
        self.include_packages_edit.setPlaceholderText("输入要包含的包名，多个用逗号分隔")
        optimize_layout.addWidget(self.include_packages_edit)
        
        self.enable_plugin_check = QCheckBox("启用插件 (--enable-plugin)")
        self.enable_plugin_check.setChecked(True)
        optimize_layout.addWidget(self.enable_plugin_check)
        
        self.plugins_edit = QLineEdit()
        self.plugins_edit.setPlaceholderText("输入要启用的插件，多个用逗号分隔")
        self.plugins_edit.setText("tk-inter,pylint-warnings")
        optimize_layout.addWidget(self.plugins_edit)
        
        optimize_group.setLayout(optimize_layout)
        layout.addWidget(optimize_group)
        
        file_include_group = QGroupBox("包含文件")
        file_include_layout = QVBoxLayout()
        
        self.included_files_list = QListWidget()
        file_include_layout.addWidget(self.included_files_list)
        
        file_buttons_layout = QHBoxLayout()
        add_file_button = QPushButton("添加文件")
        add_file_button.clicked.connect(self.add_include_file)
        remove_file_button = QPushButton("移除选中")
        remove_file_button.clicked.connect(self.remove_include_file)
        clear_files_button = QPushButton("清空列表")
        clear_files_button.clicked.connect(self.clear_include_files)
        
        file_buttons_layout.addWidget(add_file_button)
        file_buttons_layout.addWidget(remove_file_button)
        file_buttons_layout.addWidget(clear_files_button)
        file_include_layout.addLayout(file_buttons_layout)
        
        file_include_group.setLayout(file_include_layout)
        layout.addWidget(file_include_group)
        
        other_group = QGroupBox("其他选项")
        other_layout = QVBoxLayout()
        
        icon_layout = QHBoxLayout()
        icon_layout.addWidget(QLabel("程序图标:"))
        self.icon_path = QLineEdit()
        self.icon_path.setPlaceholderText("选择程序图标文件 (可选)")
        icon_layout.addWidget(self.icon_path)
        icon_browse = QPushButton("浏览...")
        icon_browse.clicked.connect(lambda: self.browse_file(self.icon_path, "图标文件 (*.ico *.icns)"))
        icon_layout.addWidget(icon_browse)
        other_layout.addLayout(icon_layout)
        
        company_layout = QHBoxLayout()
        company_layout.addWidget(QLabel("公司名称:"))
        self.company_name = QLineEdit()
        self.company_name.setPlaceholderText("输入公司名称 (可选)")
        company_layout.addWidget(self.company_name)
        other_layout.addLayout(company_layout)
        
        product_layout = QHBoxLayout()
        product_layout.addWidget(QLabel("产品名称:"))
        self.product_name = QLineEdit()
        self.product_name.setPlaceholderText("输入产品名称 (可选)")
        product_layout.addWidget(self.product_name)
        other_layout.addLayout(product_layout)
        
        version_layout = QHBoxLayout()
        version_layout.addWidget(QLabel("版本号:"))
        self.version_edit = QLineEdit()
        self.version_edit.setPlaceholderText("输入版本号 (可选)")
        version_layout.addWidget(self.version_edit)
        other_layout.addLayout(version_layout)
        
        self.console_window_check = QCheckBox("显示控制台窗口 (仅Windows)")
        self.console_window_check.setChecked(True)
        other_layout.addWidget(self.console_window_check)
        
        self.parallel_check = QCheckBox("并行编译 (--jobs)")
        self.parallel_check.setChecked(True)
        other_layout.addWidget(self.parallel_check)
        
        parallel_count_layout = QHBoxLayout()
        parallel_count_layout.addWidget(QLabel("并行任务数:"))
        self.parallel_count = QSpinBox()
        self.parallel_count.setRange(1, 32)
        self.parallel_count.setValue(4)
        parallel_count_layout.addWidget(self.parallel_count)
        parallel_count_layout.addStretch()
        other_layout.addLayout(parallel_count_layout)
        
        other_group.setLayout(other_layout)
        layout.addWidget(other_group)
        
        layout.addStretch()

    def setup_history_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self.load_config_from_history)
        layout.addWidget(self.history_list)
        
        button_layout = QHBoxLayout()
        
        self.load_history_button = QPushButton("加载配置")
        self.load_history_button.setIcon(QIcon("resources/icons/load.png"))
        self.load_history_button.clicked.connect(self.load_selected_config)
        button_layout.addWidget(self.load_history_button)
        
        self.delete_history_button = QPushButton("删除配置")
        self.delete_history_button.setIcon(QIcon("resources/icons/delete.png"))
        self.delete_history_button.clicked.connect(self.delete_selected_config)
        button_layout.addWidget(self.delete_history_button)
        
        self.refresh_history_button = QPushButton("刷新列表")
        self.refresh_history_button.setIcon(QIcon("resources/icons/refresh.png"))
        self.refresh_history_button.clicked.connect(self.load_history)
        button_layout.addWidget(self.refresh_history_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)

    def add_include_file(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择要包含的文件", "", "All Files (*)")
        if files:
            for file in files:
                if file not in self.included_files:
                    self.included_files.append(file)
                    self.included_files_list.addItem(file)

    def remove_include_file(self):
        selected_items = self.included_files_list.selectedItems()
        if not selected_items:
            return
            
        for item in selected_items:
            self.included_files.remove(item.text())
            self.included_files_list.takeItem(self.included_files_list.row(item))

    def clear_include_files(self):
        self.included_files.clear()
        self.included_files_list.clear()

    def load_history(self):
        self.history_list.clear()
        configs = self.config_manager.get_saved_configs()
        
        for config in configs:
            item = QListWidgetItem(config)
            self.history_list.addItem(item)

    def load_selected_config(self):
        selected_items = self.history_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个配置!")
            return
        
        config_name = selected_items[0].text()
        self.load_config(config_name)

    def delete_selected_config(self):
        selected_items = self.history_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个配置!")
            return
        
        config_name = selected_items[0].text()
        
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除配置 '{config_name}' 吗?", 
            QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            if self.config_manager.delete_config(config_name):
                self.load_history()
                QMessageBox.information(self, "成功", "配置已删除!")
            else:
                QMessageBox.warning(self, "错误", "删除配置失败!")

    def load_config_from_history(self, item):
        config_name = item.text()
        self.load_config(config_name)

    def load_config(self, name):
        config_data = self.config_manager.load_config(name)
        if config_data is None:
            return
        
        self.script_path.setText(config_data.get("script_path", ""))
        self.output_dir.setText(config_data.get("output_dir", ""))
        self.mode_combo.setCurrentText(config_data.get("mode", "单文件"))
        self.platform_combo.setCurrentText(config_data.get("platform", "自动检测"))
        self.standalone_check.setChecked(config_data.get("standalone", True))
        self.onefile_check.setChecked(config_data.get("onefile", False))
        self.remove_output_check.setChecked(config_data.get("remove_output", False))
        self.show_progress_check.setChecked(config_data.get("show_progress", True))
        self.follow_imports_check.setChecked(config_data.get("follow_imports", False))
        self.include_packages_check.setChecked(config_data.get("include_packages", True))
        self.include_packages_edit.setText(config_data.get("include_packages_list", ""))
        self.enable_plugin_check.setChecked(config_data.get("enable_plugin", True))
        self.plugins_edit.setText(config_data.get("plugins_list", "tk-inter,pylint-warnings"))
        self.icon_path.setText(config_data.get("icon_path", ""))
        self.company_name.setText(config_data.get("company_name", ""))
        self.product_name.setText(config_data.get("product_name", ""))
        self.version_edit.setText(config_data.get("version", ""))
        self.console_window_check.setChecked(config_data.get("console_window", True))
        self.parallel_check.setChecked(config_data.get("parallel", True))
        self.parallel_count.setValue(config_data.get("parallel_count", 4))
        
        self.included_files = config_data.get("included_files", [])
        self.included_files_list.clear()
        for file in self.included_files:
            self.included_files_list.addItem(file)
        
        self.status_bar.showMessage(f"已加载配置: {name}", 3000)

    def get_current_config(self):
        config_data = {
            "script_path": self.script_path.text(),
            "output_dir": self.output_dir.text(),
            "mode": self.mode_combo.currentText(),
            "platform": self.platform_combo.currentText(),
            "standalone": self.standalone_check.isChecked(),
            "onefile": self.onefile_check.isChecked(),
            "remove_output": self.remove_output_check.isChecked(),
            "show_progress": self.show_progress_check.isChecked(),
            "follow_imports": self.follow_imports_check.isChecked(),
            "include_packages": self.include_packages_check.isChecked(),
            "include_packages_list": self.include_packages_edit.text(),
            "enable_plugin": self.enable_plugin_check.isChecked(),
            "plugins_list": self.plugins_edit.text(),
            "icon_path": self.icon_path.text(),
            "company_name": self.company_name.text(),
            "product_name": self.product_name.text(),
            "version": self.version_edit.text(),
            "console_window": self.console_window_check.isChecked(),
            "parallel": self.parallel_check.isChecked(),
            "parallel_count": self.parallel_count.value(),
            "included_files": self.included_files.copy()
        }
        
        return config_data

    def save_current_config(self):
        config_data = self.get_current_config()
        
        if not config_data["script_path"]:
            QMessageBox.warning(self, "警告", "请先选择要打包的Python脚本!")
            return
        
        default_name = os.path.splitext(os.path.basename(config_data["script_path"]))[0]
        
        name, ok = QInputDialog.getText(
            self, "保存配置", "输入配置名称:", text=default_name)
        
        if ok and name:
            if self.config_manager.save_config(config_data, name):
                self.status_bar.showMessage(f"配置已保存: {name}", 3000)
                self.load_history()
            else:
                QMessageBox.warning(self, "错误", "保存配置失败!")

    def save_config_as(self):
        config_data = self.get_current_config()
        
        name, ok = QInputDialog.getText(
            self, "另存配置", "输入新配置名称:")
        
        if ok and name:
            if self.config_manager.save_config(config_data, name):
                self.status_bar.showMessage(f"配置已另存为: {name}", 3000)
                self.load_history()
            else:
                QMessageBox.warning(self, "错误", "保存配置失败!")

    def new_config(self):
        if any([
            self.script_path.text(),
            self.output_dir.text(),
            not self.standalone_check.isChecked(),
            self.onefile_check.isChecked(),
            self.follow_imports_check.isChecked(),
            self.include_packages_edit.text(),
            self.plugins_edit.text() != "tk-inter,pylint-warnings",
            self.icon_path.text(),
            self.company_name.text(),
            self.product_name.text(),
            self.version_edit.text(),
            self.included_files
        ]):
            reply = QMessageBox.question(
                self, "新建配置", 
                "当前配置有未保存的更改，是否保存?", 
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            
            if reply == QMessageBox.Save:
                self.save_current_config()
            elif reply == QMessageBox.Cancel:
                return
        
        self.script_path.clear()
        self.output_dir.clear()
        self.mode_combo.setCurrentIndex(0)
        self.platform_combo.setCurrentIndex(0)
        self.standalone_check.setChecked(True)
        self.onefile_check.setChecked(False)
        self.remove_output_check.setChecked(False)
        self.show_progress_check.setChecked(True)
        self.follow_imports_check.setChecked(False)
        self.include_packages_check.setChecked(True)
        self.include_packages_edit.clear()
        self.enable_plugin_check.setChecked(True)
        self.plugins_edit.setText("tk-inter,pylint-warnings")
        self.icon_path.clear()
        self.company_name.clear()
        self.product_name.clear()
        self.version_edit.clear()
        self.console_window_check.setChecked(True)
        self.parallel_check.setChecked(True)
        self.parallel_count.setValue(4)
        self.clear_include_files()
        
        self.status_bar.showMessage("已重置为新配置", 3000)

    def export_config(self):
        config_data = self.get_current_config()
        
        if not config_data["script_path"]:
            QMessageBox.warning(self, "警告", "请先配置至少包含脚本路径!")
            return
        
        if self.config_manager.export_config(config_data):
            self.status_bar.showMessage("配置已导出", 3000)
        else:
            QMessageBox.warning(self, "错误", "导出配置失败!")

    def import_config(self):
        config_data = self.config_manager.import_config()
        if config_data is None:
            return
        
        if any([
            self.script_path.text(),
            self.output_dir.text(),
            not self.standalone_check.isChecked(),
            self.onefile_check.isChecked(),
            self.follow_imports_check.isChecked(),
            self.include_packages_edit.text(),
            self.plugins_edit.text() != "tk-inter,pylint-warnings",
            self.icon_path.text(),
            self.company_name.text(),
            self.product_name.text(),
            self.version_edit.text(),
            self.included_files
        ]):
            reply = QMessageBox.question(
                self, "导入配置", 
                "当前配置有未保存的更改，是否保存?", 
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            
            if reply == QMessageBox.Save:
                self.save_current_config()
            elif reply == QMessageBox.Cancel:
                return
        
        self.load_config_from_data(config_data)
        self.status_bar.showMessage("配置已导入", 3000)

    def load_config_from_data(self, config_data):
        self.script_path.setText(config_data.get("script_path", ""))
        self.output_dir.setText(config_data.get("output_dir", ""))
        self.mode_combo.setCurrentText(config_data.get("mode", "单文件"))
        self.platform_combo.setCurrentText(config_data.get("platform", "自动检测"))
        self.standalone_check.setChecked(config_data.get("standalone", True))
        self.onefile_check.setChecked(config_data.get("onefile", False))
        self.remove_output_check.setChecked(config_data.get("remove_output", False))
        self.show_progress_check.setChecked(config_data.get("show_progress", True))
        self.follow_imports_check.setChecked(config_data.get("follow_imports", False))
        self.include_packages_check.setChecked(config_data.get("include_packages", True))
        self.include_packages_edit.setText(config_data.get("include_packages_list", ""))
        self.enable_plugin_check.setChecked(config_data.get("enable_plugin", True))
        self.plugins_edit.setText(config_data.get("plugins_list", "tk-inter,pylint-warnings"))
        self.icon_path.setText(config_data.get("icon_path", ""))
        self.company_name.setText(config_data.get("company_name", ""))
        self.product_name.setText(config_data.get("product_name", ""))
        self.version_edit.setText(config_data.get("version", ""))
        self.console_window_check.setChecked(config_data.get("console_window", True))
        self.parallel_check.setChecked(config_data.get("parallel", True))
        self.parallel_count.setValue(config_data.get("parallel_count", 4))
        
        self.included_files = config_data.get("included_files", [])
        self.included_files_list.clear()
        for file in self.included_files:
            self.included_files_list.addItem(file)

    def check_nuitka_update(self):
        self.status_bar.showMessage("正在检查Nuitka更新...")
        
        try:
            result = subprocess.run(
                ["pip", "list", "--outdated"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if result.returncode == 0:
                output = result.stdout
                if "nuitka" in output.lower():
                    self.append_to_console("Nuitka有新版本可用!\n", level="WARNING")
                    self.append_to_console("可以使用以下命令更新:\n", level="INFO")
                    self.append_to_console("pip install --upgrade nuitka\n", level="COMMAND")
                else:
                    self.append_to_console("Nuitka已是最新版本\n", level="INFO")
            else:
                self.append_to_console("检查更新失败:\n" + result.stderr, level="ERROR")
        except Exception as e:
            self.append_to_console(f"检查更新异常: {str(e)}\n", level="ERROR")
        
        self.status_bar.showMessage("Nuitka更新检查完成", 3000)

    def show_environment_diagnosis(self):
        info = [
            "=== 环境诊断信息 ===",
            f"Python路径: {sys.executable}",
            f"Python版本: {sys.version.split()[0]}",
            f"系统平台: {sys.platform}",
            f"工作目录: {os.getcwd()}",
            f"Nuitka路径: {self.get_nuitka_path() or '未找到'}",
            f"系统PATH环境变量:",
            *os.environ.get("PATH", "").split(os.pathsep)
        ]
        
        self.append_to_console("\n".join(info) + "\n", level="INFO")
        QMessageBox.information(
            self,
            "环境诊断",
            "\n".join(info[:6]) + "\n\nPATH变量已输出到控制台",
            QMessageBox.Ok
        )

    def show_about(self):
        about_text = """
        <h2>Nuitka 高级打包工具</h2>
        <p>版本: 1.1.0</p>
        <p>一个图形化界面工具，用于简化Nuitka打包过程。</p>
        <p>Nuitka是一个Python编译器，可以将Python代码编译为可执行文件。</p>
        <p>© 2023 Nuitka打包工具开发者</p>
        """
        
        QMessageBox.about(self, "关于", about_text)

    def browse_file(self, line_edit, file_filter):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文件", "", file_filter)
        if file_path:
            line_edit.setText(file_path)

    def browse_directory(self, line_edit):
        dir_path = QFileDialog.getExistingDirectory(self, "选择目录")
        if dir_path:
            line_edit.setText(dir_path)

    def generate_nuitka_command(self):
        """生成Nuitka打包命令"""
        command = ["nuitka"]
        
        # 添加基本参数
        command.append("--standalone")
        command.append("--follow-imports")
        command.append("--remove-output")
        command.append("--show-progress")
        command.append("--show-memory")
        
        # 添加高级设置中的插件选项
        if hasattr(self, 'enable_plugin_check') and self.enable_plugin_check.isChecked() and self.plugins_edit.text().strip():
            plugins = [p.strip() for p in self.plugins_edit.text().split(',') if p.strip()]
            for plugin in plugins:
                command.append(f"--enable-plugin={plugin}")
        
        # 添加包含包选项
        if hasattr(self, 'include_packages_check') and self.include_packages_check.isChecked() and self.include_packages_edit.text().strip():
            packages = [p.strip() for p in self.include_packages_edit.text().split(',') if p.strip()]
            for package in packages:
                command.append(f"--include-package={package}")
        
        # 添加Qt插件路径
        qt_plugin_path = os.path.join(
            os.path.dirname(sys.executable),
            "Lib\\site-packages\\PyQt5\\Qt5\\plugins"
        )
        command.append(f"--include-data-dir={qt_plugin_path}=PyQt5/Qt5/plugins")
        
        # 添加资源目录
        resource_path = self.get_resource_path("resources")
        if os.path.exists(resource_path):
            command.append(f"--include-data-dir={resource_path}=resources")
        
        # 添加单文件模式参数
        if self.onefile_check.isChecked():
            command.append("--onefile")
        
        # 添加输出目录
        output_dir = self.output_dir.text().strip()
        if output_dir:
            if not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir)
                except Exception as e:
                    self.append_to_console(f"错误: 无法创建输出目录 {output_dir}: {str(e)}\n", level="ERROR")
                    return None
            command.append(f"--output-dir={os.path.abspath(output_dir)}")
        else:
            default_dir = os.path.join(os.getcwd(), 'dist')
            if not os.path.exists(default_dir):
                os.makedirs(default_dir)
            command.append(f"--output-dir={default_dir}")
        
        # 添加Windows特定参数
        if sys.platform == "win32":
            if self.icon_path.text().strip():
                icon_path = os.path.abspath(self.icon_path.text().strip())
                if os.path.exists(icon_path):
                    command.append(f"--windows-icon-from-ico={icon_path}")
                else:
                    self.append_to_console(f"警告: 指定的图标文件 {icon_path} 不存在\n", level="WARNING")
            command.append("--windows-disable-console")
            command.append("--platform=windows")
        
        # 添加包含的文件
        for file_path in self.included_files:
            if os.path.isdir(file_path):
                command.append(f"--include-data-dir={file_path}={os.path.basename(file_path)}")
            else:
                command.append(f"--include-data-file={file_path}={os.path.basename(file_path)}")
        
        # 添加主模块
        command.append("main.py")
        
        return command
    
    def show_command_preview(self):
        """显示将要执行的打包命令"""
        command = " ".join(self.generate_nuitka_command())
        dialog = QDialog(self)
        dialog.setWindowTitle("命令预览")
        dialog.resize(800, 600)  # 设置对话框初始大小
        layout = QVBoxLayout(dialog)
        
        text_edit = QTextEdit()
        text_edit.setPlainText(command)
        text_edit.setReadOnly(False)
        text_edit.setFont(QFont("Courier New", 10))
        text_edit.setLineWrapMode(QTextEdit.NoWrap)  # 禁用自动换行
        text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)  # 始终显示水平滚动条
        
        button = QPushButton("关闭")
        button.clicked.connect(dialog.close)
        
        layout.addWidget(text_edit)
        layout.addWidget(button)
        dialog.exec_()
    
    def start_packaging(self):
        if not self.script_path.text():
            QMessageBox.warning(self, "错误", "请选择要打包的Python脚本!")
            return
        
        self.console.clear()
        self.current_stage = 0
        self.stage_progress = 0
        self.progress.setValue(0)
        
        try:
            nuitka_path = self.get_nuitka_path()
            if not nuitka_path:
                raise FileNotFoundError("无法定位nuitka可执行文件")
            
            command = [nuitka_path]
            
            if self.standalone_check.isChecked():
                command.append("--standalone")
            
            if self.onefile_check.isChecked():
                command.append("--onefile")
            
            if self.remove_output_check.isChecked():
                command.append("--remove-output")
            
            if self.show_progress_check.isChecked():
                command.append("--show-progress")
            
            if self.output_dir.text():
                command.append(f"--output-dir={self.output_dir.text()}")
            
            for file_path in self.included_files:
                command.append(f"--include-data-file={file_path}={os.path.basename(file_path)}")
            
            platform_map = {
                "Windows": "win",
                "Linux": "linux",
                "macOS": "macos"
            }
            if self.platform_combo.currentIndex() > 0:
                platform = platform_map[self.platform_combo.currentText()]
                command.append(f"--assume-platform={platform}")
            
            if self.follow_imports_check.isChecked():
                command.append("--follow-imports")
            
            if self.include_packages_check.isChecked() and self.include_packages_edit.text():
                packages = self.include_packages_edit.text().split(",")
                for pkg in packages:
                    command.append(f"--include-package={pkg.strip()}")
            
            if self.enable_plugin_check.isChecked() and self.plugins_edit.text():
                plugins = self.plugins_edit.text().split(",")
                for plugin in plugins:
                    command.append(f"--enable-plugin={plugin.strip()}")
            
            if self.icon_path.text():
                command.append(f"--windows-icon-from-ico={self.icon_path.text()}")
            
            if self.company_name.text():
                command.append(f"--windows-company-name={self.company_name.text()}")
            
            if self.product_name.text():
                command.append(f"--windows-product-name={self.product_name.text()}")
            
            if self.version_edit.text():
                command.append(f"--windows-product-version={self.version_edit.text()}")
            
            if not self.console_window_check.isChecked():
                command.append("--windows-disable-console")
            
            if self.parallel_check.isChecked():
                command.append(f"--jobs={self.parallel_count.value()}")
            
            command.append(self.script_path.text())
            
            self.append_to_console("=== 执行命令 ===\n", level="STAGE")
            self.append_to_console(" ".join(command).replace("\\", "/") + "\n\n", level="COMMAND")
            
            # 使用QProcess执行打包命令
            try:
                self.process = QProcess(self)
                self.process.setProcessChannelMode(QProcess.MergedChannels)
                self.process.readyReadStandardOutput.connect(self.handle_process_output)
                self.process.readyReadStandardError.connect(self.handle_process_output)
                self.process.finished.connect(self.process_finished)
                
                # 设置工作目录
                if self.output_dir.text():
                    try:
                        os.makedirs(self.output_dir.text(), exist_ok=True)
                        self.process.setWorkingDirectory(self.output_dir.text())
                    except Exception as e:
                        error_msg = f"无法创建输出目录: {str(e)}\n"
                        self.append_to_console(error_msg, level="ERROR")
                        self.run_button.setEnabled(True)
                        self.stop_button.setEnabled(False)
                        return
                
                self.process.start(command[0], command[1:])
                
                self.run_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                self.progress_timer.start(80)
                
                self.start_time = QDateTime.currentDateTime()
                self.append_to_console(f"打包开始于: {self.start_time.toString('yyyy-MM-dd hh:mm:ss')}\n", 
                                    level="INFO")
                
            except Exception as e:
                error_msg = f"启动进程失败: {str(e)}\n"
                self.append_to_console(error_msg, level="ERROR")
                self.run_button.setEnabled(True)
                self.stop_button.setEnabled(False)
            
        except Exception as e:
            error_msg = f"""
            启动失败详细诊断:
            - 错误类型: {type(e).__name__}
            - 错误信息: {str(e)}
            - Nuitka路径: {self.get_nuitka_path() or '未找到'}
            - Python路径: {sys.executable}
            - 工作目录: {os.getcwd()}
            """
            # 避免使用colorama的ANSI转义序列
            error_msg = error_msg.replace("\\", "/")
            plain_message = error_msg
            
            if hasattr(self, 'console') and self.console:
                cursor = self.console.textCursor()
                cursor.movePosition(QTextCursor.End)
            
            if "ERROR" in self.console_colors:
                char_format = QTextCharFormat()
                char_format.setForeground(self.console_colors["ERROR"])
                cursor.setCharFormat(char_format)
            
                cursor.insertText(plain_message)
                self.console.setTextCursor(cursor)
                self.progress.setValue(0)
                self.run_button.setEnabled(True)
                self.stop_button.setEnabled(False)

    def handle_process_output(self):
        """处理打包进程的输出"""
        if not self.process:
            return
            
        # 读取标准输出
        output = self.process.readAllStandardOutput().data().decode().strip()
        if output:
            self.append_to_console(output, level="INFO")
            
            # 更新进度条状态
            for line in output.split('\n'):
                for stage in self.stages:
                    if stage["pattern"] in line:
                        self.current_stage = self.stages.index(stage)
                        self.stage_progress = 0
                        self.append_to_console(f"\n=== 进入阶段: {stage['name']} ===\n", level="STAGE")
                        break
                
                # 简单模拟进度更新
                if "Progress" in line:
                    self.stage_progress = min(self.stage_progress + 5, 100)
                
                # 检测到输出文件行时才标记为完成
                if "输出文件:" in line:
                    self.current_stage = len(self.stages) - 1
                    self.stage_progress = 100
                    # 只在检测到输出文件行后显示完成弹窗
                    QMessageBox.information(self, "打包完成", "Nuitka打包已完成！")
                    # 打开输出目录
                    output_dir = line.split(":")[1].strip()
                    if os.path.exists(output_dir):
                        from PyQt5.QtGui import QDesktopServices
                        from PyQt5.QtCore import QUrl
                        QDesktopServices.openUrl(QUrl.fromLocalFile(output_dir))
                    
            # 计算总进度
            total_progress = 0
            for i, stage in enumerate(self.stages):
                if i < self.current_stage:
                    total_progress += stage["weight"]
                elif i == self.current_stage:
                    total_progress += stage["weight"] * (self.stage_progress / 100)
                    
            self.progress.setValue(int(total_progress))
            
        # 读取错误输出
        error = self.process.readAllStandardError().data().decode().strip()
        if error:
            self.append_to_console(error, level="ERROR")
    
    def stop_packaging(self):
        """停止打包进程"""
        if self.process and self.process.state() == QProcess.Running:
            self.process.terminate()
            self.append_to_console("\n打包过程已终止\n", level="WARNING")
        
        if hasattr(self, 'output_thread'):
            self.output_thread.terminate()
        
        self.progress_timer.stop()
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def update_progress(self, output_line=None):
        if output_line:
            # 根据Nuitka的实际输出更新进度
            for i, stage in enumerate(self.stages):
                if stage["pattern"] in output_line:
                    if i > self.current_stage:
                        # 进入新阶段时重置进度
                        self.current_stage = i
                        self.stage_progress = 0
                        self.progress.setValue(0)
                    break
        
        if self.current_stage < len(self.stages):
            # 缓慢增加当前阶段的进度
            self.stage_progress = min(self.stage_progress + 2, 100)
            
            # 显示当前阶段进度
            self.progress.setValue(self.stage_progress)
            
            # 当前阶段完成后自动进入下一阶段
            if self.stage_progress >= 100:
                if self.current_stage < len(self.stages) - 1:
                    self.current_stage += 1
                    self.stage_progress = 0
                else:
                    # 所有阶段完成
                    self.progress_timer.stop()
        else:
            # 打包失败处理
            self.progress_timer.stop()
            QMessageBox.warning(self, "错误", "打包过程中出现错误！")

    def process_finished(self, exit_code, exit_status):
        self.progress_timer.stop()
        
        if hasattr(self, 'output_thread'):
            self.output_thread.terminate()
        
        end_time = QDateTime.currentDateTime()
        elapsed = self.start_time.secsTo(end_time)
        
        # 确保所有输出都已处理完毕
        QApplication.processEvents()
        
        if exit_code == 0:
            self.progress.setValue(100)
            self.append_to_console("\n=== 打包成功 ===\n", level="STAGE")
            self.append_to_console(f"耗时: {elapsed}秒\n", level="INFO")
            
            # 显示输出路径信息但不强制检查文件是否存在
            if self.output_dir.text():
                output_path = os.path.join(self.output_dir.text(), 
                                         os.path.basename(self.script_path.text()))
                if self.onefile_check.isChecked():
                    output_path = output_path.replace(".py", ".exe" if sys.platform == "win32" else "")
                else:
                    output_path = os.path.join(output_path, os.path.basename(self.script_path.text()).replace(".py", ".dist"), os.path.basename(self.script_path.text()).replace(".py", ".exe"))
                
                self.append_to_console(f"预期输出文件: {output_path}\n", level="INFO")
        else:
            self.progress.setValue(0)
            self.append_to_console("\n=== 打包失败 ===\n", level="ERROR")
            self.append_to_console(f"进程退出代码: {exit_code}\n", level="ERROR")
            self.append_to_console(f"耗时: {elapsed}秒\n", level="INFO")
        
        # 确保UI状态更新完成
        QApplication.processEvents()
        
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def append_to_console(self, text, color=None, level="INFO"):
        """更安全的控制台输出方法，避免使用colorama"""
        timestamp = QDateTime.currentDateTime().toString("[hh:mm:ss] ")
        
        # 使用Qt原生颜色代替colorama
        self.console.moveCursor(QTextCursor.End)
        self.console.setTextColor(Qt.gray)
        self.console.insertPlainText(timestamp)
        
        if level == "INFO":
            self.console.setTextColor(Qt.blue)
        elif level == "WARNING":
            self.console.setTextColor(QColor(255, 165, 0))  # 橙色
        elif level == "ERROR":
            self.console.setTextColor(Qt.red)
        elif level == "STAGE":
            self.console.setTextColor(Qt.darkGreen)
        elif level == "COMMAND":
            self.console.setTextColor(QColor(128, 0, 128))  # 紫色
        else:
            self.console.setTextColor(Qt.black)
            
        self.console.insertPlainText(text)
        self.console.ensureCursorVisible()

    def clear_console(self):
        self.console.clear()

class OutputThread(QThread):
    output_signal = pyqtSignal(str, str)
    
    def __init__(self, process, parent=None):
        super().__init__(parent)
        self.process = process
        self.parent = parent
    
    def run(self):
        if not self.process:
            self.output_signal.emit("进程未正确初始化\n", "ERROR")
            return
            
        if not hasattr(self.process, 'stdout') or not self.process.stdout:
            self.output_signal.emit("进程输出管道未正确设置\n", "ERROR")
            return
            
        while True:
            output = self.process.stdout.readline()
            if output == '' and self.process.poll() is not None:
                break
            if output:
                self.output_signal.emit(output, "INFO")
                if self.parent:
                    self.parent.update_progress(output)
        
        if hasattr(self.process, 'stderr') and self.process.stderr:
            error = self.process.stderr.read()
            if error:
                self.output_signal.emit(error, "ERROR")