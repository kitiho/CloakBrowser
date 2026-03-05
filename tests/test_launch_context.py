"""Unit tests for launch_context() — context kwargs, viewport defaults, close cleanup."""

import warnings
from unittest.mock import MagicMock, call, patch

import pytest

from cloakbrowser.config import DEFAULT_VIEWPORT


# All tests mock launch() to avoid needing a binary.
# launch_context() calls launch() internally, then browser.new_context().


def _make_mock_browser():
    """Create a mock browser with new_context() returning a mock context."""
    browser = MagicMock()
    context = MagicMock()
    browser.new_context.return_value = context
    return browser, context


@patch("cloakbrowser.browser.ensure_binary", return_value="/fake/chrome")
@patch("cloakbrowser.browser.launch")
def test_default_viewport(mock_launch, _mock_bin):
    """DEFAULT_VIEWPORT applied when no viewport given."""
    browser, context = _make_mock_browser()
    mock_launch.return_value = browser

    from cloakbrowser.browser import launch_context
    launch_context()

    ctx_kwargs = browser.new_context.call_args
    assert ctx_kwargs[1]["viewport"] == DEFAULT_VIEWPORT


@patch("cloakbrowser.browser.ensure_binary", return_value="/fake/chrome")
@patch("cloakbrowser.browser.launch")
def test_custom_viewport(mock_launch, _mock_bin):
    """Custom viewport overrides DEFAULT_VIEWPORT."""
    browser, context = _make_mock_browser()
    mock_launch.return_value = browser

    from cloakbrowser.browser import launch_context
    custom = {"width": 1280, "height": 720}
    launch_context(viewport=custom)

    ctx_kwargs = browser.new_context.call_args
    assert ctx_kwargs[1]["viewport"] == custom


@patch("cloakbrowser.browser.ensure_binary", return_value="/fake/chrome")
@patch("cloakbrowser.browser.launch")
def test_user_agent(mock_launch, _mock_bin):
    """user_agent forwarded to new_context()."""
    browser, context = _make_mock_browser()
    mock_launch.return_value = browser

    from cloakbrowser.browser import launch_context
    launch_context(user_agent="Mozilla/5.0 Custom")

    ctx_kwargs = browser.new_context.call_args
    assert ctx_kwargs[1]["user_agent"] == "Mozilla/5.0 Custom"


@patch("cloakbrowser.browser.ensure_binary", return_value="/fake/chrome")
@patch("cloakbrowser.browser.launch")
def test_locale_forwarded(mock_launch, _mock_bin):
    """locale flows to both launch() binary args AND new_context()."""
    browser, context = _make_mock_browser()
    mock_launch.return_value = browser

    from cloakbrowser.browser import launch_context
    launch_context(locale="de-DE")

    # Locale in launch() call (for --lang binary flag)
    assert mock_launch.call_args[1]["locale"] == "de-DE"
    # Locale in new_context() call
    ctx_kwargs = browser.new_context.call_args
    assert ctx_kwargs[1]["locale"] == "de-DE"


@patch("cloakbrowser.browser.ensure_binary", return_value="/fake/chrome")
@patch("cloakbrowser.browser.launch")
def test_timezone_via_context_not_binary(mock_launch, _mock_bin):
    """timezone passed to new_context(timezone_id=...) but NOT to launch(timezone=...).

    This is intentional: the --fingerprint-timezone binary flag only applies to the
    default context and would conflict with Playwright's timezone_id on new contexts.
    """
    browser, context = _make_mock_browser()
    mock_launch.return_value = browser

    from cloakbrowser.browser import launch_context
    launch_context(timezone="America/New_York")

    # timezone=None in launch() — binary flag skipped
    assert mock_launch.call_args[1]["timezone"] is None
    # timezone_id in new_context()
    ctx_kwargs = browser.new_context.call_args
    assert ctx_kwargs[1]["timezone_id"] == "America/New_York"


