#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建和部署脚本

用于打包和部署AI小说编辑器
"""

import os
import sys
import shutil
import subprocess
import zipfile
from pathlib import Path
from datetime import datetime
import argparse


class BuildManager:
    """
    构建管理器

    负责AI小说编辑器的构建、打包和部署流程。
    提供清理、构建、测试和发布等完整的构建管道功能。

    实现方式：
    - 自动检测项目结构和版本信息
    - 支持多种构建目标（开发、生产、便携版）
    - 集成PyInstaller进行可执行文件打包
    - 提供自动化的测试和验证流程
    - 支持增量构建和缓存优化

    Attributes:
        project_root: 项目根目录路径
        build_dir: 构建输出目录
        dist_dir: 分发包目录
        version: 当前版本号
    """

    def __init__(self):
        """
        初始化构建管理器

        自动检测项目路径和版本信息，创建必要的目录结构。
        """
        self.project_root = Path(__file__).parent.parent
        self.build_dir = self.project_root / "build"
        self.dist_dir = self.project_root / "dist"
        self.version = self._get_version()

    def _get_version(self) -> str:
        """
        获取项目版本号

        从VERSION文件读取版本号，如果文件不存在则生成默认版本号。

        Returns:
            str: 版本号字符串
        """
        try:
            version_file = self.project_root / "VERSION"
            if version_file.exists():
                return version_file.read_text().strip()
            else:
                return f"1.0.0-{datetime.now().strftime('%Y%m%d')}"
        except Exception:
            return "1.0.0-dev"

    def clean(self):
        """
        清理构建目录和缓存文件

        删除之前的构建输出和Python缓存文件，确保干净的构建环境。
        """
        print("🧹 清理构建目录...")

        for directory in [self.build_dir, self.dist_dir]:
            if directory.exists():
                shutil.rmtree(directory)
                print(f"   删除: {directory}")

        # 清理Python缓存
        for cache_dir in self.project_root.rglob("__pycache__"):
            shutil.rmtree(cache_dir)
            print(f"   删除缓存: {cache_dir}")
        
        print("✅ 清理完成")
    
    def install_dependencies(self):
        """安装依赖"""
        print("📦 安装依赖...")
        
        requirements_file = self.project_root / "requirements.txt"
        if requirements_file.exists():
            try:
                subprocess.run([
                    sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
                ], check=True)
                print("✅ 依赖安装完成")
            except subprocess.CalledProcessError as e:
                print(f"❌ 依赖安装失败: {e}")
                return False
        else:
            print("⚠️ 未找到requirements.txt文件")
        
        return True
    
    def run_tests(self):
        """
        运行项目测试套件

        自动安装测试依赖并运行所有测试用例。
        使用pytest框架执行测试，支持异步测试。

        Returns:
            bool: 测试是否全部通过
        """
        print("🧪 运行测试...")
        
        tests_dir = self.project_root / "tests"
        if not tests_dir.exists():
            print("⚠️ 未找到测试目录")
            return True
        
        try:
            # 安装pytest（如果未安装）
            subprocess.run([
                sys.executable, "-m", "pip", "install", "pytest", "pytest-asyncio"
            ], check=True, capture_output=True)
            
            # 运行测试
            result = subprocess.run([
                sys.executable, "-m", "pytest", str(tests_dir), "-v"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ 所有测试通过")
                return True
            else:
                print("❌ 测试失败:")
                print(result.stdout)
                print(result.stderr)
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"❌ 测试运行失败: {e}")
            return False
    
    def build_executable(self):
        """
        构建可执行文件

        使用PyInstaller将Python应用程序打包为独立的可执行文件。
        自动处理依赖关系和资源文件的打包。

        Returns:
            bool: 构建是否成功
        """
        print("🔨 构建可执行文件...")
        
        try:
            # 安装PyInstaller
            subprocess.run([
                sys.executable, "-m", "pip", "install", "pyinstaller"
            ], check=True, capture_output=True)
            
            # 创建构建目录
            self.build_dir.mkdir(exist_ok=True)
            
            # PyInstaller命令
            cmd = [
                sys.executable, "-m", "PyInstaller",
                "--name", "AI小说编辑器",
                "--onedir",
                "--windowed",
                "--icon", str(self.project_root / "assets" / "icon.ico") if (self.project_root / "assets" / "icon.ico").exists() else None,
                "--distpath", str(self.dist_dir),
                "--workpath", str(self.build_dir),
                "--specpath", str(self.build_dir),
                "--add-data", f"{self.project_root / 'assets'};assets",
                "--add-data", f"{self.project_root / 'config'};config",
                "--hidden-import", "PyQt6",
                "--hidden-import", "asyncio",
                str(self.project_root / "run_app.py")
            ]
            
            # 移除None值
            cmd = [arg for arg in cmd if arg is not None]
            
            subprocess.run(cmd, check=True)
            print("✅ 可执行文件构建完成")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ 构建失败: {e}")
            return False
    
    def create_installer(self):
        """创建安装包"""
        print("📦 创建安装包...")
        
        try:
            app_dir = self.dist_dir / "AI小说编辑器"
            if not app_dir.exists():
                print("❌ 未找到应用程序目录")
                return False
            
            # 创建ZIP安装包
            installer_name = f"AI小说编辑器-v{self.version}-{datetime.now().strftime('%Y%m%d')}.zip"
            installer_path = self.dist_dir / installer_name
            
            with zipfile.ZipFile(installer_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in app_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(app_dir.parent)
                        zipf.write(file_path, arcname)
            
            print(f"✅ 安装包创建完成: {installer_path}")
            return True
            
        except Exception as e:
            print(f"❌ 创建安装包失败: {e}")
            return False
    
    def create_portable(self):
        """创建便携版"""
        print("💼 创建便携版...")
        
        try:
            app_dir = self.dist_dir / "AI小说编辑器"
            if not app_dir.exists():
                print("❌ 未找到应用程序目录")
                return False
            
            # 创建便携版目录
            portable_dir = self.dist_dir / f"AI小说编辑器-便携版-v{self.version}"
            if portable_dir.exists():
                shutil.rmtree(portable_dir)
            
            shutil.copytree(app_dir, portable_dir)
            
            # 创建便携版标识文件
            portable_flag = portable_dir / "portable.flag"
            portable_flag.write_text("这是便携版标识文件，请勿删除")
            
            # 创建启动脚本
            start_script = portable_dir / "启动AI小说编辑器.bat"
            start_script.write_text("""@echo off
