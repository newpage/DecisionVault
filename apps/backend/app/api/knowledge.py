"""Compatibility import for the Knowledge bounded-context router.

Existing imports of ``app.api.knowledge.router`` remain valid while the
implementation now lives in ``app.modules.knowledge``.
"""

from app.modules.knowledge.router import router

__all__ = ["router"]
