from __future__ import annotations
from datetime import date
from app.models import NormalizedJob, compute_dedupe_hash

# Sample descriptions are inlined here (not imported from tests/) so production
# code carries no dependency on the test package.
_STRONG = ("AI Platform Operations Specialist. Fully remote, United States. You will administer "
           "Microsoft Foundry: model deployment, RBAC, content filter, model evaluation, and AI governance. "
           "You will build internal tools and automation, and own applied AI implementation. You work "
           "alongside engineers on developer enablement, partnering with AI engineers on the platform team. "
           "Requirements: REST API, BigQuery, monitoring, and troubleshooting. You will help with "
           "documentation and onboarding. You report to the platform team.")
_BRIDGE = ("AI Implementation Analyst. Remote. Responsibilities: build automation and integration for "
           "internal tools, support adoption with documentation and onboarding. Requirements: scripting, APIs. "
           "You will work with the platform team.")
_HELPDESK = ("Help Desk Technician. On-site. Responsibilities: triage tickets in the ticket queue, deskside "
             "end-user support, tier 1 desktop support. Requirements: customer service. Report to IT manager.")
_SENIOR_SWE = ("Senior Software Engineer. Remote. You will write production-grade code, design distributed "
               "systems, and pass a system design interview. Requirements: 5+ years of professional software, "
               "strong algorithm and data structures skills.")
_HIGH_BUT_ONSITE = ("AI Platform Engineer. On-site in Austin. Administer Azure AI, model deployment, RBAC, "
                    "build internal tools, automation, integration, developer enablement, documentation.")

_DEFS = [
    ("AI Platform Operations Specialist", "Northstar AI", _STRONG, "https://example.com/apply/1"),
    ("AI Implementation Analyst", "BridgeWorks", _BRIDGE, "https://example.com/apply/2"),
    ("Help Desk Technician", "OldCorp IT", _HELPDESK, "https://example.com/apply/3"),
    ("Senior Software Engineer", "DeepStack", _SENIOR_SWE, "https://example.com/apply/4"),
    ("AI Platform Engineer", "Onsite Labs", _HIGH_BUT_ONSITE, "https://example.com/apply/5"),
]


class MockProvider:
    def fetch(self) -> list[NormalizedJob]:
        out = []
        for title, company, desc, url in _DEFS:
            out.append(NormalizedJob(
                title=title, company_name=company, description=desc, application_url=url,
                source="mock", date_found=date.today().isoformat(),
                dedupe_hash=compute_dedupe_hash(title, company, desc)))
        return out
