# 消息管理器 - 处理消息生成和发送逻辑

import json
import random
import logging
import datetime
from typing import List, Dict, Any, Optional, AsyncGenerator
from astrbot.api.all import (
    AstrBotMessage,
    MessageType,
    MessageMember,
    MessageChain,
    MessageEventResult,
)
from astrbot.api.event import MessageChain
from astrbot.api.message_components import Plain

logger = logging.getLogger("message_manager")


class MessageManager:
    """消息管理器，负责生成和发送各类消息"""

    def __init__(self, parent):
        """初始化消息管理器

        Args:
            parent: 父插件实例，用于访问上下文
        """
        self.parent = parent
        self.context = parent.context

    async def generate_and_send_message(
        self,
        user_id: str,
        conversation_id: str,
        unified_msg_origin: str,
        prompts: List[str],
        message_type: str = "一般",
        time_period: Optional[str] = None,
        extra_context: Optional[str] = None,
    ):
        """生成并发送消息

        Args:
            user_id: 用户ID
            conversation_id: 会话ID
            unified_msg_origin: 统一消息来源
            prompts: 可用的提示词列表
            message_type: 消息类型描述（用于日志）
            time_period: 时间段描述（如"早上"、"下午"等）
            extra_context: 额外的上下文信息

        """
        try:
            # 移除针对日常分享的冗余时间间隔检查
            # # 检查消息间隔时间（如果是随机日常消息）
            # if message_type.endswith("日常分享"):
            #     # 获取随机日常模块的配置
            #     if hasattr(self.parent, 'random_daily'):
            #         last_time = self.parent.random_daily.last_sharing_time.get(user_id)
            #         now = datetime.datetime.now()
                    
            #         if last_time:
            #             # 计算距离上次发送经过的分钟数
            #             minutes_since_last = (now - last_time).total_seconds() / 60
            #             min_interval = self.parent.random_daily.min_interval_minutes
                        
            #             # 如果未达到最小间隔时间，取消发送
            #             if minutes_since_last < min_interval:
            #                 logger.info(f"用户 {user_id} 上次消息发送于 {minutes_since_last:.1f} 分钟前，未达到最小间隔 {min_interval} 分钟，取消发送 (冗余检查)")
            #                 return False # <--- 移除这部分逻辑

            # 解析 unified_msg_origin 获取平台信息
            platform_id, msg_type, session_id = self.parse_unified_msg_origin(unified_msg_origin)
            
            if not platform_id:
                logger.error(f"无法解析平台ID: {unified_msg_origin}")
                return False
            
            # 获取对话对象
            conversation = await self.context.conversation_manager.get_conversation(
                unified_msg_origin, conversation_id
            )

            if not conversation:
                logger.error(
                    f"无法获取用户 {user_id} 的对话，会话ID: {conversation_id} 可能不存在"
                )
                return False

            # 获取对话历史和系统提示
            system_prompt = "你是一个可爱的AI助手，喜欢和用户互动。"

            # 获取当前对话的人格设置
            if conversation:
                persona_id = conversation.persona_id

                # 获取对话使用的人格设置
                system_prompt = self._get_system_prompt(persona_id, system_prompt)

            # 检查今天是否是特殊节日
            festival_detector = self.parent.festival_detector if hasattr(self.parent, 'festival_detector') else None
            festival_prompts = None
            festival_name = None
            
            if festival_detector:
                festival_prompts = festival_detector.get_festival_prompts()
                festival_name = festival_detector.get_festival_name()
            
            # 如果今天是节日且不是特定消息类型，优先使用节日相关提示词
            if festival_prompts and message_type not in ["主动消息", "早安", "晚安", "日程安排"]:
                prompts = festival_prompts
                logger.info(f"今天是{festival_name}，使用节日相关提示词")

            # 随机选择一个提示词
            prompt = random.choice(prompts)

            # 添加特殊标识，用于识别这是系统提示词而非用户消息
            # 使用特殊标记 [SYS_PROMPT] 这种格式不会影响LLM，但可以被代码检测到
            system_marker = "[SYS_PROMPT]"
            
            # 调整提示词
            adjusted_prompt = f"{system_marker} {prompt}"
            context_requirement = "请确保回复贴合当前的对话上下文情景。" # 新增上下文要求

            # 获取当前时间段的AI日程安排（如果有）
            ai_schedule = None
            if hasattr(self.parent, 'ai_schedule') and time_period and message_type != "日程安排":
                ai_schedule = self.parent.ai_schedule.get_schedule_by_time_period(time_period)
            
            # 将AI日程安排融入提示中
            if ai_schedule:
                # 如果有额外的上下文，将日程安排添加到额外上下文之前
                if extra_context:
                    extra_context = f"根据你今天的日程安排，{time_period}你计划{ai_schedule}。{extra_context}"
                else:
                    extra_context = f"根据你今天的日程安排，{time_period}你计划{ai_schedule}。请在对话中自然地融入这个安排，但不要直接告诉用户这是你的日程安排。"

            if festival_name and message_type not in ["主动消息", "日程安排"]:
                if time_period:
                    adjusted_prompt = f"{system_marker} {prompt}，今天是{festival_name}，现在是{time_period}，请保持与你的人格设定一致的风格，确保回复符合你的人设特点。{context_requirement}"
                else:
                    adjusted_prompt = f"{system_marker} {prompt}，今天是{festival_name}，请保持与你的人格设定一致的风格，确保回复符合你的人设特点。{context_requirement}"
            elif time_period:
                adjusted_prompt = f"{system_marker} {prompt}，现在是{time_period}，请保持与你的人格设定一致的风格，确保回复符合你的人设特点。{context_requirement}"
            else:
                # 对非节日、非特定时间段的消息也添加上下文要求
                adjusted_prompt = f"{system_marker} {prompt}，请保持与你的人格设定一致的风格，确保回复符合你的人设特点。{context_requirement}"

            if extra_context:
                # 将 extra_context 放在通用要求之前，确保其优先被考虑
                adjusted_prompt = f"{adjusted_prompt.replace(context_requirement, '')} {extra_context} {context_requirement}"

            # 获取LLM工具管理器
            func_tools_mgr = self.context.get_llm_tool_manager()

            # 调用LLM获取回复
            logger.info(f"正在为用户 {user_id} 生成{message_type}消息内容...")
            logger.debug(f"使用的提示词: {adjusted_prompt}")

            # 【修改】使用 get_platform_inst 获取正确的平台实例
            platform = self.context.get_platform_inst(platform_id)
            
            if not platform:
                logger.error(f"无法获取平台实例: {platform_id}")
                return False

            # 根据平台元数据的适配器名称（而非用户自定义的 platform_id）分发到对应的事件构造逻辑
            platform_name = platform.meta().name

            fake_event = self.create_fake_event(
                message_str=adjusted_prompt,
                platform=platform,
                platform_name=platform_name,
                umo=unified_msg_origin,
                sender_id=user_id,
                session_id=session_id,
                platform_meta=platform.meta(),
            )
            if not fake_event:
                logger.error(f"暂不支持的平台类型: {platform_name}，无法发送主动消息")
                return False

            platform.commit_event(fake_event)
            
            # 仅在为主动消息类型时添加到标记集合中
            if message_type == "主动消息":
                self.parent.dialogue_core.users_received_initiative.add(user_id)
                
            return fake_event.request_llm(
                prompt=adjusted_prompt,
                func_tool_manager=func_tools_mgr,
                image_urls=[],
                system_prompt=system_prompt,
                conversation=conversation,
            )

        except Exception as e:
            import traceback

            error_traceback = traceback.format_exc()
            logger.error(
                f"发送{message_type}消息时发生错误: {str(e)}\n{error_traceback}"
            )
            return

    def parse_unified_msg_origin(self, unified_msg_origin: str):
        """解析统一消息来源

        格式: platform_name:message_type:session_id
        """
        try:
            parts = unified_msg_origin.split(":")
            if len(parts) != 3:
                raise ValueError("统一消息来源格式错误")

            platform_name = parts[0]
            message_type = parts[1]
            session_id = parts[2]

            return platform_name, message_type, session_id
        except Exception as e:
            logger.error(f"解析统一消息来源时发生错误: {str(e)}")
            return None, None, None

    def create_fake_event(
        self,
        message_str: str,
        platform,
        platform_name: str,
        umo: str,
        session_id: str,
        sender_id: str = "123456",
        platform_meta=None,
    ):
        """构造一个伪造的消息事件，用于借助框架的 LLM 请求管线发送主动消息

        不同平台的消息事件类构造参数不同（例如 aiocqhttp 用 `bot`，telegram 用
        `client`），因此按 `platform_name` 分发到各自的构造逻辑。

        Args:
            message_str: 消息文本内容
            platform: 平台实例，用于获取发送消息所需的客户端对象
            platform_name: 平台适配器名称（如 "aiocqhttp"、"telegram"）
            umo: 统一消息来源
            session_id: 会话id
            sender_id: 发送者id
            platform_meta: 平台元数据

        Returns:
            构造好的消息事件对象；如果平台不受支持则返回 None
        """
        # 使用配置中的self_id
        self_id = self.parent.config.get("self_id", "")
        if not self_id:
            logger.warning("配置中未设置self_id，使用默认值，可能会导致异常")
            self_id = sender_id

        abm = AstrBotMessage()
        abm.message_str = message_str
        abm.message = [Plain(message_str)]
        abm.self_id = self_id  # 使用配置中的self_id
        abm.sender = MessageMember(user_id=sender_id)
        abm.session_id = session_id
        abm.type = MessageType.FRIEND_MESSAGE

        if platform_name == "aiocqhttp":
            from .aiocqhttp_message_event import AiocqhttpMessageEvent

            bot = getattr(platform, "bot", None)
            if not bot:
                logger.error(f"平台 {platform_name} 没有 bot 属性")
                return None

            if "group" in umo.lower():
                # 群消息
                group_id = umo.split("_")[-1] if "_" in umo else sender_id
                abm.raw_message = {
                    "message_type": "group",
                    "group_id": int(group_id),
                    "user_id": int(sender_id),
                    "message": message_str,
                }
            else:
                # 私聊消息
                abm.raw_message = {
                    "message_type": "private",
                    "user_id": int(sender_id),
                    "message": message_str,
                }

            event = AiocqhttpMessageEvent(
                message_str=message_str,
                message_obj=abm,
                platform_meta=platform_meta,
                session_id=session_id,
                bot=bot,
            )
        elif platform_name == "telegram":
            from astrbot.core.platform.sources.telegram.tg_event import (
                TelegramPlatformEvent,
            )

            client = getattr(platform, "client", None)
            if not client:
                logger.error(f"平台 {platform_name} 没有 client 属性")
                return None

            # telegram 的 raw_message 仅在框架内部读取原消息时使用，主动消息没有
            # 真实的原始 Update，留空即可，不影响发送
            abm.raw_message = None

            event = TelegramPlatformEvent(
                message_str=message_str,
                message_obj=abm,
                platform_meta=platform_meta,
                session_id=session_id,
                client=client,
            )
        else:
            logger.error(f"暂不支持的平台类型: {platform_name}")
            return None

        event.is_wake = True
        event.call_llm = False

        return event

    def _get_system_prompt(self, persona_id: Optional[str], default_prompt: str) -> str:
        """获取系统提示词

        Args:
            persona_id: 人格ID
            default_prompt: 默认提示词

        Returns:
            str: 系统提示词
        """
        try:
            if persona_id is None:
                # 使用默认人格
                default_persona = self.context.provider_manager.selected_default_persona
                if default_persona:
                    return default_persona.get("prompt", default_prompt)
            elif persona_id != "[%None]":
                # 使用指定人格
                personas = self.context.provider_manager.personas
                for persona in personas:
                    if persona.get("id") == persona_id:
                        return persona.get("prompt", default_prompt)
        except Exception as e:
            logger.error(f"获取人格信息时出错: {str(e)}")

        return default_prompt
