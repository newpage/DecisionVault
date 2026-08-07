from app.modules.decisions.schemas import DecisionCreate


def test_decision_defaults_are_industry_neutral():
    decision = DecisionCreate(
        workspace_id="workspace-id",
        title="Review operating model",
        question="Should the proposed operating model be approved?",
        supplier_name="Decision subject",
        owner_name="Decision owner",
    )

    assert decision.supplier_category == ""
    assert decision.business_unit == ""
