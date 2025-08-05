#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI服务仓储实现

集成多种AI服务提供商的实现
"""

import asyncio
import aiohttp
import json
import hashlib
from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime, timedelta

from src.domain.repositories.ai_service_repository import IAIServiceRepository
from src.shared.utils.logger import get_logger
from config.settings import Settings

logger = get_logger(__name__)


class AIServiceRepository(IAIServiceRepository):
    """AI服务仓储实现"""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self._session: Optional[aiohttp.ClientSession] = None
        self._client_manager: Optional['AIClientManager'] = None

        # 缓存
        self._response_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 3600  # 1小时
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取HTTP会话"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.settings.ai_service.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    def _get_client_manager(self):
        """获取AI客户端管理器（单例）"""
        if self._client_manager is None:
            from src.infrastructure.ai_clients.openai_client import AIClientManager
            self._client_manager = AIClientManager()
        return self._client_manager

    def _get_cache_key(self, prompt: str, context: str, **kwargs) -> str:
        """生成缓存键"""
        content = f"{prompt}|{context}|{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """检查缓存是否有效"""
        if 'timestamp' not in cache_entry:
            return False
        
        cache_time = datetime.fromisoformat(cache_entry['timestamp'])
        return datetime.now() - cache_time < timedelta(seconds=self._cache_ttl)
    
    async def generate_text(
        self, 
        prompt: str, 
        context: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
        model: Optional[str] = None
    ) -> str:
        """生成文本"""
        try:
            logger.info(f"🏪 AI仓储开始生成文本，提示词长度: {len(prompt)}")
            logger.debug(f"参数 - max_tokens: {max_tokens}, temperature: {temperature}, model: {model}")

            # 检查缓存
            cache_key = self._get_cache_key(prompt, context, max_tokens=max_tokens, temperature=temperature, model=model)
            if cache_key in self._response_cache:
                cache_entry = self._response_cache[cache_key]
                if self._is_cache_valid(cache_entry):
                    logger.info("💾 使用缓存的AI响应")
                    return cache_entry['response']
                else:
                    logger.debug("🗑️ 缓存已过期，删除缓存条目")
                    del self._response_cache[cache_key]

            # 使用单例AI客户端管理器
            logger.debug("🔌 获取AI客户端管理器...")
            client_manager = self._get_client_manager()
            logger.debug(f"客户端管理器类型: {type(client_manager)}")

            logger.info("📡 调用AI客户端生成文本...")
            response = await client_manager.simple_generate(
                prompt=prompt,
                context=context,
                max_tokens=max_tokens,
                temperature=temperature,
                model=model
            )

            logger.info(f"✅ AI客户端响应成功，响应长度: {len(response) if response else 0}")
            logger.debug(f"响应内容: {response[:100] if response else 'None'}...")

            # 缓存响应
            self._response_cache[cache_key] = {
                'response': response,
                'timestamp': datetime.now().isoformat()
            }
            logger.debug("💾 响应已缓存")

            return response
            
        except Exception as e:
            logger.error(f"AI文本生成失败: {e}")
            raise Exception(f"AI服务不可用: {str(e)}")
    
    async def generate_text_stream(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
        model: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """流式生成文本"""
        try:
            logger.info(f"🌊 AI仓储开始流式生成，提示词长度: {len(prompt)}")
            logger.debug(f"参数 - max_tokens: {max_tokens}, temperature: {temperature}, model: {model}")

            # 使用单例AI客户端管理器
            logger.debug("🔌 获取AI客户端管理器...")
            client_manager = self._get_client_manager()

            logger.info("📡 开始流式生成...")
            chunk_count = 0
            total_length = 0

            async for chunk in client_manager.stream_generate(
                prompt=prompt,
                context=context,
                max_tokens=max_tokens,
                temperature=temperature,
                model=model
            ):
                chunk_count += 1
                chunk_length = len(chunk) if chunk else 0
                total_length += chunk_length

                if chunk_count <= 3:
                    logger.debug(f"📝 仓储接收第 {chunk_count} 个块: {chunk[:50]}...")
                elif chunk_count % 10 == 0:
                    logger.debug(f"📊 仓储已处理 {chunk_count} 个块，总长度: {total_length}")

                yield chunk

            logger.info(f"✅ 流式生成完成，共处理 {chunk_count} 个块，总长度: {total_length}")

        except Exception as e:
            logger.error(f"❌ AI流式生成失败: {e}")
            import traceback
            logger.debug(f"错误堆栈: {traceback.format_exc()}")

            # 如果是异步迭代器错误，尝试降级到非流式生成
            if "'async for' requires an object with __aiter__ method" in str(e):
                logger.warning("检测到异步迭代器错误，尝试降级到非流式生成")
                try:
                    # 降级到非流式生成
                    result = await client_manager.simple_generate(
                        prompt=prompt,
                        context=context,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )

                    # 分块返回结果模拟流式输出
                    if result:
                        chunk_size = 15  # 每次返回15个字符
                        chunk_count = 0
                        for i in range(0, len(result), chunk_size):
                            chunk = result[i:i + chunk_size]
                            chunk_count += 1

                            if chunk_count <= 3:
                                logger.debug(f"📝 仓储模拟第 {chunk_count} 个块: {chunk[:50]}...")

                            yield chunk

                            # 添加小延迟模拟流式效果
                            import asyncio
                            await asyncio.sleep(0.05)

                    logger.info(f"✅ 模拟流式生成完成，共处理 {chunk_count} 个块")
                    return

                except Exception as fallback_error:
                    logger.error(f"降级到非流式生成也失败: {fallback_error}")

            raise Exception(f"AI流式服务不可用: {str(e)}")
    
    async def _generate_with_openai(
        self, 
        prompt: str, 
        context: str,
        max_tokens: int,
        temperature: float,
        model: Optional[str]
    ) -> str:
        """使用OpenAI生成文本"""
        if not self.settings.ai_service.openai_api_key:
            raise ValueError("OpenAI API密钥未配置")
        
        session = await self._get_session()
        
        headers = {
            "Authorization": f"Bearer {self.settings.ai_service.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if context:
            messages.append({"role": "system", "content": context})
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": model or self.settings.ai_service.openai_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        url = f"{self.settings.ai_service.openai_base_url}/chat/completions"
        
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                return result["choices"][0]["message"]["content"]
            else:
                error_text = await response.text()
                raise Exception(f"OpenAI API错误: {response.status}, {error_text}")
    
    async def _generate_with_deepseek(
        self, 
        prompt: str, 
        context: str,
        max_tokens: int,
        temperature: float,
        model: Optional[str]
    ) -> str:
        """使用DeepSeek生成文本"""
        if not self.settings.ai_service.deepseek_api_key:
            raise ValueError("DeepSeek API密钥未配置")
        
        session = await self._get_session()
        
        headers = {
            "Authorization": f"Bearer {self.settings.ai_service.deepseek_api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if context:
            messages.append({"role": "system", "content": context})
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": model or self.settings.ai_service.deepseek_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        url = f"{self.settings.ai_service.deepseek_base_url}/chat/completions"
        
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                return result["choices"][0]["message"]["content"]
            else:
                error_text = await response.text()
                raise Exception(f"DeepSeek API错误: {response.status}, {error_text}")
    

    
    async def _generate_stream_openai(
        self,
        prompt: str,
        context: str,
        max_tokens: int,
        temperature: float,
        model: Optional[str]
    ) -> AsyncGenerator[str, None]:
        """OpenAI流式生成"""
        if not self.settings.ai_service.openai_api_key:
            raise ValueError("OpenAI API密钥未配置")

        session = await self._get_session()

        headers = {
            "Authorization": f"Bearer {self.settings.ai_service.openai_api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }

        messages = []
        if context:
            messages.append({"role": "system", "content": context})
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": model or self.settings.ai_service.openai_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True
        }

        url = f"{self.settings.ai_service.openai_base_url}/chat/completions"

        try:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"OpenAI API错误: {response.status}, {error_text}")

                async for line in response.content:
                    line = line.decode('utf-8').strip()

                    if line.startswith('data: '):
                        data_str = line[6:]  # 移除 'data: ' 前缀

                        if data_str == '[DONE]':
                            break

                        try:
                            import json
                            data_obj = json.loads(data_str)

                            if 'choices' in data_obj and len(data_obj['choices']) > 0:
                                delta = data_obj['choices'][0].get('delta', {})
                                content = delta.get('content', '')

                                if content:
                                    yield content

                        except json.JSONDecodeError:
                            continue

        except Exception as e:
            logger.error(f"OpenAI流式生成失败: {e}")
            raise Exception(f"OpenAI流式服务不可用: {str(e)}")
    
    async def _generate_stream_deepseek(
        self,
        prompt: str,
        context: str,
        max_tokens: int,
        temperature: float,
        model: Optional[str]
    ) -> AsyncGenerator[str, None]:
        """DeepSeek流式生成"""
        if not self.settings.ai_service.deepseek_api_key:
            raise ValueError("DeepSeek API密钥未配置")

        session = await self._get_session()

        headers = {
            "Authorization": f"Bearer {self.settings.ai_service.deepseek_api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }

        messages = []
        if context:
            messages.append({"role": "system", "content": context})
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": model or self.settings.ai_service.deepseek_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True
        }

        url = f"{self.settings.ai_service.deepseek_base_url}/chat/completions"

        try:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"DeepSeek API错误: {response.status}, {error_text}")

                async for line in response.content:
                    line = line.decode('utf-8').strip()

                    if line.startswith('data: '):
                        data_str = line[6:]  # 移除 'data: ' 前缀

                        if data_str == '[DONE]':
                            break

                        try:
                            import json
                            data_obj = json.loads(data_str)

                            if 'choices' in data_obj and len(data_obj['choices']) > 0:
                                delta = data_obj['choices'][0].get('delta', {})
                                content = delta.get('content', '')

                                if content:
                                    yield content

                        except json.JSONDecodeError:
                            continue

        except Exception as e:
            logger.error(f"DeepSeek流式生成失败: {e}")
            raise Exception(f"DeepSeek流式服务不可用: {str(e)}")
    

    
    async def analyze_text(
        self, 
        text: str, 
        analysis_type: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """分析文本"""
        try:
            if analysis_type == "style":
                return await self._analyze_style(text, model)
            elif analysis_type == "plot":
                return await self._analyze_plot(text, model)
            elif analysis_type == "character":
                return await self._analyze_character(text, model)
            else:
                return {"error": f"不支持的分析类型: {analysis_type}"}
                
        except Exception as e:
            logger.error(f"文本分析失败: {e}")
            return {"error": str(e)}
    
    async def _analyze_style(self, text: str, model: Optional[str]) -> Dict[str, Any]:
        """风格分析"""
        # 模拟风格分析结果
        await asyncio.sleep(0.5)
        
        return {
            "analysis_type": "style",
            "characteristics": [
                "文笔流畅自然",
                "描写细腻生动",
                "情感表达丰富",
                "语言简洁明了"
            ],
            "tone": "温和亲切",
            "complexity": "中等",
            "readability": "良好",
            "suggestions": [
                "可以增加一些修辞手法",
                "适当丰富词汇表达",
                "注意句式的变化"
            ]
        }
    
    async def _analyze_plot(self, text: str, model: Optional[str]) -> Dict[str, Any]:
        """情节分析"""
        # 模拟情节分析结果
        await asyncio.sleep(0.5)
        
        return {
            "analysis_type": "plot",
            "structure": {
                "beginning": "引人入胜的开头",
                "development": "情节发展自然",
                "climax": "高潮部分需要加强",
                "resolution": "结尾有待完善"
            },
            "pacing": "节奏适中",
            "tension": "张力适度",
            "suggestions": [
                "可以增加更多冲突",
                "加强情节转折",
                "丰富细节描写"
            ]
        }
    
    async def _analyze_character(self, text: str, model: Optional[str]) -> Dict[str, Any]:
        """角色分析"""
        # 模拟角色分析结果
        await asyncio.sleep(0.5)
        
        return {
            "analysis_type": "character",
            "development": "角色发展较好",
            "consistency": "性格一致性良好",
            "depth": "人物深度适中",
            "relationships": "角色关系清晰",
            "suggestions": [
                "可以增加角色背景",
                "丰富角色内心活动",
                "加强角色对话特色"
            ]
        }
    
    async def improve_text(
        self, 
        text: str, 
        improvement_type: str,
        instructions: str = "",
        model: Optional[str] = None
    ) -> str:
        """改进文本"""
        try:
            context = f"请对以下文本进行{improvement_type}改进。"
            if instructions:
                context += f" 具体要求：{instructions}"
            
            prompt = f"原文：\n{text}\n\n改进后的文本："
            
            return await self.generate_text(prompt, context, model=model)
            
        except Exception as e:
            logger.error(f"文本改进失败: {e}")
            return text  # 返回原文
    
    async def check_availability(self, provider: str) -> bool:
        """检查特定提供商的AI服务可用性"""
        try:
            if provider == "openai":
                return bool(self.settings.ai_service.openai_api_key)
            elif provider == "deepseek":
                return bool(self.settings.ai_service.deepseek_api_key)
            else:
                return True  # 模拟服务总是可用

        except Exception as e:
            logger.error(f"检查AI服务可用性失败: {e}")
            return False

    async def is_available(self) -> bool:
        """检查AI服务整体可用性"""
        try:
            # 检查是否有任何可用的提供商
            openai_available = await self.check_availability("openai")
            deepseek_available = await self.check_availability("deepseek")

            return openai_available or deepseek_available

        except Exception as e:
            logger.error(f"检查AI服务整体可用性失败: {e}")
            return False
    
    async def get_model_info(self, model: str) -> Dict[str, Any]:
        """获取模型信息"""
        # 支持的模型信息
        model_info = {
            "gpt-3.5-turbo": {
                "name": "GPT-3.5 Turbo",
                "provider": "OpenAI",
                "max_tokens": 4096,
                "cost_per_1k_tokens": 0.002
            },
            "gpt-4": {
                "name": "GPT-4",
                "provider": "OpenAI",
                "max_tokens": 8192,
                "cost_per_1k_tokens": 0.03
            },
            "deepseek-chat": {
                "name": "DeepSeek Chat",
                "provider": "DeepSeek",
                "max_tokens": 4096,
                "cost_per_1k_tokens": 0.001
            }
        }
        
        return model_info.get(model, {"name": model, "provider": "Unknown"})
    
    async def list_available_models(self, provider: str) -> List[str]:
        """列出可用模型"""
        models = {
            "openai": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
            "deepseek": ["deepseek-chat", "deepseek-coder"]
        }

        return models.get(provider, [])

    def reload_settings(self):
        """重新加载设置"""
        try:
            logger.info("重新加载AI仓储设置...")

            # 重新加载设置对象
            from config.settings import get_settings
            self.settings = get_settings()

            # 清理缓存
            self._response_cache.clear()

            # 关闭现有会话
            if self._session and not self._session.closed:
                asyncio.create_task(self._session.close())
                self._session = None

            # 重置客户端管理器
            self._client_manager = None

            logger.info("AI仓储设置重新加载完成")

        except Exception as e:
            logger.error(f"重新加载AI仓储设置失败: {e}")
    
    async def close(self):
        """关闭连接"""
        if self._session and not self._session.closed:
            await self._session.close()
