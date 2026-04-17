"""
P0 Proof System - Registry and Configuration (v14)

Implements the P0 proof registry for top ATS platforms with:
- Required_any semantics (Fix #1) - OR instead of AND
- Multiple alternative proofs per provider (Fix #6)
- Identification and submission tiers

P0 Proofs = Network request patterns that definitively prove ATS identity.
"""

import logging
from typing import Dict, Optional
from .types import P0ProofTierConfig, P0ProofRequest, DomainMatchMode

logger = logging.getLogger(__name__)


# =============================================================================
# P0 PROOF REGISTRY
# =============================================================================

# Global registry: {provider_id: {tier: P0ProofTierConfig}}
P0_PROOF_CONFIGS: Dict[str, Dict[str, P0ProofTierConfig]] = {}


def register_proof_config(config: P0ProofTierConfig) -> None:
    """
    Register a proof tier configuration.

    Args:
        config: Proof tier configuration to register

    Example:
        register_proof_config(P0ProofTierConfig(
            provider_id="greenhouse",
            tier="identification",
            proofs=[...],
            required_any=1
        ))
    """
    if config.provider_id not in P0_PROOF_CONFIGS:
        P0_PROOF_CONFIGS[config.provider_id] = {}

    P0_PROOF_CONFIGS[config.provider_id][config.tier] = config

    logger.debug(
        f"[P0Registry] Registered {config.tier} for {config.provider_id}: "
        f"{len(config.proofs)} proofs, required_any={config.required_any}"
    )


def get_proof_config(
    provider_id: str,
    tier: str = "identification"
) -> Optional[P0ProofTierConfig]:
    """
    Get proof configuration for a provider and tier.

    Args:
        provider_id: ATS provider ID
        tier: "identification" or "submission"

    Returns:
        P0ProofTierConfig if registered, None otherwise
    """
    provider_configs = P0_PROOF_CONFIGS.get(provider_id)
    if not provider_configs:
        return None

    return provider_configs.get(tier)


# =============================================================================
# P0 PROOF CONFIGURATIONS (Top 10 ATS - Fix #6)
# =============================================================================

# ---------------------------------------------------------------------------
# GREENHOUSE (Stable, reliable API patterns)
# ---------------------------------------------------------------------------

register_proof_config(P0ProofTierConfig(
    provider_id="greenhouse",
    tier="identification",
    proofs=[
        P0ProofRequest(
            method="GET",
            domain="boards-api.greenhouse.io",
            path="/v1/boards/",
            match_mode=DomainMatchMode.EXACT
        ),
        P0ProofRequest(
            method="GET",
            domain="boards.greenhouse.io",
            path="/embed/job_board",
            match_mode=DomainMatchMode.EXACT
        ),
    ],
    required_any=1  # v14: Only need ONE to match
))

register_proof_config(P0ProofTierConfig(
    provider_id="greenhouse",
    tier="submission",
    proofs=[
        P0ProofRequest(
            method="POST",
            domain="boards-api.greenhouse.io",
            path="/v1/boards/",
            match_mode=DomainMatchMode.EXACT
        ),
    ],
    required_any=1
))


# ---------------------------------------------------------------------------
# LEVER (v14 FIX: Multiple alternatives, not single brittle path)
# ---------------------------------------------------------------------------

register_proof_config(P0ProofTierConfig(
    provider_id="lever",
    tier="identification",
    proofs=[
        # Alternative 1: API endpoint
        P0ProofRequest(
            method="GET",
            domain="api.lever.co",
            path="/v0/postings/",
            match_mode=DomainMatchMode.EXACT
        ),
        # Alternative 2: Jobs domain
        P0ProofRequest(
            method="GET",
            domain="jobs.lever.co",
            path="/",
            match_mode=DomainMatchMode.EXACT
        ),
    ],
    required_any=1  # v14: Only need ONE
))

register_proof_config(P0ProofTierConfig(
    provider_id="lever",
    tier="submission",
    proofs=[
        # v14 FIX: Multiple alternatives (not single brittle path!)
        # Alternative 1: Frame workaround (some Lever flows)
        P0ProofRequest(
            method="POST",
            domain="jobs.lever.co",
            path="/lever-frame-workaround/",
            match_mode=DomainMatchMode.EXACT
        ),
        # Alternative 2: Direct POST to jobs domain
        P0ProofRequest(
            method="POST",
            domain="jobs.lever.co",
            path="/",
            match_mode=DomainMatchMode.EXACT
        ),
        # Alternative 3: API apply endpoint
        P0ProofRequest(
            method="POST",
            domain="api.lever.co",
            path="/v0/postings/",
            match_mode=DomainMatchMode.EXACT
        ),
    ],
    required_any=1  # v14: Only need ONE to match
))


# ---------------------------------------------------------------------------
# WORKDAY (Tenant variability with suffix matching)
# ---------------------------------------------------------------------------

register_proof_config(P0ProofTierConfig(
    provider_id="workday",
    tier="identification",
    proofs=[
        P0ProofRequest(
            method="GET",
            domain=".myworkday.com",
            path="/wday/cxs/",
            match_mode=DomainMatchMode.SUFFIX
        ),
        P0ProofRequest(
            method="GET",
            domain=".myworkday.com",
            path="/recruiter/",
            match_mode=DomainMatchMode.SUFFIX
        ),
    ],
    required_any=1
))


# ---------------------------------------------------------------------------
# ASHBY (GraphQL POST patterns)
# ---------------------------------------------------------------------------

