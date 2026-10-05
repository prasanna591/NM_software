"""revisions IDENTITY = 0001_initial_schema

The initial SCIX schema.

Two constraints in this migration are IRREVERSIBLE and must never be relaxed:

  1. audit_logs.attribution is NOT NULL.
     Retrofitting attribution means history that was never attributed -- exactly the
     failure this product exists to prevent. See docs/06-integrity-authorship.md 6.4.

  2. data_transformations is an ORDERED, REPLAYABLE log (seq + transform_type + params).
     The spec's provenance example is "Normalization -> Log transformation", a two-step
     chain. A flag-based design cannot satisfy Trace Figure. See docs/03-plot-studio.md 3.13.

Three more constraints are defensive and enforce the core rules:

  3. graph_annotations.source_analysis_id NOT NULL when kind='significance'  (R3)
  4. statistical_analyses.library_version NOT NULL                            (reproducibility)
  5. journal_presets.rule_source + rule_verified_at NOT NULL                 (S2 10)

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-03
"""
