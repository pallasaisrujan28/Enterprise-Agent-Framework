"""Policy enforcement — loads YAML rules and evaluates against them.

Works alongside gate.py (skill obligation engine): gate.py enforces per-skill
obligations; this module enforces platform-wide policies (PII, data residency).
"""
