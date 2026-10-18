"""时间感知：给模型一个「查现在时间」的工具，由模型自己决定何时调用。

为什么需要它：LLM 本身没有时间概念（训练数据有截止日期，而且它也不知道「现在」），
AstrBot 默认注入的当前时间又是在系统提示词里，模型不一定用得上。

本插件注册一个函数工具 get_current_time，模型在需要时会主动调用，
比如：用户问「现在几点」「今天几号」、要判断早中晚、算时间差、
聊到「今天/明天/昨天/最近」这类相对时间。

⚠️ 关键：AstrBot 容器通常是 UTC，而用户在 UTC+8，所以这里**必须做时区换算**，
否则模型拿到的时间会差 8 小时。优先用 zoneinfo（IANA 时区名），
失败时回退到固定 UTC 偏移。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore[assignment]

DEFAULT_TIMEZONE = "Asia/Shanghai"
DEFAULT_OFFSET_HOURS = 8.0
DEFAULT_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_TOOL_NAME = "get_current_time"
_WEEKDAYS = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")


@register(
    "astrbot_plugin_time_sense",
    "q1w2e3r4t5y6658",
    "给模型一个获取当前现实时间的函数工具，由模型自行决定何时调用",
    "1.0.1",
    "https://github.com/q1w2e3r4t5y6658/astrbot_plugin_time_sense",
)
class TimeSensePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        self.config = config

    # ------------------------------------------------------------------ #
    # 配置
    # ------------------------------------------------------------------ #
    def _cfg(self, key: str, default):
        try:
            if self.config is None:
                return default
            value = self.config.get(key, default)
            return default if value in (None, "") else value
        except Exception:  # noqa: BLE001
            return default

    def _cfg_bool(self, key: str, default: bool) -> bool:
        try:
            if self.config is None:
                return default
            return bool(self.config.get(key, default))
        except Exception:  # noqa: BLE001
            return default

    # ------------------------------------------------------------------ #
    # 取当前时间（做时区换算）
    # ------------------------------------------------------------------ #
    def _now(self) -> tuple[datetime, str]:
        """返回 (配置时区的当前时间, 时区说明)。"""
        tz_name = str(self._cfg("timezone", DEFAULT_TIMEZONE) or DEFAULT_TIMEZONE)
        if ZoneInfo is not None:
            try:
                return datetime.now(ZoneInfo(tz_name)), tz_name
            except Exception as exc:  # noqa: BLE001
                logger.debug("[time_sense] 时区 %r 不可用(%s)，回退到固定偏移", tz_name, exc)
        # 回退：固定 UTC 偏移（默认 +8）
        try:
            offset = float(self._cfg("utc_offset_hours", DEFAULT_OFFSET_HOURS) or 0)
        except Exception:  # noqa: BLE001
            offset = DEFAULT_OFFSET_HOURS
        tz = dt_timezone(timedelta(hours=offset))
        sign = "+" if offset >= 0 else "-"
        return datetime.now(tz), "UTC%s%g" % (sign, abs(offset))

    @staticmethod
    def _period(hour: int) -> str:
        """把小时数翻译成人话，方便模型判断早晚。"""
        if hour < 5:
            return "凌晨"
        if hour < 8:
            return "清晨"
        if hour < 11:
            return "上午"
        if hour < 13:
            return "中午"
        if hour < 17:
            return "下午"
        if hour < 19:
            return "傍晚"
        if hour < 23:
            return "晚上"
        return "深夜"

    # ------------------------------------------------------------------ #
    # 给模型的工具（模型自己决定何时调用）
    # ------------------------------------------------------------------ #
    @filter.llm_tool(name=DEFAULT_TOOL_NAME)
    async def get_current_time(self, event: AstrMessageEvent):
        """获取当前的现实日期与时间（这是你唯一可靠的时间来源）。

        只要涉及「现在 / 今天 / 几点 / 几号 / 星期几 / 早中晚 / 多久 / 刚才 / 最近 /
        今天明天昨天」，就**必须调用本工具**，然后照它返回的内容回答。
        不要凭记忆或推测报时间 —— 猜出来的时间是错的。
        """
        now, tz_label = self._now()
        fmt = str(self._cfg("time_format", DEFAULT_FORMAT) or DEFAULT_FORMAT)
        try:
            text = now.strftime(fmt)
        except Exception:  # noqa: BLE001
            text = now.strftime(DEFAULT_FORMAT)

        parts = ["现在是 %s" % text]
        if self._cfg_bool("include_weekday", True):
            parts.append(_WEEKDAYS[now.weekday()])
        if self._cfg_bool("include_period", True):
            parts.append(self._period(now.hour))
        result = "，".join(parts)
        result += "（时区 %s，UTC%s%02d:%02d）" % (
            tz_label,
            "+" if now.utcoffset() and now.utcoffset().total_seconds() >= 0 else "-",
            abs(int((now.utcoffset() or timedelta()).total_seconds())) // 3600,
            abs(int((now.utcoffset() or timedelta()).total_seconds())) % 3600 // 60,
        )
        logger.debug("[time_sense] 模型查询时间 -> %s", result)
        return result

    async def terminate(self) -> None:
        logger.debug("[time_sense] 插件已卸载")
