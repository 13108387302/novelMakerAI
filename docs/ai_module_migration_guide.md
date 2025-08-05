# AI模块迁移指南

## 📋 概述

本指南详细说明如何从旧版本AI模块迁移到重构后的新架构。新架构遵循DDD（领域驱动设计）原则，提供更好的代码质量、可维护性和100%智能化功能。

## 🎯 迁移目标

- ✅ **保持100%智能化功能**：所有AI功能继续支持智能化执行
- ✅ **提升架构质量**：遵循DDD原则，提高代码质量
- ✅ **向后兼容**：现有代码无需修改即可继续工作
- ✅ **性能优化**：更好的异步处理和资源管理
- ✅ **易于扩展**：更容易添加新功能和提供商

## 🏗️ 架构对比

### 旧架构
```
src/application/services/ai/
├── ai_service_manager.py          # 服务管理器
├── base_ai_service.py             # 基础服务
├── core_abstractions.py          # 核心抽象
├── function_modules.py            # 功能模块
├── providers.py                   # 提供商适配器
├── performance_monitor.py         # 性能监控
└── unified_ai_service.py          # 统一AI服务
```

### 新架构（DDD）
```
src/
├── domain/ai/                     # 领域层
│   ├── entities/                  # 实体
│   │   ├── ai_request.py
│   │   └── ai_response.py
│   └── value_objects/             # 值对象
│       ├── ai_execution_mode.py
│       ├── ai_request_type.py
│       ├── ai_priority.py
│       └── ai_capability.py
├── application/services/ai/       # 应用层
│   ├── core/                      # 核心服务
│   │   └── ai_orchestration_service.py
│   ├── intelligence/              # 智能化服务
│   │   ├── ai_intelligence_service.py
│   │   ├── ai_function_registry.py
│   │   └── builtin_functions.py
│   └── legacy/                    # 向后兼容
├── infrastructure/ai/             # 基础设施层
│   └── clients/                   # AI客户端
│       ├── base_ai_client.py
│       ├── openai_client.py
│       ├── deepseek_client.py
│       └── ai_client_factory.py
└── presentation/widgets/ai/       # 表现层
    └── refactored/                # 重构后的UI组件
        ├── components/
        ├── panels/
        └── intelligence/
```

## 🔄 迁移步骤

### 步骤1：了解新架构

#### 核心组件映射

| 旧组件 | 新组件 | 说明 |
|--------|--------|------|
| `AIServiceManager` | `AIOrchestrationService` | 主要的AI服务编排器 |
| `UnifiedAIService` | `AIOrchestrationService` | 统一的AI请求处理 |
| `BaseFunctionModule` | `AIIntelligentFunction` | 智能化功能基类 |
| `ai_function_registry` | `ai_function_registry` | 功能注册表（增强版） |
| `OpenAIProvider` | `OpenAIClient` | OpenAI客户端 |
| `DeepSeekProvider` | `DeepSeekClient` | DeepSeek客户端 |

#### 智能化执行模式

新架构提供更丰富的智能化执行模式：

```python
from src.domain.ai.value_objects.ai_execution_mode import AIExecutionMode

# 100%智能化模式
AIExecutionMode.AUTO_CONTEXT      # 自动基于上下文执行
AIExecutionMode.AUTO_SELECTION    # 自动基于选中文字执行
AIExecutionMode.HYBRID            # 智能选择输入源
AIExecutionMode.MANUAL_INPUT      # 手动输入（兼容模式）
```

### 步骤2：更新导入语句

#### 旧版本导入
```python
# 旧版本
from src.application.services.ai import AIServiceManager
from src.application.services.ai import UnifiedAIService
from src.application.services.ai.function_modules import BaseFunctionModule
```

#### 新版本导入
```python
# 新版本
from src.application.services.ai.core.ai_orchestration_service import AIOrchestrationService
from src.application.services.ai.intelligence.ai_intelligence_service import AIIntelligenceService
from src.application.services.ai.intelligence.ai_function_registry import ai_function_registry
```

#### 兼容性导入（推荐）
```python
# 使用兼容性导入，自动选择最佳版本
from src.application.services.ai import get_ai_service
from src.application.services.ai import get_ai_function_registry

# 获取AI服务（自动选择新旧版本）
ai_service = get_ai_service(config)
```

### 步骤3：更新服务初始化

#### 旧版本初始化
```python
# 旧版本
ai_service_manager = AIServiceManager(config)
unified_ai_service = UnifiedAIService(providers)
```

#### 新版本初始化
```python
# 新版本
config = {
    'providers': {
        'openai': {
            'api_key': 'your-api-key',
            'default_model': 'gpt-3.5-turbo'
        }
    },
    'default_provider': 'openai'
}

ai_orchestration_service = AIOrchestrationService(config)
await ai_orchestration_service.initialize()

ai_intelligence_service = AIIntelligenceService()
ai_intelligence_service.initialize()
```

### 步骤4：更新AI功能注册

#### 旧版本功能注册
```python
# 旧版本
class MyAIFunction(BaseFunctionModule):
    def __init__(self):
        super().__init__("my_function", "我的AI功能")
    
    def execute(self, input_text):
        # 功能实现
        pass

# 手动注册
ai_function_registry.register("my_function", MyAIFunction())
```

