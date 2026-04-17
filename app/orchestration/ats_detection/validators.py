"""
P0 Proof Validation - Required_Any Semantics with Match Quality (v14)

Implements proof validation with:
- Required_any semantics (Fix #1) - OR instead of AND
- Match quality tracking (Fix #2) - weak vs strong matches
- Confidence penalties for unknown status matches

Key Innovation:
- proof_valid = (matched_count >= required_any) instead of ALL must match
- match_quality = "weak" if any unknown_status, "strong" if all usable
- Confidence penalty applied for weak matches
"""

import logging
import re
from typing import List, Optional
from urllib.parse import urlparse

from .types import (
    NetworkRequest,
    P0ProofRequest,
    P0ProofValidationResult,
    DomainMatchMode,
)
from .proofs import get_proof_config

logger = logging.getLogger(__name__)


# =============================================================================
# DOMAIN MATCHING UTILITIES
# =============================================================================

def normalize_domain(url: str) -> str:
    """
    Extract and normalize domain from URL.

    Args:
        url: Full URL

    Returns:
        Normalized domain (lowercase)

    Example:
        "https://Boards-API.Greenhouse.io/v1/boards" → "boards-api.greenhouse.io"
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception as e:
        logger.warning(f"[DomainNorm] Failed to parse URL: {e}")
        return ""


def match_domain(
    request_domain: str,
    proof_domain: str,
    match_mode: DomainMatchMode
) -> bool:
    """
    Match request domain against proof domain pattern.

    Args:
        request_domain: Domain from request (e.g., "api.greenhouse.io")
        proof_domain: Domain pattern from proof (e.g., ".icims.com")
        match_mode: How to match (EXACT, SUFFIX, REGEX)

    Returns:
        True if match, False otherwise
    """
    request_domain = request_domain.lower()
    proof_domain = proof_domain.lower()

    if match_mode == DomainMatchMode.EXACT:
        return request_domain == proof_domain

    elif match_mode == DomainMatchMode.SUFFIX:
        # e.g., ".icims.com" matches "acme.icims.com"
        if proof_domain.startswith('.'):
            return request_domain.endswith(proof_domain) or request_domain == proof_domain[1:]
        else:
            return request_domain == proof_domain

    elif match_mode == DomainMatchMode.REGEX:
        # e.g., r".*\.taleo\.net" matches "acme.taleo.net"
        try:
            pattern = re.compile(proof_domain)
            return bool(pattern.match(request_domain))
        except re.error as e:
            logger.error(f"[DomainMatch] Invalid regex pattern '{proof_domain}': {e}")
            return False

    else:
        logger.warning(f"[DomainMatch] Unknown match mode: {match_mode}")
        return False


# =============================================================================
# P0 PROOF SET VALIDATOR (v14 FIX #1 & #2)
# =============================================================================

class P0ProofSetValidator:
    """
    v14 REFINED: P0 proof validator with required_any semantics and match quality.

    Key Features:
    - OR semantics: proof_valid if matched_count >= required_any (not ALL)
    - Match quality: "strong" if all usable status, "weak" if any unknown status
    - Separate usable (status 200-499) from unknown (status None) for quality tracking
    """

    @staticmethod
    def validate_proof_set_with_details(
        network_requests: List[NetworkRequest],
        provider_id: str,
        tier: str = "identification",
        allow_unknown_status: bool = True
    ) -> P0ProofValidationResult:
        """
        v14 REFINED: Validate proof set with required_any semantics and match quality.

        Args:
            network_requests: Captured network requests
            provider_id: ATS provider ID (e.g., "greenhouse")
            tier: "identification" or "submission"
            allow_unknown_status: Whether to accept status=None matches (default: True)

        Returns:
            P0ProofValidationResult with:
            - proof_valid: True if matched_count >= required_any
            - match_quality: "strong" if all usable, "weak" if any unknown_status
            - matched_count, required_any for debugging

        Example:
            # Config: 3 proofs, required_any=1
            # Observed: only proof_a matched (with status=200)
            # Result: proof_valid=True, match_quality="strong"
        """
        # v14: Get proof tier config (not just list)
        config = get_proof_config(provider_id, tier)

        if not config:
            # No proofs configured → proof not applicable
            logger.debug(
                f"[P0ProofSet] No {tier} proofs configured for {provider_id} "
                f"→ proof_applicable=False"
            )
            return P0ProofValidationResult(
                proof_applicable=False,
                proof_valid=True  # No proofs = pass by default
            )

        logger.info(
            f"[P0ProofSet] Validating {tier} for {provider_id}: "
            f"{len(config.proofs)} alternatives, required_any={config.required_any}"
        )

        # Separate usable and unknown status requests
        usable_requests = [
            req for req in network_requests
            if req.status is not None and 200 <= req.status < 500
        ]
        unknown_requests = [
            req for req in network_requests
            if req.status is None
        ]

        logger.debug(
            f"[P0ProofSet] Network requests: {len(usable_requests)} usable, "
            f"{len(unknown_requests)} unknown status"
        )

        matched_proofs = []
        matched_with_unknown_status = []

        # v14: Try to match each proof (OR semantics)
        for proof_req in config.proofs:
            # Try usable first
            matched = P0ProofSetValidator._find_matching_request(
                usable_requests,
                proof_req
            )

            if matched:
                matched_proofs.append(proof_req)
                logger.info(
                    f"[P0ProofSet] ✓ Matched (usable): {proof_req.method} "
                    f"{proof_req.domain}{proof_req.path}"
                )
            elif allow_unknown_status:
                # v14: Fallback to unknown status
                matched_unknown = P0ProofSetValidator._find_matching_request(
                    unknown_requests,
                    proof_req
                )
                if matched_unknown:
                    matched_proofs.append(proof_req)
                    matched_with_unknown_status.append(proof_req)
                    logger.info(
                        f"[P0ProofSet] ⚠️  Matched (unknown status): {proof_req.method} "
                        f"{proof_req.domain}{proof_req.path}"
                    )

        # v14 FIX: Proof valid if matched >= required_any (OR semantics)
        matched_count = len(matched_proofs)
        proof_valid = matched_count >= config.required_any

        # v14 NEW: Determine match quality
        if matched_with_unknown_status:
            match_quality = "weak"  # At least one unknown status
        else:
            match_quality = "strong"  # All usable

        # Compute missing
        missing_proofs = [p for p in config.proofs if p not in matched_proofs]

        if proof_valid:
            logger.info(
                f"[P0ProofSet] ✓ Proof valid: {matched_count}/{len(config.proofs)} matched "
                f"(required_any={config.required_any}, quality={match_quality})"
            )
        else:
            logger.warning(
                f"[P0ProofSet] ✗ Proof invalid: {matched_count}/{len(config.proofs)} matched "
                f"(required_any={config.required_any})"
            )

        return P0ProofValidationResult(
            proof_applicable=True,
            proof_valid=proof_valid,
            required_any=config.required_any,
            matched_count=matched_count,
            missing_proofs=missing_proofs,
            matched_proofs=matched_proofs,
            match_quality=match_quality
        )

    @staticmethod
    def _find_matching_request(
        requests: List[NetworkRequest],
        proof_req: P0ProofRequest
    ) -> Optional[NetworkRequest]:
        """
        v14: Find network request matching P0 proof.

        Uses url_full from debug trace (ephemeral) for matching,
        but logs only url_sanitized for security.

        Args:
            requests: List of network requests to search
            proof_req: P0 proof requirement to match

        Returns:
            Matching NetworkRequest if found, None otherwise
        """
        for req in requests:
            # v14: Parse url_full from debug trace (ephemeral)
            req_domain = normalize_domain(req.url_full)  # Uses property

            try:
                parsed = urlparse(req.url_full)
                req_path = parsed.path
            except Exception as e:
                logger.warning(f"[P0ProofSet] Failed to parse URL: {e}")
                continue

            # Match method, domain, and path
            method_match = req.method.upper() == proof_req.method.upper()
            domain_match = match_domain(req_domain, proof_req.domain, proof_req.match_mode)
            path_match = req_path.startswith(proof_req.path)

            if method_match and domain_match and path_match:
                # v14 CRITICAL: Log only sanitized URL (not url_full!)
                logger.debug(
                    f"[P0ProofSet] ✓ Matched: {req.method} {req.url_sanitized} "
                    f"(status={req.status})"
                )
                return req

        return None

    @staticmethod
    def apply_proof_quality_penalty(
        base_confidence: float,
        proof_result: P0ProofValidationResult
    ) -> float:
        """
        v14 NEW (Fix #2): Apply confidence penalty for weak proof matches.

        Args:
            base_confidence: Base confidence before penalty
            proof_result: Proof validation result with match quality

        Returns:
            Adjusted confidence with penalty applied if weak

        Penalties:
            - Strong match: No penalty (1.0x)
            - Weak match (unknown status): 10% penalty (0.9x)
        """
        if not proof_result.proof_applicable or not proof_result.proof_valid:
            # Proofs not applicable or invalid → no penalty
            return base_confidence

        if proof_result.match_quality == "weak":
            # v14: 10% penalty for weak (unknown status) matches
            penalty = 0.9
            adjusted = base_confidence * penalty

            logger.info(
                f"[P0ProofSet] Weak match quality (unknown status) "
                f"→ confidence penalty {penalty:.2f}x: {base_confidence:.2f} → {adjusted:.2f}"
            )

            return adjusted
        else:
            # Strong match → no penalty
            return base_confidence
