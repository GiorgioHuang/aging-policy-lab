"""Ingest connectors — one module per data source (docs/10).

Phase 2 adds Care-Access-first connectors (StatCan WDS, an NS Open Data source,
a CIHI public table). Each connector fetches a payload, records a DatasetVersion
(checksum + row_count), and hands rows to transform/. Empty in Phase 1.
"""
