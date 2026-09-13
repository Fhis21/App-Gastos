import flet as ft
from datetime import datetime
import sqlite3
import pandas as pd
import os

# Si estamos en Render con el disco montado en /data, lo guardamos ahí. 
# Si estamos probando en la PC, lo guardamos localmente.
if os.path.exists("/data"):
    DB_FILE = "/data/control_gastos.db"
else:
    DB_FILE = "control_gastos.db"
PRESUPUESTO_SEMANAL = 100000.0  # Tu límite semanal

def inicializar_bd():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gastos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            concepto TEXT,
            monto REAL,
            categoria TEXT,
            medio_pago TEXT,
            fecha TEXT
        )
    ''')
    try:
        cursor.execute("ALTER TABLE gastos ADD COLUMN medio_pago TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

def cargar_gastos_db():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM gastos", conn)
    conn.close()
    return df.to_dict(orient="records")

def main(page: ft.Page):
    page.title = "Control de Gastos Personal"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 20
    page.bgcolor = "#f8fafc"

    inicializar_bd()
    lista_gastos = cargar_gastos_db()

    titulo_app = ft.Text("Control de Gastos", size=26, weight=ft.FontWeight.BOLD, color="#1e293b")
    
    ANCHO_CAMPOS = 350

    input_concepto = ft.TextField(
        label="Nombre del Gasto (ej. Supermercado, Cine)", 
        border_radius=10, 
        filled=True, 
        bgcolor="#ffffff",
        width=ANCHO_CAMPOS
    )
    
    input_monto = ft.TextField(
        label="Monto ($)", 
        keyboard_type=ft.KeyboardType.NUMBER, 
        border_radius=10, 
        filled=True, 
        bgcolor="#ffffff",
        width=ANCHO_CAMPOS
    )

    dropdown_categoria = ft.Dropdown(
        label="Categoría",
        border_radius=10,
        filled=True,
        bgcolor="#ffffff",
        border_color="#cbd5e1",
        focused_border_color="#0f766e",
        label_style=ft.TextStyle(color="#64748b", size=14),
        color="#1e293b",
        width=ANCHO_CAMPOS,
        options=[
            ft.dropdown.Option("Alimentación"),
            ft.dropdown.Option("Entretenimiento"),
            ft.dropdown.Option("Servicios"),
            ft.dropdown.Option("Suscripciones"),
            ft.dropdown.Option("Transporte"),
            ft.dropdown.Option("Salud"),
            ft.dropdown.Option("Hogar"),
            ft.dropdown.Option("Vestuario"),
            ft.dropdown.Option("Vacaciones"),
            ft.dropdown.Option("Comidita Rica"),
            ft.dropdown.Option("Comida Trabajo"),
            ft.dropdown.Option("Prestamos"),
            ft.dropdown.Option("Otros"),
        ],
    )

    dropdown_medio_pago = ft.Dropdown(
        label="Medio de Pago",
        border_radius=10,
        filled=True,
        bgcolor="#ffffff",
        border_color="#cbd5e1",
        focused_border_color="#0f766e",
        label_style=ft.TextStyle(color="#64748b", size=14),
        color="#1e293b",
        width=ANCHO_CAMPOS,
        options=[
            ft.dropdown.Option("Efectivo"),
            ft.dropdown.Option("Débito"),
            ft.dropdown.Option("Crédito"),
        ],
    )

    columna_resultados = ft.Column(scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    contenedor_resumen_categorias = ft.Column(spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    contenedor_resumen_pagos = ft.Column(spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER) # Nuevo contenedor
    
    texto_presupuesto = ft.Text("Semana: $0.00 / $100,000.00", size=15, weight=ft.FontWeight.BOLD, color="#1e293b")
    barra_progreso = ft.ProgressBar(value=0.0, width=350, color="#0f766e", bgcolor="#e2e8f0")
    texto_total = ft.Text("Total Histórico: $0.00", size=16, weight=ft.FontWeight.BOLD, color="#64748b")

    def insertar_en_db(concepto, monto, categoria, medio_pago, fecha):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO gastos (concepto, monto, categoria, medio_pago, fecha) VALUES (?, ?, ?, ?, ?)", 
                       (concepto, monto, categoria, medio_pago, fecha))
        conn.commit()
        conn.close()

    def eliminar_de_db(gasto_id):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM gastos WHERE id = ?", (gasto_id,))
        conn.commit()
        conn.close()

    def agregar_gasto(e):
        if not input_concepto.value or not input_monto.value or not dropdown_categoria.value or not dropdown_medio_pago.value:
            page.snack_bar = ft.SnackBar(ft.Text("Por favor completa todos los campos"), bgcolor="#ef4444")
            page.snack_bar.open = True
            page.update()
            return

        try:
            monto_num = float(input_monto.value)
        except ValueError:
            page.snack_bar = ft.SnackBar(ft.Text("El monto debe ser un número válido"), bgcolor="#ef4444")
            page.snack_bar.open = True
            page.update()
            return

        fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")
        insertar_en_db(input_concepto.value, monto_num, dropdown_categoria.value, dropdown_medio_pago.value, fecha_actual)

        nonlocal lista_gastos
        lista_gastos = cargar_gastos_db()

        # Limpiar formulario
        input_concepto.value = ""
        input_monto.value = ""
        dropdown_categoria.value = None
        dropdown_medio_pago.value = None

        actualizar_pantalla()

    def eliminar_gasto(gasto_id):
        eliminar_de_db(gasto_id)
        nonlocal lista_gastos
        lista_gastos = cargar_gastos_db()
        actualizar_pantalla()
        page.snack_bar = ft.SnackBar(ft.Text("Gasto eliminado correctamente"), bgcolor="#0284c7")
        page.snack_bar.open = True
        page.update()

    def actualizar_pantalla():
        columna_resultados.controls.clear()
        contenedor_resumen_categorias.controls.clear()
        contenedor_resumen_pagos.controls.clear()
        total_historico = 0
        total_semana = 0

        hoy = datetime.now()
        anio_actual, semana_actual, _ = hoy.isocalendar()

        if lista_gastos:
            df = pd.DataFrame(lista_gastos)
            df['fecha_dt'] = pd.to_datetime(df['fecha'], format="%d/%m/%Y %H:%M")
            df['anio'] = df['fecha_dt'].dt.isocalendar().year
            df['semana'] = df['fecha_dt'].dt.isocalendar().week

            df_semana = df[(df['anio'] == anio_actual) & (df['semana'] == semana_actual)]
            total_semana = df_semana['monto'].sum()

        # 1. Historial de Gastos
        for gasto in reversed(lista_gastos):
            total_historico += gasto["monto"]
            g_id = gasto["id"]
            medio = gasto.get("medio_pago", "No especificado")
            
            btn_eliminar = ft.TextButton(
                content="Eliminar",
                style=ft.ButtonStyle(color="#ef4444"),
                on_click=lambda e, gid=g_id: eliminar_gasto(gid)
            )

            tarjeta = ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(gasto["concepto"], weight=ft.FontWeight.BOLD, size=16, color="#1e293b"),
                            ft.Text(f"${gasto['monto']:.2f}", weight=ft.FontWeight.BOLD, color="#0d9488", size=16)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Row([
                            ft.Text(f"Cat: {gasto['categoria']} | Pago: {medio}", size=12, color="#64748b"),
                            ft.Text(gasto["fecha"], size=12, color="#64748b")
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Row([
                            btn_eliminar
                        ], alignment=ft.MainAxisAlignment.END)
                    ]),
                    padding=15,
                    bgcolor="#ffffff",
                    border_radius=10,
                    width=350
                )
            )
            columna_resultados.controls.append(tarjeta)

        if lista_gastos:
            # 2. Desglose por categoría ordenado de mayor a menor
            totales_cat = df.groupby("categoria")["monto"].sum().reset_index()
            totales_cat = totales_cat.sort_values(by="monto", ascending=False)
            
            for _, row in totales_cat.iterrows():
                fila_cat = ft.Row([
                    ft.Text(row["categoria"], size=13, color="#475569"),
                    ft.Text(f"${row['monto']:.2f}", size=13, weight=ft.FontWeight.BOLD, color="#334155")
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, width=350)
                contenedor_resumen_categorias.controls.append(fila_cat)

            # 3. Desglose por Medio de Pago (Efectivo, Débito, Crédito)
            totales_pago = df.groupby("medio_pago")["monto"].sum().reset_index()
            totales_pago = totales_pago.sort_values(by="monto", ascending=False)

            for _, row in totales_pago.iterrows():
                fila_pago = ft.Row([
                    ft.Text(f"💳 {row['medio_pago']}", size=13, color="#475569"),
                    ft.Text(f"${row['monto']:.2f}", size=13, weight=ft.FontWeight.BOLD, color="#0f766e")
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, width=350)
                contenedor_resumen_pagos.controls.append(fila_pago)

        texto_presupuesto.value = f"Gasto esta semana: ${total_semana:,.2f} / ${PRESUPUESTO_SEMANAL:,.2f}"
        
        porcentaje = min(total_semana / PRESUPUESTO_SEMANAL, 1.0)
        barra_progreso.value = porcentaje
        
        if total_semana > PRESUPUESTO_SEMANAL:
            barra_progreso.color = "#ef4444"
            texto_presupuesto.color = "#ef4444"
        else:
            barra_progreso.color = "#0f766e"
            texto_presupuesto.color = "#1e293b"

        texto_total.value = f"Total Histórico Acumulado: ${total_historico:,.2f}"
        page.update()

    boton_guardar = ft.Button(
        content=ft.Text("Registrar Gasto", color="#ffffff"),
        on_click=agregar_gasto,
        bgcolor="#0f766e",
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        width=350
    )

    card_presupuesto = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.Text("Gastos Semanales", size=14, weight=ft.FontWeight.BOLD, color="#64748b"),
                texto_presupuesto,
                barra_progreso
            ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=15,
            bgcolor="#ffffff",
            border_radius=10,
            width=350
        )
    )

    pestanas = ft.Tabs(
        length=2,
        selected_index=0,
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[
                ft.TabBar(
                    tabs=[
                        ft.Tab(label="Registrar y Ver"),
                        ft.Tab(label="Resumen y Metas"),
                    ],
                ),
                ft.TabBarView(
                    expand=True,
                    controls=[
                        ft.Container(
                            content=ft.Column([
                                ft.Divider(height=10, color="transparent"),
                                input_concepto,
                                input_monto,
                                dropdown_categoria,
                                dropdown_medio_pago,
                                ft.Divider(height=5, color="transparent"),
                                boton_guardar,
                                ft.Divider(height=20, color="transparent"),
                                ft.Text("Historial de Gastos:", weight=ft.FontWeight.BOLD, size=16, color="#475569"),
                                columna_resultados
                            ], scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            padding=10
                        ),
                        ft.Container(
                            content=ft.Column([
                                ft.Divider(height=10, color="transparent"),
                                card_presupuesto,
                                ft.Divider(height=10, color="transparent"),
                                texto_total,
                                ft.Divider(height=15, color="transparent"),
                                ft.Text("Gastos por Medio de Pago:", weight=ft.FontWeight.BOLD, size=14, color="#475569"),
                                contenedor_resumen_pagos, # <-- Sección nueva de medios de pago
                                ft.Divider(height=15, color="transparent"),
                                ft.Text("Desglose por Categoría (Mayor a Menor):", weight=ft.FontWeight.BOLD, size=14, color="#475569"),
                                contenedor_resumen_categorias
                            ], scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            padding=10
                        ),
                    ],
                ),
            ],
        ),
    )

    page.add(titulo_app, ft.Container(content=pestanas, expand=True))

    if lista_gastos:
        actualizar_pantalla()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8550))
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=port)