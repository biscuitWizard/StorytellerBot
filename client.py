import logging
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class AgentClient:
    def __init__(
        self,
        base_url: str,
        *,
        retries: int = 3,
        backoff_factor: float = 0.3,
        status_forcelist: Optional[list] = None,
        timeout: float = 360.0,
    ):
        """
        :param base_url: root URL for your API (e.g. "https://api.example.com/v1")
        :param retries: number of total retry attempts
        :param backoff_factor: sleep multiplier between retries (e.g. 0.3s, 0.6s, 1.2s…)
        :param status_forcelist: HTTP status codes that should trigger a retry
        :param timeout: default socket timeout for connect/read (in seconds)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        status_forcelist = status_forcelist or [429, 500, 502, 503, 504]

        # build a Session with a Retry policy
        retry_strategy = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
            raise_on_status=False,  # we’ll check status manually
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)

        self.session = requests.Session()
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            resp = self.session.request(
                method,
                url,
                params=params,
                json=json,
                headers=headers,
                timeout=timeout or self.timeout,
            )
            # raise_for_status will throw for 4xx/5xx
            resp.raise_for_status()
        except requests.exceptions.Timeout:
            logging.exception(f"Timeout when calling {url}")
            raise
        except requests.exceptions.HTTPError as e:
            logging.exception(f"HTTP error {resp.status_code} for {url}: {resp.text}")
            raise
        except requests.exceptions.RequestException as e:
            logging.exception(f"Error during request to {url}")
            raise

        # parse JSON (or return text if not JSON)
        try:
            return resp.json()
        except ValueError:
            return resp.text

    def get(self, path: str, **kwargs) -> Any:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> Any:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> Any:
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> Any:
        return self.request("DELETE", path, **kwargs)