cd /d "%~dp0"
"AI小说编辑器.exe"
pause
""")
            
            print(f"✅ 便携版创建完成: {portable_dir}")
            return True
            
        except Exception as e:
            print(f"❌ 创建便携版失败: {e}")
            return False
    
    def generate_docs(self):
        """生成文档"""
        print("📚 生成文档...")
        
        try:
            docs_dir = self.project_root / "docs"
            docs_dir.mkdir(exist_ok=True)
            
            # 生成README
            readme_content = f"""# AI小说编辑器 v{self.version}

## 简介
AI小说编辑器是一款专为小说创作设计的智能写作工具，集成了AI助手、项目管理、版本控制等功能。

## 功能特性
- 🤖 AI写作助手：智能续写、对话优化、场景扩展
- 📚 项目管理：章节组织、角色管理、大纲规划
- 💾 自动备份：项目备份、版本控制、数据安全
- 🎨 界面美观：深色主题、响应式布局
- 🔌 插件系统：可扩展的功能插件
- 📊 写作统计：字数统计、进度跟踪、可读性分析

## 系统要求
- Windows 10/11 (64位)
- 内存: 4GB以上
- 硬盘: 500MB可用空间

## 安装说明
1. 下载安装包
2. 解压到任意目录
3. 运行"AI小说编辑器.exe"

## 使用指南
1. 创建新项目或打开现有项目
2. 使用AI助手进行写作辅助
3. 管理章节和角色信息
4. 定期备份项目数据

## 技术支持
如有问题请联系技术支持。

## 版本历史
- v{self.version}: 功能完善版本

---
构建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            readme_file = docs_dir / "README.md"
            readme_file.write_text(readme_content, encoding='utf-8')
            
            print("✅ 文档生成完成")
            return True
            
        except Exception as e:
            print(f"❌ 文档生成失败: {e}")
            return False
    
    def build_all(self, skip_tests=False):
        """完整构建流程"""
        print(f"🚀 开始构建 AI小说编辑器 v{self.version}")
        print("=" * 50)
        
        steps = [
            ("清理", self.clean),
            ("安装依赖", self.install_dependencies),
            ("生成文档", self.generate_docs),
        ]
        
        if not skip_tests:
            steps.append(("运行测试", self.run_tests))
        
        steps.extend([
            ("构建可执行文件", self.build_executable),
            ("创建安装包", self.create_installer),
            ("创建便携版", self.create_portable),
        ])
        
        for step_name, step_func in steps:
            print(f"\n📋 {step_name}...")
            if not step_func():
                print(f"❌ 构建失败于: {step_name}")
                return False
        
        print("\n" + "=" * 50)
        print(f"🎉 构建完成! 版本: v{self.version}")
        print(f"📁 输出目录: {self.dist_dir}")
        
        # 显示构建结果
        if self.dist_dir.exists():
            print("\n📦 构建产物:")
            for item in self.dist_dir.iterdir():
                if item.is_file():
                    size = item.stat().st_size / (1024 * 1024)  # MB
                    print(f"   📄 {item.name} ({size:.1f} MB)")
                elif item.is_dir():
                    print(f"   📁 {item.name}/")
        
        return True


def main():
    """
    构建脚本主函数

    解析命令行参数并执行相应的构建操作。
    支持清理、测试、构建等多种操作模式。

    命令行参数：
        --clean: 只清理构建目录
        --test: 只运行测试
        --skip-tests: 跳过测试直接构建
        --portable: 创建便携版
        --dev: 开发模式构建
    """
    parser = argparse.ArgumentParser(description="AI小说编辑器构建脚本")
    parser.add_argument("--clean", action="store_true", help="只清理构建目录")
    parser.add_argument("--test", action="store_true", help="只运行测试")
    parser.add_argument("--skip-tests", action="store_true", help="跳过测试")
    parser.add_argument("--docs", action="store_true", help="只生成文档")
    
    args = parser.parse_args()
    
    builder = BuildManager()
    
    if args.clean:
        builder.clean()
    elif args.test:
        builder.run_tests()
    elif args.docs:
        builder.generate_docs()
    else:
        builder.build_all(skip_tests=args.skip_tests)


if __name__ == "__main__":
    main()
