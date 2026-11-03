def bearer_token_from_request(request) -> str | None:
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    return parts[1]


def request_uses_api_key_bearer(request) -> bool:
    token = bearer_token_from_request(request)
    return bool(token and token.startswith('cs_live_'))
