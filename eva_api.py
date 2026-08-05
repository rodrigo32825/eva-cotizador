from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


class EvaApiError(RuntimeError):
    """Error legible devuelto por el puente de Apps Script."""


@dataclass(frozen=True)
class EvaApi:
    base_url: str
    token: str
    timeout_seconds: int = 90

    def _post(self, action: str, **payload: Any) -> dict[str, Any]:
        body = {"token": self.token, "action": action, **payload}
        try:
            response = requests.post(
                self.base_url,
                json=body,
                timeout=self.timeout_seconds,
                allow_redirects=True,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            raise EvaApiError(f"No fue posible conectar con Google Sheets: {exc}") from exc
        except ValueError as exc:
            raise EvaApiError("La conexión respondió con un formato no válido.") from exc

        if not data.get("ok"):
            raise EvaApiError(str(data.get("error") or "La operación no pudo completarse."))
        return data

    def health(self) -> dict[str, Any]:
        return self._post("health")

    def bootstrap(self) -> dict[str, Any]:
        return self._post("bootstrap")

    def list_records(
        self,
        sheet: str,
        *,
        query: str = "",
        search_fields: list[str] | None = None,
        active_only: bool = False,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        result = self._post(
            "list",
            sheet=sheet,
            query=query,
            search_fields=search_fields or [],
            active_only=active_only,
            limit=limit,
        )
        return list(result.get("rows", []))

    def create_record(
        self,
        sheet: str,
        data: dict[str, Any],
        *,
        actor_name: str = "",
    ) -> dict[str, Any]:
        result = self._post(
            "create",
            sheet=sheet,
            data=data,
            actor_name=actor_name,
        )
        return dict(result.get("record", {}))

    def update_record(
        self,
        sheet: str,
        id_value: str,
        data: dict[str, Any],
        *,
        id_field: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "sheet": sheet,
            "id_value": id_value,
            "data": data,
        }
        if id_field:
            payload["id_field"] = id_field
        result = self._post("update", **payload)
        return dict(result.get("record", {}))

    def quote_bundle(self, quote_id: str) -> dict[str, Any]:
        return self._post("get_quote_bundle", quote_id=quote_id)