#### 新版本功能注册
```python
# 新版本 - 使用装饰器注册
from src.application.services.ai.intelligence.ai_function_registry import register_ai_function
from src.application.services.ai.intelligence.ai_intelligence_service import AIIntelligentFunction
from src.domain.ai.value_objects.ai_execution_mode import AIExecutionMode

@register_ai_function(
    function_id="my_intelligent_function",
    name="我的智能AI功能",
    description="这是一个100%智能化的AI功能",
    category=AIFunctionCategory.GENERATION,
    execution_mode=AIExecutionMode.AUTO_CONTEXT,  # 100%智能化
    icon="🤖",
    smart_description="无需输入，AI自动分析文档内容"
)
class MyIntelligentFunction(AIIntelligentFunction):
    def can_auto_execute(self, context: str = "", selected_text: str = "") -> bool:
        return len(context.strip()) >= 50  # 智能检测是否可执行
    
    def _build_intelligent_prompt(self, input_text: str, context: str, selected_text: str) -> str:
        return f"请基于以下内容进行智能处理：\n{context}"
```

### 步骤5：更新UI组件

#### 旧版本UI组件
```python
# 旧版本
from src.presentation.widgets.ai import AIFunctionPanel

panel = AIFunctionPanel(parent)
panel.set_ai_service(ai_service)
```

#### 新版本UI组件
```python
# 新版本
from src.presentation.widgets.ai.refactored import create_intelligent_ai_panel

panel = create_intelligent_ai_panel(parent)
if panel:
    panel.set_context(document_context="文档内容", selected_text="选中文字")
```

### 步骤6：更新配置

#### 旧版本配置
```python
# 旧版本配置
ai_config = {
    'openai_api_key': 'your-key',
    'openai_model': 'gpt-3.5-turbo',
    'max_requests': 10
}
```

#### 新版本配置
```python
# 新版本配置
ai_config = {
    'providers': {
        'openai': {
            'api_key': 'your-key',
            'base_url': 'https://api.openai.com/v1',
            'default_model': 'gpt-3.5-turbo',
            'max_tokens': 2000,
            'temperature': 0.7
        },
        'deepseek': {
            'api_key': 'your-deepseek-key',
            'base_url': 'https://api.deepseek.com/v1',
            'default_model': 'deepseek-chat'
        }
    },
    'default_provider': 'openai',
    'max_concurrent_requests': 10,
    'request_timeout': 30.0,
    'retry_attempts': 3
}
```

## 🔧 常见迁移场景

### 场景1：简单AI功能调用

#### 旧版本
```python
ai_service = get_ai_service()
result = ai_service.generate_text("写一个故事")
```

#### 新版本
```python
# 方式1：直接使用编排服务
ai_service = AIOrchestrationService(config)
await ai_service.initialize()

request = AIRequest(
    prompt="写一个故事",
    request_type=AIRequestType.CREATIVE_WRITING,
    execution_mode=AIExecutionMode.MANUAL_INPUT
)

response = await ai_service.process_request(request)
```

#### 兼容性方式
```python
# 方式2：使用兼容性函数（推荐）
ai_service = get_ai_service(config)
result = ai_service.generate_text("写一个故事")  # 自动适配新旧版本
```

### 场景2：智能化功能执行

#### 新版本（100%智能化）
```python
# 获取智能化功能
function = ai_function_registry.get_function("intelligent_continuation")

# 检查是否可以智能执行
if function.can_auto_execute(context="当前文档内容"):
    # 构建智能化请求
    request = function.build_auto_request(context="当前文档内容")
    
    # 执行请求
    response = await ai_service.process_request(request)
```

### 场景3：自定义AI功能

#### 旧版本
```python
class CustomFunction(BaseFunctionModule):
    def execute(self, input_text):
        return f"处理结果: {input_text}"

ai_function_registry.register("custom", CustomFunction())
```

#### 新版本
```python
@register_ai_function(
    function_id="custom_intelligent",
    name="自定义智能功能",
    description="智能处理用户输入",
    category=AIFunctionCategory.OPTIMIZATION,
    execution_mode=AIExecutionMode.HYBRID,  # 智能化模式
    icon="⚡"
)
class CustomIntelligentFunction(AIIntelligentFunction):
    def can_auto_execute(self, context: str = "", selected_text: str = "") -> bool:
        return bool(context.strip()) or bool(selected_text.strip())
    
    def _build_intelligent_prompt(self, input_text: str, context: str, selected_text: str) -> str:
        if selected_text:
            return f"请优化以下选中文字: {selected_text}"
        else:
            return f"请分析以下内容: {context}"
```

## ⚠️ 注意事项

### 1. 向后兼容性
- 旧版本API继续可用，但会显示弃用警告
- 建议逐步迁移到新版本API
- 新旧版本可以并存运行

### 2. 配置迁移
- 旧版本配置自动兼容
- 建议更新到新版本配置格式以获得更多功能

### 3. 性能考虑
- 新版本使用异步处理，性能更好
- 建议在异步环境中使用新版本API

### 4. 智能化功能
- 新版本提供更丰富的智能化执行模式
- 建议将现有功能升级为智能化功能

## 🚀 迁移检查清单

- [ ] 了解新架构和组件映射
- [ ] 更新导入语句
- [ ] 更新服务初始化代码
- [ ] 迁移AI功能注册
- [ ] 更新UI组件使用
- [ ] 更新配置格式
- [ ] 测试功能完整性
- [ ] 验证智能化功能
- [ ] 性能测试
- [ ] 文档更新

## 📞 支持

如果在迁移过程中遇到问题：

1. 查看详细的API文档
2. 参考示例代码
3. 检查日志中的弃用警告
4. 使用兼容性函数作为过渡方案

## 🎉 迁移完成

迁移完成后，您将获得：

- ✅ **100%智能化**：所有AI功能支持智能化执行
- ✅ **更好的架构**：清晰的DDD分层架构
- ✅ **更高的性能**：异步处理和资源优化
- ✅ **更强的扩展性**：易于添加新功能和提供商
- ✅ **更好的维护性**：高质量、低耦合的代码

恭喜您成功迁移到新的AI模块架构！🎊