@patch("cloakbrowser.browser.ensure_binary", return_value="/fake/chrome")
@patch("cloakbrowser.browser.launch")
def test_color_scheme(mock_launch, _mock_bin):
    """color_scheme forwarded to new_context()."""
    browser, context = _make_mock_browser()
    mock_launch.return_value = browser

    from cloakbrowser.browser import launch_context
    launch_context(color_scheme="dark")

    ctx_kwargs = browser.new_context.call_args
    assert ctx_kwargs[1]["color_scheme"] == "dark"


@patch("cloakbrowser.browser._maybe_resolve_geoip", return_value=("Europe/Berlin", "de-DE"))
@patch("cloakbrowser.browser.ensure_binary", return_value="/fake/chrome")
@patch("cloakbrowser.browser.launch")
def test_geoip_resolution(mock_launch, _mock_bin, _mock_geoip):
    """geoip fills timezone+locale, both flow to correct places."""
    browser, context = _make_mock_browser()
    mock_launch.return_value = browser

    from cloakbrowser.browser import launch_context
    launch_context(proxy="http://proxy:8080", geoip=True)

    # Locale goes to launch() for binary flag
    assert mock_launch.call_args[1]["locale"] == "de-DE"
    # Timezone goes to context, not binary
    assert mock_launch.call_args[1]["timezone"] is None
    ctx_kwargs = browser.new_context.call_args
    assert ctx_kwargs[1]["timezone_id"] == "Europe/Berlin"
    assert ctx_kwargs[1]["locale"] == "de-DE"


@patch("cloakbrowser.browser.ensure_binary", return_value="/fake/chrome")
@patch("cloakbrowser.browser.launch")
def test_timezone_id_deprecation(mock_launch, _mock_bin):
    """timezone_id kwarg triggers FutureWarning, value migrated to timezone."""
    browser, context = _make_mock_browser()
    mock_launch.return_value = browser

    from cloakbrowser.browser import launch_context
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        launch_context(timezone_id="Europe/Paris")

    assert len(w) == 1
    assert issubclass(w[0].category, FutureWarning)
    assert "timezone_id" in str(w[0].message)
    # Migrated value flows to context
    ctx_kwargs = browser.new_context.call_args
    assert ctx_kwargs[1]["timezone_id"] == "Europe/Paris"


@patch("cloakbrowser.browser.ensure_binary", return_value="/fake/chrome")
@patch("cloakbrowser.browser.launch")
def test_close_closes_browser(mock_launch, _mock_bin):
    """context.close() also calls browser.close()."""
    browser, context = _make_mock_browser()
    # Save reference before launch_context() monkey-patches context.close
    original_ctx_close = context.close
    mock_launch.return_value = browser

    from cloakbrowser.browser import launch_context
    ctx = launch_context()

    # The returned context has a patched close()
    ctx.close()
    # Original context close was called
    original_ctx_close.assert_called_once()
    # Browser close was also called
    browser.close.assert_called_once()


@patch("cloakbrowser.browser.ensure_binary", return_value="/fake/chrome")
@patch("cloakbrowser.browser.launch")
def test_error_closes_browser(mock_launch, _mock_bin):
    """If new_context() raises, browser is still closed."""
    browser = MagicMock()
    browser.new_context.side_effect = RuntimeError("context creation failed")
    mock_launch.return_value = browser

    from cloakbrowser.browser import launch_context
    with pytest.raises(RuntimeError, match="context creation failed"):
        launch_context()

    browser.close.assert_called_once()


@patch("cloakbrowser.browser.ensure_binary", return_value="/fake/chrome")
@patch("cloakbrowser.browser.launch")
def test_kwargs_passthrough(mock_launch, _mock_bin):
    """Extra kwargs forwarded to new_context(), NOT to launch().

    Important contract: kwargs like record_video_dir go to context creation,
    not browser launch.
    """
    browser, context = _make_mock_browser()
    mock_launch.return_value = browser

    from cloakbrowser.browser import launch_context
    launch_context(record_video_dir="/tmp/videos")

    # Verify kwarg reached new_context()
    ctx_kwargs = browser.new_context.call_args
    assert ctx_kwargs[1]["record_video_dir"] == "/tmp/videos"

    # Verify kwarg did NOT leak to launch()
    launch_kwargs = mock_launch.call_args[1]
    assert "record_video_dir" not in launch_kwargs
