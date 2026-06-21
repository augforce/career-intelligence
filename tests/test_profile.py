from app.profile import load_profile


def test_profile_loads_and_weights_sum_to_100():
    p = load_profile()
    assert p.version == 1
    assert sum(p.weights.values()) == 100
    assert set(p.weights) == {
        "build_intensity", "ai_platform_relevance", "career_progression",
        "remote_fit", "developer_proximity", "current_strengths", "enablement_fit",
    }


def test_profile_has_gate_thresholds_for_all_role_gates():
    p = load_profile()
    for gate in ("support", "admin", "sales_customer", "traditional_swe"):
        assert "body_density_min" in p.gates[gate]
        assert "title_keywords" in p.gates[gate]


def test_unknown_remote_fit_default_is_5():
    assert load_profile().remote_fit["unknown_default"] == 5
