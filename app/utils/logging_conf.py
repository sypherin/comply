from __future__ import annotations
import os
import logging

def setup_logging():
    level = os.getenv("LOG_LEVEL","INFO").upper()
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    conn = os.getenv("AZURE_MONITOR_CONNECTION_STRING")
    if conn:
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            provider = TracerProvider()
            processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=conn))
            provider.add_span_processor(processor)
            trace.set_tracer_provider(provider)
            logging.getLogger("app").info("OpenTelemetry OTLP exporter configured.")
        except Exception:
            logging.getLogger("app").warning("Failed to configure OpenTelemetry exporter.")
