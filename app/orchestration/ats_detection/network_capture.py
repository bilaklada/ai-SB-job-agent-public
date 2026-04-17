"""
Network Capture Session - Playwright Integration (v14)

Implements network request capture with:
- Idempotent stop() - no spurious warnings (Fix #7)
- Ephemeral url_full tracking via debug trace (Fix #3)
- Deterministic async task tracking
- Handler leak prevention

Key Innovation:
- Captures network requests during browser automation
- Sanitizes URLs for persistence while keeping full URLs ephemeral
- Clean teardown with idempotent stop()
"""

import logging
import asyncio
from typing import List, Dict, Optional

try:
    from playwright.async_api import Page, Request, Response
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Page = None
    Request = None
    Response = None

from .types import NetworkRequest, NetworkRequestDebugTrace, sanitize_network_url

logger = logging.getLogger(__name__)


# =============================================================================
# NETWORK CAPTURE SESSION (v14 FIX #7: Idempotent Stop)
# =============================================================================

class NetworkCaptureSession:
    """
    v14 REFINED: Network capture session with idempotent stop() and ephemeral url_full.

    Captures network requests during Playwright browser automation with:
    - Separate sanitized URL (persistence-safe) and full URL (ephemeral)
    - Idempotent stop() - can be called multiple times safely (Fix #7)
    - Clean handler teardown - prevents leaks
    - Deterministic async task tracking

    Usage:
        session = NetworkCaptureSession(page)
        session.start()

        # ... browser automation ...

        await session.stop()  # Can call multiple times safely
        requests = session.get_requests()
    """

    def __init__(self, page: Page):
        """
        Initialize network capture session.

        Args:
            page: Playwright page to monitor
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright not available. Install with: pip install playwright")

        self.page = page
        self.captured_requests: List[NetworkRequest] = []
        self.request_map: Dict[Request, NetworkRequest] = {}
        self.response_tasks: List[asyncio.Task] = []
        self._handlers_attached = False
        self._stopped = False  # v14 NEW: Track stop state

        # Store handler references for clean detachment
        self._on_request_handler = self._on_request
        self._on_response_handler = self._on_response

    def start(self) -> None:
        """
        v14 REFINED: Start capturing network requests (idempotent).

        Can be called multiple times - will only attach handlers once.
        """
        if self._handlers_attached:
            # v14: Idempotent - return silently (no warning on normal paths)
            logger.debug("[NetworkCapture] Handlers already attached")
            return

        if self._stopped:
            logger.warning("[NetworkCapture] Cannot start - session already stopped")
            return

        # Attach handlers
        self.page.on('request', self._on_request_handler)
        self.page.on('response', self._on_response_handler)
        self._handlers_attached = True

        logger.debug("[NetworkCapture] Handlers attached - capture started")

    async def stop(self, timeout: float = 2.0) -> None:
        """
        v14 REFINED: Stop capturing (idempotent, quiet, no spurious warnings).

        Can be called multiple times safely (e.g., try + finally).
        No warnings logged on normal retry paths.

        Args:
            timeout: Maximum time to wait for pending response tasks (seconds)
        """
        # v14 FIX: Idempotent - return silently if already stopped
        if self._stopped:
            return

        if not self._handlers_attached:
            # v14: Already cleaned up or never started - silent return
            self._stopped = True
            return

        # Detach handlers
        try:
            self.page.off('request', self._on_request_handler)
            self.page.off('response', self._on_response_handler)
            logger.debug("[NetworkCapture] Handlers detached")
        except Exception as e:
            # v14: Log only on exceptional teardown
            logger.warning(f"[NetworkCapture] Exception during handler detach: {e}")

        self._handlers_attached = False

        # Await pending response tasks
        if self.response_tasks:
            logger.debug(f"[NetworkCapture] Awaiting {len(self.response_tasks)} response tasks...")
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.response_tasks, return_exceptions=True),
                    timeout=timeout
                )
                logger.debug("[NetworkCapture] Response tasks completed")
            except asyncio.TimeoutError:
                logger.debug(
                    f"[NetworkCapture] Response tasks timeout after {timeout}s (non-critical)"
                )

        # Clear maps
        self.request_map.clear()
        self.response_tasks.clear()

        # v14: Mark as stopped
        self._stopped = True

        logger.debug("[NetworkCapture] Capture stopped")

    def get_requests(self) -> List[NetworkRequest]:
        """
        Get all captured network requests.

        Returns:
            List of NetworkRequest objects (with ephemeral debug traces)

        Note: Requests include ephemeral url_full via _debug_trace.
        Call .to_dict() before persistence to sanitize!
        """
        return self.captured_requests.copy()

    def get_usable_requests(self) -> List[NetworkRequest]:
        """
        Get network requests with usable status codes (200-499).

        Filters out requests with status=None (unknown/failed).

        Returns:
            List of NetworkRequest with known status codes
        """
        return [
            req for req in self.captured_requests
            if req.status is not None and 200 <= req.status < 500
        ]

    # -------------------------------------------------------------------------
    # INTERNAL: Event Handlers
    # -------------------------------------------------------------------------

    def _on_request(self, request: Request) -> None:
        """
        v14 REFINED: Handle request event - store sanitized + debug trace.

        Creates NetworkRequest with:
        - url_sanitized: Safe for logs/database
        - _debug_trace: Ephemeral, contains url_full
        """
        try:
            url_full = request.url
            url_sanitized = sanitize_network_url(url_full)

            # v14 NEW: Create debug trace (ephemeral)
            debug_trace = NetworkRequestDebugTrace(url_full=url_full)

            # v14: Create request with sanitized URL + debug trace
            nr = NetworkRequest(
                method=request.method,
                url_sanitized=url_sanitized,  # v14: Only sanitized in main object
                resource_type=request.resource_type,
                status=None,  # Will be updated on response
                _debug_trace=debug_trace  # v14: Ephemeral only
            )

            self.request_map[request] = nr
            self.captured_requests.append(nr)

            logger.debug(
                f"[NetworkCapture] Request: {nr.method} {nr.url_sanitized} "
                f"({nr.resource_type})"
            )

        except Exception as e:
            logger.warning(f"[NetworkCapture] Error capturing request: {e}")

    def _on_response(self, response: Response) -> None:
        """
        Handle response event - update status and content_type asynchronously.

        Creates async task to fetch headers without blocking.
        """
        try:
            request = response.request
            nr = self.request_map.get(request)

            if not nr:
                # Request not in map (shouldn't happen)
                return

            # Create async task for response processing
            task = asyncio.create_task(self._process_response(response, nr))
            self.response_tasks.append(task)

        except Exception as e:
            logger.warning(f"[NetworkCapture] Error handling response: {e}")

    async def _process_response(
        self,
        response: Response,
        nr: NetworkRequest
    ) -> None:
        """
        Process response asynchronously - update status and content_type.

        Args:
            response: Playwright response object
            nr: NetworkRequest to update
        """
        try:
            # Update status
            nr.status = response.status

            # Get content_type from headers
            try:
                headers = await response.all_headers()
                nr.content_type = headers.get('content-type')
            except Exception as e:
                logger.debug(f"[NetworkCapture] Failed to get headers: {e}")

            logger.debug(
                f"[NetworkCapture] Response: {nr.method} {nr.url_sanitized} "
                f"→ {nr.status} ({nr.content_type})"
            )

        except Exception as e:
            logger.warning(f"[NetworkCapture] Error processing response: {e}")


# =============================================================================
# UTILITIES
# =============================================================================

def filter_xhr_requests(requests: List[NetworkRequest]) -> List[NetworkRequest]:
    """
    Filter for XHR/Fetch requests only.

    Args:
        requests: List of all network requests

    Returns:
        List of requests with resource_type in ['xhr', 'fetch']
    """
    return [
        req for req in requests
        if req.resource_type in ['xhr', 'fetch']
    ]


def filter_by_domain(
    requests: List[NetworkRequest],
    domain_pattern: str
) -> List[NetworkRequest]:
    """
    Filter requests by domain pattern.

    Args:
        requests: List of network requests
        domain_pattern: Domain to match (e.g., "greenhouse.io")

    Returns:
        List of requests with matching domain
    """
    return [
        req for req in requests
        if domain_pattern.lower() in req.url_sanitized.lower()
    ]


def get_request_count_by_type(requests: List[NetworkRequest]) -> Dict[str, int]:
    """
    Get count of requests by resource type.

    Args:
        requests: List of network requests

    Returns:
        Dict mapping resource_type to count

    Example:
        {'xhr': 12, 'document': 3, 'script': 5, 'image': 8}
    """
    counts = {}
    for req in requests:
        counts[req.resource_type] = counts.get(req.resource_type, 0) + 1

    return counts
