"""
Shared pytest fixtures for the Gita Agent test suite.

Currently provides only `in_memory_spans` — an in-memory OTel span exporter
wired into ingestion.observability so per-module tests can assert that the
expected spans were emitted without contacting Cloud Trace.
"""

import pytest


@pytest.fixture
def in_memory_spans():
    """Reset observability to use an in-memory span exporter and yield it.

    Any tracer obtained via `ingestion.observability.get_tracer(...)` during
    the test will emit spans into the returned `InMemorySpanExporter`.
    Test bodies typically call:

        spans = in_memory_spans.get_finished_spans()
        assert any(s.name == "drive.download" for s in spans)
    """
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    from ingestion import observability

    observability.reset_for_testing()
    exporter = InMemorySpanExporter()
    observability.init_tracing(
        exporter=exporter, processor_cls=SimpleSpanProcessor
    )
    yield exporter
    observability.reset_for_testing()
