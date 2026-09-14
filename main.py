import flet as ft
from datetime import datetime, timedelta
import os
import pandas as pd
import sqlalchemy
import urllib.parse

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
    page.theme_mode = ft.ThemeMode.DARK  # Arranca en oscuro por defecto
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 20
    page.bgcolor = "#0f172a"  # Fondo oscuro inicial

    if DATABASE_URL:
        inicializar_bd()
    
    lista_gastos = cargar_gastos_db()

    # Función para alternar el tema claro/oscuro
    def cambiar_tema(e):
        if page.theme_mode == ft.ThemeMode.DARK:
            page.theme_mode = ft.ThemeMode.LIGHT
            page.bgcolor = "#f8fafc"
            btn_tema.icon = ft.Icons.DARK_MODE
            btn_tema.tooltip = "Cambiar a Modo Oscuro"
        else:
            page.theme_mode = ft.ThemeMode.DARK
            page.bgcolor = "#0f172a"
            btn_tema.icon = ft.Icons.LIGHT_MODE
            btn_tema.tooltip = "Cambiar a Modo Claro"
        page.update()

    btn_tema = ft.IconButton(
        icon=ft.Icons.LIGHT_MODE,
        tooltip="Cambiar a Modo Claro",
        on_click=cambiar_tema,
        icon_color="#f8fafc"
    )

    titulo_app = ft.Text("Control de Gastos", size=26, weight=ft.FontWeight.BOLD, color="#f8fafc")
    
    header_row = ft.Row(
        [titulo_app, btn_tema],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        width=350
    )

    ANCHO_CAMPOS = 350

    input_concepto = ft.TextField(
        label="Nombre del Gasto (ej. Supermercado, Cine)", 
        border_radius=10, 
        filled=True, 
        bgcolor="#1e293b",
        color="#f8fafc",
        label_style=ft.TextStyle(color="#94a3b8"),
        border_color="#334155",
        focused_border_color="#14b8a6",
        width=ANCHO_CAMPOS
    )
    
    input_monto = ft.TextField(
        label="Monto ($)", 
        keyboard_type=ft.KeyboardType.NUMBER, 
        border_radius=10, 
        filled=True, 
        bgcolor="#1e293b",
        color="#f8fafc",
        label_style=ft.TextStyle(color="#94a3b8"),
        border_color="#334155",
        focused_border_color="#14b8a6",
        width=ANCHO_CAMPOS
    )

    LISTA_CATEGORIAS = [
        "Alimentación", "Entretenimiento", "Servicios", "Suscripciones",
        "Transporte", "Salud", "Hogar", "Vestuario", "Vacaciones",
        "Comidita Rica", "Comida Trabajo", "Prestamos", "Otros"
    ]

    LISTA_MEDIOS_PAGO = ["Efectivo", "Débito", "Crédito"]

    dropdown_categoria = ft.Dropdown(
        label="Categoría",
        border_radius=10,
        filled=True,
        bgcolor="#1e293b",
        border_color="#334155",
        focused_border_color="#14b8a6",
        label_style=ft.TextStyle(color="#94a3b8", size=14),
        color="#f8fafc",
        width=ANCHO_CAMPOS,
        options=[ft.dropdown.Option(cat) for cat in LISTA_CATEGORIAS],
    )

    dropdown_medio_pago = ft.Dropdown(
        label="Medio de Pago",
        border_radius=10,
        filled=True,
        bgcolor="#1e293b",
        border_color="#334155",
        focused_border_color="#14b8a6",
        label_style=ft.TextStyle(color="#94a3b8", size=14),
        color="#f8fafc",
        width=ANCHO_CAMPOS,
        options=[ft.dropdown.Option(pago) for pago in LISTA_MEDIOS_PAGO],
    )

    columna_resultados = ft.Column(scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    
    contenedor_resumen_categorias_semana = ft.Column(spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    contenedor_resumen_categorias = ft.Column(spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    contenedor_resumen_pagos = ft.Column(spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    contenedor_semanas_mes = ft.Column(spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    
    texto_presupuesto = ft.Text("Semana: $0.00 / $100,000.00", size=15, weight=ft.FontWeight.BOLD, color="#f8fafc")
    barra_progreso = ft.ProgressBar(value=0.0, width=350, color="#14b8a6", bgcolor="#334155")
    texto_total_historico = ft.Text("Total Histórico Acumulado: $0.00", size=15, weight=ft.FontWeight.BOLD, color="#94a3b8")
    texto_total_mes = ft.Text("Total del Periodo Seleccionado: $0.00", size=15, weight=ft.FontWeight.BOLD, color="#2dd4bf")

    # Dropdown para filtrar histórico por Mes/Año (sin on_change)
    dropdown_mes_filtro = ft.Dropdown(
        label="Filtrar Histórico por Mes",
        border_radius=10,
        filled=True,
        bgcolor="#1e293b",
        border_color="#334155",
        focused_border_color="#14b8a6",
        label_style=ft.TextStyle(color="#94a3b8", size=14),
        color="#f8fafc",
        width=ANCHO_CAMPOS
    )

    def actualizar_opciones_meses(df_gastos):
        if df_gastos.empty:
            dropdown_mes_filtro.options = [ft.dropdown.Option("Todos")]
            dropdown_mes_filtro.value = "Todos"
            return
        
        meses_unicos = df_gastos['fecha_dt'].dt.to_period('M').unique()
        meses_unicos = sorted(meses_unicos, reverse=True)
        
        opciones = [ft.dropdown.Option("Todos")]
        mes_actual_str = pd.Period(datetime.now(), freq='M').strftime('%Y-%m')
        
        encontro_actual = False
        for m in meses_unicos:
            m_str = m.strftime('%Y-%m')
            nombre_legible = m.strftime('%B %Y').capitalize()
            opciones.append(ft.dropdown.Option(key=m_str, text=nombre_legible))
            if m_str == mes_actual_str:
                encontro_actual = True

        dropdown_mes_filtro.options = opciones
        if dropdown_mes_filtro.value is None:
            dropdown_mes_filtro.value = mes_actual_str if encontro_actual else "Todos"

    def aplicar_filtro_mes(e):
        actualizar_pantalla()

    btn_aplicar_filtro = ft.ElevatedButton(
        content=ft.Text("Aplicar Filtro de Mes", color="#ffffff"),
        on_click=aplicar_filtro_mes,
        bgcolor="#334155",
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        width=350
    )

    def exportar_excel(e):
        if not lista_gastos:
            page.snack_bar = ft.SnackBar(ft.Text("No hay gastos registrados para exportar"), bgcolor="#ef4444")
            page.snack_bar.open = True
            page.update()
            return
        
        try:
            df = pd.DataFrame(lista_gastos)
            if 'id' in df.columns:
                df = df.drop(columns=['id'])
            if 'fecha_dt' in df.columns:
                df = df.drop(columns=['fecha_dt'])
            
            df.columns = ['Concepto', 'Monto', 'Categoría', 'Medio de Pago', 'Fecha']
            csv_str = df.to_csv(index=False, encoding='utf-8-sig')
            page.launch_url(f"data:text/csv;charset=utf-8,{urllib_parse.quote(csv_str)}")
        except Exception:
            try:
                nombre_archivo = f"gastos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                df.to_csv(nombre_archivo, index=False, encoding='utf-8-sig')
                page.snack_bar = ft.SnackBar(ft.Text(f"Archivo guardado como {nombre_archivo}"), bgcolor="#0284c7")
                page.snack_bar.open = True
                page.update()
            except Exception as inner_ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error al exportar: {inner_ex}"), bgcolor="#ef4444")
                page.snack_bar.open = True
                page.update()

    btn_exportar = ft.ElevatedButton(
        content=ft.Row([
            ft.Icon(ft.Icons.DOWNLOAD, color="#ffffff"),
            ft.Text("Descargar Excel / CSV", color="#ffffff")
        ], alignment=ft.MainAxisAlignment.CENTER),
        on_click=exportar_excel,
        bgcolor="#0d9488",
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        width=350
    )

    def insertar_en_db(concepto, monto, categoria, medio_pago, fecha):
        engine = obtener_conexion()
        with engine.begin() as conn:
            conn.execute(
                sqlalchemy.text("INSERT INTO gastos (concepto, monto, categoria, medio_pago, fecha) VALUES (:c, :m, :cat, :p, :f)"),
                {"c": concepto, "m": monto, "cat": categoria, "p": medio_pago, "f": fecha}
            )

    def actualizar_en_db(gasto_id, concepto, monto, categoria, medio_pago):
        engine = obtener_conexion()
        with engine.begin() as conn:
            conn.execute(
                sqlalchemy.text("UPDATE gastos SET concepto = :c, monto = :m, categoria = :cat, medio_pago = :p WHERE id = :id"),
                {"c": concepto, "m": monto, "cat": categoria, "p": medio_pago, "id": gasto_id}
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
        page.snack_bar = ft.SnackBar(ft.Text("Gasto registrado con éxito"), bgcolor="#0d9488")
        page.snack_bar.open = True
        page.update()

    def eliminar_gasto(gasto_id):
        eliminar_de_db(gasto_id)
        nonlocal lista_gastos
        lista_gastos = cargar_gastos_db()
        actualizar_pantalla()
        page.snack_bar = ft.SnackBar(ft.Text("Gasto eliminado correctamente"), bgcolor="#0284c7")
        page.snack_bar.open = True
        page.update()

    def abrir_dialogo_editar(gasto):
        txt_edit_concepto = ft.TextField(label="Concepto", value=gasto["concepto"], bgcolor="#1e293b", color="#f8fafc", border_radius=10, width=300)
        txt_edit_monto = ft.TextField(label="Monto ($)", value=str(gasto["monto"]), keyboard_type=ft.KeyboardType.NUMBER, bgcolor="#1e293b", color="#f8fafc", border_radius=10, width=300)
        
        dd_edit_categoria = ft.Dropdown(
            label="Categoría", value=gasto["categoria"], bgcolor="#1e293b", color="#f8fafc", border_radius=10, width=300,
            options=[ft.dropdown.Option(cat) for cat in LISTA_CATEGORIAS]
        )
        dd_edit_pago = ft.Dropdown(
            label="Medio de Pago", value=gasto.get("medio_pago", "Efectivo"), bgcolor="#1e293b", color="#f8fafc", border_radius=10, width=300,
            options=[ft.dropdown.Option(pago) for pago in LISTA_MEDIOS_PAGO]
        )

        def guardar_cambios_edicion(e):
            try:
                nuevo_monto = float(txt_edit_monto.value)
            except ValueError:
                page.snack_bar = ft.SnackBar(ft.Text("El monto debe ser un número válido"), bgcolor="#ef4444")
                page.snack_bar.open = True
                page.update()
                return

            if not txt_edit_concepto.value or not dd_edit_categoria.value or not dd_edit_pago.value:
                page.snack_bar = ft.SnackBar(ft.Text("Todos los campos son obligatorios"), bgcolor="#ef4444")
                page.snack_bar.open = True
                page.update()
                return

            actualizar_en_db(gasto["id"], txt_edit_concepto.value, nuevo_monto, dd_edit_categoria.value, dd_edit_pago.value)
            
            nonlocal lista_gastos
            lista_gastos = cargar_gastos_db()
            
            dialogo_editar.open = False
            actualizar_pantalla()
            
            page.snack_bar = ft.SnackBar(ft.Text("Gasto actualizado correctamente"), bgcolor="#0284c7")
            page.snack_bar.open = True
            page.update()

        dialogo_editar = ft.AlertDialog(
            title=ft.Text("Editar Gasto", color="#f8fafc"),
            content=ft.Column([
                txt_edit_concepto,
                txt_edit_monto,
                dd_edit_categoria,
                dd_edit_pago
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(dialogo_editar, 'open', False) or page.update()),
                ft.ElevatedButton("Guardar", on_click=guardar_cambios_edicion, bgcolor="#0d9488", color="#ffffff")
            ],
            bgcolor="#0f172a"
        )
        
        page.dialog = dialogo_editar
        dialogo_editar.open = True
        page.update()

    def actualizar_pantalla():
        columna_resultados.controls.clear()
        contenedor_resumen_categorias_semana.controls.clear()
        contenedor_resumen_categorias.controls.clear()
        contenedor_resumen_pagos.controls.clear()
        contenedor_semanas_mes.controls.clear()
        
        total_historico = 0
        total_semana = 0
        total_mes_filtrado = 0

        ahora = datetime.now()
        inicio_lunes = ahora - timedelta(days=ahora.weekday())
        inicio_lunes = inicio_lunes.replace(hour=0, minute=0, second=0, microsecond=0)

        df_global = pd.DataFrame()
        if lista_gastos:
            df_global = pd.DataFrame(lista_gastos)
            df_global['fecha_dt'] = pd.to_datetime(df_global['fecha'], format="%d/%m/%Y %H:%M")
            
            df_semana = df_global[df_global['fecha_dt'] >= inicio_lunes].copy()
            total_semana = df_semana['monto'].sum()

            if not dropdown_mes_filtro.options or len(dropdown_mes_filtro.options) <= 1:
                actualizar_opciones_meses(df_global)

        mes_seleccionado = dropdown_mes_filtro.value
        df_filtrado = df_global.copy()
        
        if not df_global.empty:
            total_historico = df_global['monto'].sum()
            if mes_seleccionado and mes_seleccionado != "Todos":
                df_filtrado = df_global[df_global['fecha_dt'].dt.to_period('M').astype(str) == mes_seleccionado].copy()
            
            total_mes_filtrado = df_filtrado['monto'].sum()

        if not df_filtrado.empty:
            df_filtrado_ordenado = df_filtrado.sort_values(by='fecha_dt', ascending=False)
            for _, row in df_filtrado_ordenado.iterrows():
                gasto_dict = row.to_dict()
                g_id = gasto_dict["id"]
                medio = gasto_dict.get("medio_pago", "No especificado")
                
                btn_editar = ft.IconButton(
                    icon=ft.Icons.EDIT_OUTLINED,
                    icon_color="#38bdf8",
                    tooltip="Editar gasto",
                    icon_size=18,
                    on_click=lambda e, g=gasto_dict: abrir_dialogo_editar(g)
                )
                btn_eliminar = ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_color="#f87171",
                    tooltip="Eliminar gasto",
                    icon_size=18,
                    on_click=lambda e, gid=g_id: eliminar_gasto(gid)
                )

                tarjeta = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(gasto_dict["concepto"], weight=ft.FontWeight.BOLD, size=16, color="#f8fafc"),
                                ft.Text(f"${gasto_dict['monto']:.2f}", weight=ft.FontWeight.BOLD, color="#2dd4bf", size=16)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([
                                ft.Text(f"Cat: {gasto_dict['categoria']} | Pago: {medio}", size=12, color="#94a3b8"),
                                ft.Text(gasto_dict["fecha"], size=12, color="#94a3b8")
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([
                                ft.Row([btn_editar, btn_eliminar], spacing=0)
                            ], alignment=ft.MainAxisAlignment.END)
                        ]),
                        padding=15,
                        bgcolor="#1e293b",
                        border_radius=10,
                        width=350
                    )
                )
                columna_resultados.controls.append(tarjeta)
        else:
            columna_resultados.controls.append(
                ft.Text("No hay gastos en este periodo", size=13, color="#64748b")
            )

        if lista_gastos and not df_semana.empty:
            totales_cat_semana = df_semana.groupby("categoria")["monto"].sum().reset_index()
            totales_cat_semana = totales_cat_semana.sort_values(by="monto", ascending=False)
            
            for _, row in totales_cat_semana.iterrows():
                fila_cat_sem = ft.Row([
                    ft.Text(row["categoria"], size=13, color="#94a3b8"),
                    ft.Text(f"${row['monto']:.2f}", size=13, weight=ft.FontWeight.BOLD, color="#f8fafc")
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, width=350)
                contenedor_resumen_categorias_semana.controls.append(fila_cat_sem)
        else:
            contenedor_resumen_categorias_semana.controls.append(
                ft.Text("Sin gastos registrados esta semana", size=12, color="#64748b")
            )

        if not df_global.empty:
            ahora_periodo = pd.Period(ahora, freq='M')
            df_mes_actual = df_global[df_global['fecha_dt'].dt.to_period('M') == ahora_periodo].copy()
            if not df_mes_actual.empty:
                df_mes_actual['semana_del_mes'] = df_mes_actual['fecha_dt'].apply(lambda d: (d.day - 1) // 7 + 1)
                totales_semanas = df_mes_actual.groupby('semana_del_mes')['monto'].sum().reset_index()
                
                for _, row in totales_semanas.iterrows():
                    num_sem = int(row['semana_del_mes'])
                    fila_sem = ft.Row([
                        ft.Text(f"📅 Semana {num_sem} del mes", size=13, color="#94a3b8"),
                        ft.Text(f"${row['monto']:.2f}", size=13, weight=ft.FontWeight.BOLD, color="#2dd4bf")
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, width=350)
                    contenedor_semanas_mes.controls.append(fila_sem)
            else:
                contenedor_semanas_mes.controls.append(
                    ft.Text("Sin gastos registrados este mes", size=12, color="#64748b")
                )

        if not df_filtrado.empty:
            totales_pago = df_filtrado.groupby("medio_pago")["monto"].sum().reset_index()
            totales_pago = totales_pago.sort_values(by="monto", ascending=False)

            for _, row in totales_pago.iterrows():
                fila_pago = ft.Row([
                    ft.Text(f"💳 {row['medio_pago']}", size=13, color="#94a3b8"),
                    ft.Text(f"${row['monto']:.2f}", size=13, weight=ft.FontWeight.BOLD, color="#2dd4bf")
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, width=350)
                contenedor_resumen_pagos.controls.append(fila_pago)

            totales_cat = df_filtrado.groupby("categoria")["monto"].sum().reset_index()
            totales_cat = totales_cat.sort_values(by="monto", ascending=False)
            
            for _, row in totales_cat.iterrows():
                fila_cat = ft.Row([
                    ft.Text(row["categoria"], size=13, color="#94a3b8"),
                    ft.Text(f"${row['monto']:.2f}", size=13, weight=ft.FontWeight.BOLD, color="#f8fafc")
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, width=350)
                contenedor_resumen_categorias.controls.append(fila_cat)

        texto_presupuesto.value = f"Gasto esta semana: ${total_semana:,.2f} / ${PRESUPUESTO_SEMANAL:,.2f}"
        porcentaje = min(total_semana / PRESUPUESTO_SEMANAL, 1.0)
        barra_progreso.value = porcentaje
        
        if total_semana > PRESUPUESTO_SEMANAL:
            barra_progreso.color = "#f87171"
            texto_presupuesto.color = "#f87171"
        else:
            barra_progreso.color = "#14b8a6"
            texto_presupuesto.color = "#f8fafc"

        texto_total_historico.value = f"Total Histórico Acumulado: ${total_historico:,.2f}"
        texto_total_mes.value = f"Total en periodo seleccionado: ${total_mes_filtrado:,.2f}"
        page.update()

    boton_guardar = ft.Button(
        content=ft.Text("Registrar Gasto", color="#ffffff"),
        on_click=agregar_gasto,
        bgcolor="#0d9488",
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        width=350
    )

    card_presupuesto = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.Text("Gastos de la Semana Actual (Desde el lunes)", size=14, weight=ft.FontWeight.BOLD, color="#94a3b8"),
                texto_presupuesto,
                barra_progreso
            ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=15,
            bgcolor="#1e293b",
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
                                ft.Text("Historial Reciente:", weight=ft.FontWeight.BOLD, size=16, color="#f8fafc"),
                                columna_resultados
                            ], scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            padding=10
                        ),
                        ft.Container(
                            content=ft.Column([
                                ft.Divider(10, color="transparent"),
                                card_presupuesto,
                                ft.Divider(15, color="transparent"),
                                ft.Text("Categorías de esta semana:", weight=ft.FontWeight.BOLD, size=14, color="#f8fafc"),
                                contenedor_resumen_categorias_semana
                            ], scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            padding=10
                        ),
                        ft.Container(
                            content=ft.Column([
                                ft.Divider(height=10, color="transparent"),
                                texto_total_historico,
                                texto_total_mes,
                                ft.Divider(height=5, color="transparent"),
                                dropdown_mes_filtro,
                                btn_aplicar_filtro,
                                ft.Divider(height=5, color="transparent"),
                                btn_exportar,
                                ft.Divider(height=15, color="transparent"),
                                ft.Text("Desglose por Semanas del Mes Actual:", weight=ft.FontWeight.BOLD, size=14, color="#f8fafc"),
                                contenedor_semanas_mes,
                                ft.Divider(height=15, color="transparent"),
                                ft.Text("Gastos por Medio de Pago:", weight=ft.FontWeight.BOLD, size=14, color="#f8fafc"),
                                contenedor_resumen_pagos,
                                ft.Divider(height=15, color="transparent"),
                                ft.Text("Desglose por Categoría:", weight=ft.FontWeight.BOLD, size=14, color="#f8fafc"),
                                contenedor_resumen_categorias
                            ], scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            padding=10
                        ),
                    ],
                ),
            ],
        ),
    )

    page.add(header_row, ft.Container(content=pestanas, expand=True))

    if lista_gastos:
        actualizar_pantalla()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8550))
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=port)
    #Version 001 Domingo 13 de Septiembre del 2026