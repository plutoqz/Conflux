"""断路器模式（§10.2）

每个外部 API 调用独立熔断，防止级联故障。
当连续失败达到阈值时自动断路，冷却后恢复。
"""

import time
from dataclasses import dataclass, field
from enum import Enum


class CircuitState(Enum):
    CLOSED = "closed"         # 正常
    OPEN = "open"             # 熔断中
    HALF_OPEN = "half_open"   # 试探恢复


@dataclass
class CircuitBreaker:
    """单个服务的断路器"""
    name: str
    failure_threshold: int = 3       # 连续失败 N 次后断路
    recovery_timeout: float = 30.0   # 断路后冷却秒数
    _state: CircuitState = CircuitState.CLOSED
    _failure_count: int = 0
    _last_failure_time: float = 0
    _last_success_time: float = 0

    def call(self, fn, fallback_fn=None, *args, **kwargs):
        """执行 fn()，失败时执行 fallback_fn()

        Returns:
            fn 的返回值或 fallback_fn 的返回值
        """
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time > self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
            else:
                if fallback_fn:
                    return fallback_fn(*args, **kwargs)
                raise RuntimeError(f"断路器 {self.name} 已熔断，剩余冷却 {self.recovery_timeout - (time.time() - self._last_failure_time):.0f}s")

        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            if fallback_fn:
                return fallback_fn(*args, **kwargs)
            raise

    async def acall(self, fn, fallback_fn=None, *args, **kwargs):
        """异步版 call()"""
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time > self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
            else:
                if fallback_fn:
                    return await fallback_fn(*args, **kwargs)
                raise RuntimeError(f"断路器 {self.name} 已熔断")

        try:
            result = await fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            if fallback_fn:
                return await fallback_fn(*args, **kwargs)
            raise

    def _on_success(self):
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_success_time = time.time()

    def _on_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN

    @property
    def state(self) -> str:
        return self._state.value


# 全局断路器注册表
_breakers: dict[str, CircuitBreaker] = {}


def get_breaker(name: str, threshold: int = 3, timeout: float = 30.0) -> CircuitBreaker:
    """获取或创建指定名称的断路器"""
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(name=name, failure_threshold=threshold, recovery_timeout=timeout)
    return _breakers[name]


def reset_all():
    _breakers.clear()
