"""
Evidence Level Policies - Conditional Proof Gating (v14)

Implements intelligent evidence-level-aware policies for P0 proof enforcement.

Key Innovation (v14):
- Don't enforce P0 proofs for low-evidence detections (L1/L2)
- Only enforce for high-evidence detections (L4 with sufficient network density)
- Prevents blocking legitimate detections due to network capture artifacts
"""

import logging
from .types import EvidenceLevel

logger = logging.getLogger(__name__)


class EvidenceLevelPolicy:
    """
    v14: Evidence-level-aware policy for P0 proof enforcement.

    Conditional Gating Logic:
    - L1/L2: Never enforce P0 proofs (low evidence, accept LLM verdict)
    - L3: Never enforce (apply button doesn't guarantee network capture)
    - L4: Enforce only if sufficient network density (min 3 XHR requests)

    This prevents false negatives from network capture artifacts while
    maintaining ZERO wrong submissions guarantee via route eligibility.
    """

    # Policy constants
    MIN_L4_NETWORK_DENSITY = 3  # Minimum XHR requests to enforce P0 proofs
    L4_PROOF_ENFORCEMENT_ENABLED = True  # Feature flag

    @staticmethod
    def should_enforce_p0_proofs(
        evidence_level: EvidenceLevel,
        network_request_count: int = 0
    ) -> bool:
        """
        Determine whether to enforce P0 proof validation.

        Args:
            evidence_level: Highest evidence level reached
            network_request_count: Number of network requests captured

        Returns:
            True if P0 proofs should be enforced, False otherwise

        Decision Matrix:
            L1 (URL): Never enforce
            L2 (DOM): Never enforce
            L3 (Apply): Never enforce
            L4 (Network): Enforce only if network_request_count >= MIN_L4_NETWORK_DENSITY

        Rationale:
        - Low evidence levels (L1/L2): LLM verdict is best signal, proofs too strict
        - L3: Apply button found but network may not capture submission endpoints
        - L4: Only enforce if we captured sufficient network activity
        """
        if not EvidenceLevelPolicy.L4_PROOF_ENFORCEMENT_ENABLED:
            logger.debug("[Policy] P0 proof enforcement globally disabled")
            return False

        if evidence_level == EvidenceLevel.L4_NETWORK:
            # L4: Conditional enforcement based on network density
            enforce = network_request_count >= EvidenceLevelPolicy.MIN_L4_NETWORK_DENSITY

            if enforce:
                logger.info(
                    f"[Policy] L4 with sufficient network density ({network_request_count} reqs) "
                    f"→ ENFORCE P0 proofs"
                )
            else:
                logger.info(
                    f"[Policy] L4 but low network density ({network_request_count} reqs) "
                    f"→ DO NOT enforce P0 proofs"
                )

            return enforce

        else:
            # L1/L2/L3: Never enforce
            logger.info(
                f"[Policy] {evidence_level.value} (low evidence) "
                f"→ DO NOT enforce P0 proofs (accept LLM verdict)"
            )
            return False

    @staticmethod
    def get_confidence_threshold(evidence_level: EvidenceLevel) -> float:
        """
        Get minimum confidence threshold for route eligibility by evidence level.

        Args:
            evidence_level: Evidence level reached

        Returns:
            Minimum confidence (0.0-1.0) to be route eligible

        Thresholds:
            L1: 0.85 (high threshold due to low evidence)
            L2: 0.80 (medium threshold)
            L3: 0.75 (lower threshold, apply button is strong signal)
            L4: 0.70 (lowest threshold, network proofs are strongest)
        """
        thresholds = {
            EvidenceLevel.L1_URL: 0.85,
            EvidenceLevel.L2_DOM: 0.80,
            EvidenceLevel.L3_APPLY: 0.75,
            EvidenceLevel.L4_NETWORK: 0.70,
        }

        return thresholds.get(evidence_level, 0.85)

    @staticmethod
    def apply_evidence_level_bonus(
        base_confidence: float,
        evidence_level: EvidenceLevel
    ) -> float:
        """
        Apply evidence level bonus to base confidence.

        Higher evidence levels get confidence boost.

        Args:
            base_confidence: Base confidence from LLM
            evidence_level: Evidence level reached

        Returns:
            Adjusted confidence (capped at 1.0)

        Bonuses:
            L1: +0.00 (no bonus)
            L2: +0.05 (small bonus for DOM signals)
            L3: +0.10 (medium bonus for apply button)
            L4: +0.15 (large bonus for network proofs)
        """
        bonuses = {
            EvidenceLevel.L1_URL: 0.00,
            EvidenceLevel.L2_DOM: 0.05,
            EvidenceLevel.L3_APPLY: 0.10,
            EvidenceLevel.L4_NETWORK: 0.15,
        }

        bonus = bonuses.get(evidence_level, 0.00)
        adjusted = min(base_confidence + bonus, 1.0)

        logger.debug(
            f"[Policy] Confidence: {base_confidence:.2f} + "
            f"{bonus:.2f} ({evidence_level.value} bonus) = {adjusted:.2f}"
        )

        return adjusted
