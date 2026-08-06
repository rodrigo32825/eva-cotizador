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
    read_timeout_seconds: int = 35

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
                    timeout=(
                        self.connect_timeout_seconds,
                        self.read_timeout_seconds,
                    ),
                    allow_redirects=True,
                )
                response.raise_for_status()
                data = response.json()

                if not data.get("ok"):
                    raise EvaApiError(
                        str(
                            data.get("error")
                            or "La operación no pudo completarse."
                        )
                    )

                return data

            except EvaApiError:
                raise

            except requests.HTTPError as exc:
                last_error = exc
                status_code = (
                    exc.response.status_code
                    if exc.response is not None
                    else 0
                )

                # Apps Script usa redirecciones temporales. En consultas seguras,
                # repetimos desde la URL principal cuando Google devuelve un
                # error temporal o un enlace de redirección vencido.
                retryable_statuses = {
                    404,
                    408,
                    429,
                    500,
                    502,
                    503,
                    504,
                }

                if (
                    retry_safe
                    and status_code in retryable_statuses
                    and attempt < attempts
                ):
                    time.sleep(1.0 * attempt)
                    continue

                raise EvaApiError(
                    "No fue posible conectar con Google Sheets. "
                    f"Google respondió con el error {status_code}."
                ) from exc

            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error = exc

                if retry_safe and attempt < attempts:
                    time.sleep(1.0 * attempt)
                    continue

                break

            except requests.RequestException as exc:
                last_error = exc

                if retry_safe and attempt < attempts:
                    time.sleep(1.0 * attempt)
                    continue

                raise EvaApiError(
                    f"No fue posible conectar con Google Sheets: {exc}"
                ) from exc

            except ValueError as exc:
                last_error = exc

                if retry_safe and attempt < attempts:
                    time.sleep(1.0 * attempt)
                    continue

                raise EvaApiError(
                    "La conexión respondió con un formato no válido."
                ) from exc

        raise EvaApiError(
            "Google Sheets tardó demasiado en responder. "
            "Espera unos segundos y vuelve a sincronizar. "
            "Si estabas guardando un registro, revisa primero la hoja "
            "para confirmar que no se haya creado antes de intentarlo otra vez."
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
