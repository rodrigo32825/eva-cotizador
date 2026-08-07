from __future__ import annotations

from datetime import time
from typing import Any

import streamlit as st


st.set_page_config(
    page_title="SIVE · Proyecto EVA",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      :root {
        --eva-text: #2f3437;
        --eva-muted: #737b80;
        --eva-accent: #2f9fa3;
        --eva-soft: #f1f8f8;
        --eva-border: #d7e3e3;
      }
      .block-container {max-width: 1080px; padding-top: 1.2rem; padding-bottom: 7rem;}
      .sive-header {border: 1px solid var(--eva-border); background: var(--eva-soft); border-radius: 24px; padding: 1.4rem 1.5rem; margin-bottom: 1.2rem;}
      .sive-kicker {color: var(--eva-accent); font-weight: 700; letter-spacing: .14em; text-transform: uppercase; font-size: .78rem;}
      .sive-title {color: var(--eva-text); font-size: clamp(1.8rem, 4vw, 2.5rem); font-weight: 500; margin-top: .2rem;}
      .sive-subtitle {color: var(--eva-muted); margin-top: .2rem;}
      .sive-card {border: 1px solid var(--eva-border); border-radius: 20px; padding: 1rem 1.1rem; background: #fff; margin-bottom: .8rem;}
      .sive-card-title {font-size: 1.05rem; font-weight: 700; color: var(--eva-text);}
      .sive-card-text {color: var(--eva-muted); margin-top: .25rem;}
      div[data-testid="stButton"] > button {
        min-height: 74px;
        border-radius: 18px;
        font-weight: 650;
        text-align: left;
        justify-content: flex-start;
        white-space: pre-line;
        padding: .9rem 1rem;
      }
      div[data-testid="stButton"] > button p {line-height: 1.35;}
      div[data-testid="stMetric"] {border: 1px solid var(--eva-border); border-radius: 16px; padding: .8rem 1rem; background: white;}
      @media (max-width: 700px) {
        .block-container {padding-left: .8rem; padding-right: .8rem; padding-top: .7rem;}
        .sive-header {border-radius: 18px; padding: 1rem;}
        .sive-title {font-size: 1.75rem;}
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def init_state() -> None:
    defaults: dict[str, Any] = {
        "page": "Inicio",
        "quote_step": 1,
        "draft": {
            "modo_viajero": "Buscar viajero existente",
            "viajero_existente": "",
            "nombres": "",
            "apellido_paterno": "",
            "apellido_materno": "",
            "cliente_contacto": "",
            "correo": "",
            "telefono": "",
            "componentes": ["Vuelos"],
            "cargo_tipo": "Estándar",
            "cargo_texto": "Cargo por servicio",
            "cargo_importe": 250.0,
            "cargo_aplicacion": "Por cotización",
        },
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()


def go(page: str) -> None:
    st.session_state.page = page
    st.rerun()


def header() -> None:
    st.markdown(
        """
        <div class="sive-header">
          <div class="sive-kicker">Proyecto EVA</div>
          <div class="sive-title">Cotizador y control de viajes</div>
          <div class="sive-subtitle">SIVE · Sistema Integral de Viajes EVA</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def top_navigation() -> None:
    labels = ["Inicio", "Nueva", "Cotizaciones", "Pasajeros", "Reportes"]
    current = st.session_state.page
    index_map = {"Inicio": 0, "Nueva cotización": 1, "Abrir cotización": 2, "Pasajeros": 3, "Ventas y reportes": 4}
    reverse_map = {"Inicio": "Inicio", "Nueva": "Nueva cotización", "Cotizaciones": "Abrir cotización", "Pasajeros": "Pasajeros", "Reportes": "Ventas y reportes"}
    selected = st.radio("Navegación", labels, index=index_map.get(current, 0), horizontal=True, label_visibility="collapsed", key="main_navigation")
    mapped = reverse_map[selected]
    if mapped != current:
        st.session_state.page = mapped
        st.rerun()


def section_card(title: str, text: str) -> None:
    st.markdown(f'<div class="sive-card"><div class="sive-card-title">{title}</div><div class="sive-card-text">{text}</div></div>', unsafe_allow_html=True)


def page_home() -> None:
    st.markdown("## Menú principal")
    st.caption("Selecciona la tarea que deseas realizar.")

    if st.button(
        "👤  Viajeros\nAlta, consulta y edición",
        use_container_width=True,
        key="home_travelers",
    ):
        go("Viajeros")

    if st.button(
        "✈️  Nueva cotización\nCrear una propuesta de viaje",
        use_container_width=True,
        type="primary",
        key="home_new_quote",
    ):
        go("Nueva cotización")

    if st.button(
        "📄  Abrir cotización\nConsultar, editar o generar PDF",
        use_container_width=True,
        key="home_open_quote",
    ):
        go("Abrir cotización")

    if st.button(
        "📊  Ventas\nRevisar ventas, cargos y rentabilidad",
        use_container_width=True,
        key="home_sales",
    ):
        go("Ventas")

def page_new_quote() -> None:
    if st.button("← Volver al inicio", key="back_new_quote"):
        go("Inicio")

    draft = st.session_state.draft
    st.markdown("## Nueva cotización")
    st.caption("Todo se conserva localmente hasta que decidas guardar.")
    step = st.session_state.quote_step
    step_names = {
        1: "Viajero",
        2: "Contenido",
        3: "Captura",
        4: "Revisión",
        5: "PDF y guardado",
    }
    st.caption(f"Paso {step} de 5 · {step_names[step]}")
    st.progress(step / 5)

    if step == 1:
        st.markdown("### Viajero y contacto")

        modo_viajero = st.radio(
            "¿Cómo deseas agregar al viajero?",
            ["Buscar viajero existente", "Registrar nuevo viajero"],
            index=0 if draft["modo_viajero"] == "Buscar viajero existente" else 1,
            horizontal=True,
        )

        if modo_viajero == "Buscar viajero existente":
            viajero_existente = st.text_input(
                "Buscar viajero",
                value=draft["viajero_existente"],
                placeholder="Escribe nombre, apellido, correo o teléfono",
            )
            st.caption(
                "Cuando conectemos esta pantalla, aquí aparecerán coincidencias "
                "de los viajeros ya registrados."
            )
            nombres = draft["nombres"]
            apellido_paterno = draft["apellido_paterno"]
            apellido_materno = draft["apellido_materno"]
        else:
            c1, c2, c3 = st.columns([1.2, 1, 1])
            nombres = c1.text_input(
                "Nombre(s) *",
                value=draft["nombres"],
                placeholder="Ej. Evelyne",
            )
            apellido_paterno = c2.text_input(
                "Apellido paterno *",
                value=draft["apellido_paterno"],
                placeholder="Ej. Charland",
            )
            apellido_materno = c3.text_input(
                "Apellido materno",
                value=draft["apellido_materno"],
                placeholder="Opcional",
            )
            viajero_existente = ""

            st.caption(
                "Captura el nombre exactamente como aparece en el pasaporte "
                "o identificación del viajero."
            )

        c4, c5 = st.columns(2)
        contact = c4.text_input(
            "Cliente o contacto",
            value=draft["cliente_contacto"],
            placeholder="Puede ser distinto al viajero",
        )
        phone = c5.text_input(
            "Teléfono",
            value=draft["telefono"],
        )
        email = st.text_input(
            "Correo",
            value=draft["correo"],
        )

        if st.button("Continuar", type="primary", use_container_width=True):
            if modo_viajero == "Buscar viajero existente":
                if not viajero_existente.strip():
                    st.warning("Busca y selecciona un viajero.")
                    return
            else:
                if not nombres.strip():
                    st.warning("Escribe el nombre o nombres del viajero.")
                    return
                if not apellido_paterno.strip():
                    st.warning("Escribe el apellido paterno del viajero.")
                    return

            draft["modo_viajero"] = modo_viajero
            draft["viajero_existente"] = viajero_existente.strip()
            draft["nombres"] = nombres.strip()
            draft["apellido_paterno"] = apellido_paterno.strip()
            draft["apellido_materno"] = apellido_materno.strip()
            draft["cliente_contacto"] = contact.strip()
            draft["telefono"] = phone.strip()
            draft["correo"] = email.strip()
            st.session_state.quote_step = 2
            st.rerun()

    elif step == 2:
        st.markdown("### ¿Qué incluirá esta cotización?")
        components = st.multiselect("Selecciona uno o varios componentes", ["Vuelos", "Hospedaje", "Seguro de viaje", "Traslados", "Tours o actividades", "Otro servicio"], default=draft["componentes"])
        st.markdown("### Cargo por servicio")
        c1, c2 = st.columns(2)
        charge_type = c1.radio("Modalidad", ["Estándar", "Personalizado", "Sin cargo"], index=["Estándar", "Personalizado", "Sin cargo"].index(draft["cargo_tipo"]))
        charge_apply = c2.radio("Aplicar", ["Por cotización", "Por pasajero"], index=["Por cotización", "Por pasajero"].index(draft["cargo_aplicacion"]))
        if charge_type == "Estándar":
            charge_text, charge_amount = "Cargo por servicio", 250.0
            st.info("Se aplicará un cargo estándar de $250 MXN.")
        elif charge_type == "Personalizado":
            charge_text = st.text_input("Texto del cargo", value=draft["cargo_texto"], placeholder="Ej. Servicio de asesoría y emisión")
            charge_amount = st.number_input("Importe del cargo (MXN)", min_value=0.0, value=float(draft["cargo_importe"]), step=50.0)
        else:
            charge_text, charge_amount = "", 0.0
        b1, b2 = st.columns(2)
        if b1.button("Regresar", use_container_width=True):
            st.session_state.quote_step = 1
            st.rerun()
        if b2.button("Continuar", type="primary", use_container_width=True):
            if not components:
                st.warning("Selecciona al menos un componente.")
                return
            draft["componentes"] = components
            draft["cargo_tipo"] = charge_type
            draft["cargo_texto"] = charge_text
            draft["cargo_importe"] = float(charge_amount)
            draft["cargo_aplicacion"] = charge_apply
            st.session_state.quote_step = 3
            st.rerun()

    elif step == 3:
        st.markdown("### Captura")
        if "Vuelos" in draft["componentes"]:
            st.markdown("#### Vuelos")
            trip_type = st.radio(
                "Tipo de viaje",
                ["Viaje sencillo", "Viaje redondo", "Multidestino"],
                horizontal=True,
                key="flight_trip_type",
            )

            def render_segment(prefix: str, segment_number: int, title: str) -> None:
                st.markdown(f"##### {title}")

                airline_col, flight_col = st.columns([1.4, 1])
                airline_col.text_input(
                    "Aerolínea *",
                    placeholder="Ej. Volaris, Aeroméxico, LATAM",
                    key=f"{prefix}_airline_{segment_number}",
                )
                flight_col.text_input(
                    "Número de vuelo",
                    placeholder="Ej. Y4 245",
                    key=f"{prefix}_number_{segment_number}",
                )

                st.caption("Ruta")
                origin, destination = st.columns(2)
                origin.text_input(
                    "Origen *",
                    placeholder="Ciudad o aeropuerto",
                    key=f"{prefix}_origin_{segment_number}",
                )
                destination.text_input(
                    "Destino *",
                    placeholder="Ciudad o aeropuerto",
                    key=f"{prefix}_destination_{segment_number}",
                )

                st.caption("Salida")
                dep_date, dep_time = st.columns(2)
                dep_date.date_input(
                    "Fecha de salida *",
                    value=None,
                    key=f"{prefix}_departure_date_{segment_number}",
                )
                dep_time.time_input(
                    "Hora de salida *",
                    value=time(8, 0),
                    key=f"{prefix}_departure_time_{segment_number}",
                )

                st.caption("Llegada")
                arr_date, arr_time = st.columns(2)
                arr_date.date_input(
                    "Fecha de llegada *",
                    value=None,
                    key=f"{prefix}_arrival_date_{segment_number}",
                )
                arr_time.time_input(
                    "Hora de llegada *",
                    value=time(12, 0),
                    key=f"{prefix}_arrival_time_{segment_number}",
                )

                fare_col, cabin_col = st.columns(2)
                fare_col.text_input(
                    "Tarifa o familia",
                    placeholder="Ej. Básica, Classic, Plus",
                    key=f"{prefix}_fare_{segment_number}",
                )
                cabin_col.selectbox(
                    "Cabina",
                    ["Económica", "Premium Economy", "Ejecutiva", "Primera"],
                    key=f"{prefix}_cabin_{segment_number}",
                )

                baggage_col, notes_col = st.columns(2)
                baggage_col.text_input(
                    "Equipaje incluido",
                    placeholder="Ej. Artículo personal + 15 kg",
                    key=f"{prefix}_baggage_{segment_number}",
                )
                notes_col.text_input(
                    "Observaciones",
                    placeholder="Ej. Operado por otra aerolínea",
                    key=f"{prefix}_notes_{segment_number}",
                )

            def render_direction(label: str, prefix: str) -> None:
                st.markdown(f"### {label}")

                connection_type = st.radio(
                    "Tipo de recorrido",
                    ["Vuelo directo", "Con escalas"],
                    horizontal=True,
                    key=f"{prefix}_connection_type",
                )

                if connection_type == "Con escalas":
                    stops = st.selectbox(
                        "Número de escalas",
                        [1, 2, 3],
                        key=f"{prefix}_stops",
                    )
                else:
                    stops = 0

                total_segments = stops + 1

                for idx in range(total_segments):
                    render_segment(
                        prefix,
                        idx + 1,
                        f"Tramo {idx + 1} de {total_segments}",
                    )

                    if idx < total_segments - 1:
                        st.info(
                            "La llegada de este tramo será el aeropuerto de conexión "
                            "del siguiente."
                        )
                        st.divider()

            if trip_type == "Viaje sencillo":
                render_direction("Trayecto", "outbound")

            elif trip_type == "Viaje redondo":
                render_direction("Ida", "outbound")
                st.divider()
                render_direction("Regreso", "return")

            else:
                st.info(
                    "En multidestino, cada tramo representa una ruta distinta. "
                    "Podrás agregar tantos como necesites."
                )

                if "multicity_segments" not in st.session_state:
                    st.session_state.multicity_segments = 2

                for idx in range(st.session_state.multicity_segments):
                    render_segment(
                        "multicity",
                        idx + 1,
                        f"Tramo {idx + 1}",
                    )
                    if idx < st.session_state.multicity_segments - 1:
                        st.divider()

                add_col, remove_col = st.columns(2)
                if add_col.button(
                    "+ Agregar tramo",
                    use_container_width=True,
                    key="add_multicity_segment",
                ):
                    st.session_state.multicity_segments += 1
                    st.rerun()

                if remove_col.button(
                    "Quitar último tramo",
                    use_container_width=True,
                    disabled=st.session_state.multicity_segments <= 2,
                    key="remove_multicity_segment",
                ):
                    st.session_state.multicity_segments -= 1
                    st.rerun()

            st.markdown("### Precio de la opción")
            price_col, currency_col = st.columns([1.4, 1])
            price_col.number_input(
                "Precio total mostrado por la aerolínea",
                min_value=0.0,
                step=100.0,
                key="flight_total_price",
            )
            currency_col.selectbox(
                "Moneda",
                ["MXN", "USD", "CAD", "EUR", "COP", "PEN", "BRL"],
                key="flight_total_currency",
            )

        if "Hospedaje" in draft["componentes"]:
            st.markdown("#### Hospedaje")

            hotel_name = st.text_input(
                "Nombre del hotel *",
                placeholder="Ej. JW Marriott Hotel Lima",
                key="hotel_name_1",
            )

            city_col, room_col = st.columns([1.3, 1])
            hotel_city = city_col.text_input(
                "Ciudad o destino *",
                placeholder="Ej. Lima",
                key="hotel_city_1",
            )
            room_type = room_col.text_input(
                "Tipo de habitación",
                placeholder="Ej. Deluxe King",
                key="hotel_room_type_1",
            )

            st.caption("Estancia")
            checkin_col, checkout_col = st.columns(2)
            checkin = checkin_col.date_input(
                "Entrada *",
                value=None,
                key="hotel_checkin_1",
            )
            checkout = checkout_col.date_input(
                "Salida *",
                value=None,
                key="hotel_checkout_1",
            )

            if checkin and checkout:
                nights = (checkout - checkin).days
                if nights > 0:
                    st.success(f"{nights} noche{'s' if nights != 1 else ''}")
                else:
                    st.warning("La fecha de salida debe ser posterior a la entrada.")
                    nights = 0
            else:
                nights = 0

            rooms_col, guests_col = st.columns(2)
            rooms = rooms_col.number_input(
                "Habitaciones",
                min_value=1,
                value=1,
                step=1,
                key="hotel_rooms_1",
            )
            guests = guests_col.number_input(
                "Huéspedes",
                min_value=1,
                value=1,
                step=1,
                key="hotel_guests_1",
            )

            board_col, cancellation_col = st.columns(2)
            board = board_col.selectbox(
                "Alimentos incluidos",
                [
                    "Sin alimentos",
                    "Desayuno incluido",
                    "Media pensión",
                    "Pensión completa",
                    "Todo incluido",
                    "Otro",
                ],
                key="hotel_board_1",
            )
            cancellation = cancellation_col.text_input(
                "Política de cancelación",
                placeholder="Ej. Cancelación gratuita hasta...",
                key="hotel_cancellation_1",
            )

            st.caption("Precio")
            price_col, currency_col = st.columns([1.4, 1])
            hotel_price = price_col.number_input(
                "Precio total mostrado",
                min_value=0.0,
                step=100.0,
                key="hotel_price_1",
            )
            hotel_currency = currency_col.selectbox(
                "Moneda",
                ["MXN", "USD", "CAD", "EUR", "COP", "PEN", "BRL"],
                key="hotel_currency_1",
            )

            if nights > 0 and hotel_price > 0:
                average_night = hotel_price / nights
                st.info(
                    f"Promedio por noche: ${average_night:,.2f} {hotel_currency}"
                )

            st.caption("Imagen del hotel")
            hotel_image = st.file_uploader(
                "Adjuntar imagen",
                type=["png", "jpg", "jpeg", "webp"],
                key="hotel_image_1",
            )
            hotel_image_url = st.text_input(
                "O pega el enlace de una imagen",
                placeholder="https://...",
                key="hotel_image_url_1",
            )

            if hotel_image is not None:
                st.image(
                    hotel_image,
                    caption=hotel_name or "Vista previa del hotel",
                    use_container_width=True,
                )
            elif hotel_image_url:
                try:
                    st.image(
                        hotel_image_url,
                        caption=hotel_name or "Vista previa del hotel",
                        use_container_width=True,
                    )
                except Exception:
                    st.warning("No pudimos mostrar la imagen desde ese enlace.")

            links_col1, links_col2 = st.columns(2)
            hotel_url = links_col1.text_input(
                "Página del hotel",
                placeholder="https://...",
                key="hotel_url_1",
            )
            map_url = links_col2.text_input(
                "Ubicación en Maps",
                placeholder="https://maps.google.com/...",
                key="hotel_map_url_1",
            )

            hotel_notes = st.text_area(
                "Condiciones y observaciones",
                placeholder="Incluye impuestos, resort fee, horarios de check-in, etc.",
                key="hotel_notes_1",
            )

            st.button(
                "+ Agregar otra opción de hospedaje",
                use_container_width=True,
                key="add_hotel_option",
            )

        other_services = [item for item in draft["componentes"] if item not in {"Vuelos", "Hospedaje"}]
        if other_services:
            st.markdown("#### Servicios adicionales")
            for service in other_services:
                with st.expander(service, expanded=True):
                    st.text_input("Descripción", key=f"desc_{service}")
                    st.number_input("Precio (MXN)", min_value=0.0, step=100.0, key=f"price_{service}")
        b1, b2 = st.columns(2)
        if b1.button("Regresar", use_container_width=True):
            st.session_state.quote_step = 2
            st.rerun()
        if b2.button("Revisar cotización", type="primary", use_container_width=True):
            st.session_state.quote_step = 4
            st.rerun()

    elif step == 4:
        st.markdown("### Revisión")
        if draft["modo_viajero"] == "Buscar viajero existente":
            nombre_completo = draft["viajero_existente"]
        else:
            nombre_completo = " ".join(
                parte
                for parte in [
                    draft["nombres"],
                    draft["apellido_paterno"],
                    draft["apellido_materno"],
                ]
                if parte
            )

        section_card(
            nombre_completo or "Viajero sin nombre",
            "Verifica que el nombre esté escrito exactamente como aparece en su documento.",
        )
        st.write("**Componentes incluidos:**")
        for item in draft["componentes"]:
            st.write(f"• {item}")
        if draft["cargo_tipo"] != "Sin cargo":
            st.write(f"**{draft['cargo_texto']}:** ${draft['cargo_importe']:,.2f} MXN · {draft['cargo_aplicacion']}")
        st.info("Esta primera versión valida el flujo y la experiencia. Todavía no envía información a Google Sheets.")
        b1, b2 = st.columns(2)
        if b1.button("Editar", use_container_width=True):
            st.session_state.quote_step = 1
            st.rerun()
        if b2.button("Continuar", type="primary", use_container_width=True):
            st.session_state.quote_step = 5
            st.rerun()

    else:
        st.markdown("### Documento y guardado")
        st.success("El borrador está listo para generar documento o guardar.")
        c1, c2 = st.columns(2)
        c1.button("Generar PDF", use_container_width=True, type="primary")
        c2.button("Guardar cotización", use_container_width=True)
        if st.button("Regresar a revisión", use_container_width=True):
            st.session_state.quote_step = 4
            st.rerun()


def page_open_quote() -> None:
    if st.button("← Volver al inicio", key="back_open_quote"):
        go("Inicio")

    st.markdown("## Abrir cotización")
    query = st.text_input("Buscar", placeholder="Nombre del pasajero, destino o folio")
    filters = st.radio("Estatus", ["Todas", "Borradores", "Enviadas", "Vendidas", "Recientes"], horizontal=True)
    st.caption(f"Filtro activo: {filters}")
    if query:
        section_card("Resultados", "En la siguiente fase conectaremos esta búsqueda ligera con Google Sheets.")
    else:
        st.info("Escribe un pasajero, destino o folio para buscar.")
    st.markdown("### Acciones disponibles")
    c1, c2 = st.columns(2)
    c1.button("Abrir cotización", use_container_width=True)
    c2.button("Generar PDF", use_container_width=True, type="primary")


def page_passengers() -> None:
    if st.button("← Volver al inicio", key="back_travelers"):
        go("Inicio")

    st.markdown("## Viajeros")
    st.text_input("Buscar viajero", placeholder="Nombre, correo o teléfono")
    st.info("La búsqueda y edición se conectarán en una fase posterior.")


def page_reports() -> None:
    if st.button("← Volver al inicio", key="back_sales"):
        go("Inicio")

    st.markdown("## Ventas")
    st.info("Esta sección se conectará después de estabilizar el flujo de cotización.")


def main() -> None:
    header()
    page = st.session_state.page
    if page == "Inicio":
        page_home()
    elif page == "Nueva cotización":
        page_new_quote()
    elif page == "Abrir cotización":
        page_open_quote()
    elif page == "Viajeros":
        page_passengers()
    elif page == "Ventas":
        page_reports()
    else:
        page_home()


if __name__ == "__main__":
    main()
