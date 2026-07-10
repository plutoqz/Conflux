"""Knowledge source data contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


KnowledgeSourceType = Literal["LocalPaper", "LocalNote", "ProjectDoc", "Web", "ModelInference"]


@dataclass(slots=True)
class KnowledgeSource:
    """A traceable source that can contribute evidence to Conflux."""

    id: str
    source_type: KnowledgeSourceType
    title: str
    locator: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
