"""P2 Paper Radar — project-scoped paper discovery pipeline.

This module is the runtime layer that assembles project context, generates
search intents, resolves query specs from Tracks, and orchestrates the full
paper radar run for a given project.
"""

from .context_builder import (
    build_project_research_context,
)
from .deep_analyzer import (
    run_deep_analysis,
)
from .intent_generator import (
    generate_search_intents,
)
from .query_builder import (
    resolve_query_specs,
    resolve_query_specs_from_profile,
)
from .radar import (
    run_paper_radar,
    run_paper_radar_from_profile,
)

__all__ = [
    "build_project_research_context",
    "generate_search_intents",
    "resolve_query_specs",
    "resolve_query_specs_from_profile",
    "run_deep_analysis",
    "run_paper_radar",
    "run_paper_radar_from_profile",
]
