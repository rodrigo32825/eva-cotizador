from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from eva_api import EvaApi, EvaApiError


APP_DIR = Path(__file__).resolve().parent
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


def clear_app_cache() -> None:
    load_quotes.clear()
    load_passengers.clear()
    load_bootstrap.clear()


def iso(value: date | None) -> str:
    return value.isoformat() if value else ""


def clean_text(value: str) -> str:
    return " ".join(str(value or "").strip().split())


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
    st.caption("Captura solo lo necesario. Los vuelos, hoteles y servicios se agregarán después como bloques.")

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
        validity_hours = c9.selectbox("Vigencia sugerida", [2, 6, 12, 24, 48, 72], index=3)
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
    st.info(
        "En la siguiente versión agregaremos las tarjetas de vuelos, hoteles y servicios "
        "dentro de esta misma cotización."
    )


def page_quotes(api: EvaApi) -> None:
    st.subheader("Cotizaciones")
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
    selected_label = st.selectbox("Abrir cotización", list(quote_map))
    selected = quote_map[selected_label]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Folio", selected.get("COTIZACION_ID", ""))
    c2.metric("Estatus", selected.get("ESTATUS", ""))
    c3.metric("Pasajeros", selected.get("NUM_PASAJEROS", ""))
    c4.metric("Moneda", selected.get("MONEDA", ""))

    try:
        bundle = api.quote_bundle(str(selected.get("COTIZACION_ID", "")))
    except EvaApiError as exc:
        st.error(str(exc))
        return

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

    with st.expander("Ver registro completo"):
        st.json(bundle)


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
        page_quotes(api)


if __name__ == "__main__":
    main()
