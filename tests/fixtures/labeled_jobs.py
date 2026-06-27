"""Labeled regression set for scoring calibration.

Every label is derived from the Career Intelligence Framework (the operating
manual in /reference), NOT from hand-tuning against any single posting. The
`rule` field cites the framework clause that fixes each verdict, so the labels
are auditable against the source of truth rather than opinion.

Bands (framework §6 "Final recommendation bands" == career_profile.yaml bands):
  strong_match  >= 75  "Pursue"
  bridge_role   60-74  "Explore deliberately"
  stretch_role  45-59  "Watch / selective"
  poor_fit      < 45   "Skip"  (or excluded by a hard gate)

The three `adversarial=True` postings reproduce the reported failure mode: a
poor-fit role whose only AI content is one isolated section. The framework is
explicit that these are NOT strong matches:
  §0  "AI sprinkled onto support is not enough."
  §5  Security/Governance: "supporting experience ... do not route the candidate
      into a primary risk/compliance career track unless explicitly requested."
  §8  "Do not push the candidate into security/risk, CRM administration, customer
      success, or traditional senior engineering just because individual bullets
      overlap the background."
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class LabeledJob:
    key: str
    title: str
    description: str
    expected: str          # one of the four categories
    rule: str              # framework clause backing the label
    adversarial: bool = False


# Most roles are held at "Fully remote, United States" so remote_fit is constant
# (15/15) and the ONLY thing that moves the score is how central the AI-platform
# and build work is to the posting. That isolates the behavior under test.
_REMOTE = "Fully remote, United States."

LABELED: list[LabeledJob] = [
    # ---- GENUINE STRONG (Pursue) — AI platform/build threaded through the role ----
    LabeledJob(
        key="ai_platform_ops",
        title="AI Platform Operations Specialist",
        description=(
            f"{_REMOTE} Own day-to-day operations of our Microsoft Foundry environment. "
            "You will create developer-ready model deployments, configure RBAC and API access, "
            "tune content filters and guardrails, manage token and quota cost controls, run model "
            "evaluations, and handle operational troubleshooting. You partner with application teams on "
            "developer enablement and safe-use configuration, write runbooks and platform documentation, "
            "and build internal automation and integrations to streamline provisioning. Requirements: "
            "experience administering an enterprise AI platform, identity and access management, REST API "
            "fluency, monitoring and logging, and a track record of operational ownership."),
        expected="strong_match",
        rule="§4 Primary role family: AI Platform Operations & Technical Enablement Specialist"),
    LabeledJob(
        key="ai_platform_admin",
        title="AI Platform Administrator",
        description=(
            f"{_REMOTE} Administer our enterprise AI platform (Azure AI / Azure OpenAI). "
            "Manage the model catalog and model deployments, configure access controls and RBAC, "
            "own content safety and responsible AI guardrails, set quotas and cost controls, and provide "
            "observability across the platform. You support engineering teams that build on the platform, "
            "handle integrations and SSO/identity, and document operational best practices. This is a "
            "platform administration and enablement role, not a software-engineering role."),
        expected="strong_match",
        rule="§4 Primary role family: AI Platform Administrator / Specialist"),
    LabeledJob(
        key="ai_ops_engineer",
        title="AI Operations Engineer",
        description=(
            f"{_REMOTE} Operate and improve the internal AI systems our teams rely on. You will build and "
            "maintain internal tools and workflow automation, own integrations between our AI platform and "
            "business applications, handle deployment and configuration, and troubleshoot reliability "
            "issues. You work closely with engineers on platform self-service and developer enablement. "
            "This role is operational and tool-building, not a high-volume ticket queue. Requirements: "
            "scripting, APIs, automation, monitoring, and comfort owning operational outcomes."),
        expected="strong_match",
        rule="§4 Primary role family: AI Operations Engineer (technical, not ticket-heavy)"),

    # ---- BRIDGE (Explore deliberately) ----
    LabeledJob(
        key="ai_impl_specialist",
        title="AI Implementation Specialist",
        description=(
            f"{_REMOTE} Help internal teams adopt AI by building practical workflows and automations. "
            "You will configure AI assistants and copilots, build internal tools and integrations via APIs, "
            "and support adoption with documentation and onboarding. You work across technical and business "
            "stakeholders and own deployment readiness. Some training and operational support is expected. "
            "Requirements: implementation experience, scripting or low-code tooling, and strong communication."),
        expected="bridge_role",
        rule="§4 Primary family AI Implementation Specialist; bridge when internal/technical, not consulting"),
    LabeledJob(
        key="technical_ai_enablement",
        title="Technical AI Enablement Lead",
        description=(
            f"{_REMOTE} Drive technical enablement for our AI platform. You will help developers and internal "
            "teams understand available capabilities, design workflow patterns, build internal prototypes and "
            "tools, contribute platform configuration, and produce technical documentation and best practices. "
            "The role pairs enablement with real platform and implementation responsibility. Requirements: "
            "familiarity with AI platforms, APIs, integration patterns, and technical writing."),
        expected="bridge_role",
        rule="§4 Secondary bridge: Technical AI Enablement (proceed when platform/tools/workflows present)"),
    LabeledJob(
        key="dev_experience_ai",
        title="Developer Experience Engineer, AI Platform",
        description=(
            f"{_REMOTE} Improve the developer experience on our Azure AI platform. You will support "
            "application teams with integration troubleshooting, sample apps, and technical onboarding, "
            "maintain reference implementations, and feed platform self-service improvements back to the "
            "platform team. You work directly with engineers. Requirements: APIs, platform fundamentals, "
            "integration debugging, and clear technical communication."),
        expected="bridge_role",
        rule="§4 Secondary bridge: Developer Experience / AI Developer Support (platform work present)"),

    # ---- STRETCH (Watch / selective) — AI-assisted building, coding-leaning ----
    LabeledJob(
        key="ai_solutions_engineer",
        title="AI Solutions Engineer",
        description=(
            f"{_REMOTE} Build applied AI solutions and internal tools. You will prototype and deploy AI "
            "workflows, integrate APIs, and ship internal automation. Comfort writing and maintaining code "
            "is expected, though much of the delivery is AI-assisted. You will collaborate with engineers on "
            "implementation. Requirements: programming ability, API integration, and a portfolio of shipped "
            "tools or automations."),
        expected="stretch_role",
        rule="§4 Stretch: AI Solutions Engineer (track only; AI-assisted building allowed, coding-leaning)"),
    LabeledJob(
        key="internal_ai_tools_eng",
        title="Internal AI Tools Engineer",
        description=(
            f"{_REMOTE} Design and build internal AI tools and automations for the business. You will own "
            "implementation of workflows, integrations, and lightweight apps end to end. The role expects "
            "hands-on development and some independent coding, with AI-assisted tooling encouraged. "
            "Requirements: solid programming skills, API and integration experience, and ownership of delivery."),
        expected="stretch_role",
        rule="§4 Stretch: Internal AI Tools Engineer (valuable only when AI-assisted building allowed)"),

    # ---- POOR (Skip) — clear rejects per hard filters ----
    LabeledJob(
        key="helpdesk",
        title="Help Desk Technician",
        description=(
            "On-site in Dallas, TX. Provide tier 1 desktop support and deskside end-user support. Triage "
            "tickets in the ticket queue, resolve hardware and software issues, and escalate as needed. "
            "Requirements: customer service, basic troubleshooting. Report to the IT manager."),
        expected="poor_fit",
        rule="§5 Hard-exclude: generic helpdesk / high ticket volume; also on-site gate"),
    LabeledJob(
        key="senior_swe",
        title="Senior Software Engineer",
        description=(
            f"{_REMOTE} Build and scale our core product. You will write production-grade code, design "
            "distributed systems, and pass a system design interview. Requirements: 5+ years of professional "
            "software development, strong algorithm and data-structures skills, object-oriented design, and "
            "deep experience with microservices architecture."),
        expected="poor_fit",
        rule="§5 Hard-exclude: traditional senior SWE requiring deep independent coding as the core bar"),
    LabeledJob(
        key="crm_admin_ai",
        title="Salesforce Administrator",
        description=(
            f"{_REMOTE} Own and administer our Salesforce CRM. You will manage users, permissions, and "
            "security settings, build reports and dashboards, configure workflows, and maintain data quality "
            "across the CRM. We are rolling out new AI-powered CRM features, so familiarity with AI assistants "
            "is a plus. Requirements: Salesforce administration experience, CRM administration, and strong "
            "stakeholder communication."),
        expected="poor_fit",
        rule="§5 Hard-exclude: generic SaaS/CRM administration with AI as a minor add-on"),
    LabeledJob(
        key="customer_success_ai",
        title="Customer Success Manager, AI Products",
        description=(
            "Remote with travel up to 50%. Own a book of enterprise accounts for our AI product. Drive "
            "adoption, manage renewals and upsell, hit a retention quota, and run customer programs and "
            "business reviews. You will partner with pre-sales on strategic customer expansion. Requirements: "
            "account management, customer success, and a track record against a quota."),
        expected="poor_fit",
        rule="§5 Hard-exclude: customer success / sales intensity (quota, renewals, travel)"),

    # ---- ADVERSARIAL NEAR-MISSES — the reported failure mode ----
    LabeledJob(
        key="security_engineer",
        title="Senior Security Engineer",
        description=(
            f"{_REMOTE} Own our cloud security posture. You will harden infrastructure, lead incident "
            "response, manage identity and access management (IAM), enforce access control and least-privilege "
            "permissions, tune security settings, and run monitoring, logging, and observability across the "
            "fleet. You will manage secrets management and OAuth/SAML/SSO for the workforce, and configure "
            "security tooling with detection automation. Requirements: deep experience with cloud security "
            "(Azure, GCP), REST API security, system administration of enterprise platforms, and strong "
            "troubleshooting. AI security governance: as one part of the role, you will help define guardrails "
            "and AI governance policy for internal LLM usage. You partner with engineers on secure rollouts."),
        expected="poor_fit",
        rule="§5/§8 Security is supporting experience only; do not route into a primary security track",
        adversarial=True),
    LabeledJob(
        key="mlops_ml_engineer",
        title="Machine Learning Engineer (MLOps)",
        description=(
            f"{_REMOTE} Build and operate our production ML and LLM platform. You will own model deployment "
            "and model evaluation pipelines, generative AI infrastructure, and serving for large models. "
            "Requirements: deep statistics and machine-learning fundamentals, production ML pipelines, "
            "distributed systems, Kubernetes at scale, strong programming, and several years of professional "
            "software development. Experience with model catalogs and AI platform internals required."),
        expected="poor_fit",
        rule="§5 Hard-exclude: ML research / MLOps requiring deep stats, production ML pipelines, Kubernetes",
        adversarial=True),
    LabeledJob(
        key="ai_trainer",
        title="AI Enablement Trainer",
        description=(
            f"{_REMOTE} Help our workforce adopt AI through training and change management. You will run "
            "prompt-writing workshops and office hours, create training materials and a knowledge base, drive "
            "AI adoption across departments, and coordinate change-management programs. This is a "
            "training-and-enablement role; there is no platform administration or tool-building component. "
            "Requirements: excellent communication, facilitation, and curriculum development."),
        expected="poor_fit",
        rule="§5 Hard-exclude: pure AI training / prompt workshops with no platform ownership or building",
        adversarial=True),

    # ---- CODING-REQUIREMENT GROUP — from-scratch / independent-authorship framing ----
    # Two AI-platform roles that differ ONLY in how they frame coding. Both are
    # genuinely AI-centered (high core_share), so the composition rule does not touch
    # them — this gap needs its own penalty. "familiarity / a plus" framing is a bar
    # the candidate clears and must stay clean; "proficiency / writes code
    # independently / from scratch" is the disqualifier and must be docked. (Framework
    # §5: appropriate technical bar = "experience preferred" not strict dev years;
    # hard-exclude = independent senior-level coding as the core bar.)
    LabeledJob(
        key="coding_a_plus",
        title="AI Platform Operations Specialist",
        description=(
            f"{_REMOTE} Administer our enterprise AI platform: create model deployments, configure RBAC and "
            "API access, tune content filters and guardrails, manage quotas and cost controls, and run model "
            "evaluations. You build internal automation and integrations and support developer enablement with "
            "documentation and runbooks. Familiarity with Python a plus; comfortable reading scripts is "
            "helpful. Requirements: administering an AI platform, identity and access management, monitoring, "
            "and troubleshooting."),
        expected="strong_match",
        rule="§5 Appropriate technical bar: 'familiarity / a plus' coding is fine — must NOT be penalized"),
    LabeledJob(
        key="coding_required",
        title="AI Platform Engineer",
        description=(
            f"{_REMOTE} Administer our AI platform and build internal tools, automation, and integrations on "
            "top of model deployments and APIs. This is a hands-on engineering role. Requirements: proficiency "
            "in Python; you will write production code independently, design and build services from scratch, "
            "and own delivery end to end. Strong coding skills and fluency in JavaScript are required."),
        expected="poor_fit",
        rule="§5 Hard-exclude: core bar is independent from-scratch production coding (even when AI-centered)"),
]
