"""
Base integration framework for all external API connectors.

Provides:
- HTTP client with retries
- Token management helpers
- Logging utilities
- Common error handling
"""
import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

# Try httpx (async) or requests (sync)
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    try:
        import requests
        HAS_REQUESTS = True
    except ImportError:
        HAS_REQUESTS = False

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import get_connection

logger = logging.getLogger(__name__)


class IntegrationError(Exception):
    """Base exception for integration failures."""
    pass


class TokenExpiredError(IntegrationError):
    """Raised when an access token has expired and needs refresh."""
    pass


class IntegrationBase:
    """
    Base class for all integrations.
    
    Provides:
    - Token management (get, refresh, store)
    - HTTP client with retries
    - Logging
    - Error handling
    """
    
    def __init__(self, provider: str):
        """
        Initialize integration base.
        
        Args:
            provider: Provider name (e.g., 'zoho', 'google', 'twilio')
        """
        self.provider = provider
        self.logger = logging.getLogger(f"integration.{provider}")
    
    def get_token(self) -> Optional[Dict[str, Any]]:
        """
        Get access token from database.
        
        Returns:
            Dict with access_token, refresh_token, expires_at, meta, or None if not found
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT access_token, refresh_token, expires_at, meta
            FROM integration_tokens
            WHERE provider = ?
        """, (self.provider,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            "access_token": row["access_token"],
            "refresh_token": row["refresh_token"],
            "expires_at": row["expires_at"],
            "meta": json.loads(row["meta"] or "{}")
        }
    
    def store_token(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None
    ):
        """
        Store or update token in database.
        
        Args:
            access_token: Access token string
            refresh_token: Optional refresh token
            expires_at: ISO 8601 timestamp when token expires
            meta: Optional provider-specific metadata (JSON dict)
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        now = datetime.utcnow().isoformat()
        meta_json = json.dumps(meta or {})
        
        cursor.execute("""
            INSERT INTO integration_tokens (
                id, provider, access_token, refresh_token, expires_at, meta, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(provider) DO UPDATE SET
                access_token = excluded.access_token,
                refresh_token = COALESCE(excluded.refresh_token, refresh_token),
                expires_at = excluded.expires_at,
                meta = excluded.meta,
                updated_at = excluded.updated_at
        """, (
            f"{self.provider}_{now}",
            self.provider,
            access_token,
            refresh_token,
            expires_at,
            meta_json,
            now,
            now
        ))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Stored token for {self.provider}")
    
    def is_token_expired(self, expires_at: Optional[str]) -> bool:
        """
        Check if token is expired (or expires within 5 minutes).
        
        Args:
            expires_at: ISO 8601 timestamp
        
        Returns:
            True if expired or expiring soon
        """
        if not expires_at:
            return False  # No expiry info = assume valid
        
        try:
            expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            # Add 5 minute buffer
            buffer = timedelta(minutes=5)
            return datetime.utcnow() + buffer >= expiry
        except Exception:
            # If we can't parse, assume expired to be safe
            return True
    
    def get_valid_token(self) -> str:
        """
        Get a valid access token, refreshing if needed.
        
        Returns:
            Access token string
        
        Raises:
            TokenExpiredError: If token expired and refresh failed
            IntegrationError: If no token found
        """
        token_data = self.get_token()
        
        if not token_data:
            raise IntegrationError(f"No token found for {self.provider}. Configure authentication first.")
        
        # Check if expired
        if self.is_token_expired(token_data.get("expires_at")):
            self.logger.info(f"Token expired for {self.provider}, attempting refresh...")
            # Subclasses should implement refresh_token()
            if hasattr(self, "refresh_token") and callable(self.refresh_token):
                self.refresh_token()
                # Re-fetch after refresh
                token_data = self.get_token()
                if not token_data:
                    raise TokenExpiredError(f"Failed to refresh token for {self.provider}")
            else:
                raise TokenExpiredError(f"Token expired for {self.provider} and no refresh method available")
        
        return token_data["access_token"]
    
    def http_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout: float = 30.0,
        retries: int = 3
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retries.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            headers: Optional headers
            json_data: Optional JSON body
            params: Optional query params
            timeout: Request timeout in seconds
            retries: Number of retry attempts
        
        Returns:
            Response JSON as dict
        
        Raises:
            IntegrationError: If request fails after retries
        """
        if headers is None:
            headers = {}
        
        last_error = None
        
        for attempt in range(retries):
            try:
                if HAS_HTTPX:
                    # Use httpx (sync mode for simplicity in base class)
                    with httpx.Client(timeout=timeout) as client:
                        response = client.request(
                            method=method,
                            url=url,
                            headers=headers,
                            json=json_data,
                            params=params
                        )
                        response.raise_for_status()
                        return response.json()
                elif HAS_REQUESTS:
                    response = requests.request(
                        method=method,
                        url=url,
                        headers=headers,
                        json=json_data,
                        params=params,
                        timeout=timeout
                    )
                    response.raise_for_status()
                    return response.json()
                else:
                    raise IntegrationError("No HTTP client available (install httpx or requests)")
            
            except Exception as e:
                last_error = e
                if attempt < retries - 1:
                    self.logger.warning(f"Request failed (attempt {attempt + 1}/{retries}): {e}, retrying...")
                    import time
                    time.sleep(1 * (attempt + 1))  # Exponential backoff
                else:
                    raise IntegrationError(f"HTTP request failed after {retries} attempts: {str(e)}")
        
        raise IntegrationError(f"Request failed: {last_error}")
    
    def log_action(self, action: str, details: Optional[Dict] = None):
        """
        Log an integration action.
        
        Args:
            action: Action name (e.g., "search_contact", "send_email")
            details: Optional details dict
        """
        self.logger.info(f"{self.provider}.{action}", extra={"details": details or {}})
    
    def log_integration_event(self, provider: str, action: str, meta: Optional[Dict] = None):
        """
        Log an integration event to system_event table.
        
        Args:
            provider: Integration provider (e.g., "zoho", "google", "twilio")
            action: Action name (e.g., "search_contact", "refresh_token")
            meta: Optional metadata dict
        """
        import uuid
        from datetime import datetime
        
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            event_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO system_event (id, event_type, severity, message, meta, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                event_id,
                "integration_event",
                "info",
                f"{provider}.{action}",
                json.dumps(meta or {}),
                datetime.utcnow().isoformat()
            ))
            conn.commit()
        except Exception as e:
            self.logger.warning(f"Failed to log integration event: {e}")
        finally:
            conn.close()

