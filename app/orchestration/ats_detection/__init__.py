"""
ATS Detection System v14 - Production-Grade Multi-Level Evidence Extraction

This module implements the v14 ATS detection system with:
- Multi-level evidence extraction (L1-L4)
- P0 proof validation with required_any semantics
- Network request capture with Playwright
- Route eligibility gating
- ZERO wrong submissions guarantee

Architecture:
- types.py: Core data structures (NetworkRequest, Evidence, Proofs)
- proofs.py: P0 proof system and registry
- extractors.py: L1-L4 evidence extractors
- validators.py: P0 proof validation with match quality
- network_capture.py: NetworkCaptureSession with Playwright
- policies.py: Evidence level policies and gating

Author: SBAgent1 Team
Version: 14.0 (v13.1 Patch - Final Hardening)
Last Updated: 2026-01-02
"""

from .types import (
    NetworkRequest,
    NetworkRequestDebugTrace,
    ATSDetectionResult,
    ATSDetectionEvidence,
    EvidenceLevel,
    P0ProofRequest,
    P0ProofTierConfig,
    P0ProofValidationResult,
    DomainMatchMode,
)

from .proofs import (
    P0_PROOF_CONFIGS,
    register_proof_config,
    get_proof_config,
)

from .validators import (
    P0ProofSetValidator,
)

from .policies import (
    EvidenceLevelPolicy,
)

from .orchestrator import (
    ATSDetectionOrchestrator,
    detect_ats_with_evidence,
    detect_ats,
)

__all__ = [
    # Types
    'NetworkRequest',
    'NetworkRequestDebugTrace',
    'ATSDetectionResult',
    'ATSDetectionEvidence',
    'EvidenceLevel',
    'P0ProofRequest',
    'P0ProofTierConfig',
    'P0ProofValidationResult',
    'DomainMatchMode',

    # Proofs
    'P0_PROOF_CONFIGS',
    'register_proof_config',
    'get_proof_config',

    # Validators
    'P0ProofSetValidator',

    # Policies
    'EvidenceLevelPolicy',

    # Orchestrator (Main API)
    'ATSDetectionOrchestrator',
    'detect_ats_with_evidence',
    'detect_ats',
]
