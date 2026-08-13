"""C4 token 级流式：SSE 多路复用（回复 token 流 + 任务进度事件游标）。

两个来源（LLM 逐 token 输出、JobManager events 游标）经同一队列汇入 SSE，
互不阻塞：任一来源结束只关闭自己的通道，另一来源继续。
"""

from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable, Iterable, Iterator
from typing import Any

TokenSource = Iterable[str] | Callable[[], Iterable[str]]
EventSource = Callable[[], list[dict[str, Any]]]


def _emit(queue: "queue.Queue[tuple[str, Any]]", source: Any, poll: EventSource | None, run_id: str) -> None:
    """token 线程：逐 token 入队；token 源耗尽后（若有关联任务）转入进度轮询。

    所有退出路径都必须发送 done，否则消费端会等到 idle_timeout 兜底。
    """

    try:
        if callable(source) and not isinstance(source, (str, bytes)):
            source = source()
        for token in source or ():
            queue.put(("token", str(token)))
        if poll is not None and run_id:
            cursor = 0
            deadline = time.time() + 300.0
            while time.time() < deadline:
                try:
                    events = poll()
                except Exception:
                    break
                events = [
                    event for event in (events or [])
                    if int(event.get("id") or 0) > cursor
                ]
                for event in events:
                    queue.put(("progress", event))
                    cursor = max(cursor, int(event.get("id") or 0))
                if events and str(events[-1].get("status") or "") in {"completed", "failed", "cancelled"}:
                    break
                time.sleep(0.25)
    finally:
        queue.put(("done", None))


def multiplex(
    token_source: TokenSource,
    *,
    event_source: EventSource | None = None,
    run_id: str = "",
    idle_timeout: float = 60.0,
) -> Iterator[tuple[str, Any]]:
    """产出 ("token"|"progress"|"done", payload) 序列，可直转 SSE。"""

    channel: "queue.Queue[tuple[str, Any]]" = queue.Queue()
    thread = threading.Thread(
        target=_emit, args=(channel, token_source, event_source, run_id), daemon=True
    )
    thread.start()
    while True:
        try:
            kind, payload = channel.get(timeout=idle_timeout)
        except queue.Empty:
            yield ("done", None)
            return
        yield (kind, payload)
        if kind == "done":
            return


def sse_frames(items: Iterable[tuple[str, Any]]) -> Iterator[str]:
    """把 multiplex 序列序列化为 SSE 帧（`event: token` / `event: progress`）。"""

    import json

    for kind, payload in items:
        if kind == "token":
            yield f"event: token\ndata: {payload}\n\n"
        elif kind == "progress":
            yield f"event: progress\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        else:
            yield "event: done\ndata: {}\n\n"