register_proof_config(P0ProofTierConfig(
    provider_id="ashby",
    tier="identification",
    proofs=[
        P0ProofRequest(
            method="POST",  # GraphQL uses POST
            domain="jobs.ashbyhq.com",
            path="/api/non-user-graphql",
            match_mode=DomainMatchMode.EXACT
        ),
    ],
    required_any=1
))


# ---------------------------------------------------------------------------
# JOBVITE (Tenant variability)
# ---------------------------------------------------------------------------

register_proof_config(P0ProofTierConfig(
    provider_id="jobvite",
    tier="identification",
    proofs=[
        P0ProofRequest(
            method="GET",
            domain=".jobvite.com",
            path="/companyinfo/",
            match_mode=DomainMatchMode.SUFFIX
        ),
        P0ProofRequest(
            method="GET",
            domain=".jobvite.com",
            path="/j/",  # Alternative path
            match_mode=DomainMatchMode.SUFFIX
        ),
    ],
    required_any=1
))


# ---------------------------------------------------------------------------
# iCIMS (v14 FIX: Multiple alternatives, not single brittle /jobs/search)
# ---------------------------------------------------------------------------

register_proof_config(P0ProofTierConfig(
    provider_id="icims",
    tier="identification",
    proofs=[
        # Alternative 1: Search endpoint
        P0ProofRequest(
            method="GET",
            domain=".icims.com",
            path="/jobs/search",
            match_mode=DomainMatchMode.SUFFIX
        ),
        # Alternative 2: Individual job view
        P0ProofRequest(
            method="GET",
            domain=".icims.com",
            path="/jobs/intro",
            match_mode=DomainMatchMode.SUFFIX
        ),
        # Alternative 3: API endpoint
        P0ProofRequest(
            method="GET",
            domain=".icims.com",
            path="/api/",
            match_mode=DomainMatchMode.SUFFIX
        ),
    ],
    required_any=1  # v14: Only need ONE
))

register_proof_config(P0ProofTierConfig(
    provider_id="icims",
    tier="submission",
    proofs=[
        # Multiple alternatives
        P0ProofRequest(
            method="POST",
            domain=".icims.com",
            path="/jobs/intro/submit",
            match_mode=DomainMatchMode.SUFFIX
        ),
        P0ProofRequest(
            method="POST",
            domain=".icims.com",
            path="/api/apply",
            match_mode=DomainMatchMode.SUFFIX
        ),
    ],
    required_any=1
))


# ---------------------------------------------------------------------------
# SMARTRECRUITERS (Stable API patterns)
# ---------------------------------------------------------------------------

register_proof_config(P0ProofTierConfig(
    provider_id="smartrecruiters",
    tier="identification",
    proofs=[
        P0ProofRequest(
            method="GET",
            domain="jobs.smartrecruiters.com",
            path="/api/",
            match_mode=DomainMatchMode.EXACT
        ),
    ],
    required_any=1
))


# ---------------------------------------------------------------------------
# BAMBOOHR (Tenant variability)
# ---------------------------------------------------------------------------

register_proof_config(P0ProofTierConfig(
    provider_id="bamboohr",
    tier="identification",
    proofs=[
        P0ProofRequest(
            method="GET",
            domain=".bamboohr.com",
            path="/jobs/view.php",
            match_mode=DomainMatchMode.SUFFIX
        ),
        P0ProofRequest(
            method="GET",
            domain=".bamboohr.com",
            path="/careers/",
            match_mode=DomainMatchMode.SUFFIX
        ),
    ],
    required_any=1
))


# ---------------------------------------------------------------------------
# TALEO (Oracle - Regex for complex domain patterns)
# ---------------------------------------------------------------------------

register_proof_config(P0ProofTierConfig(
    provider_id="taleo",
    tier="identification",
    proofs=[
        P0ProofRequest(
            method="GET",
            domain=r".*\.taleo\.net",
            path="/careersection/",
            match_mode=DomainMatchMode.REGEX
        ),
    ],
    required_any=1
))


# ---------------------------------------------------------------------------
# ADP (Stable patterns)
# ---------------------------------------------------------------------------

register_proof_config(P0ProofTierConfig(
    provider_id="adp",
    tier="identification",
    proofs=[
        P0ProofRequest(
            method="GET",
            domain="workforcenow.adp.com",
            path="/mascsr/default/careercenter",
            match_mode=DomainMatchMode.EXACT
        ),
    ],
    required_any=1
))


# =============================================================================
# REGISTRY STATS
# =============================================================================

def get_registry_stats() -> Dict[str, any]:
    """
    Get statistics about the P0 proof registry.

    Returns:
        Dict with provider count, tier count, proof count
    """
    provider_count = len(P0_PROOF_CONFIGS)
    tier_count = sum(len(tiers) for tiers in P0_PROOF_CONFIGS.values())
    proof_count = sum(
        len(config.proofs)
        for tiers in P0_PROOF_CONFIGS.values()
        for config in tiers.values()
    )

    return {
        'provider_count': provider_count,
        'tier_count': tier_count,
        'proof_count': proof_count,
        'providers': list(P0_PROOF_CONFIGS.keys())
    }


# Log registry stats on import
if __name__ != "__main__":
    stats = get_registry_stats()
    logger.info(
        f"[P0Registry] Loaded: {stats['provider_count']} providers, "
        f"{stats['tier_count']} tiers, {stats['proof_count']} proofs"
    )
