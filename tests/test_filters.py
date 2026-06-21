from app.profile import load_profile
from app.models import NormalizedJob
from app.scoring.classifier import classify_job
from app.scoring.filters import evaluate_gates
from app.db import DEFAULT_SETTINGS
from tests.fixtures.sample_jobs import (STRONG, HELPDESK, SENIOR_SWE, HIGH_BUT_ONSITE, BRIDGE, UNKNOWN_ARR)

P = load_profile()
S = dict(DEFAULT_SETTINGS)


def J(desc, **kw):
    return NormalizedJob(title=kw.pop("title", "Role"), company_name="C", description=desc, **kw)


def gate(desc, title="Role", settings=None, **kw):
    job = J(desc, title=title, **kw)
    cls = classify_job(job, P)
    return evaluate_gates(job, cls, P, settings or S)


def test_strong_remote_role_not_gated():
    assert gate(STRONG, title="AI Platform Operations Specialist").excluded is False


def test_helpdesk_title_triggers_support_gate():
    g = gate(HELPDESK, title="Help Desk Technician")
    assert g.excluded and "support" in g.gates


def test_senior_swe_gated_only_via_body_density():
    g = gate(SENIOR_SWE, title="Senior Software Engineer")
    assert g.excluded and "traditional_swe" in g.gates


def test_platform_engineer_title_not_gated_as_swe():
    # "engineer" in title must NOT gate; body lacks deep-coding density
    g = gate("Administer Azure AI, model deployment, build internal tools and automation.",
             title="AI Platform Engineer")
    assert g.excluded is False


def test_onsite_high_score_role_is_location_gated_by_default():
    g = gate(HIGH_BUT_ONSITE, title="AI Platform Engineer")
    assert g.excluded and any(x.startswith("location") for x in g.gates)


def test_onsite_allowed_when_toggled_on():
    g = gate(HIGH_BUT_ONSITE, title="AI Platform Engineer",
             settings={**S, "include_on_site": True})
    assert g.excluded is False


def test_unknown_arrangement_never_gated():
    assert gate(UNKNOWN_ARR, title="AI Platform Specialist").excluded is False


def test_bridge_role_with_some_support_not_gated():
    assert gate(BRIDGE, title="AI Implementation Analyst").excluded is False
