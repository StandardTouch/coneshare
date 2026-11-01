from sharelinks.link_preview_policy import (
    effective_preview_mode_for_link,
    may_expose_client_pdf_preview_url,
)


def test_effective_preview_mode_falls_back_when_print_disabled():
    assert effective_preview_mode_for_link('client_pdf', allow_print=False) == 'server_pages'
    assert effective_preview_mode_for_link('client_pdf', allow_print=True) == 'client_pdf'
    assert effective_preview_mode_for_link('server_pages', allow_print=False) == 'server_pages'


def test_may_expose_client_pdf_url_only_when_print_allowed():
    assert may_expose_client_pdf_preview_url('client_pdf', allow_print=True) is True
    assert may_expose_client_pdf_preview_url('client_pdf', allow_print=False) is False
    assert may_expose_client_pdf_preview_url('server_pages', allow_print=True) is False
