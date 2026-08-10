from __future__ import annotations

from datetime import time
from io import BytesIO
from typing import Any

import requests
import streamlit as st

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import (
        Image as RLImage,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False


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
      .sive-kicker {color: var(--eva-accent); font-weight: 700; letter-spacing: .14em; text-transform: uppercase; font-size: .78rem; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;}
      .sive-title {color: var(--eva-text); font-size: clamp(1.8rem, 4vw, 2.5rem); font-weight: 500; margin-top: .2rem;}
      .sive-subtitle {color: var(--eva-muted); margin-top: .2rem;}
      .sive-card {border: 1px solid var(--eva-border); border-radius: 20px; padding: 1rem 1.1rem; background: #fff; margin-bottom: .8rem;}
      .sive-card-title {font-size: 1.05rem; font-weight: 700; color: var(--eva-text);}
      .sive-card-text {color: var(--eva-muted); margin-top: .25rem;}
      .sive-mono {font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; letter-spacing: .01em;}
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
            "capture_state": {},
            "hotel_image_cache": None,
            "hotel_image_caches": {},
            "hotel_options": 1,
            "companions": [],
            "nombres": "",
            "apellido_paterno": "",
            "apellido_materno": "",
            "cliente_contacto": "",
            "correo": "",
            "telefono": "",
            "num_viajeros": 1,
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



def build_quote_pdf(draft: dict[str, Any], captured_value) -> bytes:
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError(
            "La librería reportlab no está instalada. Agrega reportlab a requirements.txt."
        )

    buffer = BytesIO()

    teal = colors.HexColor("#2F9FA3")
    soft = colors.HexColor("#F4F8F8")
    line = colors.HexColor("#D9E2E2")
    text_color = colors.HexColor("#2F3437")
    muted = colors.HexColor("#737B80")
    dark = colors.HexColor("#202426")

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="SIVETitle",
            fontName="Helvetica",
            fontSize=18,
            leading=20,
            textColor=dark,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SIVESection",
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=13,
            textColor=dark,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SIVEBody",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=text_color,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SIVESmall",
            fontName="Helvetica",
            fontSize=6.8,
            leading=8.3,
            textColor=muted,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SIVEMono",
            fontName="Courier",
            fontSize=7.7,
            leading=9.5,
            textColor=text_color,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SIVEMonoBold",
            fontName="Courier-Bold",
            fontSize=8.2,
            leading=10,
            textColor=dark,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SIVEPrice",
            fontName="Courier-Bold",
            fontSize=10.5,
            leading=12,
            textColor=teal,
            alignment=TA_RIGHT,
        )
    )

    def P(value, style="SIVEBody"):
        return Paragraph(str(value if value not in (None, "") else "—"), styles[style])

    def money(amount: float, currency: str) -> str:
        return f"{currency} {float(amount or 0):,.2f}"

    def safe_image(source_bytes: bytes | None, source_url: str | None):
        data = source_bytes
        if not data and source_url:
            try:
                response = requests.get(source_url, timeout=5)
                response.raise_for_status()
                data = response.content
            except Exception:
                data = None
        if not data:
            return None

        try:
            bio = BytesIO(data)
            image_reader = ImageReader(bio)
            width, height = image_reader.getSize()
            max_w = 67 * mm
            max_h = 43 * mm
            scale = min(max_w / width, max_h / height)
            bio.seek(0)
            return RLImage(bio, width=width * scale, height=height * scale)
        except Exception:
            return None

    if draft.get("modo_viajero") == "Buscar viajero existente":
        principal = draft.get("viajero_existente") or "Viajero"
    else:
        principal = " ".join(
            part
            for part in [
                draft.get("nombres", ""),
                draft.get("apellido_paterno", ""),
                draft.get("apellido_materno", ""),
            ]
            if part
        ) or "Viajero"

    traveler_count = max(int(draft.get("num_viajeros", 1) or 1), 1)
    companions = list(draft.get("companions", []))

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=15 * mm,
        title="Cotización Proyecto EVA",
    )
    story = []

    header = Table(
        [
            [P("PROYECTO EVA", "SIVEMonoBold"), P("COTIZACIÓN DE VIAJE", "SIVETitle")],
            [P("SIVE · Sistema Integral de Viajes EVA", "SIVESmall"), ""],
        ],
        colWidths=[74 * mm, 101 * mm],
    )
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LINEBELOW", (0, 1), (-1, 1), 0.6, line),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
            ]
        )
    )
    story += [header, Spacer(1, 4 * mm)]

    pax_rows = [[P("PAX", "SIVEMonoBold"), P("VIAJERO", "SIVEMonoBold")]]
    pax_rows.append([P("01", "SIVEMono"), P(principal, "SIVEBody")])
    for idx in range(2, traveler_count + 1):
        companion = companions[idx - 2] if idx - 2 < len(companions) else {}
        name = companion.get("name", "").strip()
        is_tba = companion.get("tba", False)
        display = "TBA · Nombre por definir" if is_tba or not name else name
        pax_rows.append([P(f"{idx:02d}", "SIVEMono"), P(display, "SIVEBody")])

    pax_table = Table(pax_rows, colWidths=[18 * mm, 157 * mm])
    pax_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), soft),
                ("BOX", (0, 0), (-1, -1), 0.45, line),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, line),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story += [pax_table, Spacer(1, 5 * mm)]

    components = draft.get("componentes", [])
    subtotals_by_currency: dict[str, float] = {}
    total_eva_fees_mxn = 0.0

    def add_subtotal(currency: str, amount: float) -> None:
        if amount:
            subtotals_by_currency[currency] = subtotals_by_currency.get(currency, 0.0) + float(amount)

    # -------------------- VUELOS --------------------
    if "Vuelos" in components:
        story.append(P("VUELOS", "SIVESection"))

        trip_type = captured_value("flight_trip_type", "Viaje sencillo")
        flight_pax = max(int(captured_value("flight_pax", traveler_count) or traveler_count), 1)
        price_basis = captured_value("flight_price_basis", "Total de la reserva")
        entered_price = float(captured_value("flight_total_price", 0.0) or 0.0)
        currency = captured_value("flight_total_currency", "MXN")

        if price_basis == "Precio por pasajero":
            unit_price = entered_price
            air_total = entered_price * flight_pax
        else:
            air_total = entered_price
            unit_price = air_total / flight_pax if flight_pax else 0.0

        add_subtotal(currency, air_total)

        summary = Table(
            [
                [
                    P("PAX", "SIVESmall"),
                    P("TARIFA / PAX", "SIVESmall"),
                    P("SUBTOTAL VUELOS", "SIVESmall"),
                ],
                [
                    P(str(flight_pax), "SIVEMonoBold"),
                    P(money(unit_price, currency), "SIVEMonoBold"),
                    P(money(air_total, currency), "SIVEPrice"),
                ],
            ],
            colWidths=[35 * mm, 65 * mm, 75 * mm],
        )
        summary.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), soft),
                    ("BOX", (0, 0), (-1, -1), 0.5, line),
                    ("INNERGRID", (0, 0), (-1, -1), 0.3, line),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story += [P(f"Tipo de viaje: {trip_type}", "SIVESmall"), Spacer(1, 1.5 * mm), summary, Spacer(1, 2 * mm)]

        segment_rows = []
        for prefix in ("outbound", "return", "multicity"):
            for idx in range(1, 10):
                airline = captured_value(f"{prefix}_airline_{idx}", "")
                number = captured_value(f"{prefix}_number_{idx}", "")
                origin = captured_value(f"{prefix}_origin_{idx}", "")
                destination = captured_value(f"{prefix}_destination_{idx}", "")
                dep_date = captured_value(f"{prefix}_departure_date_{idx}", None)
                dep_time = captured_value(f"{prefix}_departure_time_{idx}", None)
                arr_date = captured_value(f"{prefix}_arrival_date_{idx}", None)
                arr_time = captured_value(f"{prefix}_arrival_time_{idx}", None)
                fare = captured_value(f"{prefix}_fare_{idx}", "")
                baggage = captured_value(f"{prefix}_baggage_{idx}", "")

                if not any([airline, number, origin, destination, dep_date, arr_date]):
                    continue

                dep_text = (
                    f"{dep_date or ''} "
                    f"{dep_time.strftime('%H:%M') if hasattr(dep_time, 'strftime') else dep_time or ''}"
                ).strip()
                arr_text = (
                    f"{arr_date or ''} "
                    f"{arr_time.strftime('%H:%M') if hasattr(arr_time, 'strftime') else arr_time or ''}"
                ).strip()

                segment_rows.append(
                    [
                        P(f"{airline} {number}".strip() or "Vuelo", "SIVEMono"),
                        P(f"{origin or '—'} → {destination or '—'}", "SIVEMonoBold"),
                        P(f"SAL {dep_text}<br/>LLE {arr_text}", "SIVESmall"),
                        P(f"{fare or ''}<br/>{baggage or ''}".strip(), "SIVESmall"),
                    ]
                )

        if segment_rows:
            seg = Table(
                [[P("VUELO", "SIVESmall"), P("RUTA", "SIVESmall"), P("HORARIO", "SIVESmall"), P("TARIFA / EQUIPAJE", "SIVESmall")]]
                + segment_rows,
                colWidths=[36 * mm, 43 * mm, 54 * mm, 42 * mm],
            )
            seg.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), soft),
                        ("BOX", (0, 0), (-1, -1), 0.45, line),
                        ("INNERGRID", (0, 0), (-1, -1), 0.3, line),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 5),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story += [seg, Spacer(1, 2 * mm)]

        fee = float(captured_value("review_charge_total_flights", 0.0) or 0.0)
        if fee:
            total_eva_fees_mxn += fee
            story.append(P(f"Cargo por servicio EVA: MXN {fee:,.2f}", "SIVESmall"))

        story.append(Spacer(1, 5 * mm))

    # -------------------- HOSPEDAJES --------------------
    if "Hospedaje" in components:
        hotel_options = max(int(draft.get("hotel_options", 1) or 1), 1)
        caches = draft.get("hotel_image_caches", {}) or {}

        for idx in range(1, hotel_options + 1):
            hotel_name = captured_value(f"hotel_name_{idx}", "")
            city = captured_value(f"hotel_city_{idx}", "")
            checkin = captured_value(f"hotel_checkin_{idx}", None)
            checkout = captured_value(f"hotel_checkout_{idx}", None)
            room = captured_value(f"hotel_room_type_{idx}", "")
            board = captured_value(f"hotel_board_{idx}", "")
            rooms = int(captured_value(f"hotel_rooms_{idx}", 1) or 1)
            guests = int(captured_value(f"hotel_guests_{idx}", 1) or 1)
            price = float(captured_value(f"hotel_price_{idx}", 0.0) or 0.0)
            currency = captured_value(f"hotel_currency_{idx}", "MXN")
            hotel_url = captured_value(f"hotel_url_{idx}", "")
            map_url = captured_value(f"hotel_map_url_{idx}", "")
            image_url = captured_value(f"hotel_image_url_{idx}", "")

            if not any([hotel_name, city, price, checkin, checkout]):
                continue

            add_subtotal(currency, price)
            nights = (checkout - checkin).days if checkin and checkout else 0
            average = price / nights if price and nights > 0 else 0.0

            story.append(P(f"HOSPEDAJE · OPCIÓN {idx}", "SIVESection"))

            price_box = Table(
                [
                    [
                        P("NOCHES", "SIVESmall"),
                        P("HABITACIONES", "SIVESmall"),
                        P("PROMEDIO / NOCHE", "SIVESmall"),
                        P("TOTAL HOTEL", "SIVESmall"),
                    ],
                    [
                        P(str(nights if nights > 0 else "—"), "SIVEMonoBold"),
                        P(str(rooms), "SIVEMonoBold"),
                        P(money(average, currency) if average else "—", "SIVEMonoBold"),
                        P(money(price, currency) if price else "—", "SIVEPrice"),
                    ],
                ],
                colWidths=[35 * mm, 40 * mm, 50 * mm, 50 * mm],
            )
            price_box.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), soft),
                        ("BOX", (0, 0), (-1, -1), 0.45, line),
                        ("INNERGRID", (0, 0), (-1, -1), 0.3, line),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 5),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )

            details = Table(
                [
                    [P("Hotel", "SIVESmall"), P(hotel_name)],
                    [P("Destino", "SIVESmall"), P(city)],
                    [P("Habitación", "SIVESmall"), P(room)],
                    [P("Huéspedes", "SIVESmall"), P(str(guests))],
                    [P("Estancia", "SIVESmall"), P(f"{checkin or '—'} → {checkout or '—'}")],
                    [P("Alimentos", "SIVESmall"), P(board)],
                ],
                colWidths=[34 * mm, 79 * mm],
            )
            details.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LINEBELOW", (0, 0), (-1, -2), 0.25, line),
                        ("LEFTPADDING", (0, 0), (-1, -1), 3),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )

            cache = caches.get(str(idx)) or caches.get(idx)
            if idx == 1 and not cache and draft.get("hotel_image_cache"):
                cache = draft.get("hotel_image_cache")
            image_bytes = cache.get("bytes") if isinstance(cache, dict) else None
            image = safe_image(image_bytes, image_url)

            if image:
                hotel_block = Table([[details, image]], colWidths=[113 * mm, 62 * mm])
                hotel_block.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
                story += [hotel_block, Spacer(1, 2 * mm)]
            else:
                story += [details, Spacer(1, 2 * mm)]

            links = []
            if hotel_url:
                links.append(f'<a href="{hotel_url}" color="#2F9FA3">Página del hotel</a>')
            if map_url:
                links.append(f'<a href="{map_url}" color="#2F9FA3">Ver ubicación en Google Maps</a>')
            if links:
                story.append(Paragraph("  ·  ".join(links), styles["SIVESmall"]))
                story.append(Spacer(1, 2 * mm))

            story += [price_box, Spacer(1, 2 * mm)]

            # The hotel fee is a section-level charge; show it only once.
            if idx == hotel_options:
                fee = float(captured_value("review_charge_total_hotel", 0.0) or 0.0)
                if fee:
                    total_eva_fees_mxn += fee
                    story.append(P(f"Cargo por servicio EVA: MXN {fee:,.2f}", "SIVESmall"))

            story.append(Spacer(1, 5 * mm))

    # -------------------- SERVICIOS --------------------
    service_specs = [
        ("Seguro de viaje", "SEGURO DE VIAJE", "insurance_price", "insurance_currency", "review_charge_total_insurance"),
        ("Traslados", "TRASLADO", "transfer_price", "transfer_currency", "review_charge_total_transfer"),
        ("Renta de auto", "RENTA DE AUTO", "car_price", "car_currency", "review_charge_total_car"),
        ("Tours o actividades", "TOUR O ACTIVIDAD", "tour_price", "tour_currency", "review_charge_total_tour"),
        ("Otro servicio", "OTRO SERVICIO", "other_service_price", "other_service_currency", "review_charge_total_other"),
    ]

    for component, title, price_key, currency_key, fee_key in service_specs:
        if component not in components:
            continue

        price = float(captured_value(price_key, 0.0) or 0.0)
        currency = captured_value(currency_key, "MXN")
        fee = float(captured_value(fee_key, 0.0) or 0.0)
        add_subtotal(currency, price)
        total_eva_fees_mxn += fee

        if component == "Seguro de viaje":
            details = [
                ("Proveedor", captured_value("insurance_provider", "")),
                ("Plan", captured_value("insurance_plan", "")),
                ("Cobertura", captured_value("insurance_coverage", "")),
            ]
        elif component == "Traslados":
            details = [
                ("Tipo", captured_value("transfer_type", "")),
                ("Ruta", f"{captured_value('transfer_origin', '')} → {captured_value('transfer_destination', '')}"),
            ]
        elif component == "Renta de auto":
            details = [
                ("Arrendadora", captured_value("car_company", "")),
                ("Vehículo", captured_value("car_category", "")),
            ]
        elif component == "Tours o actividades":
            details = [
                ("Actividad", captured_value("tour_name", "")),
                ("Destino", captured_value("tour_city", "")),
            ]
        else:
            details = [
                ("Servicio", captured_value("other_service_name", "")),
                ("Descripción", captured_value("other_service_description", "")),
            ]

        rows = [[P(label, "SIVESmall"), P(value)] for label, value in details if value]
        rows.append([P("Subtotal", "SIVESmall"), P(money(price, currency), "SIVEMonoBold")])
        if fee:
            rows.append([P("Cargo EVA", "SIVESmall"), P(f"MXN {fee:,.2f}", "SIVEMonoBold")])

        story.append(P(title, "SIVESection"))
        table = Table(rows, colWidths=[45 * mm, 130 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.45, line),
                    ("INNERGRID", (0, 0), (-1, -1), 0.3, line),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story += [table, Spacer(1, 5 * mm)]

    # -------------------- RESUMEN ECONÓMICO --------------------
    story.append(P("RESUMEN ECONÓMICO", "SIVESection"))

    summary_rows = [[P("CONCEPTO", "SIVEMonoBold"), P("IMPORTE", "SIVEMonoBold")]]
    for currency, amount in sorted(subtotals_by_currency.items()):
        summary_rows.append([P(f"Servicios cotizados · {currency}"), P(money(amount, currency), "SIVEMonoBold")])

    if total_eva_fees_mxn:
        summary_rows.append([P("Cargos por servicio EVA · MXN"), P(f"MXN {total_eva_fees_mxn:,.2f}", "SIVEMonoBold")])

    # Only combine into one grand total when every service is MXN.
    if subtotals_by_currency and set(subtotals_by_currency.keys()) == {"MXN"}:
        grand_total = subtotals_by_currency["MXN"] + total_eva_fees_mxn
        summary_rows.append([P("TOTAL GENERAL", "SIVEMonoBold"), P(f"MXN {grand_total:,.2f}", "SIVEPrice")])
    else:
        summary_rows.append(
            [
                P("TOTAL", "SIVEMonoBold"),
                P("Se presenta por moneda para evitar conversiones implícitas.", "SIVESmall"),
            ]
        )

    summary_table = Table(summary_rows, colWidths=[105 * mm, 70 * mm])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), soft),
                ("BOX", (0, 0), (-1, -1), 0.55, line),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, line),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story += [summary_table, Spacer(1, 5 * mm)]

    story.append(
        P(
            "Precios sujetos a disponibilidad y cambios sin previo aviso. "
            "La cotización no representa una reservación hasta la confirmación correspondiente.",
            "SIVESmall",
        )
    )

    doc.build(story)
    return buffer.getvalue()


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
    draft.setdefault("capture_state", {})
    draft.setdefault("hotel_image_cache", None)

    def is_capture_key(key: str) -> bool:
        prefixes = (
            "flight_",
            "outbound_",
            "return_",
            "multicity_",
            "hotel_",
            "insurance_",
            "transfer_",
            "car_",
            "tour_",
            "other_service_",
        )
        return key == "multicity_segments" or key.startswith(prefixes)

    def persist_capture_state() -> None:
        """Copy the currently visible quote fields into durable draft memory."""
        saved = draft["capture_state"]

        for key, value in list(st.session_state.items()):
            if not is_capture_key(str(key)):
                continue

            # Uploaded hotel files need their bytes preserved separately.
            if str(key).startswith("hotel_image_") and not str(key).startswith("hotel_image_url_"):
                if value is not None:
                    try:
                        hotel_idx = str(key).rsplit("_", 1)[-1]
                        draft.setdefault("hotel_image_caches", {})
                        draft["hotel_image_caches"][hotel_idx] = {
                            "name": getattr(value, "name", "hotel.jpg"),
                            "type": getattr(value, "type", "image/jpeg"),
                            "bytes": value.getvalue(),
                        }
                        if hotel_idx == "1":
                            draft["hotel_image_cache"] = draft["hotel_image_caches"][hotel_idx]
                    except Exception:
                        pass
                continue

            saved[key] = value

    def captured(key: str, default=None):
        """Read a field from the live widget state or the durable draft."""
        if key in st.session_state:
            return st.session_state[key]
        return draft["capture_state"].get(key, default)

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

        st.divider()
        st.markdown("#### Viajeros incluidos")
        num_viajeros = st.number_input(
            "Número de viajeros",
            min_value=1,
            value=max(int(draft.get("num_viajeros", 1) or 1), 1),
            step=1,
            help="Incluye al viajero principal.",
            key="step1_num_viajeros",
        )

        companions: list[dict[str, Any]] = []
        if int(num_viajeros) > 1:
            st.caption(
                "Si todavía no conoces el nombre de un acompañante, usa TBA "
                "(To Be Advised / nombre por definir)."
            )
            existing_companions = list(draft.get("companions", []))

            for pax_idx in range(2, int(num_viajeros) + 1):
                saved = (
                    existing_companions[pax_idx - 2]
                    if pax_idx - 2 < len(existing_companions)
                    else {}
                )
                with st.container(border=True):
                    st.markdown(f"**PAX {pax_idx:02d}**")
                    name_col, tba_col = st.columns([2.2, 1])
                    companion_name = name_col.text_input(
                        "Nombre completo",
                        value=saved.get("name", ""),
                        placeholder="Exactamente como aparece en pasaporte",
                        key=f"companion_name_{pax_idx}",
                    )
                    companion_tba = tba_col.checkbox(
                        "Nombre por definir (TBA)",
                        value=bool(saved.get("tba", False)),
                        key=f"companion_tba_{pax_idx}",
                    )
                    companions.append(
                        {"name": companion_name.strip(), "tba": bool(companion_tba)}
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
            draft["num_viajeros"] = int(num_viajeros)
            draft["companions"] = companions
            st.session_state.quote_step = 2
            st.rerun()

    elif step == 2:
        st.markdown("### ¿Qué incluirá esta cotización?")

        components = st.multiselect(
            "Selecciona uno o varios componentes",
            [
                "Vuelos",
                "Hospedaje",
                "Seguro de viaje",
                "Traslados",
                "Renta de auto",
                "Tours o actividades",
                "Otro servicio",
            ],
            default=draft["componentes"],
        )

        st.caption(
            "Puedes comenzar solo con vuelos y agregar hospedaje o servicios después."
        )

        b1, b2 = st.columns(2)
        if b1.button("Regresar", use_container_width=True):
            st.session_state.quote_step = 1
            st.rerun()

        if b2.button("Continuar", type="primary", use_container_width=True):
            if not components:
                st.warning("Selecciona al menos un componente.")
                return

            draft["componentes"] = components
            st.session_state.quote_step = 3
            st.rerun()

    elif step == 3:
        # Streamlit removes widget state when a widget is no longer rendered.
        # Restore the previously captured quote before showing the editor again.
        explicit_default_tokens = (
            "_departure_date_",
            "_departure_time_",
            "_arrival_date_",
            "_arrival_time_",
        )
        explicit_default_keys = {
            *{
                f"hotel_{field}_{idx}"
                for idx in range(1, max(int(draft.get("hotel_options", 1) or 1), 1) + 1)
                for field in ("checkin", "checkout", "rooms", "guests")
            },
            "insurance_start",
            "insurance_end",
            "insurance_people",
            "transfer_date",
            "transfer_time",
            "transfer_people",
            "tour_date",
            "tour_time",
            "tour_people",
            "car_pickup_date",
            "car_pickup_time",
            "car_return_date",
            "car_return_time",
        }

        for saved_key, saved_value in draft["capture_state"].items():
            has_dynamic_default = any(token in saved_key for token in explicit_default_tokens)
            if (
                saved_key not in st.session_state
                and saved_key not in explicit_default_keys
                and not has_dynamic_default
            ):
                st.session_state[saved_key] = saved_value

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
                    value=captured(
                        f"{prefix}_departure_date_{segment_number}", None
                    ),
                    key=f"{prefix}_departure_date_{segment_number}",
                )
                dep_time.time_input(
                    "Hora de salida *",
                    value=captured(
                        f"{prefix}_departure_time_{segment_number}", time(8, 0)
                    ),
                    key=f"{prefix}_departure_time_{segment_number}",
                )

                st.caption("Llegada")
                arr_date, arr_time = st.columns(2)
                arr_date.date_input(
                    "Fecha de llegada *",
                    value=captured(
                        f"{prefix}_arrival_date_{segment_number}", None
                    ),
                    key=f"{prefix}_arrival_date_{segment_number}",
                )
                arr_time.time_input(
                    "Hora de llegada *",
                    value=captured(
                        f"{prefix}_arrival_time_{segment_number}", time(12, 0)
                    ),
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
            st.caption(
                "Captura exactamente lo que muestra la aerolínea. SIVE hará el desglose."
            )

            pax_col, basis_col = st.columns([1, 1.5])
            flight_pax = pax_col.number_input(
                "PAX en esta opción",
                min_value=1,
                value=max(
                    int(captured("flight_pax", draft.get("num_viajeros", 1)) or 1),
                    1,
                ),
                step=1,
                key="flight_pax",
            )
            price_basis = basis_col.radio(
                "El precio capturado corresponde a",
                ["Total de la reserva", "Precio por pasajero"],
                horizontal=True,
                key="flight_price_basis",
            )

            price_col, currency_col = st.columns([1.4, 1])
            entered_flight_price = price_col.number_input(
                "Importe mostrado por la aerolínea",
                min_value=0.0,
                step=100.0,
                key="flight_total_price",
            )
            flight_currency = currency_col.selectbox(
                "Moneda",
                ["MXN", "USD", "CAD", "EUR", "COP", "PEN", "BRL"],
                key="flight_total_currency",
            )

            if price_basis == "Precio por pasajero":
                fare_per_pax = float(entered_flight_price)
                flight_subtotal = float(entered_flight_price) * int(flight_pax)
            else:
                flight_subtotal = float(entered_flight_price)
                fare_per_pax = (
                    flight_subtotal / int(flight_pax)
                    if int(flight_pax) > 0
                    else 0.0
                )

            if entered_flight_price > 0:
                st.markdown(
                    f"""
                    <div class="sive-card">
                      <div class="sive-kicker">DESGLOSE DE VUELO</div>
                      <div class="sive-card-text">
                        <span class="sive-mono">PAX {int(flight_pax):02d}</span>
                        &nbsp;·&nbsp;
                        Tarifa por pasajero <strong>{flight_currency} {fare_per_pax:,.2f}</strong>
                        &nbsp;·&nbsp;
                        Subtotal vuelos <strong>{flight_currency} {flight_subtotal:,.2f}</strong>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        if "Hospedaje" in draft["componentes"]:
            st.markdown("#### Hospedaje")

            draft["hotel_options"] = max(int(draft.get("hotel_options", 1) or 1), 1)
            draft.setdefault("hotel_image_caches", {})

            def render_hotel_option(hotel_idx: int) -> None:
                with st.container(border=True):
                    st.markdown(f"##### Opción de hospedaje {hotel_idx}")

                    hotel_name = st.text_input(
                        "Nombre del hotel *",
                        placeholder="Ej. JW Marriott Hotel Lima",
                        key=f"hotel_name_{hotel_idx}",
                    )

                    city_col, room_col = st.columns([1.3, 1])
                    hotel_city = city_col.text_input(
                        "Ciudad o destino *",
                        placeholder="Ej. Lima",
                        key=f"hotel_city_{hotel_idx}",
                    )
                    room_col.text_input(
                        "Tipo de habitación",
                        placeholder="Ej. Deluxe King",
                        key=f"hotel_room_type_{hotel_idx}",
                    )

                    st.caption("Estancia")
                    checkin_col, checkout_col = st.columns(2)
                    checkin = checkin_col.date_input(
                        "Entrada *",
                        value=captured(f"hotel_checkin_{hotel_idx}", None),
                        key=f"hotel_checkin_{hotel_idx}",
                    )
                    checkout = checkout_col.date_input(
                        "Salida *",
                        value=captured(f"hotel_checkout_{hotel_idx}", None),
                        key=f"hotel_checkout_{hotel_idx}",
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
                    rooms_col.number_input(
                        "Habitaciones",
                        min_value=1,
                        value=int(captured(f"hotel_rooms_{hotel_idx}", 1)),
                        step=1,
                        key=f"hotel_rooms_{hotel_idx}",
                    )
                    guests_col.number_input(
                        "Huéspedes",
                        min_value=1,
                        value=int(captured(f"hotel_guests_{hotel_idx}", draft.get("num_viajeros", 1))),
                        step=1,
                        key=f"hotel_guests_{hotel_idx}",
                    )

                    board_col, cancellation_col = st.columns(2)
                    board_col.selectbox(
                        "Alimentos incluidos",
                        [
                            "Sin alimentos",
                            "Desayuno incluido",
                            "Media pensión",
                            "Pensión completa",
                            "Todo incluido",
                            "Otro",
                        ],
                        key=f"hotel_board_{hotel_idx}",
                    )
                    cancellation_col.text_input(
                        "Política de cancelación",
                        placeholder="Ej. Cancelación gratuita hasta...",
                        key=f"hotel_cancellation_{hotel_idx}",
                    )

                    st.caption("Precio")
                    price_col, currency_col = st.columns([1.4, 1])
                    hotel_price = price_col.number_input(
                        "Precio total mostrado",
                        min_value=0.0,
                        step=100.0,
                        key=f"hotel_price_{hotel_idx}",
                    )
                    hotel_currency = currency_col.selectbox(
                        "Moneda",
                        ["MXN", "USD", "CAD", "EUR", "COP", "PEN", "BRL"],
                        key=f"hotel_currency_{hotel_idx}",
                    )

                    if nights > 0 and hotel_price > 0:
                        st.info(
                            f"Promedio por noche: {hotel_currency} "
                            f"{hotel_price / nights:,.2f}"
                        )

                    st.caption("Imagen del hotel")
                    hotel_image = st.file_uploader(
                        "Adjuntar imagen",
                        type=["png", "jpg", "jpeg", "webp"],
                        key=f"hotel_image_{hotel_idx}",
                    )
                    hotel_image_url = st.text_input(
                        "O pega el enlace de una imagen",
                        placeholder="https://...",
                        key=f"hotel_image_url_{hotel_idx}",
                    )

                    if hotel_image is not None:
                        try:
                            draft["hotel_image_caches"][str(hotel_idx)] = {
                                "name": getattr(hotel_image, "name", "hotel.jpg"),
                                "type": getattr(hotel_image, "type", "image/jpeg"),
                                "bytes": hotel_image.getvalue(),
                            }
                            if hotel_idx == 1:
                                draft["hotel_image_cache"] = draft["hotel_image_caches"][str(hotel_idx)]
                        except Exception:
                            pass

                    cache = draft["hotel_image_caches"].get(str(hotel_idx))
                    if hotel_idx == 1 and not cache:
                        cache = draft.get("hotel_image_cache")

                    preview_source = None
                    if hotel_image is not None:
                        preview_source = hotel_image
                    elif cache and cache.get("bytes"):
                        preview_source = cache["bytes"]
                        st.caption("Imagen adjunta conservada. Puedes reemplazarla.")
                    elif hotel_image_url:
                        preview_source = hotel_image_url

                    if preview_source is not None:
                        try:
                            preview_col, _ = st.columns([1, 2.4])
                            with preview_col:
                                st.image(
                                    preview_source,
                                    caption=hotel_name or "Vista previa",
                                    width=220,
                                )
                        except Exception:
                            st.warning("No pudimos mostrar la vista previa de esa imagen.")

                    links_col1, links_col2 = st.columns(2)
                    links_col1.text_input(
                        "Página del hotel",
                        placeholder="https://...",
                        key=f"hotel_url_{hotel_idx}",
                    )
                    links_col2.text_input(
                        "Ubicación en Maps",
                        placeholder="https://maps.google.com/...",
                        key=f"hotel_map_url_{hotel_idx}",
                    )

                    st.text_area(
                        "Condiciones y observaciones",
                        placeholder="Incluye impuestos, resort fee, horarios de check-in, etc.",
                        key=f"hotel_notes_{hotel_idx}",
                    )

            for hotel_idx in range(1, draft["hotel_options"] + 1):
                render_hotel_option(hotel_idx)

            add_hotel_col, remove_hotel_col = st.columns(2)
            if add_hotel_col.button(
                "+ Agregar otra opción de hospedaje",
                use_container_width=True,
                key="add_hotel_option",
            ):
                persist_capture_state()
                draft["hotel_options"] += 1
                st.rerun()

            if remove_hotel_col.button(
                "Quitar última opción",
                use_container_width=True,
                disabled=draft["hotel_options"] <= 1,
                key="remove_hotel_option",
            ):
                persist_capture_state()
                draft["hotel_options"] -= 1
                st.rerun()

        other_services = [
            item
            for item in draft["componentes"]
            if item not in {"Vuelos", "Hospedaje"}
        ]

        if other_services:
            st.markdown("#### Servicios adicionales")
            st.caption("Solo verás los campos necesarios para cada servicio.")

            for service in other_services:
                if service == "Seguro de viaje":
                    with st.expander("🛡️ Seguro de viaje", expanded=True):
                        provider_col, plan_col = st.columns(2)
                        provider_col.text_input(
                            "Proveedor",
                            placeholder="Ej. Assist Card",
                            key="insurance_provider",
                        )
                        plan_col.text_input(
                            "Plan",
                            placeholder="Ej. AC 60",
                            key="insurance_plan",
                        )

                        date_col1, date_col2 = st.columns(2)
                        insurance_start = date_col1.date_input(
                            "Inicio de cobertura",
                            value=captured("insurance_start", None),
                            key="insurance_start",
                        )
                        insurance_end = date_col2.date_input(
                            "Fin de cobertura",
                            value=captured("insurance_end", None),
                            key="insurance_end",
                        )

                        if insurance_start and insurance_end:
                            covered_days = (insurance_end - insurance_start).days + 1
                            if covered_days > 0:
                                st.info(
                                    f"Cobertura: {covered_days} día"
                                    f"{'s' if covered_days != 1 else ''}"
                                )
                            else:
                                st.warning(
                                    "La fecha de fin debe ser igual o posterior al inicio."
                                )

                        coverage_col, people_col = st.columns(2)
                        coverage_col.text_input(
                            "Cobertura principal",
                            placeholder="Ej. USD 60,000 asistencia médica",
                            key="insurance_coverage",
                        )
                        people_col.number_input(
                            "Viajeros cubiertos",
                            min_value=1,
                            value=int(captured("insurance_people", 1)),
                            step=1,
                            key="insurance_people",
                        )

                        price_col, currency_col = st.columns([1.4, 1])
                        price_col.number_input(
                            "Precio total",
                            min_value=0.0,
                            step=100.0,
                            key="insurance_price",
                        )
                        currency_col.selectbox(
                            "Moneda",
                            ["MXN", "USD", "CAD", "EUR", "COP", "PEN", "BRL"],
                            key="insurance_currency",
                        )

                        st.text_area(
                            "Condiciones u observaciones",
                            placeholder="Ej. Deducible, restricciones, coberturas relevantes...",
                            key="insurance_notes",
                        )

                elif service == "Traslados":
                    with st.expander("🚐 Traslado", expanded=True):
                        transfer_type = st.selectbox(
                            "Tipo de traslado",
                            [
                                "Aeropuerto → Hotel",
                                "Hotel → Aeropuerto",
                                "Aeropuerto → Hotel → Aeropuerto",
                                "Punto a punto",
                                "Otro",
                            ],
                            key="transfer_type",
                        )

                        origin_col, destination_col = st.columns(2)
                        origin_col.text_input(
                            "Origen",
                            placeholder="Ej. Aeropuerto de Lima",
                            key="transfer_origin",
                        )
                        destination_col.text_input(
                            "Destino",
                            placeholder="Ej. JW Marriott Lima",
                            key="transfer_destination",
                        )

                        date_col, time_col = st.columns(2)
                        date_col.date_input(
                            "Fecha",
                            value=captured("transfer_date", None),
                            key="transfer_date",
                        )
                        time_col.time_input(
                            "Hora",
                            value=captured("transfer_time", time(12, 0)),
                            key="transfer_time",
                        )

                        provider_col, people_col = st.columns(2)
                        provider_col.text_input(
                            "Proveedor",
                            placeholder="Opcional",
                            key="transfer_provider",
                        )
                        people_col.number_input(
                            "Pasajeros",
                            min_value=1,
                            value=int(captured("transfer_people", 1)),
                            step=1,
                            key="transfer_people",
                        )

                        price_col, currency_col = st.columns([1.4, 1])
                        price_col.number_input(
                            "Precio total",
                            min_value=0.0,
                            step=100.0,
                            key="transfer_price",
                        )
                        currency_col.selectbox(
                            "Moneda",
                            ["MXN", "USD", "CAD", "EUR", "COP", "PEN", "BRL"],
                            key="transfer_currency",
                        )

                        st.text_area(
                            "Indicaciones u observaciones",
                            placeholder="Ej. Chofer espera con letrero a nombre del pasajero...",
                            key="transfer_notes",
                        )

                elif service == "Tours o actividades":
                    with st.expander("🎟️ Tour o actividad", expanded=True):
                        st.text_input(
                            "Nombre del tour o actividad *",
                            placeholder="Ej. Tour de día completo a Machu Picchu",
                            key="tour_name",
                        )

                        city_col, provider_col = st.columns(2)
                        city_col.text_input(
                            "Ciudad o destino",
                            placeholder="Ej. Cusco",
                            key="tour_city",
                        )
                        provider_col.text_input(
                            "Proveedor",
                            placeholder="Opcional",
                            key="tour_provider",
                        )

                        date_col, time_col = st.columns(2)
                        date_col.date_input(
                            "Fecha",
                            value=captured("tour_date", None),
                            key="tour_date",
                        )
                        time_col.time_input(
                            "Hora",
                            value=captured("tour_time", time(9, 0)),
                            key="tour_time",
                        )

                        duration_col, people_col = st.columns(2)
                        duration_col.text_input(
                            "Duración",
                            placeholder="Ej. 8 horas",
                            key="tour_duration",
                        )
                        people_col.number_input(
                            "Participantes",
                            min_value=1,
                            value=int(captured("tour_people", 1)),
                            step=1,
                            key="tour_people",
                        )

                        st.text_area(
                            "Incluye",
                            placeholder="Ej. Guía, entradas, transporte, alimentos...",
                            key="tour_includes",
                        )

                        price_col, currency_col = st.columns([1.4, 1])
                        price_col.number_input(
                            "Precio total",
                            min_value=0.0,
                            step=100.0,
                            key="tour_price",
                        )
                        currency_col.selectbox(
                            "Moneda",
                            ["MXN", "USD", "CAD", "EUR", "COP", "PEN", "BRL"],
                            key="tour_currency",
                        )

                        st.text_area(
                            "Condiciones u observaciones",
                            placeholder="Punto de encuentro, restricciones, cancelación...",
                            key="tour_notes",
                        )

                elif service == "Renta de auto":
                    with st.expander("🚗 Renta de auto", expanded=True):
                        company_col, car_col = st.columns(2)
                        company_col.text_input(
                            "Arrendadora",
                            placeholder="Ej. Hertz",
                            key="car_company",
                        )
                        car_col.text_input(
                            "Categoría o vehículo",
                            placeholder="Ej. SUV mediana",
                            key="car_category",
                        )

                        pickup_col, return_col = st.columns(2)
                        pickup_col.text_input(
                            "Lugar de entrega",
                            placeholder="Ej. Aeropuerto de Cancún",
                            key="car_pickup_location",
                        )
                        return_col.text_input(
                            "Lugar de devolución",
                            placeholder="Ej. Aeropuerto de Cancún",
                            key="car_return_location",
                        )

                        pickup_date_col, pickup_time_col = st.columns(2)
                        pickup_date = pickup_date_col.date_input(
                            "Fecha de entrega",
                            value=captured("car_pickup_date", None),
                            key="car_pickup_date",
                        )
                        pickup_time_col.time_input(
                            "Hora de entrega",
                            value=captured("car_pickup_time", time(12, 0)),
                            key="car_pickup_time",
                        )

                        return_date_col, return_time_col = st.columns(2)
                        return_date = return_date_col.date_input(
                            "Fecha de devolución",
                            value=captured("car_return_date", None),
                            key="car_return_date",
                        )
                        return_time_col.time_input(
                            "Hora de devolución",
                            value=captured("car_return_time", time(12, 0)),
                            key="car_return_time",
                        )

                        if pickup_date and return_date:
                            rental_days = (return_date - pickup_date).days
                            if rental_days >= 0:
                                st.info(
                                    f"Periodo: {rental_days + 1} día"
                                    f"{'s' if rental_days + 1 != 1 else ''}"
                                )
                            else:
                                st.warning(
                                    "La devolución debe ser posterior a la entrega."
                                )

                        st.text_input(
                            "Cobertura o seguro incluido",
                            placeholder="Ej. CDW, responsabilidad civil...",
                            key="car_coverage",
                        )

                        price_col, currency_col = st.columns([1.4, 1])
                        price_col.number_input(
                            "Precio total",
                            min_value=0.0,
                            step=100.0,
                            key="car_price",
                        )
                        currency_col.selectbox(
                            "Moneda",
                            ["MXN", "USD", "CAD", "EUR", "COP", "PEN", "BRL"],
                            key="car_currency",
                        )

                        st.text_area(
                            "Condiciones u observaciones",
                            placeholder="Depósito, kilometraje, combustible, conductor adicional...",
                            key="car_notes",
                        )

                elif service == "Otro servicio":
                    with st.expander("➕ Otro servicio", expanded=True):
                        st.text_input(
                            "Nombre del servicio *",
                            placeholder="Ej. Asistencia especial",
                            key="other_service_name",
                        )
                        st.text_area(
                            "Descripción",
                            placeholder="Describe brevemente el servicio.",
                            key="other_service_description",
                        )

                        price_col, currency_col = st.columns([1.4, 1])
                        price_col.number_input(
                            "Precio total",
                            min_value=0.0,
                            step=100.0,
                            key="other_service_price",
                        )
                        currency_col.selectbox(
                            "Moneda",
                            ["MXN", "USD", "CAD", "EUR", "COP", "PEN", "BRL"],
                            key="other_service_currency",
                        )

                        st.text_area(
                            "Condiciones u observaciones",
                            key="other_service_notes",
                        )

        b1, b2 = st.columns(2)
        if b1.button("Regresar", use_container_width=True):
            persist_capture_state()
            st.session_state.quote_step = 2
            st.rerun()
        if b2.button("Revisar cotización", type="primary", use_container_width=True):
            persist_capture_state()
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

        traveler_count = max(int(draft.get("num_viajeros", 1) or 1), 1)
        st.markdown(
            f'<div class="sive-mono">PAX {traveler_count:02d}</div>',
            unsafe_allow_html=True,
        )

        companions = list(draft.get("companions", []))
        if traveler_count > 1:
            traveler_lines = []
            for idx in range(2, traveler_count + 1):
                companion = companions[idx - 2] if idx - 2 < len(companions) else {}
                name = companion.get("name", "").strip()
                if companion.get("tba", False) or not name:
                    name = "TBA · Nombre por definir"
                traveler_lines.append(f"**PAX {idx:02d}:** {name}")
            st.markdown("  \n".join(traveler_lines))

        st.markdown("#### Resumen de la cotización")
        st.caption(
            "Revisa cada sección. El cargo por servicio se define aquí, al final."
        )

        chargeable_services = {
            "Vuelos": True,
            "Hospedaje": False,
            "Seguro de viaje": False,
            "Traslados": False,
            "Renta de auto": True,
            "Tours o actividades": True,
            "Otro servicio": False,
        }

        def amount_text(amount: float, currency: str) -> str:
            if not amount:
                return "Sin precio capturado"
            return f"{currency} {amount:,.2f}"

        def render_charge(service_key: str, default_enabled: bool) -> tuple[str, float]:
            default_mode = "Estándar $250 MXN" if default_enabled else "Sin cargo"
            mode_key = f"review_charge_mode_{service_key}"
            amount_key = f"review_charge_amount_{service_key}"
            text_key = f"review_charge_text_{service_key}"
            apply_key = f"review_charge_apply_{service_key}"
            total_key = f"review_charge_total_{service_key}"

            current = captured(mode_key, default_mode)
            mode = st.radio(
                "Cargo por servicio EVA",
                ["Estándar $250 MXN", "Personalizado", "Sin cargo"],
                index=["Estándar $250 MXN", "Personalizado", "Sin cargo"].index(current),
                horizontal=True,
                key=mode_key,
            )

            if mode == "Sin cargo":
                st.session_state[text_key] = ""
                st.session_state[amount_key] = 0.0
                st.session_state[apply_key] = "Por cotización"
                st.session_state[total_key] = 0.0
                return "", 0.0

            if mode == "Estándar $250 MXN":
                concept = "Cargo por servicio"
                unit_amount = 250.0
                st.session_state[text_key] = concept
                st.session_state[amount_key] = unit_amount
            else:
                c1, c2 = st.columns([1.4, 1])
                concept = c1.text_input(
                    "Concepto",
                    value=captured(text_key, "Cargo por servicio"),
                    key=text_key,
                )
                unit_amount = c2.number_input(
                    "Importe base MXN",
                    min_value=0.0,
                    value=float(captured(amount_key, 250.0)),
                    step=50.0,
                    key=amount_key,
                )

            apply_default = "Por pasajero" if default_enabled else "Por cotización"
            apply_current = captured(apply_key, apply_default)
            apply_mode = st.radio(
                "Aplicar",
                ["Por pasajero", "Por cotización"],
                index=["Por pasajero", "Por cotización"].index(apply_current),
                horizontal=True,
                key=apply_key,
            )

            if apply_mode == "Por pasajero":
                total_amount = float(unit_amount) * int(draft.get("num_viajeros", 1) or 1)
                st.caption(
                    f"${unit_amount:,.2f} × {int(draft.get('num_viajeros', 1) or 1)} "
                    f"viajero{'s' if int(draft.get('num_viajeros', 1) or 1) != 1 else ''} "
                    f"= ${total_amount:,.2f} MXN"
                )
            else:
                total_amount = float(unit_amount)
                st.caption(f"Cargo total de esta sección: ${total_amount:,.2f} MXN")

            st.session_state[total_key] = total_amount
            return concept, total_amount


        # VUELOS
        if "Vuelos" in draft["componentes"]:
            with st.container(border=True):
                st.markdown("##### ✈️ Vuelos")

                trip_type = captured("flight_trip_type", "Viaje sencillo")
                st.write(f"**Tipo de viaje:** {trip_type}")

                flight_pax = max(
                    int(captured("flight_pax", draft.get("num_viajeros", 1)) or 1),
                    1,
                )
                entered_price = float(captured("flight_total_price", 0.0) or 0.0)
                flight_currency = captured("flight_total_currency", "MXN")
                price_basis = captured("flight_price_basis", "Total de la reserva")

                if price_basis == "Precio por pasajero":
                    fare_per_pax = entered_price
                    flight_subtotal = entered_price * flight_pax
                else:
                    flight_subtotal = entered_price
                    fare_per_pax = flight_subtotal / flight_pax if flight_pax else 0.0

                st.markdown(
                    f"""
                    <div class="sive-card">
                      <div class="sive-kicker">PRECIO DE VUELOS</div>
                      <div class="sive-card-text">
                        <span class="sive-mono">PAX {flight_pax:02d}</span><br>
                        Tarifa por pasajero: <strong>{flight_currency} {fare_per_pax:,.2f}</strong><br>
                        Subtotal vuelos: <strong>{flight_currency} {flight_subtotal:,.2f}</strong>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Mostrar ruta principal si existe
                route_candidates = [
                    ("outbound_origin_1", "outbound_destination_1"),
                    ("multicity_origin_1", "multicity_destination_1"),
                ]
                for origin_key, destination_key in route_candidates:
                    origin = captured(origin_key, "")
                    destination = captured(destination_key, "")
                    if origin or destination:
                        st.write(f"**Ruta:** {origin or '—'} → {destination or '—'}")
                        break

                render_charge("flights", chargeable_services["Vuelos"])

                if st.button("Editar vuelos", key="review_edit_flights"):
                    st.session_state.quote_step = 3
                    st.rerun()

        # HOSPEDAJE
        if "Hospedaje" in draft["componentes"]:
            with st.container(border=True):
                st.markdown("##### 🏨 Hospedaje")

                hotel_options = max(int(draft.get("hotel_options", 1) or 1), 1)
                any_hotel = False

                for hotel_idx in range(1, hotel_options + 1):
                    hotel_name = captured(f"hotel_name_{hotel_idx}", "")
                    hotel_city = captured(f"hotel_city_{hotel_idx}", "")
                    checkin = captured(f"hotel_checkin_{hotel_idx}")
                    checkout = captured(f"hotel_checkout_{hotel_idx}")
                    hotel_price = float(captured(f"hotel_price_{hotel_idx}", 0.0) or 0.0)
                    hotel_currency = captured(f"hotel_currency_{hotel_idx}", "MXN")

                    if not any([hotel_name, hotel_city, checkin, checkout, hotel_price]):
                        continue

                    any_hotel = True
                    st.markdown(f"**Opción {hotel_idx} · {hotel_name or 'Hotel'}**")
                    if hotel_city:
                        st.caption(hotel_city)
                    if checkin and checkout:
                        nights = (checkout - checkin).days
                        if nights > 0:
                            st.write(f"{nights} noche{'s' if nights != 1 else ''}")
                    st.write(
                        f"**Precio:** {amount_text(hotel_price, hotel_currency)}"
                    )
                    if hotel_idx < hotel_options:
                        st.divider()

                if not any_hotel:
                    st.caption("No hay datos de hospedaje capturados.")

                render_charge("hotel", chargeable_services["Hospedaje"])

                if st.button("Editar hospedaje", key="review_edit_hotel"):
                    st.session_state.quote_step = 3
                    st.rerun()

        # SEGURO
        if "Seguro de viaje" in draft["componentes"]:
            with st.container(border=True):
                st.markdown("##### 🛡️ Seguro de viaje")

                provider = captured("insurance_provider", "")
                plan = captured("insurance_plan", "")
                price = float(captured("insurance_price", 0.0) or 0.0)
                currency = captured("insurance_currency", "MXN")

                if provider:
                    st.write(f"**Proveedor:** {provider}")
                if plan:
                    st.write(f"**Plan:** {plan}")
                st.write(f"**Precio:** {amount_text(price, currency)}")

                render_charge("insurance", chargeable_services["Seguro de viaje"])

                if st.button("Editar seguro", key="review_edit_insurance"):
                    st.session_state.quote_step = 3
                    st.rerun()

        # TRASLADOS
        if "Traslados" in draft["componentes"]:
            with st.container(border=True):
                st.markdown("##### 🚐 Traslado")

                transfer_type = captured("transfer_type", "")
                origin = captured("transfer_origin", "")
                destination = captured("transfer_destination", "")
                price = float(captured("transfer_price", 0.0) or 0.0)
                currency = captured("transfer_currency", "MXN")

                if transfer_type:
                    st.write(f"**Tipo:** {transfer_type}")
                if origin or destination:
                    st.write(f"**Ruta:** {origin or '—'} → {destination or '—'}")
                st.write(f"**Precio:** {amount_text(price, currency)}")

                render_charge("transfer", chargeable_services["Traslados"])

                if st.button("Editar traslado", key="review_edit_transfer"):
                    st.session_state.quote_step = 3
                    st.rerun()

        # RENTA DE AUTO
        if "Renta de auto" in draft["componentes"]:
            with st.container(border=True):
                st.markdown("##### 🚗 Renta de auto")

                company = captured("car_company", "")
                category = captured("car_category", "")
                price = float(captured("car_price", 0.0) or 0.0)
                currency = captured("car_currency", "MXN")

                if company:
                    st.write(f"**Arrendadora:** {company}")
                if category:
                    st.write(f"**Vehículo:** {category}")
                st.write(f"**Precio:** {amount_text(price, currency)}")

                render_charge("car", chargeable_services["Renta de auto"])

                if st.button("Editar renta de auto", key="review_edit_car"):
                    st.session_state.quote_step = 3
                    st.rerun()

        # TOUR
        if "Tours o actividades" in draft["componentes"]:
            with st.container(border=True):
                st.markdown("##### 🎟️ Tour o actividad")

                tour_name = captured("tour_name", "")
                city = captured("tour_city", "")
                price = float(captured("tour_price", 0.0) or 0.0)
                currency = captured("tour_currency", "MXN")

                if tour_name:
                    st.write(f"**Actividad:** {tour_name}")
                if city:
                    st.write(f"**Destino:** {city}")
                st.write(f"**Precio:** {amount_text(price, currency)}")

                render_charge("tour", chargeable_services["Tours o actividades"])

                if st.button("Editar tour", key="review_edit_tour"):
                    st.session_state.quote_step = 3
                    st.rerun()

        # OTRO
        if "Otro servicio" in draft["componentes"]:
            with st.container(border=True):
                st.markdown("##### ➕ Otro servicio")

                service_name = captured("other_service_name", "")
                price = float(captured("other_service_price", 0.0) or 0.0)
                currency = captured("other_service_currency", "MXN")

                if service_name:
                    st.write(f"**Servicio:** {service_name}")
                st.write(f"**Precio:** {amount_text(price, currency)}")

                render_charge("other", chargeable_services["Otro servicio"])

                if st.button("Editar otro servicio", key="review_edit_other"):
                    st.session_state.quote_step = 3
                    st.rerun()

        st.divider()
        st.markdown("#### Resumen económico")
        st.caption("Precios base antes de cargos EVA.")

        review_totals: dict[str, float] = {}

        def add_review_total(currency: str, amount: float) -> None:
            if amount:
                review_totals[currency] = review_totals.get(currency, 0.0) + float(amount)

        if "Vuelos" in draft["componentes"]:
            flight_pax = max(int(captured("flight_pax", draft.get("num_viajeros", 1)) or 1), 1)
            entered = float(captured("flight_total_price", 0.0) or 0.0)
            currency = captured("flight_total_currency", "MXN")
            basis = captured("flight_price_basis", "Total de la reserva")
            flight_subtotal = entered * flight_pax if basis == "Precio por pasajero" else entered
            add_review_total(currency, flight_subtotal)
            st.write(f"**Vuelos:** {currency} {flight_subtotal:,.2f}")

        if "Hospedaje" in draft["componentes"]:
            for hotel_idx in range(1, max(int(draft.get("hotel_options", 1) or 1), 1) + 1):
                amount = float(captured(f"hotel_price_{hotel_idx}", 0.0) or 0.0)
                currency = captured(f"hotel_currency_{hotel_idx}", "MXN")
                if amount:
                    add_review_total(currency, amount)
                    st.write(f"**Hospedaje · opción {hotel_idx}:** {currency} {amount:,.2f}")

        review_service_specs = [
            ("Seguro de viaje", "Seguro", "insurance_price", "insurance_currency"),
            ("Traslados", "Traslado", "transfer_price", "transfer_currency"),
            ("Renta de auto", "Renta de auto", "car_price", "car_currency"),
            ("Tours o actividades", "Tour / actividad", "tour_price", "tour_currency"),
            ("Otro servicio", "Otro servicio", "other_service_price", "other_service_currency"),
        ]
        for component, label, price_key, currency_key in review_service_specs:
            if component in draft["componentes"]:
                amount = float(captured(price_key, 0.0) or 0.0)
                currency = captured(currency_key, "MXN")
                if amount:
                    add_review_total(currency, amount)
                    st.write(f"**{label}:** {currency} {amount:,.2f}")

        st.divider()
        st.markdown("#### Cargos por servicio EVA")

        charge_rows = []
        total_charge_mxn = 0.0
        service_charge_keys = [
            ("Vuelos", "flights"),
            ("Hospedaje", "hotel"),
            ("Seguro de viaje", "insurance"),
            ("Traslados", "transfer"),
            ("Renta de auto", "car"),
            ("Tours o actividades", "tour"),
            ("Otro servicio", "other"),
        ]

        for label, key in service_charge_keys:
            if label not in draft["componentes"]:
                continue
            amount = float(captured(f"review_charge_total_{key}", 0.0) or 0.0)
            concept = captured(f"review_charge_text_{key}", "")
            apply_mode = captured(f"review_charge_apply_{key}", "Por cotización")
            if amount > 0:
                charge_rows.append((label, concept or "Cargo por servicio", amount, apply_mode))
                total_charge_mxn += amount

        if charge_rows:
            for label, concept, amount, apply_mode in charge_rows:
                st.write(
                    f"**{label}:** {concept} · ${amount:,.2f} MXN · {apply_mode.lower()}"
                )
            st.success(f"Total cargos EVA: ${total_charge_mxn:,.2f} MXN")
        else:
            st.caption("Esta cotización no tiene cargos por servicio.")

        st.markdown("#### Total de la cotización")
        if review_totals:
            if set(review_totals.keys()) == {"MXN"}:
                grand_total = review_totals["MXN"] + total_charge_mxn
                st.markdown(
                    f"""
                    <div class="sive-card">
                      <div class="sive-kicker">TOTAL GENERAL</div>
                      <div class="sive-title sive-mono" style="font-size:1.6rem;">
                        MXN {grand_total:,.2f}
                      </div>
                      <div class="sive-card-text">
                        Servicios MXN {review_totals['MXN']:,.2f}
                        + cargos EVA MXN {total_charge_mxn:,.2f}
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                for currency, amount in sorted(review_totals.items()):
                    st.write(f"**Subtotal {currency}:** {currency} {amount:,.2f}")
                if total_charge_mxn:
                    st.write(f"**Cargos EVA MXN:** MXN {total_charge_mxn:,.2f}")
                st.info(
                    "Hay más de una moneda. SIVE muestra subtotales por moneda "
                    "para no hacer una conversión implícita."
                )

        b1, b2 = st.columns(2)
        if b1.button("Volver a captura", use_container_width=True):
            st.session_state.quote_step = 3
            st.rerun()

        if b2.button(
            "Continuar a PDF y guardado",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.quote_step = 5
            st.rerun()

    else:
        st.markdown("### Documento y guardado")
        st.success("El borrador está listo para generar documento o guardar.")

        st.markdown("#### Vista previa del documento")
        if draft["modo_viajero"] == "Buscar viajero existente":
            traveler_name = draft["viajero_existente"] or "Viajero"
        else:
            traveler_name = " ".join(
                parte
                for parte in [
                    draft["nombres"],
                    draft["apellido_paterno"],
                    draft["apellido_materno"],
                ]
                if parte
            ) or "Viajero"

        st.write(f"**Viajero principal:** {traveler_name}")
        total_pax = max(int(draft.get("num_viajeros", 1) or 1), 1)
        st.write(f"**Viajeros:** {total_pax}")
        if total_pax > 1:
            companions = list(draft.get("companions", []))
            for idx in range(2, total_pax + 1):
                companion = companions[idx - 2] if idx - 2 < len(companions) else {}
                companion_name = companion.get("name", "").strip()
                if companion.get("tba", False) or not companion_name:
                    companion_name = "TBA · Nombre por definir"
                st.write(f"**PAX {idx:02d}:** {companion_name}")
        st.write(
            "**Incluye:** "
            + ", ".join(draft.get("componentes", []))
        )

        try:
            pdf_bytes = build_quote_pdf(draft, captured)
            st.download_button(
                "Generar / descargar PDF",
                data=pdf_bytes,
                file_name="Cotizacion_Proyecto_EVA.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary",
            )
        except Exception as exc:
            st.error(f"No pudimos generar el PDF: {exc}")

        st.button(
            "Guardar cotización",
            use_container_width=True,
            disabled=True,
            help="La sincronización con Google Sheets se conectará en la siguiente fase.",
        )

        st.caption(
            "El PDF se genera directamente con el borrador local; no consulta Google Sheets."
        )

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
