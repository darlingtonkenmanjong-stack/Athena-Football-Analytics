def build_ai_decision(
    player_name,
    team_name,
    alerts,
    forecast=None
):
    """
    Explainable rule-based AI decision-support engine.

    Combines persistent live alerts with second-half forecasts
    and returns a transparent tactical recommendation.
    """

    if not alerts:
        return None

    forecast = forecast or {}

    severities = {
        "Informational": 1,
        "Moderate": 2,
        "High": 3,
        "Critical": 4
    }

    strongest_alert = max(
        alerts,
        key=lambda x: severities.get(x.get("severity", "Informational"), 0)
    )

    severity = strongest_alert.get("severity", "Informational")
    category = strongest_alert.get("category", "Performance")

    evidence = []
    rule_ids = []

    for alert in alerts:
        alert_category = alert.get("category", "Performance")
        alert_severity = alert.get("severity", "Informational")

        evidence.append(
            f"{alert_category} alert is {alert_severity}"
        )

    recommendation = "Continue monitoring the player."
    tactical_action = "Monitor"

    if category == "Passing Execution":

        if severity in ["High", "Critical"]:
            recommendation = (
                "Consider additional passing support, a role adjustment, "
                "or substitution monitoring."
            )
            tactical_action = "Role adjustment / support"
            rule_ids.append("AI-RULE-PASS-01")

        elif severity == "Moderate":
            recommendation = (
                "Monitor passing execution and consider additional "
                "support if the deviation persists."
            )
            tactical_action = "Monitor"
            rule_ids.append("AI-RULE-PASS-02")

    elif category == "Progression":

        if severity in ["High", "Critical"]:
            recommendation = (
                "Consider adjusting the player's positioning or passing "
                "options to improve progression."
            )
            tactical_action = "Role adjustment"
            rule_ids.append("AI-RULE-PROG-01")

        else:
            recommendation = (
                "Monitor progression and provide additional passing "
                "options if the decline continues."
            )
            tactical_action = "Monitor"
            rule_ids.append("AI-RULE-PROG-02")

    elif category == "Involvement":

        if severity in ["High", "Critical"]:
            recommendation = (
                "Consider a role or positional adjustment to increase "
                "the player's involvement."
            )
            tactical_action = "Role adjustment"
            rule_ids.append("AI-RULE-INV-01")

        else:
            recommendation = (
                "Monitor involvement and assess whether tactical support "
                "is required."
            )
            tactical_action = "Monitor"
            rule_ids.append("AI-RULE-INV-02")

    predicted_actions = forecast.get("second_half_actions_per90")
    predicted_progression = forecast.get(
        "second_half_progressive_passes_per90"
    )
    predicted_completion = forecast.get(
        "second_half_pass_completion_rate"
    )
    predicted_miscontrols = forecast.get(
        "second_half_miscontrols_per90"
    )
    predicted_xg = forecast.get(
        "second_half_statsbomb_xg_per90"
    )

    if predicted_actions is not None:
        evidence.append(
            f"Forecast second-half actions/90: {predicted_actions:.2f}"
        )

    if predicted_progression is not None:
        evidence.append(
            f"Forecast progressive passes/90: {predicted_progression:.2f}"
        )

    if predicted_completion is not None:

        completion_display = predicted_completion

        if predicted_completion <= 1:
            completion_display = predicted_completion * 100

        evidence.append(
            f"Forecast pass completion: {completion_display:.2f}%"
        )

    if predicted_miscontrols is not None:
        evidence.append(
            f"Forecast miscontrols/90: {predicted_miscontrols:.2f}"
        )

    if predicted_xg is not None:
        evidence.append(
            f"Forecast xG/90: {predicted_xg:.2f}"
        )

    if len(alerts) >= 2:
        evidence.append(
            f"{len(alerts)} persistent performance alerts are active"
        )

        if severity in ["High", "Critical"]:
            recommendation = (
                "Multiple persistent performance concerns are active. "
                "Consider tactical support, role adjustment, and "
                "substitution monitoring."
            )
            tactical_action = "Tactical intervention"
            rule_ids.append("AI-RULE-MULTI-01")

    return {
        "player": player_name,
        "team": team_name,
        "severity": severity,
        "primary_issue": category,
        "tactical_action": tactical_action,
        "recommendation": recommendation,
        "rule_ids": rule_ids,
        "evidence": evidence,
        "explanation": " | ".join(evidence)
    }
