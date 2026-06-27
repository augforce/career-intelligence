"""Hard invariants for the labeled calibration set.

These assert only the framework's non-negotiable boundaries. Exact placement of
the fuzzy bridge/stretch middle (e.g. "proceed"-grade enablement roles that sit
near the strong/bridge line) is calibration-sensitive and is *reported* by
`python -m tests.calibration`, not asserted here, so the suite does not become a
tuning straitjacket.

The core regression guard is `test_genuine_targets_outrank_near_misses`: it
reproduces the reported bug — an AI-in-passing role scoring as high as (or higher
than) a role genuinely centered on the target work.
"""
from app.profile import load_profile
from app.models import NormalizedJob
from app.evaluate import evaluate_job
from tests.calibration import run
from tests.fixtures import sample_jobs

ROWS = {r["key"]: r for r in run()}

_P = load_profile()


def _category(title, description):
    job = NormalizedJob(title=title, company_name="C", description=description)
    return evaluate_job(job, _P, _P.location_defaults).category

# Genuine target families (framework §4 primary roles).
GENUINE = ["ai_platform_ops", "ai_platform_admin", "ai_ops_engineer"]
# The two unambiguous platform-ownership roles must always be Strong.
CLEAR_STRONG = ["ai_platform_ops", "ai_platform_admin"]
# Poor fits whose AI content is confined to one isolated slice (the failure mode).
ADVERSARIAL = ["security_engineer", "mlops_ml_engineer", "ai_trainer"]
# Clear rejects guarded by gates/penalties (regression guard).
HARD_REJECTS = ["helpdesk", "senior_swe", "crm_admin_ai", "customer_success_ai"]


def test_clear_platform_roles_are_strong():
    for key in CLEAR_STRONG:
        assert ROWS[key]["actual"] == "strong_match", (
            f"{key} should be Strong, got {ROWS[key]['actual']} ({ROWS[key]['final']})")


def test_genuine_targets_outrank_near_misses():
    worst_genuine = min(ROWS[k]["final"] for k in GENUINE)
    best_near_miss = max(ROWS[k]["final"] for k in ADVERSARIAL)
    assert worst_genuine > best_near_miss, (
        f"A genuine target must outscore every AI-in-passing role. "
        f"worst genuine={worst_genuine}, best near-miss={best_near_miss} "
        f"({[(k, ROWS[k]['final']) for k in ADVERSARIAL]})")


def test_adversarial_near_misses_are_not_strong():
    for key in ADVERSARIAL:
        assert ROWS[key]["actual"] != "strong_match", (
            f"{key} is AI-in-passing and must NOT be Strong, got {ROWS[key]['final']}")


def test_hard_rejects_are_poor():
    for key in HARD_REJECTS:
        assert ROWS[key]["actual"] == "poor_fit", (
            f"{key} should be Poor Fit, got {ROWS[key]['actual']} ({ROWS[key]['final']})")


# ---- Composition / focus rule (framework §0, §2, §5) ----

def test_pure_enablement_without_platform_is_poor():
    # ai_trainer: training + change-management, zero platform/build. Framework §5:
    # "AI Enablement — Good only when paired with platform work ... Training alone
    # is not enough." So enablement signal alone must not carry it.
    assert ROWS["ai_trainer"]["actual"] == "poor_fit", (
        f"pure-training role must be Poor, got {ROWS['ai_trainer']['final']}")


def test_ai_in_passing_security_role_is_poor():
    # security_engineer: a primary security role whose only AI content is one
    # governance bullet. Framework §0 "AI sprinkled onto support is not enough" and
    # §8 "do not push ... into security ... just because individual bullets overlap."
    assert ROWS["security_engineer"]["actual"] == "poor_fit", (
        f"AI-in-passing security role must be Poor, got {ROWS['security_engineer']['final']}")


# ---- Independent / from-scratch coding penalty (framework §5 technical bar) ----

def test_familiarity_coding_is_not_penalized():
    # "familiarity with Python a plus" is a bar the candidate clears — it must not
    # trigger the coding penalty, and the role stays a good fit.
    assert ROWS["coding_a_plus"]["coding_penalty"] == 0, (
        f"'Python a plus' must not be docked, got -{ROWS['coding_a_plus']['coding_penalty']}")
    assert ROWS["coding_a_plus"]["actual"] in ("strong_match", "bridge_role"), (
        f"good-fit AI platform role must not be dragged down, got {ROWS['coding_a_plus']['actual']}")


def test_independent_coding_is_penalized():
    # "proficiency in Python; writes production code independently; from scratch" is
    # the disqualifier the existing traditional_dev penalty misses.
    assert ROWS["coding_required"]["coding_penalty"] > 0, (
        "from-scratch / independent-authorship coding framing must be docked")


def test_ai_centered_but_coding_gated_role_not_strong():
    # The gap: a role can be genuinely AI-centered (composition rule leaves it alone)
    # yet demand independent from-scratch coding. The penalty must pull it out of Strong.
    assert ROWS["coding_required"]["actual"] != "strong_match", (
        f"AI-centered + independent-coding role must not be Strong, got {ROWS['coding_required']['final']}")


def test_focus_rule_does_not_regress_genuine_admin_heavy_targets():
    # The composition rule must NOT punish roles that are legitimately heavy on the
    # candidate's current-strengths vocab. TARGET_ROLE (the canonical ideal AI
    # Systems Administrator) and STRONG must stay Strong.
    assert _category("AI Systems Administrator", sample_jobs.TARGET_ROLE) == "strong_match"
    assert _category("AI Platform Operations Specialist", sample_jobs.STRONG) == "strong_match"
