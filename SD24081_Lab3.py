"""BSD3513 Lab 3 - Explainable Scholarship Advisory Rule-Based System.

Run: streamlit run SD24081_Lab3.py
The five DEFAULT_RULES are transcribed verbatim from the assignment.
"""
from __future__ import annotations

import json
import operator
from typing import Any

import pandas as pd
import streamlit as st

DEFAULT_RULES = [
    {
        "name": "Top merit candidate", "priority": 100,
        "conditions": [["cgpa", ">=", 3.7], ["co_curricular_score", ">=", 80],
                       ["family_income", "<=", 8000], ["disciplinary_actions", "==", 0]],
        "action": {"decision": "AWARD_FULL", "reason": "Excellent academic & co-curricular performance, with acceptable need"}
    },
    {
        "name": "Good candidate - partial scholarship", "priority": 80,
        "conditions": [["cgpa", ">=", 3.3], ["co_curricular_score", ">=", 60],
                       ["family_income", "<=", 12000], ["disciplinary_actions", "<=", 1]],
        "action": {"decision": "AWARD_PARTIAL", "reason": "Good academic & involvement record with moderate need"}
    },
    {
        "name": "Need-based review", "priority": 70,
        "conditions": [["cgpa", ">=", 2.5], ["family_income", "<=", 4000]],
        "action": {"decision": "REVIEW", "reason": "High need but borderline academic score"}
    },
    {
        "name": "Low CGPA – not eligible", "priority": 95,
        "conditions": [["cgpa", "<", 2.5]],
        "action": {"decision": "REJECT", "reason": "CGPA below minimum scholarship requirement"}
    },
    {
        "name": "Serious disciplinary record", "priority": 90,
        "conditions": [["disciplinary_actions", ">=", 2]],
        "action": {"decision": "REJECT", "reason": "Too many disciplinary records"}
    }
]

OPS = {"==": operator.eq, "!=": operator.ne, ">": operator.gt, ">=": operator.ge,
       "<": operator.lt, "<=": operator.le, "in": lambda a,b: a in b,
       "not_in": lambda a,b: a not in b}
FIELDS = {"cgpa", "family_income", "co_curricular_score", "community_service_hours",
          "semester", "disciplinary_actions"}
DECISIONS = {"AWARD_FULL", "AWARD_PARTIAL", "REVIEW", "REJECT"}


def validate_rules(raw: Any) -> list[dict]:
    """Reject malformed JSON rules instead of silently using unrelated defaults."""
    if not isinstance(raw, list) or not raw:
        raise ValueError("Rules must be a non-empty JSON array.")
    for i, rule in enumerate(raw, 1):
        if not isinstance(rule, dict) or not isinstance(rule.get("name"), str) or not rule["name"].strip():
            raise ValueError(f"Rule {i}: non-empty name required.")
        if type(rule.get("priority")) is not int:
            raise ValueError(f"Rule {i}: priority must be an integer.")
        conds = rule.get("conditions")
        if not isinstance(conds, list) or not conds:
            raise ValueError(f"Rule {i}: non-empty conditions array required.")
        for cond in conds:
            if not isinstance(cond, list) or len(cond) != 3:
                raise ValueError(f"Rule {i}: each condition must be [field, operator, value].")
            field, op, threshold = cond
            if field not in FIELDS or op not in OPS:
                raise ValueError(f"Rule {i}: invalid field/operator: {field!r}, {op!r}.")
            if type(threshold) not in (float, int):
                raise ValueError(f"Rule {i}: a numeric comparison value is required.")
            if op in ("in", "not_in"):
                raise ValueError(f"Rule {i}: membership operators require collection-valued facts; not supported for numeric fields.")
        action = rule.get("action")
        if not isinstance(action, dict) or action.get("decision") not in DECISIONS or not isinstance(action.get("reason"), str):
            raise ValueError(f"Rule {i}: action needs a valid decision and reason.")
    return raw


def evaluate_condition(facts: dict, condition: list) -> bool:
    field, op, value = condition
    return field in facts and OPS[op](facts[field], value)


