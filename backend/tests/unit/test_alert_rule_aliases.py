from pydantic import ValidationError

from app.domain.schemas import AlertRuleIn


def test_alert_rule_aliases_normalize_to_canonical_values():
    below = AlertRuleIn(
        watch_id="watch-1",
        rule_type="threshold_below",
        threshold_value=30,
    )
    above = AlertRuleIn(
        watch_id="watch-1",
        rule_type="threshold_above",
        threshold_value=60,
    )

    assert below.rule_type == "threshold_low"
    assert above.rule_type == "threshold_high"


def test_threshold_rules_require_threshold_value():
    try:
        AlertRuleIn(
            watch_id="watch-1",
            rule_type="threshold_low",
            threshold_value=None,
        )
    except ValidationError as exc:
        assert "threshold_value_required" in str(exc)
    else:
        raise AssertionError("threshold_low must require threshold_value")
