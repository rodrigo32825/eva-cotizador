from __future__ import annotations

from datetime import date, time
from pathlib import Path
from typing import Any

import pandas as pd
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


def catalog_maps(bootstrap: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    airlines = bootstrap.get("aerolineas", [])
    airports = bootstrap.get("aeropuertos", [])
    providers = bootstrap.get("proveedores", [])

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
    provider_map = {
        f"{row.get('NOMBRE_COMERCIAL', '')} · {row.get('PROVEEDOR_ID', '')}": row
        for row in providers
        if row.get("PROVEEDOR_ID")
    }
    return airline_map, airport_map, provider_map


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
                st.warning("Esta opción todavía no tiene segmentos registrados.")
                continue

            for flight in option_flights:
                origin = str(flight.get("ORIGEN_IATA", ""))
                destination = str(flight.get("DESTINO_IATA", ""))
                airline = str(flight.get("AEROLINEA_IATA", ""))
                flight_number = str(flight.get("NUMERO_VUELO", ""))
                departure = str(flight.get("HORA_SALIDA", ""))[:5]
                arrival = str(flight.get("HORA_LLEGADA", ""))[:5]
                segment_type = str(flight.get("TIPO_TRAMO", ""))
                st.markdown(
                    f"""
                    <div class="eva-card">
                      <div class="eva-route">{origin} {departure} &nbsp;→&nbsp; {destination} {arrival}</div>
                      <div class="eva-subtle">{airline} {flight_number} · {flight.get('FECHA_SALIDA', '')} · {segment_type}</div>
                      <div class="eva-subtle">Equipaje: {flight.get('EQUIPAJE', 'Sin especificar')} · Proveedor: {flight.get('PROVEEDOR_ID', 'Sin especificar')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


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
    airline_map, airport_map, provider_map = catalog_maps(bootstrap)

    if not airline_map:
        st.warning("No hay aerolíneas activas en 10_CAT_AEROLINEAS.")
        return
    if not provider_map:
        st.warning("No hay proveedores activos en 12_CAT_PROVEEDORES.")
        return

    existing_options = bundle.get("opciones", [])
    default_name = f"Opción {len(existing_options) + 1}"
    segment_count = st.number_input(
        "¿Cuántos segmentos tiene esta opción?",
        min_value=1,
        max_value=8,
        value=2,
        step=1,
        key=f"segment_count_{quote_id}",
        help="Ejemplo: ida y regreso directos = 2 segmentos. Una conexión agrega otro segmento.",
    )

    airline_labels = list(airline_map)
    provider_labels = list(provider_map)

    with st.form(f"flight_option_form_{quote_id}", clear_on_submit=False):
        st.markdown("#### Datos de la opción")
        c1, c2 = st.columns([2.4, 1])
        option_name = c1.text_input("Nombre de la opción *", value=default_name, placeholder="Ej. Aeroméxico directo")
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

        st.markdown("#### Segmentos")
        segments: list[dict[str, Any]] = []
        for idx in range(int(segment_count)):
            with st.expander(f"Segmento {idx + 1}", expanded=True):
                a, b, c = st.columns([1.35, 1, 1])
                airline_label = a.selectbox(
                    "Aerolínea *",
                    airline_labels,
                    key=f"airline_{quote_id}_{idx}",
                )
                flight_number = b.text_input(
                    "Número de vuelo",
                    key=f"flight_number_{quote_id}_{idx}",
                    placeholder="Ej. AM 001",
                )
                default_type = "IDA" if idx < max(int(segment_count) - 1, 1) else "REGRESO"
                segment_type = c.selectbox(
                    "Tipo de tramo",
                    ["IDA", "REGRESO", "INTERNO"],
                    index=["IDA", "REGRESO", "INTERNO"].index(default_type),
                    key=f"segment_type_{quote_id}_{idx}",
                )

                d, e, f, g = st.columns(4)
                origin_iata = d.text_input(
                    "Origen IATA *",
                    key=f"origin_{quote_id}_{idx}",
                    max_chars=3,
                    placeholder="MEX",
                )
                destination_iata = e.text_input(
                    "Destino IATA *",
                    key=f"destination_{quote_id}_{idx}",
                    max_chars=3,
                    placeholder="MAD",
                )
                departure_date = f.date_input(
                    "Fecha de salida *",
                    value=None,
                    key=f"departure_date_{quote_id}_{idx}",
                )
                arrival_date = g.date_input(
                    "Fecha de llegada *",
                    value=None,
                    key=f"arrival_date_{quote_id}_{idx}",
                )

                h, i, j = st.columns([1, 1, 1.45])
                departure_time = h.time_input(
                    "Hora de salida",
                    value=time(8, 0),
                    key=f"departure_time_{quote_id}_{idx}",
                )
                arrival_time = i.time_input(
                    "Hora de llegada",
                    value=time(12, 0),
                    key=f"arrival_time_{quote_id}_{idx}",
                )
                provider_label = j.selectbox(
                    "Proveedor de compra *",
                    provider_labels,
                    key=f"provider_{quote_id}_{idx}",
                )

                k, l, m = st.columns(3)
                cabin = k.selectbox(
                    "Cabina",
                    ["TURISTA", "TURISTA_PREMIUM", "BUSINESS", "PRIMERA", ""],
                    key=f"cabin_{quote_id}_{idx}",
                )
                fare = l.text_input(
                    "Tarifa",
                    key=f"fare_{quote_id}_{idx}",
                    placeholder="Ej. Light / Classic",
                )
                baggage = m.text_input(
                    "Equipaje incluido",
                    key=f"baggage_{quote_id}_{idx}",
                    placeholder="Ej. 1 maleta de 23 kg",
                )

                segments.append(
                    {
                        "airline_label": airline_label,
                        "flight_number": flight_number,
                        "segment_type": segment_type,
                        "origin_iata": origin_iata,
                        "destination_iata": destination_iata,
                        "departure_date": departure_date,
                        "arrival_date": arrival_date,
                        "departure_time": departure_time,
                        "arrival_time": arrival_time,
                        "provider_label": provider_label,
                        "cabin": cabin,
                        "fare": fare,
                        "baggage": baggage,
                    }
                )

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

    for idx, segment in enumerate(segments, start=1):
        if not clean_text(segment["origin_iata"]) or not clean_text(segment["destination_iata"]):
            st.warning(f"Completa origen y destino del segmento {idx}.")
            return
        if not segment["departure_date"] or not segment["arrival_date"]:
            st.warning(f"Completa las fechas del segmento {idx}.")
            return
        if segment["arrival_date"] < segment["departure_date"]:
            st.warning(f"La llegada del segmento {idx} no puede ser anterior a la salida.")
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

        for idx, segment in enumerate(segments, start=1):
            airline = airline_map[segment["airline_label"]]
            provider = provider_map[segment["provider_label"]]
            origin_iata = clean_text(segment["origin_iata"]).upper()
            destination_iata = clean_text(segment["destination_iata"]).upper()
            origin_city = airport_map.get(origin_iata, {}).get("CIUDAD", "")
            destination_city = airport_map.get(destination_iata, {}).get("CIUDAD", "")

            api.create_record(
                "04_VUELOS",
                {
                    "COTIZACION_ID": quote_id,
                    "OPCION_ID": option_id,
                    "TIPO_TRAMO": segment["segment_type"],
                    "GRUPO_TRAMO": segment["segment_type"],
                    "ORDEN_SEGMENTO": idx,
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
                    "NUM_ESCALAS": max(int(segment_count) - 1, 0) if idx == 1 else 0,
                    "ESCALAS_IATA": "",
                    "CABINA": segment["cabin"],
                    "TARIFA": clean_text(segment["fare"]),
                    "EQUIPAJE": clean_text(segment["baggage"]),
                    "REEMBOLSABLE": "NO",
                    "CAMBIOS_PERMITIDOS": "NO",
                    "PROVEEDOR_ID": str(provider.get("PROVEEDOR_ID", "")),
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
        st.info("El módulo de hospedajes será el siguiente. Usará la misma lógica: tarjetas y varias alternativas.")

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
