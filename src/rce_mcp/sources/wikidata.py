"""Wikidata source — search entities via Wikidata API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from ..config import get_config

logger = logging.getLogger(__name__)

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
HEADERS = {"User-Agent": "RCE-MCP/1.0 (https://github.com/user/rce-mcp)"}


class WikidataSource(BaseSource):
    """Search Wikidata entities and fetch their claims."""

    name = "wikidata"

    def __init__(self, timeout: float | None = None) -> None:
        cfg = get_config()
        self._timeout = timeout or cfg.web_timeout
        self._client = httpx.AsyncClient(
            headers=HEADERS, timeout=self._timeout, follow_redirects=True
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def search(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        """Search Wikidata for entities matching *query*."""
        params = {
            "action": "wbsearchentities",
            "search": query,
            "language": "en",
            "format": "json",
            "limit": min(limit, 10),
            "utf8": 1,
        }
        try:
            resp = await self._client.get(WIKIDATA_API, params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("Wikidata search failed: %s", exc)
            return []

        search_results = data.get("search", [])
        if not search_results:
            return []

        # Fetch details for found entities
        entity_ids = "|".join(r["id"] for r in search_results)
        detail_params = {
            "action": "wbgetentities",
            "ids": entity_ids,
            "format": "json",
            "props": "claims|labels|descriptions",
            "languages": "en",
        }
        try:
            resp2 = await self._client.get(WIKIDATA_API, params=detail_params)
            resp2.raise_for_status()
            entities = resp2.json().get("entities", {})
        except Exception as exc:
            logger.warning("Wikidata details failed: %s", exc)
            entities = {}

        results: list[dict[str, Any]] = []
        for sr in search_results:
            eid = sr["id"]
            entity = entities.get(eid, {})
            label = entity.get("labels", {}).get("en", {}).get("value", sr.get("label", ""))
            description = entity.get("descriptions", {}).get("en", {}).get("value", sr.get("description", ""))

            claims = entity.get("claims", {})
            claim_summary = self._summarize_claims(claims)

            results.append(
                {
                    "title": label,
                    "snippet": f"{description}\n{claim_summary}".strip(),
                    "url": f"https://www.wikidata.org/wiki/{eid}",
                    "source": "wikidata",
                    "entity_id": eid,
                    "description": description,
                }
            )
            await asyncio.sleep(0.1)

        return results

    def _summarize_claims(self, claims: dict[str, list], max_claims: int = 5) -> str:
        """Extract key claim values into a readable summary."""
        parts: list[str] = []
        for prop, entries in list(claims.items())[:max_claims]:
            for entry in entries[:2]:
                mainsnak = entry.get("mainsnak", {})
                dtype = mainsnak.get("datatype", "")
                data_value = mainsnak.get("datavalue", {})
                if dtype == "wikibase-item":
                    value = data_value.get("value", {}).get("id", "?")
                elif dtype in ("string", "external-id", "url"):
                    value = data_value.get("value", "?")
                elif dtype == "time":
                    value = data_value.get("value", {}).get("time", "?")
                elif dtype == "quantity":
                    value = str(data_value.get("value", {}).get("amount", "?"))
                elif dtype == "monolingualtext":
                    value = data_value.get("value", {}).get("text", "?")
                else:
                    value = data_value.get("value", str(data_value))
                parts.append(f"{prop}: {value}")
        return " | ".join(parts)
