"""业务风控模块 — 规则引擎、风险评分、异常检测、黑白名单"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from langchain_core.tools import tool

# ---- 风控状态 ----
_RISK_DATA = {
    "rules": [],           # 风控规则列表
    "blacklist": set(),    # 黑名单
    "whitelist": set(),    # 白名单
    "events": [],          # 风控事件日志
    "score_config": {      # 风险评分权重
        "amount_weight": 0.3,
        "frequency_weight": 0.25,
        "ip_weight": 0.2,
        "device_weight": 0.15,
        "time_weight": 0.1,
    }
}

# 默认风控规则
_DEFAULT_RULES = [
    {"id": 1, "name": "large_amount", "desc": "单笔交易超过 10000 元", "level": "high", "action": "review"},
    {"id": 2, "name": "rapid_orders", "desc": "1 分钟内超过 5 笔订单", "level": "high", "action": "block"},
    {"id": 3, "name": "night_trading", "desc": "凌晨 2-5 点大额交易", "level": "medium", "action": "review"},
    {"id": 4, "name": "new_user_large", "desc": "新用户首笔超过 5000 元", "level": "medium", "action": "review"},
    {"id": 5, "name": "multi_device", "desc": "同一用户 10 分钟内切换 3 个以上设备", "level": "low", "action": "alert"},
]
_RISK_DATA["rules"] = _DEFAULT_RULES

# 模拟风控事件存储
_RISK_STORE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
os.makedirs(_RISK_STORE, exist_ok=True)
_RISK_LOG = os.path.join(_RISK_STORE, "risk_events.json")


def _save_events():
    """持久化风控事件"""
    try:
        with open(_RISK_LOG, "w", encoding="utf-8") as f:
            json.dump(_RISK_DATA["events"][-500:], f, ensure_ascii=False)
    except Exception:
        pass


def _load_events():
    """加载历史事件"""
    try:
        if os.path.exists(_RISK_LOG):
            with open(_RISK_LOG, "r", encoding="utf-8") as f:
                _RISK_DATA["events"] = json.load(f)
    except Exception:
        pass


_load_events()


def _risk_score(amount: float, order_count: int, is_new_user: bool,
                is_night: bool, ip_count: int, device_count: int) -> dict:
    """计算风险评分 0-100"""
    cfg = _RISK_DATA["score_config"]
    score = 0
    reasons = []

    # 金额风险
    if amount > 10000:
        score += 30 * cfg["amount_weight"]
        reasons.append("大额交易(>10000)")
    elif amount > 5000:
        score += 15 * cfg["amount_weight"]
        reasons.append("较大金额(>5000)")

    # 频率风险
    if order_count > 10:
        score += 25 * cfg["frequency_weight"]
        reasons.append("高频交易(>10次)")
    elif order_count > 5:
        score += 12 * cfg["frequency_weight"]
        reasons.append("较高频率(>5次)")

    # IP 风险
    if ip_count > 3:
        score += 20 * cfg["ip_weight"]
        reasons.append(f"多IP({ip_count}个)")

    # 设备风险
    if device_count > 2:
        score += 15 * cfg["device_weight"]
        reasons.append(f"多设备({device_count}个)")

    # 时间风险
    if is_night:
        score += 10 * cfg["time_weight"]
        reasons.append("深夜交易")

    # 新用户风险
    if is_new_user:
        score += 8
        reasons.append("新用户")

    level = "low" if score < 30 else ("medium" if score < 60 else "high")
    action = "pass" if score < 30 else ("review" if score < 60 else "block")

    return {
        "score": min(round(score), 100),
        "level": level,
        "action": action,
        "reasons": reasons,
    }


@tool
def risk_check_transaction(
    user_id: str,
    amount: float,
    order_count: int = 1,
    is_new_user: str = "false",
    ip_count: int = 1,
    device_count: int = 1,
    is_night: str = "false",
) -> str:
    """对一笔交易进行风控检查，返回风险评分和处理建议。

    参数说明：
    - user_id: 用户ID
    - amount: 交易金额（元）
    - order_count: 近期订单数
    - is_new_user: 是否新用户 ("true"/"false")
    - ip_count: 使用过的IP数量
    - device_count: 使用过的设备数量
    - is_night: 是否深夜时段 ("true"/"false")
    """
    # 白名单检查
    if user_id in _RISK_DATA["whitelist"]:
        return f"风控结果：通过（白名单用户 {user_id}）"

    # 黑名单检查
    if user_id in _RISK_DATA["blacklist"]:
        return f"风控结果：拒绝（黑名单用户 {user_id}）"

    is_new = is_new_user.lower() == "true"
    is_dark = is_night.lower() == "true"

    result = _risk_score(amount, order_count, is_new, is_dark, ip_count, device_count)

    # 记录事件
    event = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": user_id,
        "amount": amount,
        "risk_score": result["score"],
        "risk_level": result["level"],
        "action": result["action"],
        "reasons": result["reasons"],
    }
    _RISK_DATA["events"].append(event)
    _save_events()

    return f"""风控检查结果
{'='*40}
用户: {user_id}
金额: RMB{amount:,.2f}
风险评分: {result['score']}/100 ({result['level']})
处理建议: {result['action']}
风险因素: {', '.join(result['reasons']) if result['reasons'] else '无'}
{'='*40}"""


@tool
def risk_rules() -> str:
    """查看当前所有风控规则及其触发条件。"""
    rules = _RISK_DATA["rules"]
    lines = [f"风控规则列表（共 {len(rules)} 条）\n{'='*40}"]
    for r in rules:
        lines.append(f"[{r['level'].upper()}] {r['name']}")
        lines.append(f"  {r['desc']}")
        lines.append(f"  动作: {r['action']}")
    return "\n".join(lines)


@tool
def risk_add_rule(name: str, description: str, level: str, action: str) -> str:
    """添加一条风控规则。

    参数 level 为风险等级（low/medium/high），action 为处理动作（pass/review/block/alert）。
    """
    new_id = max([r["id"] for r in _RISK_DATA["rules"]], default=0) + 1
    rule = {
        "id": new_id,
        "name": name,
        "desc": description,
        "level": level.lower(),
        "action": action.lower(),
    }
    _RISK_DATA["rules"].append(rule)
    return f"规则已添加: [{rule['level'].upper()}] {rule['name']} -> {rule['action']}"


@tool
def risk_blacklist(user_id: str, reason: str = "") -> str:
    """将用户加入黑名单。

    参数 user_id 为用户ID，reason 为拉黑原因。
    """
    _RISK_DATA["blacklist"].add(user_id)
    if user_id in _RISK_DATA["whitelist"]:
        _RISK_DATA["whitelist"].discard(user_id)
    reason_text = f"（原因: {reason}）" if reason else ""
    return f"已加入黑名单: {user_id} {reason_text}"


@tool
def risk_whitelist(user_id: str) -> str:
    """将用户加入白名单，白名单用户自动通过所有风控检查。"""
    _RISK_DATA["whitelist"].add(user_id)
    _RISK_DATA["blacklist"].discard(user_id)
    return f"已加入白名单: {user_id}"


@tool
def risk_report(hours: int = 24) -> str:
    """生成风控报告，汇总近 N 小时的风险事件。

    参数 hours 为统计时长（小时），默认 24。
    """
    cutoff = datetime.now() - timedelta(hours=hours)
    recent = [
        e for e in _RISK_DATA["events"]
        if datetime.strptime(e["time"], "%Y-%m-%d %H:%M:%S") >= cutoff
    ]

    if not recent:
        return f"近 {hours} 小时无风控事件"

    high = [e for e in recent if e["risk_level"] == "high"]
    medium = [e for e in recent if e["risk_level"] == "medium"]
    low = [e for e in recent if e["risk_level"] == "low"]
    blocked = [e for e in recent if e["action"] == "block"]

    total_amount = sum(e["amount"] for e in recent)
    avg_score = sum(e["risk_score"] for e in recent) / len(recent)

    return f"""风控报告（近 {hours} 小时）
{'='*40}
事件总数: {len(recent)}
高风险  : {len(high)}
中风险  : {len(medium)}
低风险  : {len(low)}
已拦截  : {len(blocked)}
总金额  : RMB{total_amount:,.2f}
平均评分: {avg_score:.0f}/100
黑名单  : {len(_RISK_DATA['blacklist'])} 人
白名单  : {len(_RISK_DATA['whitelist'])} 人
风控规则: {len(_RISK_DATA['rules'])} 条
{'='*40}"""


def get_risk_tools():
    """返回所有风控工具"""
    return [
        risk_check_transaction,
        risk_rules,
        risk_add_rule,
        risk_blacklist,
        risk_whitelist,
        risk_report,
    ]
