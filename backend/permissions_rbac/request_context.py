"""Per-request caches for RBAC folder-rule evaluation."""
from __future__ import annotations

from contextvars import ContextVar
from typing import Any, Dict

_rbac_request_state: ContextVar[Dict[str, Any] | None] = ContextVar('rbac_request_state', default=None)


def rbac_request_state() -> Dict[str, Any]:
    state = _rbac_request_state.get()
    if state is None:
        state = {}
        _rbac_request_state.set(state)
    return state


def reset_rbac_request_state():
    return _rbac_request_state.set({})


def restore_rbac_request_state(token) -> None:
    _rbac_request_state.reset(token)
