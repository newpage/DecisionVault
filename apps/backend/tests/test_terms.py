from app.services import terms

def test_terms_are_normalized_and_deduplicated():
    assert terms("Vendor vendor onboarding") == ["vendor", "onboarding"]
