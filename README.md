# Cotizador Proyecto EVA · versión 0.1

Primera versión funcional conectada con la Hoja Maestra EVA mediante Apps Script.

## Incluye

- Pantalla de inicio.
- Registro y búsqueda de pasajeros independientes.
- Creación de cotizaciones básicas.
- Relación de pasajeros con cotizaciones.
- Consulta de cotizaciones existentes.
- Sincronización manual con Google Sheets.
- Correo institucional fijo: `travel@proyectoeva.mx`.

## Configuración local

1. Duplica `.streamlit/secrets.toml.example` y nómbralo `.streamlit/secrets.toml`.
2. Coloca la URL `/exec` y la clave privada generada en Apps Script.
3. Instala dependencias:

```bash
pip install -r requirements.txt
```

4. Ejecuta:

```bash
streamlit run streamlit_app.py
```

## Configuración en Streamlit Community Cloud

En **App settings → Secrets**, pega:

```toml
[eva]
api_url = "TU_URL_EXEC"
api_token = "TU_CLAVE_PRIVADA"
```

La clave privada no debe subirse a GitHub.

## Próxima etapa

- Constructor de opciones de viaje.
- Tarjetas dinámicas de vuelos y conexiones.
- Hospedajes y servicios adicionales.
- Costos estimados y precios de venta.
- Vista previa y generación del PDF con identidad EVA.
