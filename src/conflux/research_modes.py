"""Research-depth profiles and role-based model routing for P1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from .config import get


ResearchDepth = Literal["quick", "standard", "deep"]

_DEPTH_ALIASES = {
    "low": "quick",
    "quick": "quick",
    "medium": "standard",
    "standard": "standard",
    "high": "deep",
    "deep": "deep",
}

# P4-B 评审团：roster 条目先按 models.<entry> 字面 preset 解释；若该 preset 不存在
# 且条目恰好是研究角色名（如 "planner"），则回退为该角色在当前档位绑定的 preset。
# 例：arbitration: [planner, flash] 在 deep 档解析为 [reasoning, flash]。
_PANEL_ROLE_ALIASES = {"planner", "analyst", "reranker", "synthesizer", "verifier"}


def _resolve_panel_preset(entry: str, profile: "ResearchModeProfile") -> str:
    entry = str(entry or "").strip()
    if not entry:
        return ""
    if entry in _PANEL_ROLE_ALIASES and get("models", entry, default=None) is None:
        return str(getattr(profile, f"{entry}_model"))
    return entry


@dataclass(frozen=True, slots=True)
class ResearchModeProfile:
    """One complete quality/cost/latency policy for a research run."""

    depth: ResearchDepth
    planner_model: str
    analyst_model: str
    reranker_model: str
    synthesizer_model: str
    verifier_model: str
    max_gap_iterations: int
    max_subquestions: int
    max_parallel_subquestions: int
    candidate_limit: int
    final_evidence_limit: int
    web_max_results: int
    web_max_subqueries: int
    web_fetch_limit: int
    web_fetch_attempts: int
    max_query_rewrites: int
    factcheck_strength: str
    planner_max_tokens: int
    analyst_max_tokens: int
    reranker_max_tokens: int
    synthesizer_max_tokens: int
    verifier_max_tokens: int
    token_budget: int
    model_timeout_seconds: int
    max_retries: int
    timeout_seconds: int
    # P4-B 多模型评审团（panel）：quick 档强制关闭；成员按判断点分组，
    # 同一判断点成员必须来自不同 preset（config 校验防伪多样性）。
    panel_enabled: bool = False
    panel_roster: dict[str, list[str]] = field(default_factory=dict)
    panel_referee: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["stage_budgets"] = self.stage_budgets
        return payload

    @property
    def stage_budgets(self) -> dict[str, int]:
        """Explicit wall-clock topology, including the final commit reserve."""

        defaults = {
            "quick": {
                "planning": 20, "retrieval": 70, "analysis": 20,
                "synthesis": 30, "verification": 20, "commit": 20,
            },
            "standard": {
                "planning": 25, "retrieval": 60, "analysis": 45,
                "synthesis": 55, "verification": 35, "commit": 20,
            },
            "deep": {
                "planning": 45, "retrieval": 190, "analysis": 65,
                "synthesis": 90, "verification": 70, "commit": 20,
            },
        }[self.depth]
        if sum(defaults.values()) == self.timeout_seconds:
            return defaults
        scale = self.timeout_seconds / sum(defaults.values())
        budgets = {name: max(1, round(seconds * scale)) for name, seconds in defaults.items()}
        budgets["retrieval"] += self.timeout_seconds - sum(budgets.values())
        return budgets

    @property
    def commit_reserve_seconds(self) -> int:
        return self.stage_budgets["commit"]

    @property
    def role_timeout_seconds(self) -> dict[str, int]:
        """Per-role call ceilings derived proportionally from model_timeout_seconds.

        All role timeouts are fractions of the single `model_timeout_seconds`
        configured in config.yaml.  Changing that one value rescales every role
        without touching hard-coded magic numbers.
        """

        base = max(1, self.model_timeout_seconds)
        fractions = {
            "planner": 0.25,
            "analyst": 0.40,
            "reranker": 0.25,
            "synthesizer": 0.85,
            "verifier": 0.35,
        }
        return {
            role: max(8, round(base * fraction))
            for role, fraction in fractions.items()
        }

    @property
    def model_presets(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((
            self.planner_model,
            self.analyst_model,
            self.reranker_model,
            self.synthesizer_model,
            self.verifier_model,
            *self.panel_presets,
        )))

    @property
    def panel_presets(self) -> tuple[str, ...]:
        """All presets a panel run may touch: members per judgment point + referee."""

        if not self.panel_enabled:
            return ()
        presets: list[str] = []
        for entries in (self.panel_roster or {}).values():
            for entry in entries:
                preset = _resolve_panel_preset(entry, self)
                if preset:
                    presets.append(preset)
        if self.panel_referee:
            presets.append(_resolve_panel_preset(self.panel_referee, self))
        return tuple(dict.fromkeys(presets))

    def panel_members(self, judgment_point: str) -> list[str]:
        """Resolved member presets for one judgment point (order-preserving, deduped)."""

        entries = (self.panel_roster or {}).get(judgment_point) or []
        return list(dict.fromkeys(
            preset for entry in entries
            if (preset := _resolve_panel_preset(entry, self))
        ))

    @property
    def role_max_tokens(self) -> dict[str, int]:
        return {
            "planner": self.planner_max_tokens,
            "analyst": self.analyst_max_tokens,
            "reranker": self.reranker_max_tokens,
            "synthesizer": self.synthesizer_max_tokens,
            "verifier": self.verifier_max_tokens,
        }


_DEFAULTS: dict[str, dict[str, Any]] = {
    "quick": {
        "planner_model": "flash",
        "analyst_model": "flash",
        "reranker_model": "balanced",
        "synthesizer_model": "flash",
        "verifier_model": "flash",
        "max_gap_iterations": 0,
        "max_subquestions": 4,
        "max_parallel_subquestions": 2,
        "candidate_limit": 6,
        "final_evidence_limit": 6,
        "web_max_results": 3,
        "web_max_subqueries": 3,
        "web_fetch_limit": 2,
        "web_fetch_attempts": 3,
        "max_query_rewrites": 0,
        "factcheck_strength": "light",
        "planner_max_tokens": 4000,
        "analyst_max_tokens": 4000,
        "reranker_max_tokens": 600,
        "synthesizer_max_tokens": 5000,
        "verifier_max_tokens": 600,
        "token_budget": 55000,
        "model_timeout_seconds": 60,
        "max_retries": 0,
        "timeout_seconds": 180,
    },
    "standard": {
        "planner_model": "flash",
        "analyst_model": "flash",
        "reranker_model": "flash",
        "synthesizer_model": "verifier",
        "verifier_model": "balanced",
        "max_gap_iterations": 1,
        "max_subquestions": 4,
        "max_parallel_subquestions": 3,
        "candidate_limit": 8,
        "final_evidence_limit": 8,
        "web_max_results": 4,
        "web_max_subqueries": 4,
        "web_fetch_limit": 3,
        "web_fetch_attempts": 5,
        "max_query_rewrites": 1,
        "factcheck_strength": "full",
        "planner_max_tokens": 4500,
        "analyst_max_tokens": 3200,
        "reranker_max_tokens": 1000,
        "synthesizer_max_tokens": 5500,
        "verifier_max_tokens": 1600,
        "token_budget": 75000,
        "model_timeout_seconds": 70,
        "max_retries": 0,
        "timeout_seconds": 240,
    },
    "deep": {
        "planner_model": "reasoning",
        "analyst_model": "reasoning",
        "reranker_model": "balanced",
        "synthesizer_model": "reasoning",
        "verifier_model": "balanced",
        "max_gap_iterations": 2,
        "max_subquestions": 6,
        "max_parallel_subquestions": 3,
        "candidate_limit": 12,
        "final_evidence_limit": 8,
        "web_max_results": 5,
        "web_max_subqueries": 6,
        "web_fetch_limit": 5,
        "web_fetch_attempts": 8,
        "max_query_rewrites": 2,
        "factcheck_strength": "cross_check",
        "planner_max_tokens": 2400,
        "analyst_max_tokens": 3200,
        "reranker_max_tokens": 1200,
        "synthesizer_max_tokens": 6000,
        "verifier_max_tokens": 3200,
        "token_budget": 320000,
        "model_timeout_seconds": 120,
        "max_retries": 0,
        "timeout_seconds": 480,
    },
}


def normalize_depth(value: str | None) -> ResearchDepth:
    """Normalize UI and API aliases to the three supported depth names."""

    normalized = _DEPTH_ALIASES.get(str(value or "").strip().casefold())
    if normalized is None:
        normalized = _DEPTH_ALIASES.get(str(get("research", "depth", default="standard")).casefold())
    return (normalized or "standard")  # type: ignore[return-value]


def resolve_research_profile(depth: str | None = None) -> ResearchModeProfile:
    """Resolve one profile from defaults plus config overrides."""

    resolved_depth = normalize_depth(depth)
    payload = dict(_DEFAULTS[resolved_depth])
    configured = get("research", "profiles", resolved_depth, default={}) or {}
    if isinstance(configured, dict):
        payload.update({key: value for key, value in configured.items() if value is not None})

    # P4-B panel：quick 档强制关闭（config 不可打开）；其余档位按 enabled_by_depth。
    panel_cfg = get("research", "panel", default={}) or {}
    enabled_by_depth = panel_cfg.get("enabled_by_depth") or {} if isinstance(panel_cfg, dict) else {}
    panel_roster_raw = panel_cfg.get("roster") or {} if isinstance(panel_cfg, dict) else {}
    panel_roster = {
        str(point): [str(entry) for entry in (entries or []) if str(entry or "").strip()]
        for point, entries in (panel_roster_raw.items() if isinstance(panel_roster_raw, dict) else [])
    }
    return ResearchModeProfile(
        depth=resolved_depth,
        planner_model=str(payload["planner_model"]),
        analyst_model=str(payload["analyst_model"]),
        reranker_model=str(payload["reranker_model"]),
        synthesizer_model=str(payload["synthesizer_model"]),
        verifier_model=str(payload["verifier_model"]),
        max_gap_iterations=max(0, int(payload["max_gap_iterations"])),
        max_subquestions=max(1, int(payload["max_subquestions"])),
        max_parallel_subquestions=max(1, int(payload["max_parallel_subquestions"])),
        candidate_limit=max(1, int(payload["candidate_limit"])),
        final_evidence_limit=max(1, int(payload["final_evidence_limit"])),
        web_max_results=max(1, int(payload["web_max_results"])),
        web_max_subqueries=max(1, int(payload["web_max_subqueries"])),
        web_fetch_limit=max(1, int(payload["web_fetch_limit"])),
        web_fetch_attempts=max(1, int(payload["web_fetch_attempts"])),
        max_query_rewrites=max(0, int(payload["max_query_rewrites"])),
        factcheck_strength=str(payload["factcheck_strength"]),
        planner_max_tokens=max(1, int(payload["planner_max_tokens"])),
        analyst_max_tokens=max(1, int(payload["analyst_max_tokens"])),
        reranker_max_tokens=max(1, int(payload["reranker_max_tokens"])),
        synthesizer_max_tokens=max(1, int(payload["synthesizer_max_tokens"])),
        verifier_max_tokens=max(1, int(payload["verifier_max_tokens"])),
        token_budget=max(1, int(payload["token_budget"])),
        model_timeout_seconds=max(1, int(payload["model_timeout_seconds"])),
        max_retries=max(0, int(payload["max_retries"])),
        timeout_seconds=max(1, int(payload["timeout_seconds"])),
        panel_enabled=(
            resolved_depth != "quick"
            and bool(enabled_by_depth.get(resolved_depth, False))
        ),
        panel_roster=panel_roster,
        panel_referee=str(panel_cfg.get("referee") or "") if isinstance(panel_cfg, dict) else "",
    )


def research_model_diagnostics(depth: str | None = None) -> dict[str, Any]:
    """Return the resolved provider/model identity for every research role."""

    profile = resolve_research_profile(depth)
    roles = {}
    for role, preset in (
        ("planner", profile.planner_model),
        ("analyst", profile.analyst_model),
        ("reranker", profile.reranker_model),
        ("synthesizer", profile.synthesizer_model),
        ("verifier", profile.verifier_model),
    ):
        cfg = get("models", preset, default={}) or {}
        roles[role] = {
            "preset": preset,
            "provider": cfg.get("provider", ""),
            "model": cfg.get("model", ""),
            "base_url": cfg.get("base_url", ""),
            "max_tokens": profile.role_max_tokens[role],
            "timeout_seconds": profile.role_timeout_seconds[role],
            "max_retries": profile.max_retries,
        }
    return {"profile": profile.to_dict(), "roles": roles}


def validate_research_model_profiles() -> list[str]:
    """Validate configured role presets and depth-policy differentiation.

    A deployment may intentionally reuse one provider or model across several
    roles.  Research depth is therefore distinguished by its retrieval,
    verification, token, and timeout policy rather than by hard-coded model
    identities.
    """

    problems: list[str] = []
    profiles = {
        depth: resolve_research_profile(depth)
        for depth in ("quick", "standard", "deep")
    }
    for depth, profile in profiles.items():
        for role, preset in (
            ("planner", profile.planner_model),
            ("analyst", profile.analyst_model),
            ("reranker", profile.reranker_model),
            ("synthesizer", profile.synthesizer_model),
            ("verifier", profile.verifier_model),
        ):
            cfg = get("models", preset, default={}) or {}
            if not isinstance(cfg, dict) or not cfg.get("provider") or not cfg.get("model"):
                problems.append(
                    f"research profile {depth}.{role} 引用的 models.{preset} 缺少 provider/model 配置"
                )

    policy_signatures = {
        depth: (
            profile.max_gap_iterations,
            profile.max_subquestions,
            profile.max_parallel_subquestions,
            profile.candidate_limit,
            profile.final_evidence_limit,
            profile.web_max_results,
            profile.web_max_subqueries,
            profile.web_fetch_limit,
            profile.web_fetch_attempts,
            profile.max_query_rewrites,
            profile.factcheck_strength,
            profile.token_budget,
            profile.model_timeout_seconds,
            profile.timeout_seconds,
        )
        for depth, profile in profiles.items()
    }
    if len(set(policy_signatures.values())) < 3:
        problems.append(
            "quick/standard/deep 必须配置不同的研究循环、检索或预算策略；"
            "具体 provider/model 可由用户按需复用"
        )

    # P4-B panel 校验：同一判断点成员必须来自不同 preset（防"同一模型多采样"
    # 伪多样性）；quick 档强制关闭；arbitration 评审团仅 deep 档挂载。
    panel_cfg = get("research", "panel", default={}) or {}
    if isinstance(panel_cfg, dict):
        quorum = str(panel_cfg.get("quorum") or "majority")
        if quorum != "majority":
            problems.append(f"research.panel.quorum={quorum!r} 不受支持；仅支持 majority")
    for depth, profile in profiles.items():
        if depth == "quick":
            if profile.panel_enabled:
                problems.append("quick 档评审团被强制关闭；research.panel.enabled_by_depth.quick 必须为 false")
            continue
        if not profile.panel_enabled:
            continue
        mounted_points = ["verification"] + (["arbitration"] if depth == "deep" else [])
        for point in mounted_points:
            raw_members = [
                preset for entry in (profile.panel_roster or {}).get(point) or []
                if (preset := _resolve_panel_preset(entry, profile))
            ]
            members = list(dict.fromkeys(raw_members))
            if len(members) < 2:
                problems.append(
                    f"research.panel.roster.{point} 需要至少 2 个成员 preset（depth={depth}）"
                )
            if len(set(raw_members)) != len(raw_members):
                problems.append(
                    f"research.panel.roster.{point} 成员必须来自不同 preset（depth={depth}）：{raw_members}"
                )
            for preset in members:
                cfg = get("models", preset, default={}) or {}
                if not isinstance(cfg, dict) or not cfg.get("provider") or not cfg.get("model"):
                    problems.append(
                        f"research.panel.roster.{point} 引用的 models.{preset} 缺少 provider/model 配置"
                    )
        referee = profile.panel_referee
        if not referee:
            problems.append(f"research.panel.referee 未配置（depth={depth}）")
        else:
            cfg = get("models", referee, default={}) or {}
            if not isinstance(cfg, dict) or not cfg.get("provider") or not cfg.get("model"):
                problems.append(
                    f"research.panel.referee 引用的 models.{referee} 缺少 provider/model 配置"
                )
    return problems
