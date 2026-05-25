"""
Tests for ingestion/observability.py — OpenTelemetry tracer + Cloud Trace export.

TDD Phase: RED — tests written before implementation.

Covers:
- Env-gated export decision (PYTEST_CURRENT_TEST, K_SERVICE, OTEL_EXPORT_ENABLED).
- TracerProvider initialization with Cloud Trace exporter (when enabled).
- Span emission with arbitrary attributes captured correctly.
- structlog log-correlation processor injects trace_id/span_id when a span is active.

Design reference: docs/detailed_technical_design.md § 5.6
"""

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_observability_module():
    """Each test starts with a fresh, uninitialized TracerProvider."""
    from ingestion import observability
    observability.reset_for_testing()
    yield
    observability.reset_for_testing()


@pytest.fixture
def in_memory_exporter():
    """Build a synchronous in-memory exporter and wire it into observability."""
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    from ingestion import observability

    exporter = InMemorySpanExporter()
    observability.init_tracing(
        exporter=exporter, processor_cls=SimpleSpanProcessor
    )
    return exporter


# ---------------------------------------------------------------------------
# is_export_enabled — env-detection logic
# ---------------------------------------------------------------------------

class TestIsExportEnabled:
    def test_disabled_in_pytest_by_default(self, monkeypatch):
        """Presence of PYTEST_CURRENT_TEST disables export in the absence of override."""
        monkeypatch.delenv("OTEL_EXPORT_ENABLED", raising=False)
        monkeypatch.setenv("PYTEST_CURRENT_TEST", "fake_test::xyz")

        from ingestion import observability
        assert observability.is_export_enabled() is False

    def test_enabled_for_local_dev_run(self, monkeypatch):
        """No PYTEST_CURRENT_TEST, no override → enabled (covers local CLI + Cloud Run)."""
        monkeypatch.delenv("OTEL_EXPORT_ENABLED", raising=False)
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        from ingestion import observability
        assert observability.is_export_enabled() is True

    def test_enabled_in_cloud_run(self, monkeypatch):
        """K_SERVICE present (Cloud Run signal) keeps export on."""
        monkeypatch.delenv("OTEL_EXPORT_ENABLED", raising=False)
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        monkeypatch.setenv("K_SERVICE", "ingest-recordings")

        from ingestion import observability
        assert observability.is_export_enabled() is True

    def test_explicit_true_overrides_pytest(self, monkeypatch):
        """OTEL_EXPORT_ENABLED=true wins even inside pytest (for the OTel tests themselves)."""
        monkeypatch.setenv("OTEL_EXPORT_ENABLED", "true")
        monkeypatch.setenv("PYTEST_CURRENT_TEST", "fake_test::xyz")

        from ingestion import observability
        assert observability.is_export_enabled() is True

    def test_explicit_false_overrides_local_dev(self, monkeypatch):
        """OTEL_EXPORT_ENABLED=false silences export even in dev (offline work)."""
        monkeypatch.setenv("OTEL_EXPORT_ENABLED", "false")
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        from ingestion import observability
        assert observability.is_export_enabled() is False

    @pytest.mark.parametrize("truthy", ["true", "TRUE", "1", "yes", "on"])
    def test_truthy_values(self, monkeypatch, truthy):
        monkeypatch.setenv("OTEL_EXPORT_ENABLED", truthy)
        monkeypatch.setenv("PYTEST_CURRENT_TEST", "x")
        from ingestion import observability
        assert observability.is_export_enabled() is True

    @pytest.mark.parametrize("falsy", ["false", "0", "no", "off", ""])
    def test_falsy_values(self, monkeypatch, falsy):
        monkeypatch.setenv("OTEL_EXPORT_ENABLED", falsy)
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        from ingestion import observability
        assert observability.is_export_enabled() is False


# ---------------------------------------------------------------------------
# init_tracing — wires Cloud Trace exporter when enabled
# ---------------------------------------------------------------------------

