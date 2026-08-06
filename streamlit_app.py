from __future__ import annotations

from datetime import date, datetime, time
from pathlib import Path
import re
from typing import Any
from urllib.parse import unquote

import pandas as pd
import requests
import streamlit as st

from eva_api import EvaApi, EvaApiError


APP_DIR = Path(__file__).resolve().parent
LOGO_PATH = APP_DIR / "proyecto_eva_logo.jpeg"
if not LOGO_PATH.exists():
    LOGO_PATH = APP_DIR / "assets" / "proyecto_eva_logo.jpeg"

st.set_page_config(
    page_title="Cotizador Proyecto EVA",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      :root {
        --eva-accent: #79c9c4;
        --eva-accent-dark: #459f9a;
        --eva-text: #4d4d4d;
        --eva-soft: #eef8f7;
        --eva-border: #d9e7e6;
      }
      .stApp { background: #ffffff; color: var(--eva-text); }
      [data-testid="stSidebar"] { background: #f7fbfb; }
      .eva-hero {
        padding: 1rem 1.25rem;
        border: 1px solid var(--eva-border);
        border-radius: 18px;
        background: linear-gradient(135deg, #ffffff 0%, var(--eva-soft) 100%);
        margin-bottom: 1rem;
      }
      .eva-kicker {
        color: var(--eva-accent-dark);
        letter-spacing: .12em;
        text-transform: uppercase;
        font-size: .78rem;
        font-weight: 700;
      }
      .eva-title { margin: .2rem 0; font-size: 1.9rem; font-weight: 500; }
      .eva-subtle { color: #6f7777; }
      .eva-card {
        border: 1px solid var(--eva-border);
        border-radius: 16px;
        padding: 1rem;
        background: #ffffff;
        margin-bottom: .75rem;
      }
      .eva-badge {
        display: inline-block;
        padding: .2rem .55rem;
        border-radius: 999px;
        background: var(--eva-soft);
        color: var(--eva-accent-dark);
        font-size: .78rem;
        font-weight: 700;
      }
      .eva-route {
        font-size: 1.02rem;
        font-weight: 600;
        letter-spacing: .02em;
      }
      div[data-testid="stMetric"] {
        border: 1px solid var(--eva-border);
        border-radius: 14px;
        padding: .8rem 1rem;
        background: #ffffff;
      }
      .stButton > button[kind="primary"] {
        background: var(--eva-accent-dark);
        border-color: var(--eva-accent-dark);
      }
      [data-testid="stSidebar"] div[role="radiogroup"] label p {
        color: #2f3437 !important;
        opacity: 1 !important;
      }
      [data-testid="stSidebar"] div[role="radiogroup"] label {
        color: #2f3437 !important;
      }
      div[data-testid="stMetric"] [data-testid="stMetricLabel"] p,
      div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: var(--eva-text) !important;
        opacity: 1 !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_api() -> EvaApi:
    try:
        api_url = st.secrets["eva"]["api_url"]
        api_token = st.secrets["eva"]["api_token"]
    except (KeyError, FileNotFoundError) as exc:
        st.error(
            "Falta configurar la conexión. Agrega `api_url` y `api_token` "
            "en los Secrets de Streamlit."
        )
        st.stop()
        raise RuntimeError from exc
    return EvaApi(str(api_url).strip(), str(api_token).strip())


@st.cache_data(ttl=120, show_spinner=False)
def load_bootstrap(api_url: str, api_token: str) -> dict[str, Any]:
    return EvaApi(api_url, api_token).bootstrap()


@st.cache_data(ttl=45, show_spinner=False)
def load_quotes(api_url: str, api_token: str, query: str = "") -> list[dict[str, Any]]:
    return EvaApi(api_url, api_token).list_records(
        "01_COTIZACIONES",
        query=query,
        search_fields=["COTIZACION_ID", "CLIENTE_NOMBRE", "DESTINO_RESUMEN", "ESTATUS"],
        limit=200,
    )


@st.cache_data(ttl=45, show_spinner=False)
def load_passengers(api_url: str, api_token: str, query: str = "") -> list[dict[str, Any]]:
    return EvaApi(api_url, api_token).list_records(
        "03_PASAJEROS",
        query=query,
        search_fields=["PASAJERO_ID", "NOMBRES", "APELLIDO_PATERNO", "APELLIDO_MATERNO", "EMAIL", "TELEFONO"],
        active_only=True,
        limit=300,
    )


@st.cache_data(ttl=30, show_spinner=False)
def load_quote_bundle(api_url: str, api_token: str, quote_id: str) -> dict[str, Any]:
    return EvaApi(api_url, api_token).quote_bundle(quote_id)


def clear_app_cache() -> None:
    load_quotes.clear()
    load_passengers.clear()
    load_bootstrap.clear()
    load_quote_bundle.clear()


def iso(value: date | None) -> str:
    return value.isoformat() if value else ""


def time_text(value: time | None) -> str:
    return value.strftime("%H:%M") if value else ""


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def number(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def integer(value: Any, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def money(value: Any, currency: str) -> str:
    return f"{currency} {number(value):,.2f}"


def is_http_url(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return text.startswith("https://") or text.startswith("http://")


@st.cache_data(ttl=3600, show_spinner=False)
def resolve_map_url(url: str) -> str:
    """Resuelve enlaces cortos de Google Maps cuando sea posible."""
    clean_url = str(url or "").strip()
    if not clean_url:
        return ""
    if "maps.app.goo.gl" not in clean_url and "goo.gl/maps" not in clean_url:
        return clean_url
    try:
        response = requests.get(
            clean_url,
            allow_redirects=True,
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0 Proyecto EVA Cotizador"},
            stream=True,
        )
        return str(response.url or clean_url)
    except requests.RequestException:
        return clean_url


def coordinates_from_map_url(url: str) -> tuple[float, float] | None:
    resolved = unquote(resolve_map_url(url))
    if not resolved:
        return None

    patterns = [
        r"@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)",
        r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)",
        r"[?&](?:q|query|ll)=(-?\d+(?:\.\d+)?)[,\s]+(-?\d+(?:\.\d+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, resolved, flags=re.IGNORECASE)
        if not match:
            continue
        lat, lon = float(match.group(1)), float(match.group(2))
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon
    return None


def show_simple_map(map_url: str, *, caption_when_missing: bool = True) -> None:
    map_url = str(map_url or "").strip()
    if not map_url:
        return
    st.link_button("Abrir ubicación en Google Maps", map_url, use_container_width=True)
    coordinates = coordinates_from_map_url(map_url)
    if coordinates:
        lat, lon = coordinates
        st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}), zoom=14, use_container_width=True)
    elif caption_when_missing:
        st.caption(
            "El enlace quedó guardado. La vista previa aparece cuando Google Maps incluye "
            "las coordenadas dentro del vínculo; el botón siempre abrirá la ubicación correcta."
        )


def parse_sheet_datetime(date_value: Any, time_value: Any) -> datetime | None:
    date_text = str(date_value or "").strip()[:10]
    time_text_value = str(time_value or "").strip()[:5]
    if not date_text or not time_text_value:
        return None
    for date_format in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            parsed_date = datetime.strptime(date_text, date_format).date()
            parsed_time = datetime.strptime(time_text_value, "%H:%M").time()
            return datetime.combine(parsed_date, parsed_time)
        except ValueError:
            continue
    return None


def human_duration(total_minutes: int) -> str:
    total_minutes = max(int(total_minutes), 0)
    hours, minutes = divmod(total_minutes, 60)
    if hours and minutes:
        return f"{hours} h {minutes} min"
    if hours:
        return f"{hours} h"
    return f"{minutes} min"


def passenger_label(row: dict[str, Any]) -> str:
    full_name = " ".join(
        part for part in [row.get("NOMBRES"), row.get("APELLIDO_PATERNO"), row.get("APELLIDO_MATERNO")] if part
    ).strip()
    return f"{full_name or 'Sin nombre'} · {row.get('PASAJERO_ID', '')}"


def show_header() -> None:
    col_logo, col_text = st.columns([1.15, 3.85], vertical_alignment="center")
    with col_logo:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), use_container_width=True)
    with col_text:
        st.markdown(
            """
            <div class="eva-hero">
              <div class="eva-kicker">Proyecto EVA</div>
              <div class="eva-title">Cotizador y control de viajes</div>
              <div class="eva-subtle">Cotizaciones claras, editables y conectadas con Google Sheets.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def show_flash() -> None:
    flash = st.session_state.pop("eva_flash", None)
    if flash:
        st.success(flash)


def page_home(api: EvaApi) -> None:
    st.subheader("Inicio")
    try:
        quotes = load_quotes(api.base_url, api.token)
        passengers = load_passengers(api.base_url, api.token)
    except EvaApiError as exc:
        st.error(str(exc))
        return

    sold = sum(str(q.get("ESTATUS", "")).upper() == "VENDIDA" for q in quotes)
    pending = sum(str(q.get("ESTATUS", "")).upper() in {"BORRADOR", "ENVIADA", "EN_SEGUIMIENTO"} for q in quotes)

    a, b, c, d = st.columns(4)
    a.metric("Cotizaciones", len(quotes))
    b.metric("Pendientes", pending)
    c.metric("Vendidas", sold)
    d.metric("Pasajeros", len(passengers))

    st.markdown("### Cotizaciones recientes")
    if not quotes:
        st.info("Todavía no hay cotizaciones registradas.")
        return

    recent = list(reversed(quotes[-8:]))
    for quote in recent:
        st.markdown(
            f"""
            <div class="eva-card">
              <strong>{quote.get('COTIZACION_ID', '')}</strong> · {quote.get('CLIENTE_NOMBRE', 'Sin cliente')}<br>
              <span class="eva-subtle">{quote.get('DESTINO_RESUMEN', 'Sin destino')} · {quote.get('ESTATUS', 'BORRADOR')}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def create_passenger_widget(api: EvaApi, actor_name: str, key_prefix: str = "passenger") -> dict[str, Any] | None:
    with st.form(f"{key_prefix}_form", clear_on_submit=True):
        st.markdown("#### Nuevo pasajero")
        c1, c2, c3 = st.columns(3)
        nombres = c1.text_input("Nombre(s) *")
        apellido_paterno = c2.text_input("Apellido paterno")
        apellido_materno = c3.text_input("Apellido materno")

        c4, c5, c6 = st.columns(3)
        fecha_nacimiento = c4.date_input(
            "Fecha de nacimiento",
            value=None,
            min_value=date(1900, 1, 1),
            max_value=date.today(),
        )
        nacionalidad = c5.text_input("Nacionalidad")
        genero = c6.selectbox("Género", ["", "FEMENINO", "MASCULINO", "OTRO", "NO_ESPECIFICA"])

        c7, c8 = st.columns(2)
        email = c7.text_input("Correo")
        telefono = c8.text_input("Teléfono")

        with st.expander("Pasaporte y datos opcionales"):
            c9, c10, c11 = st.columns(3)
            pasaporte = c9.text_input("Número de pasaporte")
            vencimiento = c10.date_input("Vencimiento del pasaporte", value=None)
            pais_emisor = c11.text_input("País emisor")
            notas = st.text_area("Notas")

        submitted = st.form_submit_button("Guardar pasajero", type="primary", use_container_width=True)

    if not submitted:
        return None
    if not clean_text(nombres):
        st.warning("El nombre es obligatorio.")
        return None

    data = {
        "NOMBRES": clean_text(nombres),
        "APELLIDO_PATERNO": clean_text(apellido_paterno),
        "APELLIDO_MATERNO": clean_text(apellido_materno),
        "NOMBRE_COMPLETO_DOCUMENTO": clean_text(" ".join([nombres, apellido_paterno, apellido_materno])),
        "FECHA_NACIMIENTO": iso(fecha_nacimiento),
        "GENERO": genero,
        "NACIONALIDAD": clean_text(nacionalidad),
        "PASAPORTE": clean_text(pasaporte),
        "VENCIMIENTO_PASAPORTE": iso(vencimiento),
        "PAIS_EMISOR_PASAPORTE": clean_text(pais_emisor),
        "EMAIL": clean_text(email),
        "TELEFONO": clean_text(telefono),
        "NOTAS": clean_text(notas),
        "ACTIVO": "SI",
    }
    try:
        created = api.create_record("03_PASAJEROS", data, actor_name=actor_name)
    except EvaApiError as exc:
        st.error(str(exc))
        return None

    clear_app_cache()
    st.success(f"Pasajero guardado: {created.get('PASAJERO_ID', '')}")
    return created


def page_passengers(api: EvaApi, actor_name: str) -> None:
    st.subheader("Pasajeros")
    tab_search, tab_new = st.tabs(["Buscar", "Registrar pasajero"])

    with tab_search:
        query = st.text_input("Buscar por nombre, correo, teléfono o ID")
        try:
            rows = load_passengers(api.base_url, api.token, query)
        except EvaApiError as exc:
            st.error(str(exc))
            return

        if not rows:
            st.info("No se encontraron pasajeros.")
        else:
            display = pd.DataFrame(rows)
            columns = [
                col for col in [
                    "PASAJERO_ID",
                    "NOMBRES",
                    "APELLIDO_PATERNO",
                    "APELLIDO_MATERNO",
                    "FECHA_NACIMIENTO",
                    "PASAPORTE",
                    "VENCIMIENTO_PASAPORTE",
                    "EMAIL",
                    "TELEFONO",
                ] if col in display.columns
            ]
            st.dataframe(display[columns], hide_index=True, use_container_width=True)

    with tab_new:
        create_passenger_widget(api, actor_name, "passenger_page")


def page_new_quote(api: EvaApi, actor_name: str, bootstrap: dict[str, Any]) -> None:
    st.subheader("Nueva cotización")
    st.caption("Captura solo lo necesario. Los vuelos, hoteles y servicios se agregan después como bloques.")

    try:
        passenger_rows = load_passengers(api.base_url, api.token)
    except EvaApiError as exc:
        st.error(str(exc))
        return

    passenger_map = {passenger_label(row): row for row in passenger_rows}
    currencies = [item.get("value") for item in bootstrap.get("listas", {}).get("MONEDA", [])]
    if not currencies:
        currencies = ["MXN", "USD", "CAD", "EUR", "GBP"]

    with st.form("new_quote_form", clear_on_submit=False):
        st.markdown("#### 1. Cliente y viaje")
        c1, c2 = st.columns(2)
        client_name = c1.text_input("Nombre del cliente *")
        destination = c2.text_input("Destino o resumen del viaje *", placeholder="Ej. Madrid y Barcelona")

        c3, c4 = st.columns(2)
        client_email = c3.text_input("Correo del cliente")
        client_phone = c4.text_input("Teléfono del cliente")

        c5, c6, c7 = st.columns(3)
        start_date = c5.date_input("Inicio del viaje", value=None)
        end_date = c6.date_input("Fin del viaje", value=None)
        currency = c7.selectbox("Moneda", currencies)

        st.markdown("#### 2. Pasajeros")
        selected_labels = st.multiselect(
            "Selecciona pasajeros ya registrados",
            options=list(passenger_map),
            placeholder="Busca y selecciona uno o varios pasajeros",
        )
        estimated_passengers = st.number_input(
            "Número estimado de pasajeros",
            min_value=1,
            value=max(len(selected_labels), 1),
            step=1,
            help="Úsalo cuando todavía no tengas todos los nombres.",
        )

        st.markdown("#### 3. Datos internos")
        c8, c9 = st.columns(2)
        advisor_name = c8.text_input("Asesor responsable *", value=actor_name)
        c9.selectbox("Vigencia sugerida", [2, 6, 12, 24, 48, 72], index=3)
        notes_client = st.text_area("Notas visibles para el cliente")
        notes_internal = st.text_area("Notas internas", help="No aparecerán en el PDF.")

        submitted = st.form_submit_button("Crear cotización", type="primary", use_container_width=True)

    if not submitted:
        with st.expander("¿El pasajero todavía no está registrado?"):
            create_passenger_widget(api, actor_name, "quick_passenger")
        return

    if not clean_text(client_name) or not clean_text(destination):
        st.warning("El nombre del cliente y el destino son obligatorios.")
        return
    if start_date and end_date and end_date < start_date:
        st.warning("La fecha final no puede ser anterior a la fecha inicial.")
        return

    quote_data = {
        "ASESOR_NOMBRE": clean_text(advisor_name or actor_name),
        "CLIENTE_NOMBRE": clean_text(client_name),
        "CLIENTE_EMAIL": clean_text(client_email),
        "CLIENTE_TELEFONO": clean_text(client_phone),
        "DESTINO_RESUMEN": clean_text(destination),
        "FECHA_INICIO_VIAJE": iso(start_date),
        "FECHA_FIN_VIAJE": iso(end_date),
        "NUM_PASAJEROS": int(estimated_passengers),
        "MONEDA": currency,
        "ESTATUS": "BORRADOR",
        "NOTAS_CLIENTE": clean_text(notes_client),
        "NOTAS_INTERNAS": clean_text(notes_internal),
    }

    try:
        created_quote = api.create_record("01_COTIZACIONES", quote_data, actor_name=advisor_name or actor_name)
        quote_id = str(created_quote.get("COTIZACION_ID", ""))

        for order, label in enumerate(selected_labels, start=1):
            passenger = passenger_map[label]
            api.create_record(
                "03B_COTIZACION_PASAJEROS",
                {
                    "COTIZACION_ID": quote_id,
                    "PASAJERO_ID": passenger.get("PASAJERO_ID"),
                    "ORDEN_PASAJERO": order,
                    "TIPO_PASAJERO": "ADULTO",
                    "PASAJERO_PRINCIPAL": "SI" if order == 1 else "NO",
                    "ACTIVO": "SI",
                },
                actor_name=advisor_name or actor_name,
            )
    except EvaApiError as exc:
        st.error(str(exc))
        return

    clear_app_cache()
    st.success(f"Cotización creada correctamente: {quote_id}")
    st.info("Ahora abre la sección Cotizaciones para agregar las opciones de vuelo.")


def catalog_maps(bootstrap: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    airlines = bootstrap.get("aerolineas", [])
    airports = bootstrap.get("aeropuertos", [])

    airline_map = {
        f"{row.get('IATA', '')} · {row.get('NOMBRE', '')}": row
        for row in airlines
        if row.get("IATA")
    }
    airport_map = {
        str(row.get("IATA", "")).upper(): row
        for row in airports
        if row.get("IATA")
    }
    return airline_map, airport_map


def render_flight_options(bundle: dict[str, Any], quote: dict[str, Any]) -> None:
    options = sorted(bundle.get("opciones", []), key=lambda row: integer(row.get("ORDEN"), 999))
    flights = bundle.get("vuelos", [])
    currency = str(quote.get("MONEDA") or "MXN")
    passenger_count = max(integer(quote.get("NUM_PASAJEROS"), 1), 1)

    if not options:
        st.info("Todavía no hay opciones de vuelo en esta cotización.")
        return

    for option in options:
        option_id = str(option.get("OPCION_ID", ""))
        option_flights = sorted(
            [row for row in flights if str(row.get("OPCION_ID", "")) == option_id],
            key=lambda row: integer(row.get("ORDEN_SEGMENTO"), 999),
        )
        total = number(option.get("TOTAL_ESTIMADO"), number(option.get("PRECIO_VENTA_ESTIMADO")))
        per_person = total / passenger_count if passenger_count else total
        recommended = str(option.get("RECOMENDADA", "")).upper() == "SI"

        with st.container(border=True):
            header_left, header_right = st.columns([3.2, 1.2], vertical_alignment="center")
            with header_left:
                badge = ' <span class="eva-badge">RECOMENDADA</span>' if recommended else ""
                st.markdown(
                    f"### {option.get('NOMBRE_OPCION', 'Opción de vuelo')}{badge}",
                    unsafe_allow_html=True,
                )
                if option.get("DESCRIPCION_CORTA"):
                    st.caption(str(option.get("DESCRIPCION_CORTA")))
            with header_right:
                st.metric("Total opción", money(total, currency))
                st.caption(f"Aprox. {money(per_person, currency)} por persona")

            if not option_flights:
                st.warning("Esta opción todavía no tiene vuelos registrados.")
                continue

            grouped: dict[str, list[dict[str, Any]]] = {}
            group_order: list[str] = []
            for flight in option_flights:
                group = str(flight.get("GRUPO_TRAMO") or flight.get("TIPO_TRAMO") or "TRAYECTO")
                if group not in grouped:
                    grouped[group] = []
                    group_order.append(group)
                grouped[group].append(flight)

            for group in group_order:
                group_flights = grouped[group]
                route_parts = [str(group_flights[0].get("ORIGEN_IATA", ""))]
                route_parts.extend(str(item.get("DESTINO_IATA", "")) for item in group_flights)
                scale_count = max(len(group_flights) - 1, 0)
                scale_label = "Directo" if scale_count == 0 else f"{scale_count} escala" + ("s" if scale_count > 1 else "")
                st.markdown(f"#### {group.replace('_', ' ').title()} · {' → '.join(route_parts)}")
                st.caption(scale_label)

                for idx, flight in enumerate(group_flights):
                    origin = str(flight.get("ORIGEN_IATA", ""))
                    destination = str(flight.get("DESTINO_IATA", ""))
                    airline = str(flight.get("AEROLINEA_IATA", ""))
                    flight_number = str(flight.get("NUMERO_VUELO", ""))
                    departure = str(flight.get("HORA_SALIDA", ""))[:5]
                    arrival = str(flight.get("HORA_LLEGADA", ""))[:5]
                    st.markdown(
                        f"""
                        <div class="eva-card">
                          <div class="eva-route">{origin} {departure} &nbsp;→&nbsp; {destination} {arrival}</div>
                          <div class="eva-subtle">{airline} {flight_number} · {flight.get('FECHA_SALIDA', '')}</div>
                          <div class="eva-subtle">Equipaje: {flight.get('EQUIPAJE', 'Sin especificar')}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if idx < len(group_flights) - 1:
                        next_flight = group_flights[idx + 1]
                        arrival_dt = parse_sheet_datetime(flight.get("FECHA_LLEGADA"), flight.get("HORA_LLEGADA"))
                        next_departure_dt = parse_sheet_datetime(
                            next_flight.get("FECHA_SALIDA"), next_flight.get("HORA_SALIDA")
                        )
                        layover_text = "Tiempo de conexión pendiente"
                        if arrival_dt and next_departure_dt and next_departure_dt >= arrival_dt:
                            layover_text = human_duration(int((next_departure_dt - arrival_dt).total_seconds() // 60))
                        st.info(f"Escala en {destination}: {layover_text}")


def create_flight_option_widget(
    api: EvaApi,
    actor_name: str,
    bootstrap: dict[str, Any],
    quote: dict[str, Any],
    bundle: dict[str, Any],
) -> None:
    quote_id = str(quote.get("COTIZACION_ID", ""))
    currency = str(quote.get("MONEDA") or "MXN")
    passenger_count = max(integer(quote.get("NUM_PASAJEROS"), 1), 1)
    airline_map, airport_map = catalog_maps(bootstrap)

    if not airline_map:
        st.warning("No hay aerolíneas activas en 10_CAT_AEROLINEAS.")
        return

    existing_options = bundle.get("opciones", [])
    default_name = f"Opción {len(existing_options) + 1}"
    trip_type = st.radio(
        "Tipo de viaje",
        ["Viaje sencillo", "Viaje redondo", "Multidestino"],
        horizontal=True,
        key=f"trip_type_{quote_id}",
    )

    if trip_type == "Viaje sencillo":
        journey_labels = ["IDA"]
    elif trip_type == "Viaje redondo":
        journey_labels = ["IDA", "REGRESO"]
    else:
        journey_count = st.number_input(
            "Número de trayectos",
            min_value=2,
            max_value=8,
            value=3,
            step=1,
            key=f"journey_count_{quote_id}",
            help="Cada trayecto representa un destino real, no una escala.",
        )
        journey_labels = [f"TRAYECTO_{idx + 1}" for idx in range(int(journey_count))]

    stop_counts: dict[str, int] = {}
    st.markdown("#### Escalas por trayecto")
    for label in journey_labels:
        friendly = label.replace("_", " ").title()
        col_check, col_count = st.columns([2.4, 1])
        has_stops = col_check.checkbox(
            f"{friendly}: incluye escala(s)",
            key=f"has_stops_{quote_id}_{label}",
        )
        if has_stops:
            stop_counts[label] = int(
                col_count.number_input(
                    "Número de escalas",
                    min_value=1,
                    max_value=4,
                    value=1,
                    step=1,
                    key=f"stop_count_{quote_id}_{label}",
                    label_visibility="visible",
                )
            )
        else:
            stop_counts[label] = 0

    airline_labels = list(airline_map)
    airport_label_map = {
        " · ".join(
            part
            for part in [
                str(row.get("IATA", "")).upper(),
                str(row.get("CIUDAD", "")).strip(),
                str(row.get("PAIS", "")).strip(),
                str(row.get("NOMBRE_AEROPUERTO", "")).strip(),
            ]
            if part
        ): row
        for row in airport_map.values()
    }
    airport_labels = sorted(airport_label_map, key=lambda item: item.lower())

    if not airport_labels:
        st.warning("No hay aeropuertos activos en 11_CAT_AEROPUERTOS.")
        return

    with st.form(f"flight_option_form_{quote_id}", clear_on_submit=False):
        st.markdown("#### Datos de la opción")
        c1, c2 = st.columns([2.4, 1])
        option_name = c1.text_input("Nombre de la opción *", value=default_name, placeholder="Ej. Aeroméxico con escala")
        recommended = c2.checkbox("Marcar como recomendada")
        description = st.text_input(
            "Descripción breve",
            placeholder="Ej. Mejor horario y equipaje documentado incluido",
        )

        c3, c4 = st.columns(2)
        price_per_person = c3.number_input(
            f"Precio de venta por persona ({currency}) *",
            min_value=0.0,
            value=0.0,
            step=100.0,
            format="%.2f",
        )
        displayed_passengers = c4.number_input(
            "Pasajeros considerados",
            min_value=1,
            value=passenger_count,
            step=1,
        )

        with st.expander("Costos internos y ajustes opcionales"):
            c5, c6, c7 = st.columns(3)
            cost_per_person = c5.number_input(
                f"Costo estimado por persona ({currency})",
                min_value=0.0,
                value=0.0,
                step=100.0,
                format="%.2f",
            )
            extra_taxes = c6.number_input(
                f"Impuestos adicionales totales ({currency})",
                min_value=0.0,
                value=0.0,
                step=100.0,
                format="%.2f",
            )
            service_fee = c7.number_input(
                f"Tarifa de servicio total ({currency})",
                min_value=0.0,
                value=0.0,
                step=100.0,
                format="%.2f",
            )
            internal_notes = st.text_area("Notas internas de la opción")

        st.markdown("#### Vuelos")
        journeys: list[dict[str, Any]] = []
        for journey_index, label in enumerate(journey_labels, start=1):
            segment_total = stop_counts[label] + 1
            friendly = label.replace("_", " ").title()
            st.markdown(f"### {friendly}")
            st.caption(
                "Directo" if stop_counts[label] == 0 else f"{stop_counts[label]} escala" + ("s" if stop_counts[label] > 1 else "")
            )
            journey_segments: list[dict[str, Any]] = []
            for segment_index in range(segment_total):
                with st.expander(
                    f"Vuelo {segment_index + 1} de {segment_total} · {friendly}",
                    expanded=True,
                ):
                    a, b = st.columns([1.45, 1])
                    airline_label = a.selectbox(
                        "Aerolínea *",
                        airline_labels,
                        key=f"airline_{quote_id}_{label}_{segment_index}",
                    )
                    flight_number = b.text_input(
                        "Número de vuelo",
                        key=f"flight_number_{quote_id}_{label}_{segment_index}",
                        placeholder="Ej. AM 001",
                    )

                    d, e, f, g = st.columns(4)
                    origin_label = d.selectbox(
                        "Origen *",
                        airport_labels,
                        index=None,
                        key=f"origin_{quote_id}_{label}_{segment_index}",
                        placeholder="Escribe ciudad, aeropuerto o IATA",
                        help="Puedes buscar por código IATA, ciudad, país o nombre del aeropuerto.",
                    )
                    destination_label = e.selectbox(
                        "Destino *",
                        airport_labels,
                        index=None,
                        key=f"destination_{quote_id}_{label}_{segment_index}",
                        placeholder="Escribe ciudad, aeropuerto o IATA",
                        help="Puedes buscar por código IATA, ciudad, país o nombre del aeropuerto.",
                    )

                    departure_date = f.date_input(
                        "Fecha de salida *",
                        value=None,
                        key=f"departure_date_{quote_id}_{label}_{segment_index}",
                    )
                    departure_time = g.time_input(
                        "Hora de salida",
                        value=time(8, 0),
                        key=f"departure_time_{quote_id}_{label}_{segment_index}",
                    )

                    h, i = st.columns(2)

                    arrival_date = h.date_input(
                        "Fecha de llegada *",
                        value=None,
                        key=f"arrival_date_{quote_id}_{label}_{segment_index}",
                    )
                    arrival_time = i.time_input(
                        "Hora de llegada",
                        value=time(12, 0),
                        key=f"arrival_time_{quote_id}_{label}_{segment_index}",
                    )

                    st.caption("Tarifa y equipaje")
                    k, l, m = st.columns(3)
                    cabin = k.selectbox(
                        "Cabina",
                        ["TURISTA", "TURISTA_PREMIUM", "BUSINESS", "PRIMERA", ""],
                        key=f"cabin_{quote_id}_{label}_{segment_index}",
                    )
                    fare = l.text_input(
                        "Tarifa",
                        key=f"fare_{quote_id}_{label}_{segment_index}",
                        placeholder="Ej. Light / Classic",
                    )
                    baggage = m.text_input(
                        "Equipaje incluido",
                        key=f"baggage_{quote_id}_{label}_{segment_index}",
                        placeholder="Ej. 1 maleta de 23 kg",
                    )

                    if segment_index < segment_total - 1:
                        st.caption(
                            "La llegada de este vuelo y la salida del siguiente definirán automáticamente "
                            "el lugar y tiempo de la escala."
                        )

                    origin_airport = airport_label_map.get(origin_label, {}) if origin_label else {}
                    destination_airport = airport_label_map.get(destination_label, {}) if destination_label else {}

                    journey_segments.append(
                        {
                            "airline_label": airline_label,
                            "flight_number": flight_number,
                            "origin_iata": str(origin_airport.get("IATA", "")).upper(),
                            "destination_iata": str(destination_airport.get("IATA", "")).upper(),
                            "departure_date": departure_date,
                            "arrival_date": arrival_date,
                            "departure_time": departure_time,
                            "arrival_time": arrival_time,
                            "cabin": cabin,
                            "fare": fare,
                            "baggage": baggage,
                        }
                    )
            journeys.append({"label": label, "segments": journey_segments})

        visible_notes = st.text_area(
            "Observaciones visibles para el cliente",
            placeholder="Ej. Horarios sujetos a cambios por la aerolínea.",
        )
        submitted = st.form_submit_button(
            "Guardar opción de vuelo",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return

    if not clean_text(option_name):
        st.warning("El nombre de la opción es obligatorio.")
        return
    if price_per_person <= 0:
        st.warning("Captura un precio de venta por persona mayor a cero.")
        return

    for journey in journeys:
        for idx, segment in enumerate(journey["segments"], start=1):
            if not clean_text(segment["origin_iata"]) or not clean_text(segment["destination_iata"]):
                st.warning(f"Completa origen y destino del vuelo {idx} en {journey['label']}.")
                return
            if not segment["departure_date"] or not segment["arrival_date"]:
                st.warning(f"Completa las fechas del vuelo {idx} en {journey['label']}.")
                return
            if segment["arrival_date"] < segment["departure_date"]:
                st.warning(f"La llegada del vuelo {idx} en {journey['label']} no puede ser anterior a la salida.")
                return
        for idx in range(len(journey["segments"]) - 1):
            current = journey["segments"][idx]
            following = journey["segments"][idx + 1]
            if clean_text(current["destination_iata"]).upper() != clean_text(following["origin_iata"]).upper():
                st.warning(
                    f"En {journey['label']}, el destino del vuelo {idx + 1} debe coincidir "
                    f"con el origen del vuelo {idx + 2}."
                )
                return
            arrival_dt = datetime.combine(current["arrival_date"], current["arrival_time"])
            next_departure_dt = datetime.combine(following["departure_date"], following["departure_time"])
            if next_departure_dt < arrival_dt:
                st.warning(f"En {journey['label']}, la salida posterior a la escala ocurre antes de la llegada.")
                return

    option_total_base = float(price_per_person) * int(displayed_passengers)
    estimated_cost = float(cost_per_person) * int(displayed_passengers)
    option_data = {
        "COTIZACION_ID": quote_id,
        "ORDEN": len(existing_options) + 1,
        "NOMBRE_OPCION": clean_text(option_name),
        "DESCRIPCION_CORTA": clean_text(description),
        "RECOMENDADA": "SI" if recommended else "NO",
        "ESTATUS_OPCION": "ACTIVA",
        "MONEDA": currency,
        "COSTO_ESTIMADO": estimated_cost if estimated_cost else "",
        "PRECIO_VENTA_ESTIMADO": option_total_base,
        "IMPUESTOS_ESTIMADOS": float(extra_taxes) if extra_taxes else "",
        "TARIFA_SERVICIO_ESTIMADA": float(service_fee) if service_fee else "",
        "SELECCIONADA_CLIENTE": "NO",
        "OBSERVACIONES_CLIENTE": clean_text(visible_notes),
        "OBSERVACIONES_INTERNAS": clean_text(internal_notes),
        "ACTIVA": "SI",
    }

    try:
        created_option = api.create_record("02_OPCIONES", option_data, actor_name=actor_name)
        option_id = str(created_option.get("OPCION_ID", ""))
        overall_order = 0

        for journey in journeys:
            segments = journey["segments"]
            scale_airports = [clean_text(item["destination_iata"]).upper() for item in segments[:-1]]
            if trip_type == "Viaje sencillo":
                segment_type = "IDA"
            elif trip_type == "Viaje redondo":
                segment_type = journey["label"]
            else:
                segment_type = "INTERNO"

            for idx, segment in enumerate(segments):
                overall_order += 1
                airline = airline_map[segment["airline_label"]]
                origin_iata = clean_text(segment["origin_iata"]).upper()
                destination_iata = clean_text(segment["destination_iata"]).upper()
                origin_city = airport_map.get(origin_iata, {}).get("CIUDAD", "")
                destination_city = airport_map.get(destination_iata, {}).get("CIUDAD", "")

                api.create_record(
                    "04_VUELOS",
                    {
                        "COTIZACION_ID": quote_id,
                        "OPCION_ID": option_id,
                        "TIPO_TRAMO": segment_type,
                        "GRUPO_TRAMO": journey["label"],
                        "ORDEN_SEGMENTO": overall_order,
                        "AEROLINEA_IATA": str(airline.get("IATA", "")),
                        "NUMERO_VUELO": clean_text(segment["flight_number"]).upper(),
                        "ORIGEN_IATA": origin_iata,
                        "ORIGEN_CIUDAD": origin_city,
                        "DESTINO_IATA": destination_iata,
                        "DESTINO_CIUDAD": destination_city,
                        "FECHA_SALIDA": iso(segment["departure_date"]),
                        "HORA_SALIDA": time_text(segment["departure_time"]),
                        "FECHA_LLEGADA": iso(segment["arrival_date"]),
                        "HORA_LLEGADA": time_text(segment["arrival_time"]),
                        "NUM_ESCALAS": max(len(segments) - 1, 0) if idx == 0 else 0,
                        "ESCALAS_IATA": ",".join(scale_airports) if idx == 0 else "",
                        "CABINA": segment["cabin"],
                        "TARIFA": clean_text(segment["fare"]),
                        "EQUIPAJE": clean_text(segment["baggage"]),
                        "REEMBOLSABLE": "NO",
                        "CAMBIOS_PERMITIDOS": "NO",
                        "PROVEEDOR_ID": "",
                        "CANTIDAD_PASAJEROS": int(displayed_passengers),
                        "MONEDA": currency,
                        "IMPUESTOS_INCLUIDOS": "SI",
                        "OBSERVACIONES_CLIENTE": clean_text(visible_notes),
                        "ACTIVO": "SI",
                    },
                    actor_name=actor_name,
                )

        if recommended:
            try:
                api.update_record(
                    "01_COTIZACIONES",
                    quote_id,
                    {"OPCION_RECOMENDADA_ID": option_id},
                    id_field="COTIZACION_ID",
                )
            except EvaApiError:
                pass

    except EvaApiError as exc:
        st.error(
            f"No se pudo terminar de guardar la opción: {exc}. "
            "Revisa 02_OPCIONES y 04_VUELOS antes de volver a intentarlo."
        )
        return

    clear_app_cache()
    st.session_state["eva_flash"] = f"Opción de vuelo guardada: {option_id}"
    st.rerun()


def render_hotels(bundle: dict[str, Any], quote: dict[str, Any]) -> None:
    hotels = bundle.get("hospedajes", [])
    currency = str(quote.get("MONEDA") or "MXN")
    if not hotels:
        st.info("Todavía no hay hospedajes registrados en esta cotización.")
        return

    for hotel in hotels:
        with st.container(border=True):
            image_url = str(hotel.get("IMAGEN_URL") or "").strip()
            info_col, price_col = st.columns([3.2, 1.15], vertical_alignment="top")
            with info_col:
                if image_url:
                    image_col, text_col = st.columns([1.15, 2.35], vertical_alignment="top")
                    with image_col:
                        try:
                            st.image(image_url, use_container_width=True)
                        except Exception:
                            st.caption("No fue posible cargar la fotografía.")
                    target_col = text_col
                else:
                    target_col = st.container()

                with target_col:
                    st.markdown(f"### {hotel.get('HOTEL_NOMBRE', 'Hospedaje')}")
                    location = ", ".join(
                        item for item in [str(hotel.get("CIUDAD") or ""), str(hotel.get("PAIS") or "")] if item
                    )
                    if location:
                        st.caption(location)
                    if hotel.get("DIRECCION"):
                        st.write(str(hotel.get("DIRECCION")))
                    st.write(
                        f"**Estancia:** {hotel.get('CHECKIN', '')} → {hotel.get('CHECKOUT', '')} "
                        f"· {hotel.get('NOCHES', '') or '—'} noches"
                    )
                    st.write(
                        f"**Habitación:** {hotel.get('TIPO_HABITACION', 'Sin especificar')} "
                        f"· {hotel.get('OCUPACION', 'Ocupación pendiente')}"
                    )
                    if hotel.get("PLAN_ALIMENTOS"):
                        st.write(f"**Plan de alimentos:** {hotel.get('PLAN_ALIMENTOS')}")
            with price_col:
                st.metric("Precio total", money(hotel.get("PRECIO_VENTA_TOTAL"), currency))
                st.caption(f"{hotel.get('NUM_HABITACIONES', 1)} habitación(es)")

            map_url = str(hotel.get("MAPA_URL") or "").strip()
            if map_url:
                with st.expander("Ver ubicación del hotel"):
                    show_simple_map(map_url)


def create_hotel_widget(
    api: EvaApi,
    actor_name: str,
    quote: dict[str, Any],
    bundle: dict[str, Any],
) -> None:
    quote_id = str(quote.get("COTIZACION_ID", ""))
    currency = str(quote.get("MONEDA") or "MXN")
    options = sorted(bundle.get("opciones", []), key=lambda row: integer(row.get("ORDEN"), 999))
    option_choices = {"Todas las opciones de la cotización": "GLOBAL"}
    for option in options:
        option_choices[f"{option.get('NOMBRE_OPCION', 'Opción')} · {option.get('OPCION_ID', '')}"] = str(
            option.get("OPCION_ID", "")
        )

    key_prefix = f"hotel_{quote_id}"
    applies_label = st.selectbox(
        "¿A qué opción aplica?",
        list(option_choices),
        key=f"{key_prefix}_applies",
    )

    c1, c2, c3 = st.columns([2.1, 1.2, 1.2])
    hotel_name = c1.text_input("Nombre del hotel *", key=f"{key_prefix}_name")
    city = c2.text_input("Ciudad *", key=f"{key_prefix}_city")
    country = c3.text_input("País", key=f"{key_prefix}_country")
    address = st.text_input(
        "Dirección del hotel",
        key=f"{key_prefix}_address",
        placeholder="Ej. Calle, número, colonia o zona",
    )

    c4, c5 = st.columns(2)
    image_url = c4.text_input(
        "URL de la fotografía",
        key=f"{key_prefix}_image",
        placeholder="https://...",
    )
    map_url = c5.text_input(
        "URL de Google Maps",
        key=f"{key_prefix}_map",
        placeholder="Pega el vínculo de Compartir → Copiar vínculo",
    )

    if image_url:
        if is_http_url(image_url):
            try:
                st.image(image_url, caption="Vista previa de la fotografía", width=360)
            except Exception:
                st.caption("La fotografía se guardará, aunque la vista previa no pudo cargarse.")
        else:
            st.warning("La URL de la fotografía debe comenzar con http:// o https://")

    if map_url:
        if is_http_url(map_url):
            with st.expander("Vista previa de la ubicación", expanded=True):
                show_simple_map(map_url)
        else:
            st.warning("La URL de Google Maps debe comenzar con http:// o https://")

    c6, c7 = st.columns(2)
    checkin = c6.date_input("Check-in *", value=None, key=f"{key_prefix}_checkin")
    checkout = c7.date_input("Check-out *", value=None, key=f"{key_prefix}_checkout")

    c8, c9, c10 = st.columns([1.7, 1.2, 1])
    room_type = c8.text_input("Tipo de habitación", key=f"{key_prefix}_room")
    occupancy = c9.text_input("Ocupación", key=f"{key_prefix}_occupancy", placeholder="Ej. 2 adultos")
    room_count = c10.number_input(
        "Habitaciones",
        min_value=1,
        value=1,
        step=1,
        key=f"{key_prefix}_room_count",
    )

    meal_plan = st.text_input(
        "Plan de alimentos",
        key=f"{key_prefix}_meal",
        placeholder="Ej. Desayuno incluido / Solo alojamiento",
    )
    cancellation = st.text_area(
        "Política de cancelación",
        key=f"{key_prefix}_cancellation",
        placeholder="Resume la política que debe conocer el cliente.",
    )

    c11, c12 = st.columns([1.4, 1])
    price_total = c11.number_input(
        f"Precio total al cliente ({currency}) *",
        min_value=0.0,
        value=0.0,
        step=100.0,
        format="%.2f",
        key=f"{key_prefix}_price",
    )
    taxes_included = c12.checkbox("Impuestos incluidos", value=True, key=f"{key_prefix}_taxes")

    visible_notes = st.text_area(
        "Observaciones visibles para el cliente",
        key=f"{key_prefix}_visible_notes",
    )
    with st.expander("Notas internas"):
        internal_notes = st.text_area("Notas internas del hospedaje", key=f"{key_prefix}_internal_notes")

    submitted = st.button(
        "Guardar hospedaje",
        type="primary",
        use_container_width=True,
        key=f"{key_prefix}_submit",
    )
    if not submitted:
        return

    if not clean_text(hotel_name) or not clean_text(city):
        st.warning("El nombre del hotel y la ciudad son obligatorios.")
        return
    if not checkin or not checkout:
        st.warning("Captura check-in y check-out.")
        return
    if checkout <= checkin:
        st.warning("El check-out debe ser posterior al check-in.")
        return
    if price_total <= 0:
        st.warning("Captura un precio total mayor a cero.")
        return
    if image_url and not is_http_url(image_url):
        st.warning("Corrige la URL de la fotografía.")
        return
    if map_url and not is_http_url(map_url):
        st.warning("Corrige la URL de Google Maps.")
        return

    hotel_data = {
        "COTIZACION_ID": quote_id,
        "OPCION_ID": option_choices[applies_label],
        "HOTEL_NOMBRE": clean_text(hotel_name),
        "CIUDAD": clean_text(city),
        "PAIS": clean_text(country),
        "DIRECCION": clean_text(address),
        "CHECKIN": iso(checkin),
        "CHECKOUT": iso(checkout),
        "TIPO_HABITACION": clean_text(room_type),
        "OCUPACION": clean_text(occupancy),
        "NUM_HABITACIONES": int(room_count),
        "PLAN_ALIMENTOS": clean_text(meal_plan),
        "POLITICA_CANCELACION": clean_text(cancellation),
        "PROVEEDOR_ID": "",
        "IMAGEN_URL": str(image_url or "").strip(),
        "MAPA_URL": str(map_url or "").strip(),
        "MONEDA": currency,
        "PRECIO_VENTA_TOTAL": float(price_total),
        "IMPUESTOS_INCLUIDOS": "SI" if taxes_included else "NO",
        "OBSERVACIONES_CLIENTE": clean_text(visible_notes),
        "OBSERVACIONES_INTERNAS": clean_text(internal_notes),
        "ACTIVO": "SI",
    }

    try:
        created = api.create_record("05_HOSPEDAJES", hotel_data, actor_name=actor_name)
    except EvaApiError as exc:
        st.error(str(exc))
        return

    clear_app_cache()
    st.session_state["eva_flash"] = f"Hospedaje guardado: {created.get('HOSPEDAJE_ITEM_ID', '')}"
    st.rerun()


def page_quotes(api: EvaApi, actor_name: str, bootstrap: dict[str, Any]) -> None:
    st.subheader("Cotizaciones")
    show_flash()
    query = st.text_input("Buscar por folio, cliente, destino o estatus")
    try:
        rows = load_quotes(api.base_url, api.token, query)
    except EvaApiError as exc:
        st.error(str(exc))
        return

    if not rows:
        st.info("No se encontraron cotizaciones.")
        return

    quote_map = {
        f"{row.get('COTIZACION_ID', '')} · {row.get('CLIENTE_NOMBRE', 'Sin cliente')}": row
        for row in rows
    }
    default_index = 0
    selected_label = st.selectbox("Abrir cotización", list(quote_map), index=default_index)
    selected = quote_map[selected_label]
    quote_id = str(selected.get("COTIZACION_ID", ""))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Folio", quote_id)
    c2.metric("Estatus", selected.get("ESTATUS", ""))
    c3.metric("Pasajeros", selected.get("NUM_PASAJEROS", ""))
    c4.metric("Moneda", selected.get("MONEDA", ""))

    try:
        bundle = load_quote_bundle(api.base_url, api.token, quote_id)
    except EvaApiError as exc:
        st.error(str(exc))
        return

    tab_summary, tab_flights, tab_hotels, tab_services = st.tabs(
        ["Resumen", "Opciones de vuelo", "Hospedajes", "Servicios adicionales"]
    )

    with tab_summary:
        left, right = st.columns(2)
        with left:
            st.markdown("#### Datos generales")
            st.write(f"**Cliente:** {selected.get('CLIENTE_NOMBRE', '')}")
            st.write(f"**Destino:** {selected.get('DESTINO_RESUMEN', '')}")
            st.write(f"**Asesor:** {selected.get('ASESOR_NOMBRE', '')}")
            st.write("**Contacto:** travel@proyectoeva.mx")
        with right:
            st.markdown("#### Contenido")
            st.write(f"**Pasajeros relacionados:** {len(bundle.get('pasajeros', []))}")
            st.write(f"**Opciones:** {len(bundle.get('opciones', []))}")
            st.write(f"**Vuelos:** {len(bundle.get('vuelos', []))}")
            st.write(f"**Hospedajes:** {len(bundle.get('hospedajes', []))}")
            st.write(f"**Servicios:** {len(bundle.get('servicios', []))}")

        if bundle.get("pasajeros"):
            st.markdown("#### Pasajeros")
            for passenger in bundle.get("pasajeros", []):
                st.write(f"• {passenger_label(passenger)}")

        with st.expander("Ver registro completo"):
            st.json(bundle)

    with tab_flights:
        st.markdown("### Opciones guardadas")
        render_flight_options(bundle, selected)
        st.divider()
        with st.expander("+ Agregar otra opción de vuelo", expanded=not bool(bundle.get("opciones"))):
            create_flight_option_widget(api, actor_name, bootstrap, selected, bundle)

    with tab_hotels:
        st.markdown("### Hospedajes guardados")
        render_hotels(bundle, selected)
        st.divider()
        with st.expander("+ Agregar hospedaje", expanded=not bool(bundle.get("hospedajes"))):
            create_hotel_widget(api, actor_name, selected, bundle)

    with tab_services:
        st.info("Después agregaremos traslados, seguros, equipaje, tours y otros servicios como bloques sencillos.")


def main() -> None:
    api = get_api()
    show_header()

    try:
        bootstrap = load_bootstrap(api.base_url, api.token)
        health = api.health()
    except EvaApiError as exc:
        st.error(str(exc))
        st.stop()

    users = bootstrap.get("usuarios", [])
    active_names = [str(user.get("NOMBRE", "")).strip() for user in users if user.get("NOMBRE")]
    default_actor = active_names[0] if active_names else "Equipo EVA"

    with st.sidebar:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), use_container_width=True)
        st.success(f"Conectado · API {health.get('version', '')}")
        actor_name = st.selectbox(
            "Trabajando como",
            active_names or [default_actor],
        )
        page = st.radio(
            "Menú",
            ["Inicio", "Nueva cotización", "Pasajeros", "Cotizaciones"],
        )
        if st.button("Sincronizar con Google Sheets", use_container_width=True):
            clear_app_cache()
            st.rerun()
        st.caption("Contacto institucional: travel@proyectoeva.mx")

    if page == "Inicio":
        page_home(api)
    elif page == "Nueva cotización":
        page_new_quote(api, actor_name, bootstrap)
    elif page == "Pasajeros":
        page_passengers(api, actor_name)
    else:
        page_quotes(api, actor_name, bootstrap)


if __name__ == "__main__":
    main()