def explain_rule(facts: dict, rule: dict) -> dict:
    checks = [{"field": field, "actual": facts.get(field), "operator": op,
               "threshold": value, "passed": evaluate_condition(facts, [field, op, value])}
              for field, op, value in rule["conditions"]]
    return {"name": rule["name"], "priority": rule["priority"],
            "matched": all(c["passed"] for c in checks), "checks": checks,
            "decision": rule["action"]["decision"], "reason": rule["action"]["reason"]}


def evaluate_applicant(facts: dict, rules: list[dict]) -> dict:
    """Priority-descending first-match inference; original rule order breaks priority ties."""
    explanations = [explain_rule(facts, rule) for rule in rules]
    matched = sorted((e for e in explanations if e["matched"]),
                     key=lambda e: -e["priority"])
    winner = matched[0] if matched else None
    return {"decision": winner["decision"] if winner else "REVIEW",
            "reason": winner["reason"] if winner else "No supplied rule matched; committee review is required.",
            "winning_rule": winner["name"] if winner else "None - safe fallback",
            "matching_rules": matched, "rule_trace": explanations}


def test_cases() -> list[dict]:
    base = {"cgpa": 3.8, "family_income": 5000, "co_curricular_score": 85,
            "community_service_hours": 30, "semester": 4, "disciplinary_actions": 0}
    examples = [
        ("Full award", {}, "AWARD_FULL"),
        ("Partial award", {"cgpa": 3.5, "co_curricular_score": 65}, "AWARD_PARTIAL"),
        ("Financial need review", {"cgpa": 2.8, "family_income": 3000, "co_curricular_score": 30}, "REVIEW"),
        ("Low CGPA rejection", {"cgpa": 2.4}, "REJECT"),
        ("Disciplinary rejection", {"disciplinary_actions": 2}, "REJECT"),
        ("No matching rule", {"cgpa": 2.9, "family_income": 9500, "co_curricular_score": 40}, "REVIEW"),
        ("Rule priority overlap", {"cgpa": 3.85, "family_income": 3200, "co_curricular_score": 88}, "AWARD_FULL"),
        ("CGPA exactly 3.70", {"cgpa": 3.7}, "AWARD_FULL"),
        ("Income exceeds full threshold", {"family_income": 8001}, "AWARD_PARTIAL"),
    ]
    rows = []
    for title, overrides, expected in examples:
        facts = {**base, **overrides}
        outcome = evaluate_applicant(facts, DEFAULT_RULES)
        rows.append({"Case": title, "Expected": expected, "Actual": outcome["decision"],
                     "Pass": outcome["decision"] == expected, "Winning rule": outcome["winning_rule"]})
    return rows


