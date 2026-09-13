import flet as ft
from datetime import datetime, timedelta
import os
import pandas as pd
import sqlalchemy

# Obtenemos la URL de la base de datos desde las variables de entorno de Render
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def obtener_conexion():
    engine = sqlalchemy.create_engine(DATABASE_URL)
    return engine

def inicializar_bd():
    engine = obtener_conexion()
    with engine.begin() as conn:
        conn.execute(sqlalchemy.text('''
            CREATE TABLE IF NOT EXISTS gastos (
                id SERIAL PRIMARY KEY,
                concepto TEXT,
                monto REAL,
                categoria TEXT,
                medio_pago TEXT,
                fecha TEXT
            )
        '''))

def cargar_gastos_db():
    try:
        engine = obtener_conexion()
        df = pd.read_sql("SELECT * FROM gastos", engine)
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"Error cargando datos: {e}")
        return []

PRESUPUESTO_SEMANAL = 100000.0  # Tu límite semanal

def main(page: ft.Page):
    page.title = "Control de Gastos Personal"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 20
    page.bgcolor = "#f8fafc"

    if DATABASE_URL:
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
    
    # Contenedores de resúmenes separados
    contenedor_resumen_categorias_semana = ft.Column(spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    contenedor_resumen_categorias = ft.Column(spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    contenedor_resumen_pagos = ft.Column(spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    contenedor_semanas_mes = ft.Column(spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    
    texto_presupuesto = ft.Text("Semana: $0.00 / $100,000.00", size=15, weight=ft.FontWeight.BOLD, color="#1e293b")
    barra_progreso = ft.ProgressBar(value=0.0, width=350, color="#0f766e", bgcolor="#e2e8f0")
    texto_total = ft.Text("Total Histórico: $0.00", size=16, weight=ft.FontWeight.BOLD, color="#64748b")

    def insertar_en_db(concepto, monto, categoria, medio_pago, fecha):
        engine = obtener_conexion()
        with engine.begin() as conn:
            conn.execute(
                sqlalchemy.text("INSERT INTO gastos (concepto, monto, categoria, medio_pago, fecha) VALUES (:c, :m, :cat, :p, :f)"),
                {"c": concepto, "m": monto, "cat": categoria, "p": medio_pago, "f": fecha}
            )

    def eliminar_de_db(gasto_id):
        engine = obtener_conexion()
        with engine.begin() as conn:
            conn.execute(
                sqlalchemy.text("DELETE FROM gastos WHERE id = :id"),
                {"id": gasto_id}
            )

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
        try:
            insertar_en_db(input_concepto.value, monto_num, dropdown_categoria.value, dropdown_medio_pago.value, fecha_actual)
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Error al guardar: {ex}"), bgcolor="#ef4444")
            page.snack_bar.open = True
            page.update()
            return

        nonlocal lista_gastos
        lista_gastos = cargar_gastos_db()

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
        contenedor_resumen_categorias_semana.controls.clear()
        contenedor_resumen_categorias.controls.clear()
        contenedor_resumen_pagos.controls.clear()
        contenedor_semanas_mes.controls.clear()
        
        total_historico = 0
        total_semana = 0

        ahora = datetime.now()
        inicio_lunes = ahora - timedelta(days=ahora.weekday())
        inicio_lunes = inicio_lunes.replace(hour=0, minute=0, second=0, microsecond=0)

        if lista_gastos:
            df = pd.DataFrame(lista_gastos)
            df['fecha_dt'] = pd.to_datetime(df['fecha'], format="%d/%m/%Y %H:%M")
            
            # Gasto de la semana actual (desde este lunes)
            df_semana = df[df['fecha_dt'] >= inicio_lunes].copy()
            total_semana = df_semana['monto'].sum()

        # 1. Historial de Gastos (Pestaña Registrar)
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
            # 2. Desglose de Categorías de la Semana Actual
            if not df_semana.empty:
                totales_cat_semana = df_semana.groupby("categoria")["monto"].sum().reset_index()
                totales_cat_semana = totales_cat_semana.sort_values(by="monto", ascending=False)
                
                for _, row in totales_cat_semana.iterrows():
                    fila_cat_sem = ft.Row([
                        ft.Text(row["categoria"], size=13, color="#475569"),
                        ft.Text(f"${row['monto']:.2f}", size=13, weight=ft.FontWeight.BOLD, color="#334155")
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, width=350)
                    contenedor_resumen_categorias_semana.controls.append(fila_cat_sem)
            else:
                contenedor_resumen_categorias_semana.controls.append(
                    ft.Text("Sin gastos registrados esta semana", size=12, color="#94a3b8")
                )

            # 3. Desglose por Semanas del Mes Actual
            df['mes_anio'] = df['fecha_dt'].dt.to_period('M')
            mes_actual_periodo = pd.Period(ahora, freq='M')
            
            df_mes_actual = df[df['mes_anio'] == mes_actual_periodo].copy()
            if not df_mes_actual.empty:
                df_mes_actual['semana_del_mes'] = df_mes_actual['fecha_dt'].apply(lambda d: (d.day - 1) // 7 + 1)
                totales_semanas = df_mes_actual.groupby('semana_del_mes')['monto'].sum().reset_index()
                
                for _, row in totales_semanas.iterrows():
                    num_sem = int(row['semana_del_mes'])
                    fila_sem = ft.Row([
                        ft.Text(f"📅 Semana {num_sem} del mes", size=13, color="#475569"),
                        ft.Text(f"${row['monto']:.2f}", size=13, weight=ft.FontWeight.BOLD, color="#0f766e")
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, width=350)
                    contenedor_semanas_mes.controls.append(fila_sem)
            else:
                contenedor_semanas_mes.controls.append(
                    ft.Text("Sin gastos registrados este mes", size=12, color="#94a3b8")
                )

            # 4. Desglose por Medio de Pago (Histórico)
            totales_pago = df.groupby("medio_pago")["monto"].sum().reset_index()
            totales_pago = totales_pago.sort_values(by="monto", ascending=False)

            for _, row in totales_pago.iterrows():
                fila_pago = ft.Row([
                    ft.Text(f"💳 {row['medio_pago']}", size=13, color="#475569"),
                    ft.Text(f"${row['monto']:.2f}", size=13, weight=ft.FontWeight.BOLD, color="#0f766e")
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, width=350)
                contenedor_resumen_pagos.controls.append(fila_pago)

            # 5. Desglose por categoría ordenado de mayor a menor (Histórico)
            totales_cat = df.groupby("categoria")["monto"].sum().reset_index()
            totales_cat = totales_cat.sort_values(by="monto", ascending=False)
            
            for _, row in totales_cat.iterrows():
                fila_cat = ft.Row([
                    ft.Text(row["categoria"], size=13, color="#475569"),
                    ft.Text(f"${row['monto']:.2f}", size=13, weight=ft.FontWeight.BOLD, color="#334155")
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, width=350)
                contenedor_resumen_categorias.controls.append(fila_cat)

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
                ft.Text("Gastos de la Semana Actual (Desde el lunes)", size=14, weight=ft.FontWeight.BOLD, color="#64748b"),
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
        length=3,
        selected_index=0,
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[
                ft.TabBar(
                    tabs=[
                        ft.Tab(label="Registrar"),
                        ft.Tab(label="Semana Actual"),
                        ft.Tab(label="Histórico y Semanas"),
                    ],
                ),
                ft.TabBarView(
                    expand=True,
                    controls=[
                        # PESTAÑA 1: Registrar y Ver Historial
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
                        # PESTAÑA 2: Semana Actual + Categorías de la semana
                        ft.Container(
                            content=ft.Column([
                                ft.Divider(height=10, color="transparent"),
                                card_presupuesto,
                                ft.Divider(height=15, color="transparent"),
                                ft.Text("Categorías de esta semana:", weight=ft.FontWeight.BOLD, size=14, color="#475569"),
                                contenedor_resumen_categorias_semana
                            ], scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            padding=10
                        ),
                        # PESTAÑA 3: Total Histórico y Desglose de Semanas del Mes + Categorías/Pagos
                        ft.Container(
                            content=ft.Column([
                                ft.Divider(height=10, color="transparent"),
                                texto_total,
                                ft.Divider(height=15, color="transparent"),
                                ft.Text("Desglose por Semanas del Mes Actual:", weight=ft.FontWeight.BOLD, size=14, color="#475569"),
                                contenedor_semanas_mes,
                                ft.Divider(height=15, color="transparent"),
                                ft.Text("Gastos por Medio de Pago (Histórico):", weight=ft.FontWeight.BOLD, size=14, color="#475569"),
                                contenedor_resumen_pagos,
                                ft.Divider(height=15, color="transparent"),
                                ft.Text("Desglose por Categoría (Histórico):", weight=ft.FontWeight.BOLD, size=14, color="#475569"),
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
    
    #Version 001 Domingo 13 de Septiembre del 2026