#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安装验证脚本

验证AI小说编辑器的安装和基本功能是否正常。
"""

import sys
import os
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def check_python_version():
    """检查Python版本"""
    print("🐍 检查Python版本...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python版本过低: {version.major}.{version.minor}")
        print("   需要Python 3.8或更高版本")
        return False
    print(f"✅ Python版本: {version.major}.{version.minor}.{version.micro}")
    return True

def check_dependencies():
    """检查依赖包"""
    print("\n📦 检查依赖包...")
    
    required_packages = [
        ("PyQt6", "PyQt6"),
        ("pydantic", "pydantic"),
        ("aiohttp", "aiohttp"),
        ("aiofiles", "aiofiles"),
        ("openai", "openai"),
        ("requests", "requests"),
        ("markdown", "markdown"),
        ("cryptography", "cryptography"),
        ("keyring", "keyring"),
        ("Pillow", "PIL"),
        ("psutil", "psutil")
    ]
    
    missing_packages = []
    
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
            print(f"✅ {package_name}")
        except ImportError:
            print(f"❌ {package_name} - 未安装")
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"\n缺少以下依赖包: {', '.join(missing_packages)}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    return True

def check_project_structure() -> bool:
    """
    检查项目结构完整性

    验证项目的目录结构和关键文件是否存在，确保项目结构符合预期。

    Returns:
        bool: 项目结构是否完整
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info("📁 检查项目结构...")

    required_dirs = [
        "src",
        "src/application",
        "src/domain",
        "src/infrastructure",
        "src/presentation",
        "src/shared",
        "config",
        "plugins"
    ]

    required_files = [
        "main_app.py",
        "config/settings.py",
        "src/__init__.py",
        "requirements.txt"
    ]

    missing_items = []

    # 检查目录
    for dir_path in required_dirs:
        full_path = PROJECT_ROOT / dir_path
        if full_path.exists() and full_path.is_dir():
            logger.info(f"✅ {dir_path}/")
        else:
            logger.error(f"❌ {dir_path}/ - 目录不存在")
            missing_items.append(dir_path)

    # 检查文件
    for file_path in required_files:
        full_path = PROJECT_ROOT / file_path
        if full_path.exists() and full_path.is_file():
            logger.info(f"✅ {file_path}")
        else:
            logger.error(f"❌ {file_path} - 文件不存在")
            missing_items.append(file_path)

    if missing_items:
        logger.warning(f"发现 {len(missing_items)} 个缺失项目")
    else:
        logger.info("项目结构检查完成，所有必需项目都存在")

    return len(missing_items) == 0

def check_imports() -> bool:
    """
    检查核心模块导入功能

    验证项目的核心模块是否可以正常导入，确保模块依赖关系正确。

    Returns:
        bool: 所有核心模块是否可以正常导入
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info("🔧 检查核心模块导入...")

    test_imports = [
        ("config.settings", "get_settings"),
        ("src.shared.events.event_bus", "EventBus"),
        ("src.shared.ioc.container", "Container"),
        ("src.shared.utils.logger", "get_logger"),
        ("src.application.services.application_service", "ApplicationService"),
        ("src.domain.entities.project.project", "Project"),
        ("src.domain.entities.document", "Document"),
        ("src.domain.entities.character", "Character")
    ]
    
    failed_imports = []
    
    for module_name, class_name in test_imports:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"✅ {module_name}.{class_name}")
        except Exception as e:
            print(f"❌ {module_name}.{class_name} - {e}")
            failed_imports.append(f"{module_name}.{class_name}")
    
    return len(failed_imports) == 0

async def check_async_functionality():
    """检查异步功能"""
    print("\n⚡ 检查异步功能...")
    
    try:
        # 测试事件总线
        from src.shared.events.event_bus import EventBus, Event
        
        class TestEvent(Event):
            def __init__(self, message: str):
                super().__init__()
                self.message = message
        
        event_bus = EventBus()
        event_bus.start()
        
        received_events = []
        
        def test_handler(event):
            received_events.append(event.message)
        
        event_bus.subscribe(TestEvent, test_handler)
        
        # 发布测试事件
        test_event = TestEvent("test_message")
        event_bus.publish(test_event)
        
        # 等待事件处理
        await asyncio.sleep(0.1)
        
        event_bus.stop()
        
        if received_events and received_events[0] == "test_message":
            print("✅ 事件总线功能正常")
        else:
            print("❌ 事件总线功能异常")
            return False
            
    except Exception as e:
        print(f"❌ 异步功能测试失败: {e}")
        return False
    
    return True

def check_configuration():
    """检查配置系统"""
    print("\n⚙️ 检查配置系统...")
    
    try:
        from config.settings import get_settings
        
        settings = get_settings()
        
        # 检查基本配置项
        required_attrs = ['app_name', 'app_version', 'data_dir']
        
        for attr in required_attrs:
            if hasattr(settings, attr):
                print(f"✅ 配置项 {attr}: {getattr(settings, attr)}")
            else:
                print(f"❌ 缺少配置项: {attr}")
                return False
                
    except Exception as e:
        print(f"❌ 配置系统测试失败: {e}")
        return False
    
    return True

def create_test_directories():
    """创建测试目录"""
    print("\n📂 创建测试目录...")
    
    test_dirs = [
        PROJECT_ROOT / ".novel_editor",
        PROJECT_ROOT / ".novel_editor" / "cache",
        PROJECT_ROOT / ".novel_editor" / "logs",
        PROJECT_ROOT / "data",
        PROJECT_ROOT / "projects"
    ]
    
    for test_dir in test_dirs:
        try:
            test_dir.mkdir(parents=True, exist_ok=True)
            print(f"✅ {test_dir.relative_to(PROJECT_ROOT)}")
        except Exception as e:
            print(f"❌ 创建目录失败 {test_dir}: {e}")
            return False
    
    return True

async def main() -> None:
    """
    主验证函数

    执行完整的安装验证流程，包括Python版本、依赖包、项目结构、
    模块导入、配置系统、测试目录和异步功能的检查。

    Returns:
        None
    """
    import logging

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    logger = logging.getLogger(__name__)

    logger.info("🚀 AI小说编辑器安装验证")
    logger.info("=" * 50)

    checks = [
        ("Python版本", check_python_version),
        ("依赖包", check_dependencies),
        ("项目结构", check_project_structure),
        ("模块导入", check_imports),
        ("配置系统", check_configuration),
        ("测试目录", create_test_directories),
        ("异步功能", check_async_functionality)
    ]

    passed = 0
    total = len(checks)

    for check_name, check_func in checks:
        try:
            if asyncio.iscoroutinefunction(check_func):
                result = await check_func()
            else:
                result = check_func()

            if result:
                passed += 1
                logger.info(f"✅ {check_name} 检查通过")
            else:
                logger.error(f"❌ {check_name} 检查失败")

        except Exception as e:
            logger.error(f"❌ {check_name} 检查出错: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 验证结果: {passed}/{total} 项检查通过")
    
    if passed == total:
        print("🎉 所有检查通过！AI小说编辑器安装正常。")
        print("\n🚀 可以运行以下命令启动应用程序:")
        print("   python main_app.py")
        return True
    else:
        print("⚠️  部分检查失败，请解决上述问题后重新验证。")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  验证被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 验证过程出现异常: {e}")
        sys.exit(1)
