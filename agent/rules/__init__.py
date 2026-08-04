"""Rules — the two-form artifact the business publishes.

model.py        what a rule is: guidance body + obligations + version
loader.py       reading rule files, and refusing unenforceable ones
obligations.py  the parameterised checks a rule author can use without code
"""

from agent.rules.loader import RuleError, RuleSet, load_rule, load_ruleset
from agent.rules.model import Draft, Obligation, Rule, Violation

__all__ = [
    "Draft",
    "Obligation",
    "Rule",
    "RuleError",
    "RuleSet",
    "Violation",
    "load_rule",
    "load_ruleset",
]
