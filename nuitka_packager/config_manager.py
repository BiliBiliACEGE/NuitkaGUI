import json
import os
from datetime import datetime
from PyQt5.QtWidgets import QFileDialog

class ConfigManager:
    def __init__(self, app):
        self.app = app
        self.config_dir = "resources/saved_configs"
        os.makedirs(self.config_dir, exist_ok=True)
        
    def get_config_path(self, name):
        """获取配置文件的完整路径"""
        return os.path.join(self.config_dir, f"{name}.json")
    
    def save_config(self, config_data, name=None):
        """保存当前配置"""
        if name is None:
            name = f"config_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        config_path = self.get_config_path(name)
        
        try:
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=4)
            return True
        except Exception as e:
            QMessageBox.warning(self.app, "保存配置错误", f"无法保存配置: {str(e)}")
            return False
    
    def load_config(self, name):
        """加载指定配置"""
        config_path = self.get_config_path(name)
        
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            QMessageBox.warning(self.app, "加载配置错误", f"无法加载配置: {str(e)}")
            return None
    
    def get_saved_configs(self):
        """获取所有保存的配置列表"""
        configs = []
        for filename in os.listdir(self.config_dir):
            if filename.endswith('.json'):
                name = filename[:-5]  # 去掉.json后缀
                configs.append(name)
        return sorted(configs)
    
    def delete_config(self, name):
        """删除指定配置"""
        config_path = self.get_config_path(name)
        try:
            os.remove(config_path)
            return True
        except Exception as e:
            QMessageBox.warning(self.app, "删除配置错误", f"无法删除配置: {str(e)}")
            return False
    
    def export_config(self, config_data):
        """导出配置到用户选择的位置"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self.app, "导出配置", "", "JSON Files (*.json)", options=options)
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(config_data, f, indent=4)
                return True
            except Exception as e:
                QMessageBox.warning(self.app, "导出配置错误", f"无法导出配置: {str(e)}")
                return False
        return False
    
    def import_config(self):
        """从用户选择的位置导入配置"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self.app, "导入配置", "", "JSON Files (*.json)", options=options)
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                QMessageBox.warning(self.app, "导入配置错误", f"无法导入配置: {str(e)}")
                return None
        return None