class TestInitTracing:
    def test_tracer_initializes_with_cloud_trace_exporter(self, monkeypatch):
        """When export is on and no injected exporter, Cloud Trace exporter is used."""
        monkeypatch.setenv("OTEL_EXPORT_ENABLED", "true")
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        with patch(
            "ingestion.observability.CloudTraceSpanExporter"
        ) as MockExporter:
            MockExporter.return_value = MagicMock()
            from ingestion import observability
            provider = observability.init_tracing()

            MockExporter.assert_called_once()
            assert provider is not None
            # Provider should have at least one span processor attached.
            assert provider._active_span_processor is not None

    def test_no_exporter_when_export_disabled(self, monkeypatch):
        """Disabled export → provider has no Cloud Trace exporter (NoOp-equivalent)."""
        monkeypatch.setenv("OTEL_EXPORT_ENABLED", "false")
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        with patch(
            "ingestion.observability.CloudTraceSpanExporter"
        ) as MockExporter:
            from ingestion import observability
            observability.init_tracing()
            MockExporter.assert_not_called()

    def test_cloud_trace_init_failure_does_not_crash(self, monkeypatch):
        """If CloudTraceSpanExporter() raises (no creds, no network), get a working provider anyway."""
        monkeypatch.setenv("OTEL_EXPORT_ENABLED", "true")
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        with patch(
            "ingestion.observability.CloudTraceSpanExporter",
            side_effect=RuntimeError("no credentials"),
        ):
            from ingestion import observability
            provider = observability.init_tracing()
            # Should still return a usable provider — pipeline must not crash on telemetry init.
            assert provider is not None
            tracer = provider.get_tracer("test")
            with tracer.start_as_current_span("x") as span:
                span.set_attribute("k", "v")

    def test_injected_exporter_is_used(self, in_memory_exporter):
        """When an exporter is injected (test path), it receives spans."""
        from ingestion import observability
        tracer = observability.get_tracer("test")
        with tracer.start_as_current_span("injected_test"):
            pass
        finished = in_memory_exporter.get_finished_spans()
        assert len(finished) == 1
        assert finished[0].name == "injected_test"


# ---------------------------------------------------------------------------
# Span emission — attributes captured
# ---------------------------------------------------------------------------

class TestSpanEmission:
    def test_spans_are_emitted_with_correct_attributes(self, in_memory_exporter):
        """A span captures every attribute set on it, with correct name."""
        from ingestion import observability
        tracer = observability.get_tracer("test")

        with tracer.start_as_current_span("drive.download") as span:
            span.set_attribute("video_id", "nanna_udaya_2025_07_06")
            span.set_attribute("size_bytes", 671088640)

        spans = in_memory_exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].name == "drive.download"
        assert spans[0].attributes["video_id"] == "nanna_udaya_2025_07_06"
        assert spans[0].attributes["size_bytes"] == 671088640

    def test_nested_spans_form_parent_child(self, in_memory_exporter):
        """A span opened inside another becomes its child (parent_span_id matches)."""
        from ingestion import observability
        tracer = observability.get_tracer("test")

        with tracer.start_as_current_span("parent") as parent:
            with tracer.start_as_current_span("child") as child:
                pass

        spans = in_memory_exporter.get_finished_spans()
        # Children finish before parents, so child is index 0
        assert {s.name for s in spans} == {"parent", "child"}
        child_span = next(s for s in spans if s.name == "child")
        parent_span = next(s for s in spans if s.name == "parent")
        assert child_span.parent.span_id == parent_span.context.span_id


# ---------------------------------------------------------------------------
# structlog correlation
# ---------------------------------------------------------------------------

class TestStructlogCorrelation:
    def test_processor_injects_trace_context_inside_span(self, in_memory_exporter):
        """Inside a span, the structlog processor adds trace_id and span_id."""
        from ingestion import observability
        tracer = observability.get_tracer("test")
        processor = observability.inject_trace_context

        with tracer.start_as_current_span("test_span"):
            event_dict = processor(None, "info", {"event": "test"})

        assert "trace_id" in event_dict
        assert "span_id" in event_dict
        # trace_id is 32 hex chars; span_id is 16 hex chars
        assert len(event_dict["trace_id"]) == 32
        assert len(event_dict["span_id"]) == 16

    def test_processor_omits_trace_context_outside_span(self):
        """Outside any span, the processor leaves the event dict unchanged."""
        from ingestion import observability
        processor = observability.inject_trace_context

        event_dict = processor(None, "info", {"event": "test"})
        assert "trace_id" not in event_dict
        assert "span_id" not in event_dict
