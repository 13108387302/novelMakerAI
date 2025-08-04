# AI小说编辑器 (AI Novel Editor)

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.0%2B-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Code Quality](https://img.shields.io/badge/code%20quality-A%2B-brightgreen.svg)](#)

一个功能强大的AI驱动小说编辑器，集成了多种AI服务，提供智能写作辅助、文本分析和项目管理功能。

## ✨ 主要特性

### 🤖 AI智能辅助
- **多AI服务支持**：集成OpenAI、DeepSeek等多种AI服务
- **智能文本生成**：角色对话、场景描写、情节发展
- **流式响应**：实时显示AI生成内容
- **文本分析**：风格分析、情节结构分析、角色分析

### 📝 专业编辑功能
- **项目管理**：完整的小说项目组织和管理
- **文档类型**：支持章节、角色设定、世界观等多种文档类型
- **版本控制**：文档历史记录和版本管理
- **搜索功能**：全文搜索、正则表达式搜索

### 🎨 用户体验
- **现代化界面**：基于PyQt6的美观界面
- **主题切换**：支持明暗主题切换
- **快捷键**：丰富的键盘快捷键支持
- **插件系统**：可扩展的插件架构

### 📊 数据管理
- **多格式支持**：支持Markdown、Word、PDF等格式导入导出
- **数据备份**：自动备份和恢复功能
- **统计分析**：写作进度统计和分析

## 🏗️ 架构设计

项目采用**领域驱动设计(DDD)**和**六边形架构**，确保代码的可维护性和可扩展性：

```
src/
├── domain/          # 领域层 - 业务逻辑核心
│   ├── entities/    # 实体类
│   ├── events/      # 领域事件
│   └── repositories/ # 仓库接口
├── application/     # 应用层 - 业务用例协调
│   └── services/    # 应用服务
├── infrastructure/ # 基础设施层 - 技术实现
│   ├── ai_clients/ # AI服务客户端
│   └── repositories/ # 仓库实现
├── presentation/   # 表示层 - 用户界面
│   ├── controllers/ # 控制器
│   ├── views/      # 视图
│   ├── dialogs/    # 对话框
│   └── widgets/    # 组件
└── shared/         # 共享组件
    ├── events/     # 事件系统
    ├── ioc/        # 依赖注入
    ├── plugins/    # 插件系统
    └── utils/      # 工具类
```

### 🔧 核心技术栈
- **UI框架**：PyQt6
- **异步编程**：asyncio
- **配置管理**：Pydantic
- **事件系统**：自定义事件总线
- **依赖注入**：自定义IoC容器
- **插件系统**：动态插件加载

## 🚀 快速开始

### 环境要求
- Python 3.8+
- PyQt6
- 其他依赖见 `requirements.txt`

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd ai-novel-editor
```

2. **创建虚拟环境**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置AI服务**
   - 复制 `.novel_editor/config.json.example` 为 `config.json`
   - 配置你的AI服务API密钥

5. **运行应用**
```bash
python main_app.py
```

## ⚙️ 配置说明

### AI服务配置
在 `.novel_editor/config.json` 中配置AI服务：

```json
{
  "ai_service": {
    "default_provider": "openai",
    "openai_api_key": "your-api-key",
    "deepseek_api_key": "your-api-key",
    "temperature": 0.7,
    "max_tokens": 2000
  }
}
```

### 主题配置
```json
{
  "ui": {
    "theme": "dark",
    "font_family": "Microsoft YaHei",
    "font_size": 12
  }
}
```

## 🔌 插件开发

项目支持插件扩展，插件开发示例：

```python
from src.shared.plugins.base_plugin import BasePlugin

class MyPlugin(BasePlugin):
    def get_name(self) -> str:
        return "我的插件"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def initialize(self) -> bool:
        # 插件初始化逻辑
        return True
    
    def get_menu_actions(self) -> List[Dict]:
        return [{
            "text": "我的功能",
            "callback": self.my_function
        }]
    
    def my_function(self):
        # 插件功能实现
        pass
```

## 📚 API文档

### 核心服务

#### AIService
```python
# 文本生成
text = await ai_service.generate_text("写一段对话", "现代都市背景")

# 流式生成
async for chunk in ai_service.generate_text_stream("续写故事"):
    print(chunk, end='')

# 文本分析
analysis = await ai_service.analyze_style("要分析的文本")
```

#### ProjectService
```python
# 创建项目
project = await project_service.create_project("我的小说", "/path/to/project")

# 打开项目
project = await project_service.open_project("project_id")

# 保存项目
success = await project_service.save_current_project()
```

#### DocumentService
```python
# 创建文档
doc = await doc_service.create_document("第一章", "章节内容", project_id)

# 更新内容
success = await doc_service.update_document_content(doc_id, "新内容")
```

## 🧪 测试

运行测试套件：
```bash
# 运行所有测试
python -m pytest tests/

# 运行特定测试
python -m pytest tests/test_ai_service.py

# 生成覆盖率报告
python -m pytest --cov=src tests/
```

## 📈 性能优化

- **异步处理**：所有AI请求和文件操作都是异步的
- **内存管理**：智能缓存和资源清理
- **响应式UI**：非阻塞的用户界面更新
- **批量操作**：支持批量文档处理

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 代码规范
- 遵循 PEP 8 代码风格
- 添加适当的类型注解
- 编写完整的文档字符串
- 确保测试覆盖率 > 80%

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [OpenAI](https://openai.com/) - AI服务支持
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - UI框架
- [Pydantic](https://pydantic-docs.helpmanual.io/) - 数据验证

## 📞 联系方式

- 项目主页：[GitHub Repository](#)
- 问题反馈：[Issues](#)
- 讨论交流：[Discussions](#)

---

**AI小说编辑器** - 让AI成为你的写作伙伴 ✍️🤖
