"""
ATS Detection Orchestrator - Progressive Evidence Extraction (v14)

Implements the main detection workflow with:
- Progressive L1→L4 evidence extraction
- Early exit on high confidence
- Evidence accumulation across levels
- Cost optimization (avoid expensive L4 if L1/L2 sufficient)

Key Innovation:
- Orchestrates all extractors into cohesive workflow
- Balances cost vs precision
- ZERO wrong submissions guarantee via route eligibility
"""

import logging
from typing import Tuple, Optional
from playwright.async_api import Page

from .types import (
    ATSDetectionResult,
    ATSDetectionEvidence,
    EvidenceLevel,
)
from .extractors import (
    extract_l1_evidence,
    extract_l2_evidence,
    extract_l3_evidence,
    extract_l4_evidence,
)
from .policies import EvidenceLevelPolicy

logger = logging.getLogger(__name__)


# =============================================================================
# MAIN ATS DETECTION ORCHESTRATOR
# =============================================================================

class ATSDetectionOrchestrator:
    """
    v14: Progressive ATS detection orchestrator.

    Orchestrates L1→L4 evidence extraction with:
    - Early exit on high confidence
    - Evidence accumulation
    - Cost optimization
    - ZERO wrong submissions guarantee
    """

    # Detection strategy
    EARLY_EXIT_ENABLED = True  # Exit early if confidence sufficient
    ALWAYS_RUN_L4 = False  # Force L4 even if L1/L2/L3 sufficient (debugging)

    @staticmethod
    async def detect_ats_with_evidence(
        page: Page,
        job_url: str,
        max_level: EvidenceLevel = EvidenceLevel.L4_NETWORK,
        require_route_eligible: bool = False
    ) -> Tuple[ATSDetectionResult, ATSDetectionEvidence]:
        """
        v14: Progressive ATS detection with evidence accumulation.

        Args:
            page: Playwright page (for L2/L3/L4 extraction)
            job_url: Job posting URL
            max_level: Maximum evidence level to extract (default: L4)
            require_route_eligible: If True, continue until route_eligible or max_level

        Returns:
            (ATSDetectionResult, ATSDetectionEvidence) tuple

        Strategy:
            1. L1 (URL): Fast, cheap, low precision
            2. L2 (DOM): Medium cost, medium precision
            3. L3 (Apply): Higher cost, high precision
            4. L4 (Network): Highest cost, highest precision

            Early exit if:
            - confidence >= route eligibility threshold (unless require_route_eligible=True)
            - max_level reached

        Example:
            result, evidence = await ATSDetectionOrchestrator.detect_ats_with_evidence(
                page, "https://jobs.lever.co/company/role"
            )
        """
        logger.info(f"[Orchestrator] Starting ATS detection for: {job_url}")
        logger.info(f"[Orchestrator] Config: max_level={max_level.value}, require_route_eligible={require_route_eligible}")

        result = None
        evidence = None

        # -------------------------------------------------------------------------
        # L1: URL Pattern Matching
        # -------------------------------------------------------------------------

        if max_level.value >= EvidenceLevel.L1_URL.value:
            logger.info("[Orchestrator] Running L1: URL pattern matching")
            result, evidence = extract_l1_evidence(job_url)

            logger.info(
                f"[Orchestrator] L1 complete: provider={result.provider_id}, "
                f"confidence={result.confidence:.2f}, route_eligible={result.route_eligible}"
            )

            # Early exit check
            if ATSDetectionOrchestrator._should_exit(
                result, evidence, max_level, require_route_eligible
            ):
                logger.info("[Orchestrator] Early exit after L1 (sufficient confidence)")
                return result, evidence

        # -------------------------------------------------------------------------
        # L2: DOM Inspection
        # -------------------------------------------------------------------------

        if max_level.value >= EvidenceLevel.L2_DOM.value:
            logger.info("[Orchestrator] Running L2: DOM inspection")
            result, evidence = await extract_l2_evidence(page, job_url, prior_evidence=evidence)

            logger.info(
                f"[Orchestrator] L2 complete: provider={result.provider_id}, "
                f"confidence={result.confidence:.2f}, route_eligible={result.route_eligible}"
            )

            # Early exit check
            if ATSDetectionOrchestrator._should_exit(
                result, evidence, max_level, require_route_eligible
            ):
                logger.info("[Orchestrator] Early exit after L2 (sufficient confidence)")
                return result, evidence

        # -------------------------------------------------------------------------
        # L3: Apply Button Detection
        # -------------------------------------------------------------------------

        if max_level.value >= EvidenceLevel.L3_APPLY.value:
            logger.info("[Orchestrator] Running L3: Apply button detection")
            result, evidence = await extract_l3_evidence(page, job_url, prior_evidence=evidence)

            logger.info(
                f"[Orchestrator] L3 complete: provider={result.provider_id}, "
                f"confidence={result.confidence:.2f}, route_eligible={result.route_eligible}"
            )

            # Early exit check
            if ATSDetectionOrchestrator._should_exit(
                result, evidence, max_level, require_route_eligible
            ):
                logger.info("[Orchestrator] Early exit after L3 (sufficient confidence)")
                return result, evidence

        # -------------------------------------------------------------------------
        # L4: Network Capture + P0 Proofs
        # -------------------------------------------------------------------------

        if max_level.value >= EvidenceLevel.L4_NETWORK.value:
            logger.info("[Orchestrator] Running L4: Network capture + P0 proofs")
            result, evidence = await extract_l4_evidence(page, job_url, prior_evidence=evidence)

            logger.info(
                f"[Orchestrator] L4 complete: provider={result.provider_id}, "
                f"confidence={result.confidence:.2f}, route_eligible={result.route_eligible}, "
                f"network_requests={len(evidence.network_requests)}"
            )

        # -------------------------------------------------------------------------
        # Final Result
        # -------------------------------------------------------------------------

        logger.info(
            f"[Orchestrator] Detection complete: provider={result.provider_id}, "
            f"level={result.level_extracted.value}, confidence={result.confidence:.2f}, "
            f"route_eligible={result.route_eligible}"
        )

        return result, evidence

    @staticmethod
    def _should_exit(
        result: ATSDetectionResult,
        evidence: ATSDetectionEvidence,
        max_level: EvidenceLevel,
        require_route_eligible: bool
    ) -> bool:
        """
        Determine if we should exit early (before max_level).

        Args:
            result: Current detection result
            evidence: Current evidence
            max_level: Maximum level to extract
            require_route_eligible: Whether to require route eligibility

        Returns:
            True if should exit early, False if should continue

        Exit Logic:
            - If ALWAYS_RUN_L4: Never exit early (always run full L4)
            - If !EARLY_EXIT_ENABLED: Never exit early
            - If require_route_eligible=True: Only exit if route_eligible
            - If already at max_level: Exit (no more levels to run)
            - If route_eligible: Exit (sufficient confidence)
        """
        # Force L4 mode (debugging)
        if ATSDetectionOrchestrator.ALWAYS_RUN_L4:
            if result.level_extracted == EvidenceLevel.L4_NETWORK:
                return True  # L4 done, exit
            else:
                return False  # Not L4 yet, continue

        # Early exit disabled
        if not ATSDetectionOrchestrator.EARLY_EXIT_ENABLED:
            return result.level_extracted == max_level

        # Already at max level
        if result.level_extracted == max_level:
            return True

        # Require route eligibility mode
        if require_route_eligible:
            return result.route_eligible

        # Default: exit if route eligible (sufficient confidence)
        return result.route_eligible

    @staticmethod
    async def detect_ats_simple(
        page: Page,
        job_url: str
    ) -> ATSDetectionResult:
        """
        Simplified detection API (returns only result, no evidence).

        Args:
            page: Playwright page
            job_url: Job posting URL

        Returns:
            ATSDetectionResult only (evidence discarded)

        Use this for simple detection without evidence tracking.
        """
        result, _ = await ATSDetectionOrchestrator.detect_ats_with_evidence(
            page, job_url
        )
        return result

    @staticmethod
    async def detect_ats_until_route_eligible(
        page: Page,
        job_url: str,
        max_level: EvidenceLevel = EvidenceLevel.L4_NETWORK
    ) -> Tuple[ATSDetectionResult, ATSDetectionEvidence]:
        """
        Detection strategy: Continue until route eligible OR max_level.

        Args:
            page: Playwright page
            job_url: Job posting URL
            max_level: Maximum evidence level to extract

        Returns:
            (ATSDetectionResult, ATSDetectionEvidence) tuple

        This is the recommended strategy for production:
        - Ensures route_eligible determination
        - Stops early if possible (cost optimization)
        - Falls back to max_level if needed
        """
        return await ATSDetectionOrchestrator.detect_ats_with_evidence(
            page,
            job_url,
            max_level=max_level,
            require_route_eligible=True
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def detect_ats_with_evidence(
    page: Page,
    job_url: str,
    max_level: EvidenceLevel = EvidenceLevel.L4_NETWORK,
    require_route_eligible: bool = False
) -> Tuple[ATSDetectionResult, ATSDetectionEvidence]:
    """
    Convenience wrapper for ATSDetectionOrchestrator.detect_ats_with_evidence().

    See ATSDetectionOrchestrator.detect_ats_with_evidence() for full documentation.
    """
    return await ATSDetectionOrchestrator.detect_ats_with_evidence(
        page, job_url, max_level, require_route_eligible
    )


async def detect_ats(page: Page, job_url: str) -> ATSDetectionResult:
    """
    Convenience wrapper for simple detection (result only, no evidence).

    See ATSDetectionOrchestrator.detect_ats_simple() for full documentation.
    """
    return await ATSDetectionOrchestrator.detect_ats_simple(page, job_url)