def main() -> None:
    st.set_page_config(page_title="Scholarship Advisory | BSD3513 Lab 3", page_icon="🎓", layout="wide")
    st.title("🎓 Scholarship Advisory Rule-Based System")
    st.caption("BSD3513 | Lab 3 | Chapter 3: Knowledge Representation System | SD24081")
    st.info("Decision-support demonstration. Results apply only the supplied academic exercise rules; a university committee makes final scholarship decisions.")

    with st.sidebar:
        st.header("Applicant information")
        cgpa = st.number_input("CGPA (0.00–4.00)", min_value=0.0, max_value=4.0, value=3.80, step=0.01, format="%.2f")
        income = st.number_input("Monthly family income (RM)", min_value=0.0, value=5000.0, step=100.0)
        co_score = st.slider("Co-curricular involvement (0–100)", 0, 100, 85)
        service = st.number_input("Community service hours", min_value=0, value=30, step=1)
        semester = st.number_input("Current semester", min_value=1, max_value=30, value=4, step=1)
        disciplinary = st.number_input("Disciplinary actions", min_value=0, max_value=99, value=0, step=1)

    facts = {"cgpa": float(cgpa), "family_income": float(income),
             "co_curricular_score": int(co_score), "community_service_hours": int(service),
             "semester": int(semester), "disciplinary_actions": int(disciplinary)}
    st.markdown("### How the rule engine works")
    st.write("**Facts → IF conditions (AND) → matching rules → highest priority → decision and reason.** "
             "If rules share a priority, their order in the JSON breaks the tie. If none matches, the system returns REVIEW.")
    st.caption("Community service hours and semester are collected as facts, but the five assignment rules do not reference them. Editing the JSON can add conditions on these fields.")
    with st.expander("Edit the five assignment rules (JSON)", expanded=False):
        st.warning("The default five rules match the assignment. Any changes are an optional experiment, not the official specification.")
        def reset_assignment_rules() -> None:
            st.session_state["rule_json"] = json.dumps(DEFAULT_RULES, indent=2, ensure_ascii=False)

        c1, c2 = st.columns(2)
        with c1:
            st.download_button("Download assignment rules", json.dumps(DEFAULT_RULES, indent=2, ensure_ascii=False),
                               "scholarship_rules.json", "application/json")
        with c2:
            st.button("Reset JSON to assignment rules", on_click=reset_assignment_rules)
        st.text_area("JSON rule editor", value=json.dumps(DEFAULT_RULES, indent=2, ensure_ascii=False),
                     height=420, key="rule_json")
    try:
        rules = validate_rules(json.loads(st.session_state.get("rule_json", json.dumps(DEFAULT_RULES))))
        st.success(f"Valid rules loaded: {len(rules)}")
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        st.error(f"Rule validation error: {exc}. Correct the JSON to evaluate; rules will NOT silently revert.")
        return

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Current applicant facts")
        st.json(facts)
        run = st.button("Evaluate scholarship eligibility", type="primary", use_container_width=True)
    with right:
        st.subheader("Assignment rule priorities")
        st.dataframe(pd.DataFrame([{"Rule": r["name"], "Priority": r["priority"],
                                   "Decision": r["action"]["decision"]} for r in sorted(rules, key=lambda r: -r["priority"])]),
                     use_container_width=True, hide_index=True)
    if run:
        st.session_state["result"] = evaluate_applicant(facts, rules)
        st.session_state["last_facts"] = facts
        st.session_state["last_rules"] = rules
    if "result" in st.session_state:
        if facts != st.session_state.get("last_facts") or rules != st.session_state.get("last_rules"):
            st.warning("Inputs or rules changed. Evaluate again to update the result.")
        result = st.session_state["result"]
        st.markdown("### Scholarship recommendation")
        heading = f"{result['decision']} — {result['reason']}"
        if result["decision"] in ("AWARD_FULL", "AWARD_PARTIAL"):
            st.success(heading)
        elif result["decision"] == "REJECT":
            st.error(heading)
        else:
            st.warning(heading)
        st.write(f"**Winning rule:** {result['winning_rule']}")
        st.write(f"**Matching rules:** {len(result['matching_rules'])} / {len(rules)}")
        with st.expander("Explain every IF condition", expanded=True):
            for trace in sorted(result["rule_trace"], key=lambda item: -item["priority"]):
                st.markdown(f"**{'MATCH' if trace['matched'] else 'NO MATCH'} — {trace['name']} (priority {trace['priority']})**")
                df = pd.DataFrame(trace["checks"])
                df["passed"] = df["passed"].map({True: "PASS", False: "FAIL"})
                st.dataframe(df.rename(columns={"field": "Fact", "actual": "Actual", "operator": "Test", "threshold": "Threshold", "passed": "Result"}),
                             hide_index=True, use_container_width=True)
        payload = {"facts": st.session_state.get("last_facts"), "decision": result["decision"],
                   "reason": result["reason"], "winning_rule": result["winning_rule"],
                   "matching_rules": [r["name"] for r in result["matching_rules"]]}
        st.download_button("Download decision evidence (JSON)", json.dumps(payload, indent=2),
                           "scholarship_decision.json", "application/json")
    st.divider()
    st.markdown("### Built-in verification cases")
    check = pd.DataFrame(test_cases())
    st.dataframe(check, use_container_width=True, hide_index=True)
    st.metric("Passed test cases", f"{int(check['Pass'].sum())}/{len(check)}")
    st.caption("Limitations: illustrative scholarship rules are not official university policy. Thresholds must be confirmed by the scholarship committee.")


if __name__ == "__main__":
    main()
