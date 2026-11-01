"""Preview delivery adjustments when share-link printing is restricted."""


def effective_preview_mode_for_link(preview_mode: str, *, allow_print: bool) -> str:
    """
    When printing is disabled, never expose client-side PDF.js viewing for a link;
    use server-rendered page images instead.
    """
    if preview_mode == 'client_pdf' and not allow_print:
        return 'server_pages'
    return preview_mode


def may_expose_client_pdf_preview_url(preview_mode: str, *, allow_print: bool) -> bool:
    """Whether view-data may include a signed raw-PDF URL for PDF.js preview."""
    return preview_mode == 'client_pdf' and allow_print
