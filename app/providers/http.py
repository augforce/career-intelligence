from __future__ import annotations
import json
import urllib.parse
import urllib.request

DEFAULT_TIMEOUT = 12
USER_AGENT = "CareerIntelligence/1.0 (personal job-fit tool)"


def get_json(url: str, params: dict | None = None, headers: dict | None = None,
             timeout: int = DEFAULT_TIMEOUT):
    """The single network touchpoint for all search providers.

    Tests monkeypatch this function (or urllib.request.urlopen) so no test ever
    hits the live network.
    """
    if params:
        sep = "&" if "?" in url else "?"
        url = url + sep + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT, "Accept": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))
