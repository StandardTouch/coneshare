"""
Helpers for exposing the current user's signer row on awaiting list responses only.
"""


def get_awaiting_signer_for_user(signature_request, user, *, view_type: str):
    """Return this user's Signer row when listing the awaiting view; otherwise None."""
    if view_type != "awaiting" or user is None or not user.is_authenticated:
        return None
    prefetched_list = getattr(signature_request, "_awaiting_signer_list", None)
    if prefetched_list is not None:
        return prefetched_list[0] if prefetched_list else None
    return signature_request.signers.filter(user_id=user.id).first()
