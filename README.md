修改了原项目中/utils/message_manager.py的部分逻辑，使bot在主动发起对话的时候可以在原有的会话id基础上回复消息，不会再生成一个id为None的会话

修改了原项目中/utils/message_manager.py的部分逻辑，兼容Telegram，bot_name 是 BotFather 给你的机器人链接 t.me/xxx_bot 中去掉链接里的 t.me/ 前缀的xxx_bot那部分）。

</div>

<div align="center">

![:name](https://count.getloli.com/@InitiativeDialogue?name=InitiativeDialogue&theme=minecraft&padding=7&offset=0&align=top&scale=1&pixelated=1&darkmode=auto)

</div>

# 重大更新！
 
主动对话插件2.0版本现已正式推出，支持更丰富的功能，让你的bot更加拟人

感谢[anka-afk](https://github.com/anka-afk)对2.0版本更新做出的大力支持

感谢[喵喵](https://github.com/miaoxutao123)添加的天气系统

# 插件介绍
 
astrbot_plugin_InitiativeDialogue是一款能让bot主动发起对话的插件

在私聊时，当用户长时间未与bot进行对话，则会触发此插件使bot主动发起对话

除此之外，bot还会主动与你分享ta的日常生活，在节日时会给你特殊的问候
 
# 主要功能介绍
  
该插件会自动侦测bot列表中的所有私聊会话，并记录每个会话用户发送的最后一条消息的时间以及会话id.
 
当达到指定未回复时间时（默认为2h），若用户未对bot发起对话，则会创建主动对话任务，在设定回复时间内（默认为1h）随机时间点发起对话。
 
发起对话的原理是先从prompts库中随机挑选一条，结合用户的人格设定prompt一并发送给llm，获取到llm返回的文本后发送给相应的会话，并清除任务。
 

# 更新
 
1.现已加入白名单，让bot只对指定用户发起主动对话。

2.使用了llm钩子，使bot能对用户的回应作出更生动的回答。

3.加入每日问候以及随机日常模块

4.更改了调用llm的方法，让bot主动发送的消息能加入到上下文

5.修复了随机日常无法正常发送的bug

6.修复了2.0版本更新导致的一个主动消息无法被正常计数的bug，现在最大消息条数可正常使用

7.感谢喵喵为插件加入天气系统，现在bot回复时可根据用户当地天气调整回答

 
