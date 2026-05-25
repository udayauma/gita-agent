"""
OpenTelemetry tracing + Cloud Trace exporter for the Gita Agent ingestion pipeline.

Provides a single configured TracerProvider that every ingestion module pulls
tracers from via `get_tracer(__name__)`. Spans created with those tracers are
batched and shipped to Google Cloud Trace — or to an injected exporter in tests.

Design reference: docs/detailed_technical_design.md § 5.6

Environment-gated export
------------------------
`is_export_enabled()` decides whether to ship spans to Cloud Trace.

Decision order (first match wins):
1. `OTEL_EXPORT_ENABLED=true|false` — explicit override. Use this to force
   export on inside the OTel tests themselves, or off during offline dev.
2. `PYTEST_CURRENT_TEST` present → disabled. pytest sets this automatically
   per test, so the rest of the suite never ships spans to Cloud Trace.
3. Otherwise → enabled. Covers local CLI runs (`python -m ingestion.orchestrator`)
   *and* Cloud Run Jobs (`K_SERVICE` is also a signal but the default is the
   same either way, so checking `K_SERVICE` is informational only).

This design lets us verify trace data on local dev runs from day one — the
user explicitly asked for that — while keeping the test suite quiet.

Usage
-----
    from ingestion.observability import get_tracer
    tracer = get_tracer(__name__)

    def my_function(video_id):
        with tracer.start_as_current_span("my_module.do_thing") as span:
            span.set_attribute("video_id", video_id)
            ...
"""

from __future__ import annotations

import os
from typing import Optional

import structlog
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = structlog.get_logger(__name__)

DEFAULT_SERVICE_NAME = "gita-ingestion"

# Module-level cache of the configured provider. We intentionally do *not*
# call `trace.set_tracer_provider()` — we keep our own reference so tests
# can swap it freely without poisoning the OTel global.
_provider: Optional[TracerProvider] = None


# ---------------------------------------------------------------------------
# Env-detection
# ---------------------------------------------------------------------------

_TRUTHY = {"true", "1", "yes", "on"}


def is_export_enabled() -> bool:
    """Decide whether to export spans to Cloud Trace. See module docstring."""
    explicit = os.environ.get("OTEL_EXPORT_ENABLED")
    if explicit is not None:
        return explicit.strip().lower() in _TRUTHY
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    return True


# ---------------------------------------------------------------------------
# Provider lifecycle
# ---------------------------------------------------------------------------

def init_tracing(
    *,
    service_name: str = DEFAULT_SERVICE_NAME,
    exporter=None,
    processor_cls=None,
) -> TracerProvider:
    """Build (or rebuild) the TracerProvider and return it.

    Args:
        service_name: Resource service.name. Shows up in Cloud Trace.
        exporter: Optional injected exporter (tests pass InMemorySpanExporter).
            When None and export is enabled, a CloudTraceSpanExporter is built.
        processor_cls: Span processor class. Defaults to BatchSpanProcessor
            for production; tests pass SimpleSpanProcessor for sync emission.

    Returns:
        The configured TracerProvider. Subsequent get_tracer() calls use it.
    """
    global _provider
    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)
    proc_cls = processor_cls or BatchSpanProcessor

    if exporter is not None:
        provider.add_span_processor(proc_cls(exporter))
    elif is_export_enabled():
        try:
            cloud_exporter = CloudTraceSpanExporter()
            provider.add_span_processor(proc_cls(cloud_exporter))
        except Exception as e:
            # Telemetry init must never crash the pipeline.
            logger.warning("observability.cloud_trace_init_failed", error=str(e))

    _provider = provider
    return provider


def get_tracer(name: str):
    """Return a tracer for the given module name, initializing the provider lazily."""
    if _provider is None:
        init_tracing()
    return _provider.get_tracer(name)


def reset_for_testing() -> None:
    """Drop the cached provider so the next init_tracing/get_tracer rebuilds fresh."""
    global _provider
    _provider = None


# ---------------------------------------------------------------------------
# structlog ↔ OTel correlation
# ---------------------------------------------------------------------------

def inject_trace_context(logger, method_name, event_dict):
    """structlog processor: inject trace_id + span_id when called inside a span.

    Add to the structlog processor chain in the orchestrator entry point so
    every log line emitted during a span is grep-able back to its Cloud Trace.
    Outside any span, the event dict is returned unchanged.
    """
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx.is_valid:
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict
