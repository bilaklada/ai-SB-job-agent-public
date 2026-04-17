"""
ATS Detection Types - Core Data Structures (v14)

Implements all core types for the v14 ATS detection system with:
- NetworkRequest with ephemeral debug trace (Fix #3)
- P0 proof structures with required_any semantics (Fix #1)
- Evidence levels and detection results
- Match quality tracking (Fix #2)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from urllib.parse import urlparse, parse_qs


# =============================================================================
# DOMAIN MATCHING MODES
# =============================================================================

class DomainMatchMode(str, Enum):
    """
    Domain matching strategies for P0 proof validation.

    EXACT: Exact domain match (e.g., "api.greenhouse.io")
    SUFFIX: Suffix match for tenant variability (e.g., ".icims.com")
    REGEX: Regex pattern for complex cases (e.g., Oracle Taleo)
    """
    EXACT = "exact"
    SUFFIX = "suffix"
    REGEX = "regex"


# =============================================================================
# EVIDENCE LEVELS (L1 → L4)
# =============================================================================

class EvidenceLevel(str, Enum):
    """
    Evidence extraction levels from weakest to strongest.

    L1 (URL): Cheapest, URL-only analysis, 60-70% precision
    L2 (DOM): DOM inspection without interaction, 75-85% precision
    L3 (Apply): Apply button detection + validation, 85-92% precision
    L4 (Network): Full network capture + P0 proofs, 95-99% precision
    """
    L1_URL = "L1_URL"
    L2_DOM = "L2_DOM"
    L3_APPLY = "L3_APPLY"
    L4_NETWORK = "L4_NETWORK"


# =============================================================================
# NETWORK REQUEST (v14 FIX #3: Structural url_full Non-Persistence)
# =============================================================================

@dataclass
class NetworkRequestDebugTrace:
    """
    v14 NEW: Ephemeral debug trace (NEVER persisted).

    Used only for in-memory matching during detection.
    Must NOT be serialized or stored in database/logs.
    """
    url_full: str  # Full URL with query params (ephemeral only!)
    request_headers: Optional[Dict[str, str]] = None
    response_headers: Optional[Dict[str, str]] = None


@dataclass
class NetworkRequest:
    """
    v14 REFINED: Network request with sanitized URL + ephemeral debug trace.

    CRITICAL SECURITY REQUIREMENT:
    - url_sanitized: Safe for persistence/logging (NO secrets)
    - _debug_trace: Ephemeral only, NEVER serialized
    - url_full: Accessed via property from debug trace

    Fix #3: Ensures url_full with query params never reaches persistent state.
    """
    method: str
    url_sanitized: str  # v14: Sanitized URL (was 'url')
    resource_type: str
    status: Optional[int] = None
    content_type: Optional[str] = None

    # v14 NEW: Ephemeral debug trace (never serialized!)
    _debug_trace: Optional[NetworkRequestDebugTrace] = field(default=None, repr=False)

    @property
    def url_full(self) -> str:
        """
        v14: Access full URL from debug trace (ephemeral only).

        Falls back to url_sanitized if debug trace not available.
        """
        if self._debug_trace:
            return self._debug_trace.url_full
        return self.url_sanitized

    def to_dict(self) -> Dict[str, Any]:
        """
        v14 CRITICAL: Serialization excludes url_full and debug trace!

        Only sanitized URL is included. This ensures secrets in query params
        never reach logs/database/state.
        """
        return {
            'method': self.method,
            'url': self.url_sanitized,  # v14: Only sanitized!
            'resource_type': self.resource_type,
            'status': self.status,
            'content_type': self.content_type,
            # v14: _debug_trace NOT included (ephemeral only!)
        }


def sanitize_network_url(url: str) -> str:
    """
    Sanitize URL by removing query parameters and fragments.

    Prevents secret tokens/keys from appearing in logs/database.

    Args:
        url: Full URL potentially with secrets

    Returns:
        Sanitized URL (scheme + netloc + path only)

    Example:
        Input:  "https://api.greenhouse.io/v1/boards?token=secret123"
        Output: "https://api.greenhouse.io/v1/boards"
    """
    try:
        parsed = urlparse(url)
        # Reconstruct without query and fragment
        sanitized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        return sanitized
    except Exception:
        # Fallback: return as-is if parsing fails
        return url


# =============================================================================
# P0 PROOF SYSTEM (v14 FIX #1: Required_Any Semantics)
# =============================================================================

@dataclass
class P0ProofRequest:
    """
    A single P0 proof requirement for ATS identification/submission.

    Represents a specific network request pattern that proves ATS identity.

    Example (Greenhouse identification):
        P0ProofRequest(
            method="GET",
            domain="boards-api.greenhouse.io",
            path="/v1/boards/",
            match_mode=DomainMatchMode.EXACT
        )
    """
    method: str  # HTTP method (GET, POST, etc.)
    domain: str  # Domain or pattern (e.g., "api.greenhouse.io", ".icims.com")
    path: str    # Path prefix (e.g., "/v1/boards/")
    match_mode: DomainMatchMode = DomainMatchMode.EXACT

    def __post_init__(self):
        self.method = self.method.upper()


@dataclass
class P0ProofTierConfig:
    """
    v14 NEW: Proof tier configuration with required_any semantics (Fix #1).

    Defines how many proofs must match for a tier to pass.
    Uses OR semantics instead of AND to avoid coverage collapse.

    Example:
        # Config with 3 alternatives, only need 1 to match
        P0ProofTierConfig(
            provider_id="lever",
            tier="identification",
            proofs=[proof_a, proof_b, proof_c],
            required_any=1  # Only need ONE to match (OR semantics)
        )
    """
    provider_id: str
    tier: str  # "identification" | "submission"
    proofs: List[P0ProofRequest]
    required_any: int = 1  # v14 NEW: Require at least N proofs

    def __post_init__(self):
        if self.required_any < 1:
            raise ValueError(f"required_any must be ≥ 1, got {self.required_any}")
        if self.required_any > len(self.proofs):
            raise ValueError(
                f"required_any ({self.required_any}) cannot exceed "
                f"proof count ({len(self.proofs)})"
            )


@dataclass
class P0ProofValidationResult:
    """
    v14 REFINED: Proof validation result with match quality tracking (Fix #2).

    Includes:
    - proof_valid: Whether required_any threshold was met
    - match_quality: "strong" (all usable) | "weak" (some unknown_status)
    - Matched/missing proof details for debugging
    """
    proof_applicable: bool  # Whether proofs exist for this provider
    proof_valid: bool       # Whether required_any threshold met
    required_any: int = 0   # v14 NEW: How many required
    matched_count: int = 0  # v14 NEW: How many matched
    missing_proofs: List[P0ProofRequest] = field(default_factory=list)
    matched_proofs: List[P0ProofRequest] = field(default_factory=list)
    match_quality: str = "strong"  # v14 NEW: "strong" | "weak"


# =============================================================================
# ATS DETECTION RESULT
# =============================================================================

@dataclass
class ATSDetectionResult:
    """
    Result of ATS detection process.

    Contains:
    - provider_id: Detected ATS (e.g., "greenhouse", "lever")
    - confidence: 0.0-1.0 confidence score
    - route_eligible: Whether safe to route to this ATS
    - level_extracted: Highest evidence level reached
    """
    provider_id: Optional[str] = None
    confidence: float = 0.0
    route_eligible: bool = False
    level_extracted: EvidenceLevel = EvidenceLevel.L1_URL

    # Debugging
    detection_path: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# =============================================================================
# ATS DETECTION EVIDENCE
# =============================================================================

@dataclass
class ATSDetectionEvidence:
    """
    Complete evidence bundle from ATS detection.

    Captures all signals used for detection:
    - L1: URL patterns
    - L2: DOM elements
    - L3: Apply button
    - L4: Network requests + P0 proofs
    """
    provider_id: Optional[str] = None
    confidence: float = 0.0
    level_extracted: EvidenceLevel = EvidenceLevel.L1_URL

    # URLs
    job_url: str = ""
    final_url: str = ""

    # L1 Evidence
    url_pattern_matched: bool = False
    url_pattern_details: Optional[str] = None

    # L2 Evidence
    dom_signals_found: List[str] = field(default_factory=list)
    meta_tags: Dict[str, str] = field(default_factory=dict)

    # L3 Evidence
    apply_button_found: bool = False
    apply_button_type: Optional[str] = None  # "link" | "button" | "iframe"
    apply_button_validated: bool = False

    # L4 Evidence (Network)
    apply_xhr_requests_post_click: List[NetworkRequest] = field(default_factory=list)
    network_request_count: int = 0

    # P0 Proof Validation
    proof_result: Optional[P0ProofValidationResult] = None
    proof_inconclusive: bool = False  # True if proofs exist but not enforced

    def to_dict(self) -> Dict[str, Any]:
        """
        v14 CRITICAL: Serialization must not include url_full.

        NetworkRequest.to_dict() already excludes url_full, so we're safe.
        """
        return {
            'provider_id': self.provider_id,
            'confidence': self.confidence,
            'level_extracted': self.level_extracted.value,
            'job_url': self.job_url,
            'final_url': self.final_url,

            # L1
            'url_pattern_matched': self.url_pattern_matched,
            'url_pattern_details': self.url_pattern_details,

            # L2
            'dom_signals_found': self.dom_signals_found,
            'meta_tags': self.meta_tags,

            # L3
            'apply_button_found': self.apply_button_found,
            'apply_button_type': self.apply_button_type,
            'apply_button_validated': self.apply_button_validated,

            # L4 (v14: network requests serialized WITHOUT url_full!)
            'post_click_network': [req.to_dict() for req in self.apply_xhr_requests_post_click],
            'network_request_count': self.network_request_count,

            # Proofs
            'proof_inconclusive': self.proof_inconclusive,
        }
