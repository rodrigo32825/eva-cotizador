from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

import requests


class EvaApiError(RuntimeError):
    """Error legible devuelto por el puente de Apps Script."""


@dataclass(frozen=True)
class EvaApi:
    base_url: str
    token: str
    # Apps Script puede tardar más en la primera llamada después de estar inactivo.
    connect_timeout_seconds: int = 15
    read_timeout_seconds: int = 90

    def _post(
        self,
        action: str,
        *,
        retry_safe: bool = False,
        **payload: Any,
    ) -> dict[str, Any]:
        body = {"token": self.token, "action": action, **payload}
        attempts = 3 if retry_safe else 1
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                response = requests.post(
                    self.base_url,
                    json=body,
                    timeout=(self.connect_timeout_seconds, self.read_timeout_seconds),
                    allow_redirects=True,
                )
                response.raise_for_status()
                data = response.json()

                if not data.get("ok"):
                    raise EvaApiError(
                        str(data.get("error") or "La operación no pudo completarse.")
                    )
                return data

            except EvaApiError:
                raise
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error = exc
                if attempt < attempts:
                    time.sleep(1.5 * attempt)
                    continue
                break
            except requests.RequestException as exc:
                raise EvaApiError(
                    f"No fue posible conectar con Google Sheets: {exc}"
                ) from exc
            except ValueError as exc:
                raise EvaApiError(
                    "La conexión respondió con un formato no válido."
                ) from exc

        raise EvaApiError(
            "Google Sheets tardó demasiado en responder. Espera unos segundos y "
            "vuelve a sincronizar. Si estabas guardando un registro, revisa primero "
            "la hoja para confirmar que no se haya creado antes de intentarlo otra vez."
        ) from last_error

    def health(self) -> dict[str, Any]:
        return self._post("health", retry_safe=True)

    def bootstrap(self) -> dict[str, Any]:
        return self._post("bootstrap", retry_safe=True)

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
            retry_safe=True,
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
        # No se reintenta automáticamente: un segundo intento podría duplicar
        # un registro que Apps Script sí alcanzó a guardar antes del timeout.
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
        return self._post(
            "get_quote_bundle",
            retry_safe=True,
            quote_id=quote_id,
        )

    def save_quote_bundle(
        self,
        bundle: dict[str, Any],
        *,
        actor_name: str = "",
    ) -> dict[str, Any]:
        # Un guardado completo no se reintenta automáticamente: Apps Script
        # puede haber alcanzado a escribir antes de un timeout del cliente.
        return self._post(
            "save_quote_bundle",
            bundle=bundle,
            actor_name=actor_name,
        )


    def save_travel_document(
        self,
        data: dict[str, Any],
        *,
        actor_name: str = "",
    ) -> dict[str, Any]:
        """Persist purchased options and standardized confirmation data in one call."""
        return self._post(
            "save_travel_document",
            data=data,
            actor_name=actor_name,
        )
