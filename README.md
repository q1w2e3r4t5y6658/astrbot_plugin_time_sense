# 时间感知（astrbot_plugin_time_sense）

给模型一个**查现在时间**的函数工具，由**模型自己决定**何时调用。

## 解决什么问题

LLM 本身没有时间概念：训练数据有截止日期，它也不知道「现在」是几点。
AstrBot 默认注入的当前时间写在**系统提示词**里，模型不一定用得上；
本插件把它做成一个**按需调用的工具**，模型在真正需要时才查。

## 行为

注册一个函数工具：

| 工具名 | 参数 | 返回 |
|---|---|---|
| `get_current_time` | 无 | 例如：`现在是 2026-10-15 23:58:07，星期四，深夜（时区 Asia/Shanghai，UTC+08:00）` |

模型会在这些场景主动调用：用户问「现在几点」「今天几号」、要判断早中晚、
算时间差、聊到「今天/明天/昨天/最近/刚才」。

## ⚠️ 时区（重要）

**AstrBot 容器通常是 UTC，而用户在 UTC+8** —— 直接取 `datetime.now()` 会差 8 小时。
本插件优先用 `zoneinfo`（IANA 时区名，默认 `Asia/Shanghai`）；
如果容器里没有 tzdata，会自动回退到 `utc_offset_hours`（默认 +8）。

## 配置

| 配置项 | 默认 | 说明 |
|---|---|---|
| `timezone` | `Asia/Shanghai` | IANA 时区名 |
| `utc_offset_hours` | `8` | 时区名不可用时的兜底偏移 |
| `time_format` | `%Y-%m-%d %H:%M:%S` | strftime 格式 |
| `include_weekday` | `true` | 返回里带星期 |
| `include_period` | `true` | 返回里带「上午/下午/深夜」 |

## 安装

把本目录放到 `AstrBot/data/plugins/astrbot_plugin_time_sense/`，重启 AstrBot 或热重载插件。

> ⚠️ **如果 AstrBot 配置里设置了 `plugin_set`（插件白名单，不是 `["*"]`），必须把
> `astrbot_plugin_time_sense` 加进该名单**，否则本插件的工具不会被注册。

## License

MIT
