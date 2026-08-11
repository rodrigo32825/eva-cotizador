from __future__ import annotations

from datetime import time
from io import BytesIO
from pathlib import Path
from typing import Any

import requests
import streamlit as st

try:
    from eva_api import EvaApi, EvaApiError
    EVA_API_AVAILABLE = True
except Exception:
    EvaApi = None
    EvaApiError = RuntimeError
    EVA_API_AVAILABLE = False

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import (
        Image as RLImage,
        KeepTogether,
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
      .sive-option-title {font-size: 1.18rem; font-weight: 750; line-height: 1.25; color: var(--eva-text); margin: .15rem 0 .15rem 0;}
      .sive-option-meta {font-size: .86rem; color: var(--eva-muted); margin-bottom: .45rem;}
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
        "catalogs_loaded": False,
        "catalogs_error": "",
        "airlines_catalog": [],
        "airports_catalog": [],
        "draft": {
            "modo_viajero": "Buscar viajero existente",
            "viajero_existente": "",
            "capture_state": {},
            "hotel_image_cache": None,
            "hotel_image_caches": {},
            "hotel_options": 1,
            "flight_options": 1,
            "flight_multicity_segments": {},
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




def _brand_slug(value: str) -> str:
    value = (value or "").strip().lower()
    replacements = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "ü": "u", "ñ": "n",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_")


def _first_existing_path(candidates: list[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _eva_logo_path() -> Path | None:
    base_dir = Path(__file__).resolve().parent
    return _first_existing_path(
        [
            base_dir / "assets" / "eva_logo.png",
            base_dir / "assets" / "eva_logo.jpg",
            base_dir / "eva_logo_crop.png",
            base_dir / "eva_logo.png",
            base_dir / "PROYECTO EVA_logo_02.jpeg",
        ]
    )


def _airline_logo_source(
    draft: dict[str, Any],
    airline_name: str,
) -> dict[str, Any] | None:
    """Resolve airline logo exclusively from 10_CAT_AEROLINEAS."""
    catalog = draft.get("airline_logo_catalog", {}) or {}
    normalized = _brand_slug(airline_name)

    for key, item in catalog.items():
        if isinstance(item, str):
            item = {"logo_url": item}

        if not isinstance(item, dict):
            continue

        names = [
            str(key),
            str(item.get("name", "")),
            str(item.get("nombre", "")),
            str(item.get("NOMBRE", "")),
            str(item.get("iata", "")),
            str(item.get("IATA", "")),
            str(item.get("icao", "")),
            str(item.get("ICAO", "")),
        ]

        if any(
            _brand_slug(name) == normalized
            for name in names
            if name
        ):
            if item.get("bytes"):
                return {"bytes": item["bytes"]}

            url = (
                item.get("logo_url")
                or item.get("LOGO_URL")
                or item.get("url")
                or item.get("URL_LOGO")
            )
            if url:
                return {"url": url}

    return None




def _clean_catalog_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def initialize_catalogs() -> None:
    """One bootstrap read per SIVE session.

    10_CAT_AEROLINEAS and 11_CAT_AEROPUERTOS remain local in session memory
    during quote capture. No Google request is made when selecting fields.
    """
    if st.session_state.get("catalogs_loaded"):
        return

    if not EVA_API_AVAILABLE:
        st.session_state.catalogs_error = (
            "No encuentro eva_api.py en el proyecto."
        )
        return

    try:
        api_url = str(st.secrets["eva"]["api_url"]).strip()
        api_token = str(st.secrets["eva"]["api_token"]).strip()

        api = EvaApi(api_url, api_token)
        bootstrap = api.bootstrap()

        airlines = list(bootstrap.get("aerolineas", []) or [])
        airports = list(bootstrap.get("aeropuertos", []) or [])

        st.session_state.airlines_catalog = airlines
        st.session_state.airports_catalog = airports
        st.session_state.catalogs_loaded = True
        st.session_state.catalogs_error = ""

        # Make the airline catalog available to the local PDF generator.
        logo_catalog: dict[str, dict[str, Any]] = {}
        for row in airlines:
            name = _clean_catalog_text(
                row.get("NOMBRE")
                or row.get("NOMBRE_COMERCIAL")
            )
            iata = _clean_catalog_text(row.get("IATA")).upper()
            icao = _clean_catalog_text(row.get("ICAO")).upper()
            logo_url = _clean_catalog_text(
                row.get("LOGO_URL")
                or row.get("URL_LOGO")
            )

            record = {
                "name": name,
                "IATA": iata,
                "ICAO": icao,
                "LOGO_URL": logo_url,
            }

            for key in (name, iata, icao):
                if key:
                    logo_catalog[key] = record

        st.session_state.draft["airline_logo_catalog"] = logo_catalog

    except Exception as exc:
        st.session_state.catalogs_error = str(exc)


def airline_rows() -> list[dict[str, Any]]:
    rows = []
    for row in st.session_state.get("airlines_catalog", []):
        active = str(
            row.get("ACTIVA")
            or row.get("ACTIVO")
            or row.get("ESTATUS")
            or "SI"
        ).strip().upper()

        if active in {"NO", "0", "FALSE", "INACTIVA", "INACTIVO"}:
            continue

        iata = _clean_catalog_text(row.get("IATA")).upper()
        icao = _clean_catalog_text(row.get("ICAO")).upper()
        name = _clean_catalog_text(
            row.get("NOMBRE")
            or row.get("NOMBRE_COMERCIAL")
        )

        if not name:
            continue

        rows.append(
            {
                **row,
                "_iata": iata,
                "_icao": icao,
                "_name": name,
            }
        )

    return sorted(
        rows,
        key=lambda item: (
            item["_name"].lower(),
            item["_iata"],
        ),
    )


def airport_rows() -> list[dict[str, Any]]:
    rows = []

    for row in st.session_state.get("airports_catalog", []):
        active = str(
            row.get("ACTIVO")
            or row.get("ACTIVA")
            or row.get("ESTATUS")
            or "SI"
        ).strip().upper()

        if active in {"NO", "0", "FALSE", "INACTIVO", "INACTIVA"}:
            continue

        iata = _clean_catalog_text(row.get("IATA")).upper()
        icao = _clean_catalog_text(row.get("ICAO")).upper()
        city = _clean_catalog_text(
            row.get("CIUDAD")
            or row.get("CITY")
        )
        airport = _clean_catalog_text(
            row.get("NOMBRE_AEROPUERTO")
            or row.get("AEROPUERTO")
            or row.get("NOMBRE")
        )
        country = _clean_catalog_text(
            row.get("PAIS")
            or row.get("COUNTRY")
        )

        if not iata:
            continue

        rows.append(
            {
                **row,
                "_iata": iata,
                "_icao": icao,
                "_city": city,
                "_airport": airport,
                "_country": country,
            }
        )

    return sorted(
        rows,
        key=lambda item: (
            item["_iata"],
            item["_city"].lower(),
        ),
    )


def airline_option_label(row: dict[str, Any]) -> str:
    parts = []

    if row.get("_iata"):
        parts.append(row["_iata"])

    if row.get("_name"):
        parts.append(row["_name"])

    if row.get("_icao"):
        parts.append(f"ICAO {row['_icao']}")

    return " · ".join(parts)


def airport_option_label(row: dict[str, Any]) -> str:
    first = " · ".join(
        part
        for part in [
            row.get("_iata", ""),
            row.get("_city", ""),
        ]
        if part
    )

    detail = " · ".join(
        part
        for part in [
            row.get("_airport", ""),
            row.get("_country", ""),
        ]
        if part
    )

    return f"{first} — {detail}" if detail else first


def _find_catalog_index(
    rows: list[dict[str, Any]],
    *,
    saved_iata: str = "",
    saved_name: str = "",
) -> int:
    if not rows:
        return 0

    saved_iata = _clean_catalog_text(saved_iata).upper()
    saved_name = _clean_catalog_text(saved_name).lower()

    for idx, row in enumerate(rows, start=1):
        if saved_iata and row.get("_iata") == saved_iata:
            return idx

        if (
            saved_name
            and _clean_catalog_text(
                row.get("_name")
                or row.get("_city")
            ).lower() == saved_name
        ):
            return idx

    return 0


def airline_selector(
    prefix: str,
    segment_number: int,
    captured_value,
) -> dict[str, Any] | None:
    rows = airline_rows()
    key_base = f"{prefix}_airline_{segment_number}"

    if not rows:
        st.warning(
            "No hay aerolíneas disponibles en 10_CAT_AEROLINEAS."
        )
        return None

    saved_iata = captured_value(
        f"{key_base}_iata",
        "",
    )
    saved_name = captured_value(
        f"{key_base}_name",
        "",
    )

    options: list[dict[str, Any] | None] = [None, *rows]
    index = _find_catalog_index(
        rows,
        saved_iata=saved_iata,
        saved_name=saved_name,
    )

    selected = st.selectbox(
        "Aerolínea *",
        options,
        index=index,
        format_func=lambda item: (
            "Buscar por nombre, IATA o ICAO…"
            if item is None
            else airline_option_label(item)
        ),
        key=f"{key_base}_choice",
        help=(
            "Puedes escribir Aeroméxico, AM o AMX. "
            "La búsqueda se hace sobre el catálogo ya cargado."
        ),
    )

    if selected:
        st.session_state[f"{key_base}_name"] = selected["_name"]
        st.session_state[f"{key_base}_iata"] = selected["_iata"]
        st.session_state[f"{key_base}_icao"] = selected["_icao"]
        st.session_state[f"{key_base}_logo_url"] = _clean_catalog_text(
            selected.get("LOGO_URL")
            or selected.get("URL_LOGO")
        )

        st.markdown(
            f'<div class="sive-option-meta">'
            f'<span class="sive-mono">{selected["_iata"] or "—"}</span>'
            f' · {selected["_name"]}'
            + (
                f' · ICAO <span class="sive-mono">{selected["_icao"]}</span>'
                if selected["_icao"]
                else ""
            )
            + "</div>",
            unsafe_allow_html=True,
        )

    return selected


def airport_selector(
    prefix: str,
    segment_number: int,
    field_name: str,
    label: str,
    captured_value,
) -> dict[str, Any] | None:
    rows = airport_rows()
    key_base = f"{prefix}_{field_name}_{segment_number}"

    if not rows:
        st.warning(
            "No hay aeropuertos disponibles en 11_CAT_AEROPUERTOS."
        )
        return None

    saved_iata = captured_value(
        f"{key_base}_iata",
        "",
    )
    saved_city = captured_value(
        f"{key_base}_city",
        "",
    )

    options: list[dict[str, Any] | None] = [None, *rows]
    index = _find_catalog_index(
        rows,
        saved_iata=saved_iata,
        saved_name=saved_city,
    )

    selected = st.selectbox(
        label,
        options,
        index=index,
        format_func=lambda item: (
            "Escribe IATA, ciudad o aeropuerto…"
            if item is None
            else airport_option_label(item)
        ),
        key=f"{key_base}_choice",
        help=(
            "Ejemplo: escribe MEX, Ciudad de México o Benito Juárez. "
            "SIVE filtrará el catálogo localmente."
        ),
    )

    if selected:
        st.session_state[f"{key_base}_iata"] = selected["_iata"]
        st.session_state[f"{key_base}_icao"] = selected["_icao"]
        st.session_state[f"{key_base}_city"] = selected["_city"]
        st.session_state[f"{key_base}_airport"] = selected["_airport"]
        st.session_state[f"{key_base}_country"] = selected["_country"]

        # Backward-compatible display value used by some existing screens.
        st.session_state[key_base] = selected["_iata"]

        st.markdown(
            f'<div class="sive-option-meta">'
            f'<span class="sive-mono"><strong>{selected["_iata"]}</strong></span>'
            + (
                f' · {selected["_city"]}'
                if selected["_city"]
                else ""
            )
            + (
                f'<br><span style="font-size:.78rem;">'
                f'{selected["_airport"]}'
                + (
                    f' · {selected["_country"]}'
                    if selected["_country"]
                    else ""
                )
                + "</span>"
                if selected["_airport"]
                else ""
            )
            + "</div>",
            unsafe_allow_html=True,
        )

    return selected


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
            fontSize=17,
            leading=19,
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
            name="SIVEHotel",
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=14,
            textColor=dark,
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
        return Paragraph(
            str(value if value not in (None, "") else "—"),
            styles[style],
        )

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
            max_w = 62 * mm
            max_h = 40 * mm
            scale = min(max_w / width, max_h / height)
            bio.seek(0)
            return RLImage(
                bio,
                width=width * scale,
                height=height * scale,
            )
        except Exception:
            return None

    def branded_image(
        *,
        path: Path | None = None,
        source_bytes: bytes | None = None,
        source_url: str | None = None,
        max_w: float,
        max_h: float,
    ):
        data = source_bytes

        if path is not None:
            try:
                img = RLImage(str(path))
                ratio = min(
                    max_w / img.imageWidth,
                    max_h / img.imageHeight,
                )
                img.drawWidth = img.imageWidth * ratio
                img.drawHeight = img.imageHeight * ratio
                return img
            except Exception:
                return None

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
            scale = min(max_w / width, max_h / height)
            bio.seek(0)
            return RLImage(
                bio,
                width=width * scale,
                height=height * scale,
            )
        except Exception:
            return None

    def eva_logo():
        return branded_image(
            path=_eva_logo_path(),
            max_w=53 * mm,
            max_h=20 * mm,
        )

    def airline_logo(airline_name: str):
        source = _airline_logo_source(draft, airline_name)
        if not source:
            return None
        return branded_image(
            path=source.get("path"),
            source_bytes=source.get("bytes"),
            source_url=source.get("url"),
            max_w=27 * mm,
            max_h=10 * mm,
        )



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

    logo = eva_logo()
    left_header = logo if logo else P("PROYECTO EVA", "SIVEMonoBold")

    header = Table(
        [
            [
                left_header,
                Paragraph(
                    "PROPUESTA DE VIAJE<br/>"
                    '<font name="Courier" size="7" color="#737B80">'
                    "SIVE · SISTEMA INTEGRAL DE VIAJES EVA"
                    "</font>",
                    styles["SIVETitle"],
                ),
            ],
        ],
        colWidths=[78 * mm, 97 * mm],
    )
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LINEBELOW", (0, 0), (-1, 0), 1.2, teal),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
            ]
        )
    )
    story += [header, Spacer(1, 4 * mm)]

    pax_rows = [[P("PAX", "SIVEMonoBold"), P("VIAJERO", "SIVEMonoBold")]]
    pax_rows.append([P("01", "SIVEMono"), P(principal)])
    for idx in range(2, traveler_count + 1):
        companion = companions[idx - 2] if idx - 2 < len(companions) else {}
        name = companion.get("name", "").strip()
        is_tba = companion.get("tba", False)
        display = "TBA · Nombre por definir" if is_tba or not name else name
        pax_rows.append([P(f"{idx:02d}", "SIVEMono"), P(display)])

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
    proposal_rows = []

    # -------------------- VUELOS / ALTERNATIVAS --------------------
    if "Vuelos" in components:
        flight_options = max(int(draft.get("flight_options", 1) or 1), 1)

        for option_idx in range(1, flight_options + 1):
            prefix_root = f"flight_{option_idx}"
            trip_type = captured_value(
                f"{prefix_root}_trip_type",
                "Viaje sencillo",
            )
            flight_pax = max(
                int(captured_value(f"{prefix_root}_pax", traveler_count) or traveler_count),
                1,
            )
            price_basis = captured_value(
                f"{prefix_root}_price_basis",
                "Total de la reserva",
            )
            entered_price = float(
                captured_value(f"{prefix_root}_total_price", 0.0) or 0.0
            )
            currency = captured_value(
                f"{prefix_root}_total_currency",
                "MXN",
            )

            if price_basis == "Precio por pasajero":
                unit_price = entered_price
                air_total = entered_price * flight_pax
            else:
                air_total = entered_price
                unit_price = air_total / flight_pax if flight_pax else 0.0

            if not air_total:
                continue

            proposal_rows.append(
                (f"Vuelo · opción {option_idx}", currency, air_total)
            )

            # Pick the first airline in this option for the visual brand.
            main_airline = ""
            for direction_probe in ("outbound", "return", "multicity"):
                for segment_probe in range(1, 10):
                    candidate = captured_value(
                        f"{prefix_root}_{direction_probe}_airline_{segment_probe}_name",
                        "",
                    )
                    if candidate:
                        main_airline = candidate
                        break
                if main_airline:
                    break

            air_logo = airline_logo(main_airline) if main_airline else None
            brand_cell = (
                air_logo
                if air_logo
                else P(main_airline.upper() if main_airline else "VUELO", "SIVEMonoBold")
            )

            option_header = Table(
                [
                    [
                        brand_cell,
                        Paragraph(
                            f"OPCIÓN {option_idx}<br/>"
                            f'<font name="Courier" size="7" color="#737B80">'
                            f"{trip_type.upper()}"
                            "</font>",
                            styles["SIVESection"],
                        ),
                    ]
                ],
                colWidths=[70 * mm, 105 * mm],
            )
            option_header.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.6, teal),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
                    ]
                )
            )

            option_flow = [
                option_header,
                Spacer(1, 1.8 * mm),
            ]

            price_table = Table(
                [
                    [
                        P("PAX", "SIVESmall"),
                        P("TARIFA / PAX", "SIVESmall"),
                        P("TOTAL OPCIÓN", "SIVESmall"),
                    ],
                    [
                        P(str(flight_pax), "SIVEMonoBold"),
                        P(money(unit_price, currency), "SIVEMonoBold"),
                        P(money(air_total, currency), "SIVEPrice"),
                    ],
                ],
                colWidths=[35 * mm, 65 * mm, 75 * mm],
            )
            price_table.setStyle(
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
            option_flow += [price_table, Spacer(1, 2 * mm)]

            segment_rows = []
            for direction in ("outbound", "return", "multicity"):
                segment_prefix = f"{prefix_root}_{direction}"
                for idx in range(1, 10):
                    airline = captured_value(
                        f"{segment_prefix}_airline_{idx}", ""
                    )
                    number = captured_value(
                        f"{segment_prefix}_number_{idx}", ""
                    )
                    origin = captured_value(
                        f"{segment_prefix}_origin_{idx}", ""
                    )
                    destination = captured_value(
                        f"{segment_prefix}_destination_{idx}", ""
                    )
                    dep_date = captured_value(
                        f"{segment_prefix}_departure_date_{idx}", None
                    )
                    dep_time = captured_value(
                        f"{segment_prefix}_departure_time_{idx}", None
                    )
                    arr_date = captured_value(
                        f"{segment_prefix}_arrival_date_{idx}", None
                    )
                    arr_time = captured_value(
                        f"{segment_prefix}_arrival_time_{idx}", None
                    )
                    fare = captured_value(
                        f"{segment_prefix}_fare_{idx}", ""
                    )
                    baggage = captured_value(
                        f"{segment_prefix}_baggage_{idx}", ""
                    )

                    if not any(
                        [airline, number, origin, destination, dep_date, arr_date]
                    ):
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
                            P(
                                f"{airline_iata} {number}".strip()
                                or airline
                                or "Vuelo",
                                "SIVEMonoBold",
                            ),
                            P(f"{origin or '—'} → {destination or '—'}", "SIVEMonoBold"),
                            P(
                                f"SAL {dep_text}<br/>LLE {arr_text}",
                                "SIVESmall",
                            ),
                            P(
                                f"{fare or ''}<br/>{baggage or ''}".strip(),
                                "SIVESmall",
                            ),
                        ]
                    )

            if segment_rows:
                seg_table = Table(
                    [
                        [
                            P("VUELO", "SIVESmall"),
                            P("RUTA", "SIVESmall"),
                            P("HORARIO", "SIVESmall"),
                            P("TARIFA / EQUIPAJE", "SIVESmall"),
                        ]
                    ]
                    + segment_rows,
                    colWidths=[36 * mm, 43 * mm, 54 * mm, 42 * mm],
                )
                seg_table.setStyle(
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
                option_flow += [seg_table, Spacer(1, 2 * mm)]

            # One EVA flight fee is shown as a commercial condition,
            # but is not included in a grand total while alternatives remain open.
            fee = float(
                captured_value("review_charge_total_flights", 0.0) or 0.0
            )
            if fee:
                option_flow.append(
                    P(
                        f"Cargo por servicio EVA aplicable al vuelo seleccionado: "
                        f"MXN {fee:,.2f}",
                        "SIVESmall",
                    )
                )

            option_flow.append(Spacer(1, 5 * mm))
            story.append(KeepTogether(option_flow))

    # -------------------- HOSPEDAJES / ALTERNATIVAS --------------------
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

            proposal_rows.append(
                (f"Hospedaje · opción {idx}", currency, price)
            )

            nights = (checkout - checkin).days if checkin and checkout else 0
            average = price / nights if price and nights > 0 else 0.0

            hotel_heading = Table(
                [
                    [
                        Paragraph(
                            f"HOSPEDAJE · OPCIÓN {idx}",
                            styles["SIVEMonoBold"],
                        ),
                        Paragraph(
                            city.upper() if city else "",
                            styles["SIVESmall"],
                        ),
                    ]
                ],
                colWidths=[100 * mm, 75 * mm],
            )
            hotel_heading.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.6, teal),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
                    ]
                )
            )

            block = [
                hotel_heading,
                Spacer(1, 1.4 * mm),
                P(hotel_name or "Hotel", "SIVEHotel"),
                Spacer(1, 1.2 * mm),
            ]

            details = Table(
                [
                    [P("Habitación", "SIVESmall"), P(room)],
                    [P("Huéspedes", "SIVESmall"), P(str(guests))],
                    [
                        P("Estancia", "SIVESmall"),
                        P(f"{checkin or '—'} → {checkout or '—'}"),
                    ],
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
                hotel_block = Table(
                    [[details, image]],
                    colWidths=[113 * mm, 62 * mm],
                )
                hotel_block.setStyle(
                    TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")])
                )
                block.append(hotel_block)
            else:
                block.append(details)

            block.append(Spacer(1, 2 * mm))

            links = []
            if hotel_url:
                links.append(
                    f'<a href="{hotel_url}" color="#2F9FA3">Página del hotel</a>'
                )
            if map_url:
                links.append(
                    f'<a href="{map_url}" color="#2F9FA3">Ver ubicación en Google Maps</a>'
                )
            if links:
                block += [
                    Paragraph("  ·  ".join(links), styles["SIVESmall"]),
                    Spacer(1, 2 * mm),
                ]

            price_box = Table(
                [
                    [
                        P("NOCHES", "SIVESmall"),
                        P("HABITACIONES", "SIVESmall"),
                        P("PROMEDIO / NOCHE", "SIVESmall"),
                        P("TOTAL OPCIÓN", "SIVESmall"),
                    ],
                    [
                        P(str(nights if nights > 0 else "—"), "SIVEMonoBold"),
                        P(str(rooms), "SIVEMonoBold"),
                        P(
                            money(average, currency) if average else "—",
                            "SIVEMonoBold",
                        ),
                        P(
                            money(price, currency) if price else "—",
                            "SIVEPrice",
                        ),
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
            block += [price_box, Spacer(1, 5 * mm)]
            story.append(KeepTogether(block))

    # -------------------- SERVICIOS ÚNICOS --------------------
    service_specs = [
        (
            "Seguro de viaje",
            "SEGURO DE VIAJE",
            "insurance_price",
            "insurance_currency",
            "review_charge_total_insurance",
        ),
        (
            "Traslados",
            "TRASLADO",
            "transfer_price",
            "transfer_currency",
            "review_charge_total_transfer",
        ),
        (
            "Renta de auto",
            "RENTA DE AUTO",
            "car_price",
            "car_currency",
            "review_charge_total_car",
        ),
        (
            "Tours o actividades",
            "TOUR O ACTIVIDAD",
            "tour_price",
            "tour_currency",
            "review_charge_total_tour",
        ),
        (
            "Otro servicio",
            "OTRO SERVICIO",
            "other_service_price",
            "other_service_currency",
            "review_charge_total_other",
        ),
    ]

    for component, title, price_key, currency_key, fee_key in service_specs:
        if component not in components:
            continue

        price = float(captured_value(price_key, 0.0) or 0.0)
        currency = captured_value(currency_key, "MXN")
        fee = float(captured_value(fee_key, 0.0) or 0.0)

        if not price:
            continue

        proposal_rows.append((title.title(), currency, price))

        if component == "Seguro de viaje":
            details = [
                ("Proveedor", captured_value("insurance_provider", "")),
                ("Plan", captured_value("insurance_plan", "")),
                ("Cobertura", captured_value("insurance_coverage", "")),
            ]
        elif component == "Traslados":
            details = [
                ("Tipo", captured_value("transfer_type", "")),
                (
                    "Ruta",
                    f"{captured_value('transfer_origin', '')} → "
                    f"{captured_value('transfer_destination', '')}",
                ),
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
                (
                    "Descripción",
                    captured_value("other_service_description", ""),
                ),
            ]

        rows = [
            [P(label, "SIVESmall"), P(value)]
            for label, value in details
            if value
        ]
        rows.append(
            [
                P("Precio propuesto", "SIVESmall"),
                P(money(price, currency), "SIVEMonoBold"),
            ]
        )
        if fee:
            rows.append(
                [
                    P("Cargo EVA aplicable", "SIVESmall"),
                    P(f"MXN {fee:,.2f}", "SIVEMonoBold"),
                ]
            )

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
        service_heading = Table(
            [[P(title, "SIVEMonoBold")]],
            colWidths=[175 * mm],
        )
        service_heading.setStyle(
            TableStyle(
                [
                    ("LINEBELOW", (0, 0), (-1, 0), 0.6, teal),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
                ]
            )
        )

        story.append(
            KeepTogether(
                [
                    service_heading,
                    Spacer(1, 1.5 * mm),
                    table,
                    Spacer(1, 5 * mm),
                ]
            )
        )

    # -------------------- IMPORTES PROPUESTOS --------------------
    proposal_heading = Table(
        [[P("IMPORTES PROPUESTOS", "SIVEMonoBold")]],
        colWidths=[175 * mm],
    )
    proposal_heading.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, teal),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
            ]
        )
    )
    story += [proposal_heading, Spacer(1, 1.5 * mm)]

    proposal_table_rows = [
        [P("OPCIÓN / SERVICIO", "SIVEMonoBold"), P("IMPORTE", "SIVEMonoBold")]
    ]
    for label, currency, amount in proposal_rows:
        proposal_table_rows.append(
            [P(label), P(money(amount, currency), "SIVEMonoBold")]
        )

    proposal_table = Table(
        proposal_table_rows,
        colWidths=[105 * mm, 70 * mm],
    )
    proposal_table.setStyle(
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
    story += [
        proposal_table,
        Spacer(1, 2 * mm),
        P(
            "Las alternativas no se suman entre sí. El total final se calculará "
            "cuando el cliente seleccione una opción de cada servicio y la "
            "cotización se marque como vendida.",
            "SIVESmall",
        ),
        Spacer(1, 4 * mm),
        P(
            "Precios sujetos a disponibilidad y cambios sin previo aviso. "
            "La cotización no representa una reservación hasta la confirmación correspondiente.",
            "SIVESmall",
        ),
    ]

    def footer(canvas, doc_obj):
        canvas.saveState()
        canvas.setStrokeColor(line)
        canvas.setLineWidth(0.4)
        canvas.line(
            14 * mm,
            10 * mm,
            A4[0] - 14 * mm,
            10 * mm,
        )
        canvas.setFont("Courier", 6.5)
        canvas.setFillColor(muted)
        canvas.drawString(
            14 * mm,
            6.5 * mm,
            "PROYECTO EVA · travel@proyectoeva.mx · SIVE",
        )
        canvas.drawRightString(
            A4[0] - 14 * mm,
            6.5 * mm,
            f"PÁGINA {doc_obj.page}",
        )
        canvas.restoreState()

    doc.build(
        story,
        onFirstPage=footer,
        onLaterPages=footer,
    )
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
        initialize_catalogs()

        if st.session_state.get("catalogs_loaded"):
            st.caption(
                f"Catálogos listos · "
                f"{len(airline_rows())} aerolíneas · "
                f"{len(airport_rows())} aeropuertos"
            )
        elif st.session_state.get("catalogs_error"):
            st.warning(
                "SIVE no pudo cargar los catálogos de Google Sheets. "
                f"{st.session_state.catalogs_error}"
            )

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
            draft["flight_options"] = max(
                int(draft.get("flight_options", 1) or 1),
                1,
            )
            draft.setdefault("flight_multicity_segments", {})

            def render_segment(
                prefix: str,
                segment_number: int,
                title: str,
            ) -> None:
                st.markdown(f"##### {title}")

                airline_col, flight_col = st.columns([1.55, 1])

                with airline_col:
                    selected_airline = airline_selector(
                        prefix,
                        segment_number,
                        captured,
                    )

                with flight_col:
                    iata_prefix = (
                        selected_airline["_iata"]
                        if selected_airline
                        else captured(
                            f"{prefix}_airline_{segment_number}_iata",
                            "",
                        )
                    )

                    flight_digits = st.text_input(
                        "Número de vuelo",
                        value=str(
                            captured(
                                f"{prefix}_number_{segment_number}",
                                "",
                            )
                            or ""
                        ),
                        placeholder="Ej. 123",
                        key=f"{prefix}_number_{segment_number}",
                        help=(
                            "Captura solo los dígitos. "
                            "SIVE agregará el IATA de la aerolínea."
                        ),
                    )

                    clean_digits = "".join(
                        ch
                        for ch in str(flight_digits)
                        if ch.isdigit()
                    )

                    if flight_digits != clean_digits:
                        st.warning(
                            "Captura únicamente los dígitos del vuelo."
                        )

                    flight_display = (
                        f"{iata_prefix} {clean_digits}".strip()
                    )

                    if flight_display:
                        st.markdown(
                            f'<div class="sive-card">'
                            f'<div class="sive-kicker">VUELO</div>'
                            f'<div class="sive-title sive-mono" '
                            f'style="font-size:1.28rem;">'
                            f'{flight_display}'
                            f'</div></div>',
                            unsafe_allow_html=True,
                        )

                st.caption("Ruta")
                origin_col, destination_col = st.columns(2)

                with origin_col:
                    airport_selector(
                        prefix,
                        segment_number,
                        "origin",
                        "Origen *",
                        captured,
                    )

                with destination_col:
                    airport_selector(
                        prefix,
                        segment_number,
                        "destination",
                        "Destino *",
                        captured,
                    )

                st.caption("Salida")
                dep_date, dep_time = st.columns(2)
                dep_date.date_input(
                    "Fecha de salida *",
                    value=captured(
                        f"{prefix}_departure_date_{segment_number}",
                        None,
                    ),
                    key=f"{prefix}_departure_date_{segment_number}",
                )
                dep_time.time_input(
                    "Hora de salida *",
                    value=captured(
                        f"{prefix}_departure_time_{segment_number}",
                        time(8, 0),
                    ),
                    key=f"{prefix}_departure_time_{segment_number}",
                )

                st.caption("Llegada")
                arr_date, arr_time = st.columns(2)
                arr_date.date_input(
                    "Fecha de llegada *",
                    value=captured(
                        f"{prefix}_arrival_date_{segment_number}",
                        None,
                    ),
                    key=f"{prefix}_arrival_date_{segment_number}",
                )
                arr_time.time_input(
                    "Hora de llegada *",
                    value=captured(
                        f"{prefix}_arrival_time_{segment_number}",
                        time(12, 0),
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
                    [
                        "Económica",
                        "Premium Economy",
                        "Ejecutiva",
                        "Primera",
                    ],
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

            def render_direction(
                option_idx: int,
                label: str,
                direction: str,
            ) -> None:
                prefix = f"flight_{option_idx}_{direction}"

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

                total_segments = int(stops) + 1

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

            def render_flight_option(option_idx: int) -> None:
                with st.container(border=True):
                    st.markdown(
                        f'<div class="sive-option-title">Opción de vuelo {option_idx}</div>',
                        unsafe_allow_html=True,
                    )

                    root = f"flight_{option_idx}"

                    trip_type = st.radio(
                        "Tipo de viaje",
                        [
                            "Viaje sencillo",
                            "Viaje redondo",
                            "Multidestino",
                        ],
                        horizontal=True,
                        key=f"{root}_trip_type",
                    )

                    if trip_type == "Viaje sencillo":
                        render_direction(
                            option_idx,
                            "Trayecto",
                            "outbound",
                        )

                    elif trip_type == "Viaje redondo":
                        render_direction(
                            option_idx,
                            "Ida",
                            "outbound",
                        )
                        st.divider()
                        render_direction(
                            option_idx,
                            "Regreso",
                            "return",
                        )

                    else:
                        st.info(
                            "En multidestino, cada tramo representa una ruta distinta."
                        )

                        segments = int(
                            draft["flight_multicity_segments"].get(
                                str(option_idx),
                                2,
                            )
                        )

                        for idx in range(segments):
                            render_segment(
                                f"{root}_multicity",
                                idx + 1,
                                f"Tramo {idx + 1}",
                            )
                            if idx < segments - 1:
                                st.divider()

                        add_col, remove_col = st.columns(2)
                        if add_col.button(
                            "+ Agregar tramo",
                            use_container_width=True,
                            key=f"add_multicity_segment_{option_idx}",
                        ):
                            persist_capture_state()
                            draft["flight_multicity_segments"][str(option_idx)] = (
                                segments + 1
                            )
                            st.rerun()

                        if remove_col.button(
                            "Quitar último tramo",
                            use_container_width=True,
                            disabled=segments <= 2,
                            key=f"remove_multicity_segment_{option_idx}",
                        ):
                            persist_capture_state()
                            draft["flight_multicity_segments"][str(option_idx)] = (
                                segments - 1
                            )
                            st.rerun()

                    st.markdown("### Precio de la opción")
                    st.caption(
                        "Captura exactamente lo que muestra la aerolínea. "
                        "SIVE hará el desglose por pasajero."
                    )

                    pax_col, basis_col = st.columns([1, 1.5])
                    flight_pax = pax_col.number_input(
                        "PAX en esta opción",
                        min_value=1,
                        value=max(
                            int(
                                captured(
                                    f"{root}_pax",
                                    draft.get("num_viajeros", 1),
                                )
                                or 1
                            ),
                            1,
                        ),
                        step=1,
                        key=f"{root}_pax",
                    )

                    price_basis = basis_col.radio(
                        "El precio capturado corresponde a",
                        [
                            "Total de la reserva",
                            "Precio por pasajero",
                        ],
                        horizontal=True,
                        key=f"{root}_price_basis",
                    )

                    price_col, currency_col = st.columns([1.4, 1])
                    entered_price = price_col.number_input(
                        "Importe mostrado por la aerolínea",
                        min_value=0.0,
                        step=100.0,
                        key=f"{root}_total_price",
                    )
                    currency = currency_col.selectbox(
                        "Moneda",
                        [
                            "MXN",
                            "USD",
                            "CAD",
                            "EUR",
                            "COP",
                            "PEN",
                            "BRL",
                        ],
                        key=f"{root}_total_currency",
                    )

                    if price_basis == "Precio por pasajero":
                        fare_per_pax = float(entered_price)
                        option_total = (
                            float(entered_price) * int(flight_pax)
                        )
                    else:
                        option_total = float(entered_price)
                        fare_per_pax = (
                            option_total / int(flight_pax)
                            if int(flight_pax) > 0
                            else 0.0
                        )

                    if entered_price > 0:
                        st.markdown(
                            f"""
                            <div class="sive-card">
                              <div class="sive-kicker">DESGLOSE DE LA OPCIÓN</div>
                              <div class="sive-card-text">
                                <span class="sive-mono">PAX {int(flight_pax):02d}</span>
                                &nbsp;·&nbsp;
                                Tarifa / PAX <strong>{currency} {fare_per_pax:,.2f}</strong>
                                &nbsp;·&nbsp;
                                Total opción <strong>{currency} {option_total:,.2f}</strong>
                              </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

            for option_idx in range(
                1,
                draft["flight_options"] + 1,
            ):
                render_flight_option(option_idx)

            add_flight_col, remove_flight_col = st.columns(2)
            if add_flight_col.button(
                "+ Agregar otra opción de vuelo",
                use_container_width=True,
                key="add_flight_option",
            ):
                persist_capture_state()
                draft["flight_options"] += 1
                st.rerun()

            if remove_flight_col.button(
                "Quitar última opción",
                use_container_width=True,
                disabled=draft["flight_options"] <= 1,
                key="remove_flight_option",
            ):
                persist_capture_state()
                draft["flight_options"] -= 1
                st.rerun()

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

                flight_options = max(
                    int(draft.get("flight_options", 1) or 1),
                    1,
                )
                any_flight = False

                for option_idx in range(1, flight_options + 1):
                    root = f"flight_{option_idx}"
                    trip_type = captured(
                        f"{root}_trip_type",
                        "Viaje sencillo",
                    )
                    flight_pax = max(
                        int(
                            captured(
                                f"{root}_pax",
                                draft.get("num_viajeros", 1),
                            )
                            or 1
                        ),
                        1,
                    )
                    entered_price = float(
                        captured(f"{root}_total_price", 0.0) or 0.0
                    )
                    currency = captured(
                        f"{root}_total_currency",
                        "MXN",
                    )
                    price_basis = captured(
                        f"{root}_price_basis",
                        "Total de la reserva",
                    )

                    if not entered_price:
                        continue

                    any_flight = True

                    if price_basis == "Precio por pasajero":
                        fare_per_pax = entered_price
                        option_total = entered_price * flight_pax
                    else:
                        option_total = entered_price
                        fare_per_pax = (
                            option_total / flight_pax
                            if flight_pax
                            else 0.0
                        )

                    main_airline = ""
                    for direction_probe in ("outbound", "return", "multicity"):
                        for segment_probe in range(1, 10):
                            candidate = captured(
                                f"{root}_{direction_probe}_airline_{segment_probe}_name",
                                "",
                            )
                            if candidate:
                                main_airline = candidate
                                break
                        if main_airline:
                            break

                    airline_label = (
                        f"{main_airline} · " if main_airline else ""
                    )

                    st.markdown(
                        f'<div class="sive-option-title">'
                        f'{airline_label}Opción de vuelo {option_idx}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<div class="sive-option-meta">{trip_type} · PAX {flight_pax:02d}</div>',
                        unsafe_allow_html=True,
                    )
                    st.write(
                        f"Tarifa por pasajero: **{currency} {fare_per_pax:,.2f}**"
                    )
                    st.write(
                        f"Total de esta opción: **{currency} {option_total:,.2f}**"
                    )

                    if option_idx < flight_options:
                        st.divider()

                if not any_flight:
                    st.caption("No hay opciones de vuelo con precio capturado.")

                render_charge(
                    "flights",
                    chargeable_services["Vuelos"],
                )

                if st.button(
                    "Editar vuelos",
                    key="review_edit_flights",
                ):
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
                    st.caption(f"Opción de hospedaje {hotel_idx}")
                    st.markdown(
                        f'<div class="sive-option-title">{hotel_name or "Hotel"}</div>',
                        unsafe_allow_html=True,
                    )
                    if hotel_city:
                        st.markdown(
                            f'<div class="sive-option-meta">{hotel_city}</div>',
                            unsafe_allow_html=True,
                        )
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
        st.markdown("#### Importes propuestos")
        st.caption(
            "Las alternativas se muestran por separado. No se suman entre sí "
            "mientras el cliente no haya elegido qué opción comprar."
        )

        proposal_lines = []

        if "Vuelos" in draft["componentes"]:
            for option_idx in range(
                1,
                max(int(draft.get("flight_options", 1) or 1), 1) + 1,
            ):
                root = f"flight_{option_idx}"
                entered = float(
                    captured(f"{root}_total_price", 0.0) or 0.0
                )
                currency = captured(
                    f"{root}_total_currency",
                    "MXN",
                )
                pax = max(
                    int(
                        captured(
                            f"{root}_pax",
                            draft.get("num_viajeros", 1),
                        )
                        or 1
                    ),
                    1,
                )
                basis = captured(
                    f"{root}_price_basis",
                    "Total de la reserva",
                )
                total = (
                    entered * pax
                    if basis == "Precio por pasajero"
                    else entered
                )
                if total:
                    proposal_lines.append(
                        (
                            f"Vuelo · opción {option_idx}",
                            currency,
                            total,
                        )
                    )

        if "Hospedaje" in draft["componentes"]:
            for hotel_idx in range(
                1,
                max(int(draft.get("hotel_options", 1) or 1), 1) + 1,
            ):
                amount = float(
                    captured(f"hotel_price_{hotel_idx}", 0.0) or 0.0
                )
                currency = captured(
                    f"hotel_currency_{hotel_idx}",
                    "MXN",
                )
                if amount:
                    proposal_lines.append(
                        (
                            f"Hospedaje · opción {hotel_idx}",
                            currency,
                            amount,
                        )
                    )

        service_rows = [
            (
                "Seguro de viaje",
                "Seguro",
                "insurance_price",
                "insurance_currency",
            ),
            (
                "Traslados",
                "Traslado",
                "transfer_price",
                "transfer_currency",
            ),
            (
                "Renta de auto",
                "Renta de auto",
                "car_price",
                "car_currency",
            ),
            (
                "Tours o actividades",
                "Tour / actividad",
                "tour_price",
                "tour_currency",
            ),
            (
                "Otro servicio",
                "Otro servicio",
                "other_service_price",
                "other_service_currency",
            ),
        ]

        for component, label, price_key, currency_key in service_rows:
            if component in draft["componentes"]:
                amount = float(captured(price_key, 0.0) or 0.0)
                currency = captured(currency_key, "MXN")
                if amount:
                    proposal_lines.append(
                        (label, currency, amount)
                    )

        if proposal_lines:
            for label, currency, amount in proposal_lines:
                st.write(
                    f"**{label}:** {currency} {amount:,.2f}"
                )
        else:
            st.caption("Aún no hay importes capturados.")

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
            amount = float(
                captured(
                    f"review_charge_total_{key}",
                    0.0,
                )
                or 0.0
            )
            concept = captured(
                f"review_charge_text_{key}",
                "",
            )
            apply_mode = captured(
                f"review_charge_apply_{key}",
                "Por cotización",
            )
            if amount > 0:
                charge_rows.append(
                    (
                        label,
                        concept or "Cargo por servicio",
                        amount,
                        apply_mode,
                    )
                )
                total_charge_mxn += amount

        if charge_rows:
            for label, concept, amount, apply_mode in charge_rows:
                st.write(
                    f"**{label}:** {concept} · "
                    f"${amount:,.2f} MXN · {apply_mode.lower()}"
                )
            st.success(
                f"Cargos EVA potenciales: ${total_charge_mxn:,.2f} MXN"
            )
        else:
            st.caption(
                "Esta cotización no tiene cargos por servicio."
            )

        st.markdown("#### Total final")
        st.info(
            "SIVE no calcula un total general en esta etapa porque hay "
            "alternativas de vuelo y/o hospedaje. El total se calculará "
            "cuando el cliente seleccione sus opciones y la cotización "
            "se marque como **Vendida**."
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

        st.markdown("#### Vista previa de la propuesta")

        eva_brand_ok = _eva_logo_path() is not None
        if eva_brand_ok:
            st.caption("✓ Logo de Proyecto EVA cargado")
        else:
            st.warning(
                "No encuentro el logo de EVA. Sube `assets/eva_logo.png` "
                "o `eva_logo_crop.png` a la raíz del repositorio."
            )

        if "Vuelos" in draft.get("componentes", []):
            found_airline_logo = False
            for option_idx in range(
                1,
                max(int(draft.get("flight_options", 1) or 1), 1) + 1,
            ):
                root = f"flight_{option_idx}"
                for direction_probe in ("outbound", "return", "multicity"):
                    for segment_probe in range(1, 10):
                        airline = captured(
                            f"{root}_{direction_probe}_airline_{segment_probe}",
                            "",
                        )
                        if airline and _airline_logo_source(draft, airline):
                            found_airline_logo = True
                            break
                    if found_airline_logo:
                        break
                if found_airline_logo:
                    break

            if found_airline_logo:
                st.caption("✓ Branding de aerolínea disponible para el PDF")
            else:
                st.caption(
                    "La aerolínea está identificada desde 10_CAT_AEROLINEAS. "
                    "Si su LOGO_URL está vacío, el PDF mostrará el nombre "
                    "y código IATA sin logo."
                )

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
    initialize_catalogs()
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
