#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI配置验证工具

验证AI服务配置是否正确
"""

import logging
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)


class AIConfigValidator:
    """AI配置验证器"""
    
    @staticmethod
    def validate_ai_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证AI配置
        
        Args:
            config: AI配置字典
            
        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误信息列表)
        """
        errors = []
        
        # 检查基础配置
        if not config:
            errors.append("AI配置为空")
            return False, errors
        
        # 检查提供商配置
        providers = config.get('providers', {})
        if not providers:
            errors.append("未配置AI提供商")
        else:
            # 验证每个提供商
            for provider_name, provider_config in providers.items():
                provider_errors = AIConfigValidator._validate_provider_config(
                    provider_name, provider_config
                )
                errors.extend(provider_errors)
        
        # 检查默认提供商
        default_provider = config.get('default_provider')
        if not default_provider:
            errors.append("未设置默认AI提供商")
        elif default_provider not in providers:
            errors.append(f"默认提供商 '{default_provider}' 未在providers中配置")
        
        # 检查性能配置
        max_concurrent = config.get('max_concurrent_requests', 0)
        if max_concurrent <= 0:
            errors.append("max_concurrent_requests 必须大于0")
        
        timeout = config.get('request_timeout', 0)
        if timeout <= 0:
            errors.append("request_timeout 必须大于0")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def _validate_provider_config(provider_name: str, config: Dict[str, Any]) -> List[str]:
        """验证提供商配置"""
        errors = []
        
        if provider_name == 'openai':
            errors.extend(AIConfigValidator._validate_openai_config(config))
        elif provider_name == 'deepseek':
            errors.extend(AIConfigValidator._validate_deepseek_config(config))
        else:
            errors.append(f"未知的提供商: {provider_name}")
        
        return errors
    
    @staticmethod
    def _validate_openai_config(config: Dict[str, Any]) -> List[str]:
        """验证OpenAI配置"""
        errors = []
        
        # 检查API密钥
        api_key = config.get('api_key')
        if not api_key:
            errors.append("OpenAI API密钥未配置")
        elif not api_key.startswith('sk-'):
            errors.append("OpenAI API密钥格式不正确")
        
        # 检查基础URL
        base_url = config.get('base_url')
        if not base_url:
            errors.append("OpenAI base_url未配置")
        
        # 检查模型
        model = config.get('model')
        if not model:
            errors.append("OpenAI模型未配置")
        
        return errors
    
    @staticmethod
    def _validate_deepseek_config(config: Dict[str, Any]) -> List[str]:
        """验证DeepSeek配置"""
        errors = []
        
        # 检查API密钥
        api_key = config.get('api_key')
        if not api_key:
            errors.append("DeepSeek API密钥未配置")
        elif not api_key.startswith('sk-'):
            errors.append("DeepSeek API密钥格式不正确")
        
        # 检查基础URL
        base_url = config.get('base_url')
        if not base_url:
            errors.append("DeepSeek base_url未配置")
        
        # 检查模型
        model = config.get('model')
        if not model:
            errors.append("DeepSeek模型未配置")
        
        return errors
    
    @staticmethod
    def get_ai_config_from_settings(settings_service) -> Optional[Dict[str, Any]]:
        """从设置服务获取AI配置"""
        try:
            config = {
                'default_provider': settings_service.get('ai.default_provider', 'deepseek'),
                'max_concurrent_requests': settings_service.get('ai.max_concurrent_requests', 5),
                'request_timeout': settings_service.get('ai.timeout', 30),
                'retry_attempts': settings_service.get('ai.retry_attempts', 3),
                'enable_streaming': settings_service.get('ai.enable_streaming', True),
                'providers': {}
            }
            
            # OpenAI配置
            openai_api_key = settings_service.get('ai.openai_api_key')
            if openai_api_key:
                config['providers']['openai'] = {
                    'api_key': openai_api_key,
                    'base_url': settings_service.get('ai.openai_base_url', 'https://api.openai.com/v1'),
                    'model': settings_service.get('ai.openai_model', 'gpt-3.5-turbo'),
                    'max_tokens': settings_service.get('ai.max_tokens', 2000),
                    'temperature': settings_service.get('ai.temperature', 0.7)
                }
            
            # DeepSeek配置
            deepseek_api_key = settings_service.get('ai.deepseek_api_key')
            if deepseek_api_key:
                config['providers']['deepseek'] = {
                    'api_key': deepseek_api_key,
                    'base_url': settings_service.get('ai.deepseek_base_url', 'https://api.deepseek.com/v1'),
                    'model': settings_service.get('ai.deepseek_model', 'deepseek-chat'),
                    'max_tokens': settings_service.get('ai.max_tokens', 2000),
                    'temperature': settings_service.get('ai.temperature', 0.7)
                }
            
            return config
            
        except Exception as e:
            logger.error(f"获取AI配置失败: {e}")
            return None
    
    @staticmethod
    def diagnose_ai_service(ai_orchestration_service) -> Dict[str, Any]:
        """诊断AI服务状态"""
        diagnosis = {
            'service_available': False,
            'service_initialized': False,
            'clients_status': {},
            'errors': []
        }
        
        try:
            if not ai_orchestration_service:
                diagnosis['errors'].append("AI编排服务未找到")
                return diagnosis
            
            diagnosis['service_available'] = True
            diagnosis['service_initialized'] = ai_orchestration_service.is_initialized
            
            if hasattr(ai_orchestration_service, 'clients'):
                for provider, client in ai_orchestration_service.clients.items():
                    diagnosis['clients_status'][provider] = {
                        'connected': client.is_connected if client else False,
                        'last_error': client.last_error if client else "客户端未创建"
                    }
            
            if hasattr(ai_orchestration_service, 'client_health'):
                for provider, health in ai_orchestration_service.client_health.items():
                    if provider in diagnosis['clients_status']:
                        diagnosis['clients_status'][provider]['healthy'] = health
            
        except Exception as e:
            diagnosis['errors'].append(f"诊断过程出错: {str(e)}")
        
        return diagnosis
    
    @staticmethod
    def format_diagnosis_report(diagnosis: Dict[str, Any]) -> str:
        """格式化诊断报告"""
        report = "🔍 AI服务诊断报告\n"
        report += "=" * 30 + "\n\n"
        
        # 服务状态
        if diagnosis['service_available']:
            report += "✅ AI编排服务: 可用\n"
            if diagnosis['service_initialized']:
                report += "✅ 服务状态: 已初始化\n"
            else:
                report += "⚠️ 服务状态: 未初始化\n"
        else:
            report += "❌ AI编排服务: 不可用\n"
        
        # 客户端状态
        report += "\n📡 AI客户端状态:\n"
        if diagnosis['clients_status']:
            for provider, status in diagnosis['clients_status'].items():
                report += f"  {provider}:\n"
                report += f"    连接: {'✅' if status.get('connected') else '❌'}\n"
                report += f"    健康: {'✅' if status.get('healthy') else '❌'}\n"
                if status.get('last_error'):
                    report += f"    错误: {status['last_error']}\n"
        else:
            report += "  无客户端信息\n"
        
        # 错误信息
        if diagnosis['errors']:
            report += "\n❌ 错误信息:\n"
            for error in diagnosis['errors']:
                report += f"  • {error}\n"
        
        return report
