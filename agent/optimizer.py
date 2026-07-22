"""模型性能优化 — Token 计数、响应计时、结果缓存、模型切换"""

import time
import hashlib
import json
from functools import lru_cache
from langchain_core.tools import tool

# ---- 性能统计 ----
_stats = {
    "total_calls": 0,
    "total_tokens_input": 0,
    "total_tokens_output": 0,
    "total_time_ms": 0,
    "avg_time_ms": 0,
    "avg_tokens_per_call": 0,
    "cache_hits": 0,
    "cache_misses": 0,
}

# 简单内存缓存
_cache = {}
MAX_CACHE_SIZE = 100


def _cache_key(text: str) -> str:
    """生成缓存键"""
    return hashlib.md5(text.encode()).hexdigest()


def _estimate_tokens(text: str) -> int:
    """估算 Token 数量（中文：~1.5 字/token，英文：~4 字符/token）"""
    if not text:
        return 0
    chinese_chars = sum(1 for c in text if '一' <= c <= '鿿')
    other_chars = len(text) - chinese_chars
    return int(chinese_chars / 1.5 + other_chars / 4)


def record_call(input_text: str, output_text: str, elapsed_ms: float):
    """记录一次 API 调用统计"""
    tokens_in = _estimate_tokens(input_text)
    tokens_out = _estimate_tokens(output_text)

    _stats["total_calls"] += 1
    _stats["total_tokens_input"] += tokens_in
    _stats["total_tokens_output"] += tokens_out
    _stats["total_time_ms"] += elapsed_ms
    _stats["avg_time_ms"] = _stats["total_time_ms"] / _stats["total_calls"]
    _stats["avg_tokens_per_call"] = (
        (_stats["total_tokens_input"] + _stats["total_tokens_output"])
        / _stats["total_calls"]
    )


def cache_get(query: str):
    """从缓存获取结果"""
    key = _cache_key(query)
    if key in _cache:
        _stats["cache_hits"] += 1
        return _cache[key]
    _stats["cache_misses"] += 1
    return None


def cache_set(query: str, result: str):
    """缓存查询结果"""
    key = _cache_key(query)
    if len(_cache) >= MAX_CACHE_SIZE:
        # 清除最早的缓存
        oldest = next(iter(_cache))
        del _cache[oldest]
    _cache[key] = result


@tool
def perf_dashboard() -> str:
    """查看 Agent 性能面板：API 调用次数、Token 消耗、响应时间、缓存命中率。

    用于监控和优化模型性能。
    """
    s = _stats
    if s["total_calls"] == 0:
        return "暂无调用记录"

    total_tokens = s["total_tokens_input"] + s["total_tokens_output"]

    # 估算费用（DeepSeek: input 1 RMB/M, output 4 RMB/M）
    cost_in = s["total_tokens_input"] / 1_000_000 * 1
    cost_out = s["total_tokens_output"] / 1_000_000 * 4
    total_cost = cost_in + cost_out

    cache_rate = (
        s["cache_hits"] / (s["cache_hits"] + s["cache_misses"]) * 100
        if (s["cache_hits"] + s["cache_misses"]) > 0
        else 0
    )

    return f"""性能面板
{'='*40}
调用次数: {s['total_calls']}
总 Token : {total_tokens:,} (输入 {s['total_tokens_input']:,} + 输出 {s['total_tokens_output']:,})
平均 Token/调用: {s['avg_tokens_per_call']:,.0f}
总耗时  : {s['total_time_ms']/1000:.1f}s
平均响应: {s['avg_time_ms']:.0f}ms
预估费用: RMB{total_cost:.4f} (DeepSeek)
缓存命中: {cache_rate:.1f}% (hits={s['cache_hits']}, miss={s['cache_misses']})
缓存条目: {len(_cache)}
{'='*40}"""


@tool
def clear_cache() -> str:
    """清空查询缓存。当遇到过期或错误缓存时使用。"""
    count = len(_cache)
    _cache.clear()
    _stats["cache_hits"] = 0
    _stats["cache_misses"] = 0
    return f"已清空 {count} 条缓存"


@tool
def estimate_tokens(text: str) -> str:
    """估算文本的 Token 消耗量，在调用 API 前预估成本。

    参数 text 为要估算的文本。
    """
    tokens = _estimate_tokens(text)
    cost_deepseek = tokens / 1_000_000 * 1  # input price
    return f"预估：{tokens:,} tokens | DeepSeek 费用约 RMB{cost_deepseek:.6f}（输入）"


def get_optimizer_tools():
    """返回所有性能优化工具"""
    return [perf_dashboard, estimate_tokens, clear_cache]
