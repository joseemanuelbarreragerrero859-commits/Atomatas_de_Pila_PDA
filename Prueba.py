import flet as ft
from nvo import AutomataPila, ConfigPDA
import os
import tempfile
import tkinter as tk
from tkinter import filedialog

class VisualizadorPDA:
    """Clase que construye y actualiza la vista de pila, entrada y estado."""
    def __init__(self):
        # Controles internos
        self.columna_pila = ft.Column(spacing=2, alignment=ft.MainAxisAlignment.END)
        self.fila_entrada = ft.Row(spacing=5)
        self.estado_label = ft.Text("Estado Actual: --", size=20, weight="bold")

        # Contenedor principal
        self.root = ft.Row([
            ft.Container(
                content=self.columna_pila,
                width=120,
                height=300,
                border=ft.Border.all(2, ft.Colors.BLUE_400),
                border_radius=5,
                bgcolor=ft.Colors.BLUE_GREY_900,
                padding=10,
                alignment=ft.Alignment(0,1)                        #-----------------------------------------------------------------------------------------------
            ),
            ft.Column([
                self.estado_label,
                ft.Text("Cadena de Entrada:", weight="bold"),
                self.fila_entrada
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=20)
        ])

    def get_control(self):
        """Devuelve el control raíz para agregarlo a la página."""
        return self.root

    def actualizar(self, config: ConfigPDA):
        # Actualizar pila
        self.columna_pila.controls.clear()
        if not config.pila:
            self.columna_pila.controls.append(ft.Text("[Vacía]", color=ft.Colors.RED))
        else:
            for simbolo in reversed(config.pila):
                self.columna_pila.controls.append(
                    ft.Container(
                        content=ft.Text(simbolo, weight="bold", text_align=ft.TextAlign.CENTER),  #-----------------------------------------------------------------------------------------------
                        bgcolor=ft.Colors.ORANGE_800,
                        width=80,
                        padding=5,
                        border_radius=3
                    )
                )

        # Actualizar cinta de entrada
        self.fila_entrada.controls.clear()
        for i, char in enumerate(config.entrada_restante):
            color = ft.Colors.GREEN_700 if i == 0 else ft.Colors.BLUE_GREY_800
            self.fila_entrada.controls.append(
                ft.Container(
                    content=ft.Text(char, size=18),
                    bgcolor=color,
                    padding=10,
                    border=ft.Border.all(1, ft.Colors.WHITE24)
                )
            )

        # Actualizar estado
        self.estado_label.value = f"Estado Actual: {config.estado}"
        # Nota: No llamamos a self.root.update() aquí; lo hará quien llame a actualizar()
        # pero podemos forzar una actualización de la página si es necesario.
        # Por simplicidad, asumimos que la página se actualizará externamente.


class PDASimulatorApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Simulador de Autómata de Pila (PDA)"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 20

        self.automata = AutomataPila()
        self.configuraciones = []
        self.indice_actual = -1
        self.cadena_actual = ""
        self.opciones_actuales = []

        # Componentes UI
        self.visualizador = VisualizadorPDA()
        self.txt_cadena = ft.TextField(label="Cadena a simular", width=300)
        self.btn_cargar_json = ft.ElevatedButton("Cargar PDA desde JSON", on_click=self.cargar_json)
        self.btn_iniciar = ft.ElevatedButton("Iniciar Simulación", on_click=self.iniciar_simulacion, disabled=True)
        self.btn_siguiente = ft.ElevatedButton("Siguiente", on_click=self.siguiente_paso, disabled=True)
        self.btn_anterior = ft.ElevatedButton("Anterior", on_click=self.anterior_paso, disabled=True)
        self.btn_reiniciar = ft.ElevatedButton("Reiniciar", on_click=self.reiniciar, disabled=True)
        self.btn_grafo = ft.ElevatedButton("Generar Grafo", on_click=self.generar_grafo, disabled=True)
        self.info_automata = ft.Text("No hay autómata cargado", italic=True)
        self.opciones_panel = ft.Column(visible=False)  # Para opciones no deterministas
        self.panel_constructor = self.crear_panel_constructor()

        # Montar la página
        self.page.add(
            ft.Row([self.btn_cargar_json, self.btn_grafo]),
            ft.Divider(),
            self.panel_constructor, # <--- Insertamos el constructor interactivo aquí
            ft.Divider(),
            ft.Text("Autómata cargado:", weight="bold"),
            self.info_automata,
            ft.Divider(),
            ft.Text("Simulación", size=24, weight="bold"),
            ft.Row([self.txt_cadena, self.btn_iniciar]),
            ft.Row([self.btn_siguiente, self.btn_anterior, self.btn_reiniciar]),
            self.visualizador.get_control(),
            self.opciones_panel
        )

    def cargar_json(self, e):
        # Hide the main tkinter root window
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes('-topmost', 1)

        # Show the file selection dialog
        file_path = filedialog.askopenfilename(
            title="Escoje un PDA de JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        # Clean up the tkinter root
        root.destroy()

        if file_path:
            if self.automata.cargar_desde_json(file_path):
                self.info_automata.value = (f"✅ Cargado: {len(self.automata.estados)} estados, "
                                            f"{len(self.automata.transiciones)} transiciones.\n"
                                            f"Inicial: {self.automata.estado_inicial}, "
                                            f"Finales: {self.automata.estados_finales}")
                self.btn_iniciar.disabled = False
                self.btn_grafo.disabled = False
            else:
                self.info_automata.value = "❌ Error al cargar el JSON"
            self.page.update()

    def iniciar_simulacion(self, e):
        cadena = self.txt_cadena.value.strip()
        if not cadena:
            self.page.snack_bar = ft.SnackBar(ft.Text("Ingrese una cadena"))
            self.page.snack_bar.open = True
            self.page.update()
            return

        self.cadena_actual = cadena
        config_inicial = self.automata.reiniciar_simulacion(cadena)
        self.configuraciones = [config_inicial]
        self.indice_actual = 0
        self.visualizador.actualizar(config_inicial)

        self.btn_siguiente.disabled = False
        self.btn_anterior.disabled = True
        self.btn_reiniciar.disabled = False
        self.opciones_panel.visible = False
        self.page.update()

        self.verificar_no_determinismo()

    def verificar_no_determinismo(self):
        if self.indice_actual < 0 or self.indice_actual >= len(self.configuraciones):
            return
        config_actual = self.configuraciones[self.indice_actual]
        siguientes = self.automata.obtener_siguientes_configs(config_actual)
        if len(siguientes) > 1:
            self.mostrar_opciones(siguientes)
        else:
            self.opciones_panel.visible = False
            self.page.update()

    def mostrar_opciones(self, opciones: list):
        self.opciones_panel.controls.clear()
        self.opciones_panel.visible = True
        self.opciones_panel.controls.append(ft.Text("🔀 Múltiples transiciones posibles. Elige una:", weight="bold"))
        for i, cfg in enumerate(opciones):
            trans_text = f"➡️ {cfg.estado} | entrada: {cfg.entrada_restante[:10]}... | pila: {cfg.pila[-1] if cfg.pila else 'ε'}"
            btn = ft.ElevatedButton(
                text=trans_text,
                on_click=lambda e, idx=i: self.elegir_opcion(idx, opciones)
            )
            self.opciones_panel.controls.append(btn)
        self.page.update()

    def elegir_opcion(self, idx, opciones):
        config_elegida = opciones[idx]
        self.configuraciones = self.configuraciones[:self.indice_actual+1]
        self.configuraciones.append(config_elegida)
        self.indice_actual += 1
        self.visualizador.actualizar(config_elegida)
        self.opciones_panel.visible = False
        self.verificar_no_determinismo()
        self.actualizar_botones_navegacion()
        self.page.update()

    def siguiente_paso(self, e):
        if self.indice_actual < 0:
            return
        if self.indice_actual == len(self.configuraciones) - 1:
            config_actual = self.configuraciones[self.indice_actual]
            siguientes = self.automata.obtener_siguientes_configs(config_actual)
            if len(siguientes) == 0:
                self.page.snack_bar = ft.SnackBar(ft.Text("No hay más transiciones posibles."))
                self.page.snack_bar.open = True
                self.page.update()
                return
            elif len(siguientes) == 1:
                nueva_config = siguientes[0]
                self.configuraciones.append(nueva_config)
                self.indice_actual += 1
                self.visualizador.actualizar(nueva_config)
                self.verificar_no_determinismo()
            else:
                self.mostrar_opciones(siguientes)
                return
        else:
            self.indice_actual += 1
            self.visualizador.actualizar(self.configuraciones[self.indice_actual])
            self.verificar_no_determinismo()

        self.actualizar_botones_navegacion()
        self.page.update()

    def anterior_paso(self, e):
        if self.indice_actual > 0:
            self.indice_actual -= 1
            self.visualizador.actualizar(self.configuraciones[self.indice_actual])
            self.opciones_panel.visible = False
            self.actualizar_botones_navegacion()
            self.page.update()

    def reiniciar(self, e):
        self.iniciar_simulacion(None)

    def actualizar_botones_navegacion(self):
        self.btn_anterior.disabled = (self.indice_actual <= 0)
        self.btn_siguiente.disabled = False
        self.page.update()

    def generar_grafo(self, e):
        if not self.automata.estados:
            self.page.snack_bar = ft.SnackBar(ft.Text("Primero cargue un autómata"))
            self.page.snack_bar.open = True
            self.page.update()
            return
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            nombre_temp = tmp.name.replace(".png", "")
        ruta_png = self.automata.generar_grafo(nombre_temp)
        if os.path.exists(ruta_png):
            img = ft.Image(src=ruta_png, width=800, height=600, fit="contain")                      #-----------------------------------------------------------------------------------------------
            dlg = ft.AlertDialog(content=ft.Container(content=img, width=800, height=600), title=ft.Text("Grafo del PDA"))
            self.page.dialog = dlg
            dlg.open = True
            self.page.update()
        else:
            self.page.snack_bar = ft.SnackBar(ft.Text("Error al generar el grafo"))
            self.page.snack_bar.open = True
            self.page.update()

    def crear_panel_constructor(self):
        # Campos para la configuración básica
        self.txt_estados = ft.TextField(label="Estados (separados por coma, ej: q0,q1,q2)", expand=True)
        self.txt_alfabeto = ft.TextField(label="Alfabeto entrada (ej: a,b)", expand=True)
        self.txt_alfabeto_pila = ft.TextField(label="Alfabeto pila (ej: Z,X)", expand=True)
        self.txt_inicial = ft.TextField(label="Estado Inicial (ej: q0)", width=150)
        self.txt_simbolo_pila = ft.TextField(label="Símbolo Inicial Pila (ej: Z)", value="Z", width=150)
        self.txt_finales = ft.TextField(label="Estados Finales (ej: q2)", width=200)
        
        # Campos para añadir una transición
        self.txt_t_origen = ft.TextField(label="Origen", width=100)
        self.txt_t_entrada = ft.TextField(label="Entrada (ε para vacío)", value="ε", width=100)
        self.txt_t_pop = ft.TextField(label="Pop (tope)", width=100)
        self.txt_t_destino = ft.TextField(label="Destino", width=100)
        self.txt_t_push = ft.TextField(label="Push (string o ε)", value="ε", width=120)
        
        # Área de texto para listar transiciones añadidas de forma visual
        self.txt_lista_transiciones = ft.Text("No hay transiciones registradas", italic=True)

        # Botón para consolidar datos básicos y habilitar registro de transiciones
        self.btn_guardar_base = ft.ElevatedButton("Guardar Configuración Base", on_click=self.guardar_configuracion_base)
        self.btn_reg_transicion = ft.ElevatedButton("Añadir Transición", on_click=self.registrar_transicion, disabled=True)
        self.btn_finalizar_pda = ft.ElevatedButton("Finalizar Construcción", on_click=self.finalizar_construccion, disabled=True)

        # Retornamos el contenedor de diseño con los controles organizados
        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("🛠️ Constructor de Autómata de Pila", size=20, weight="bold"),
                    ft.Row([self.txt_estados, self.txt_alfabeto, self.txt_alfabeto_pila]),
                    ft.Row([self.txt_inicial, self.txt_simbolo_pila, self.txt_finales]),
                    self.btn_guardar_base,
                    ft.Divider(),
                    ft.Text("Formulario de Transiciones:", weight="bold"),
                    ft.Row([self.txt_t_origen, self.txt_t_entrada, self.txt_t_pop, self.txt_t_destino, self.txt_t_push]),
                    self.btn_reg_transicion,
                    ft.Text("Transiciones Guardadas:", weight="bold"),
                    self.txt_lista_transiciones,
                    ft.Divider(),
                    self.btn_finalizar_pda
                ], spacing=15),
                padding=15
            )
        )
    
    def guardar_configuracion_base(self, e):
        # Reiniciar estructura interna
        self.automata.limpiar_automata()
        
        # Procesar textos limpiando espacios en blanco
        self.automata.estados = [s.strip() for s in self.txt_estados.value.split(",") if s.strip()]
        self.automata.alfabeto = [s.strip() for s in self.txt_alfabeto.value.split(",") if s.strip()]
        self.automata.alfabeto_pila = [s.strip() for s in self.txt_alfabeto_pila.value.split(",") if s.strip()]
        self.automata.estado_inicial = self.txt_inicial.value.strip()
        self.automata.simbolo_inicial_pila = self.txt_simbolo_pila.value.strip()
        self.automata.estados_finales = [s.strip() for s in self.txt_finales.value.split(",") if s.strip()]

        # Validar campos requeridos mínimos
        if not self.automata.estados or not self.automata.estado_inicial:
            self.page.snack_bar = ft.SnackBar(ft.Text("❌ Error: Defina los estados y el estado inicial"))
            self.page.snack_bar.open = True
            self.page.update()
            return

        # Habilitar el guardado de transiciones
        self.btn_reg_transicion.disabled = False
        self.btn_finalizar_pda.disabled = False
        self.page.snack_bar = ft.SnackBar(ft.Text("✅ Configuración base guardada. Proceda con las transiciones."))
        self.page.snack_bar.open = True
        self.page.update()
    
    def registrar_transicion(self, e):
        origen = self.txt_t_origen.value.strip()
        entrada = self.txt_t_entrada.value.strip()
        pop = self.txt_t_pop.value.strip()
        destino = self.txt_t_destino.value.strip()
        push = self.txt_t_push.value.strip()

        if not origen or not pop or not destino:
            self.page.snack_bar = ft.SnackBar(ft.Text("⚠️ Complete Origen, Tope(Pop) y Destino"))
            self.page.snack_bar.open = True
            self.page.update()
            return

        # Registrar de forma nativa en tu diccionario backend
        self.automata.agregar_transicion(origen, entrada, pop, destino, push)

        # Actualizar visualmente la lista en la GUI
        if self.txt_lista_transiciones.value == "No hay transiciones registradas" or self.txt_lista_transiciones.italic:
            self.txt_lista_transiciones.value = ""
            self.txt_lista_transiciones.italic = False
        
        nueva_linea = f"δ({origen}, {entrada}, {pop}) → ({destino}, {push})\n"
        self.txt_lista_transiciones.value += nueva_linea
        
        # Limpiar formularios de transición rápidos dejando listos caracteres comunes
        self.txt_t_origen.value = destino  # Encadenamiento lógico automático
        self.txt_t_entrada.value = "ε"
        self.txt_t_pop.value = ""
        self.txt_t_push.value = "ε"
        
        self.page.update()

    def finalizar_construccion(self, e):
        self.info_automata.value = (f"✅ Creado manualmente: {len(self.automata.estados)} estados, "
                                    f"{len(self.automata.transiciones)} reglas de transición.\n"
                                    f"Inicial: {self.automata.estado_inicial}, "
                                    f"Finales: {self.automata.estados_finales}")
        
        # Activar botones de control para simular la cadena
        self.btn_iniciar.disabled = False
        self.btn_grafo.disabled = False
        
        self.page.snack_bar = ft.SnackBar(ft.Text("🎉 ¡Autómata compilado con éxito! Listo para simular."))
        self.page.snack_bar.open = True
        self.page.update()






def main(page: ft.Page):
    page.scroll = ft.ScrollMode.AUTO
    PDASimulatorApp(page)

ft.app(target=main)