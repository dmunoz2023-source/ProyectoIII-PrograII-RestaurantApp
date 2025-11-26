import customtkinter as ctk
import webbrowser
import os

from tkinter import filedialog, END
from types import SimpleNamespace as sn

from src.utils.tools import *
from src.services.ingredient_service import IngredientService
from src.core.ingredient import Ingredient
from src.services.menu_service import MenuService
from src.core.order import Order
from src.utils.menupdf import generate_menu_pdf
from src.utils.receipt import Receipt
from src.config.consts import *

from src.services.client_service import ClientService # <-- NUEVO
from src.services.order_service import OrderService   # <-- NUEVO

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from src.services.statistics_service import StatisticsService # <-- NUEVO

class RestaurantApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title('Gestor de Restaurante')
        self.geometry('1000x700')
        ctk.set_appearance_mode("dark")

        Fonts.load_fonts(GLOBAL_FONTS)

        self.ingredient_service = IngredientService() 
        self.menu_service = MenuService()
        self.client_service = ClientService() # <-- NUEVO
        self.order_service = OrderService()   # <-- NUEVO
        self.stats_service = StatisticsService()

        self.menu_service.initialize_default_menus()
        
        self.temp_csv_ingredients = [] # Para almacenar la carga temporal del CSV antes de guardar
        self.temp_recipe_builder = []

        # Carrito de Compras en Memoria de UI (Diccionario para manejo fácil)
        # Key: Menu Name, Value: {quantity, price, obj}
        self.shopping_cart = {}

        tabview = TABView(self)
        tabview.pack(padx=10, pady=10, fill="both", expand=True)
        tabview.add_tabs([
            sn(key='load', title='Carga de Ingredientes', content=self._setup_load_tab),
            sn(key='stock', title='Stock', content=self._setup_stock_tab),
            sn(key='menu', title='Carta Restaurante', content=self._setup_menu_tab),
            sn(key='menu_mgmt', title='Gestión de Menús', content=self._setup_menu_mgmt_tab),
            sn(key='clients', title='Gestión Clientes', content=self._setup_client_tab),
            sn(key='order', title='Pedido', content=self._setup_order_tab),
            sn(key='history', title='Historial Pedidos', content=self._setup_order_history_tab), # <-- NUEVA PESTAÑA
            sn(key='stats', title='Gráficos Estadísticos', content=self._setup_stats_tab),
        ])

        self._generate_menu_action()
        self._update_order_buttons()

    def _show_msg(self, title, msg):
        MsgBox(self, title, msg)
    
    def _update_stock_treeview(self):
        # Llama al servicio que consulta la BD
        ingredients = self.ingredient_service.get_all_ingredients()
        # Mapea los objetos ORM a lista de listas para la UI
        table_data = [[ing.name, ing.unit, f"{ing.quantity:,.2f}"] for ing in ingredients]
        self.stock_tree_manager.load_data(table_data)

    def _update_menu_treeview(self):
        available_items = [item for item in self.menu.get_all_items() if item.is_available(self.stock)]
        table_data = [[item.name, f"${item.price:,.0f}"] for item in available_items]
        self.menu_tree_manager.load_data(table_data)
        
    def _update_order_treeview(self):
        table_data = self.order.get_order_lines()
        self.order_tree_manager.load_data(table_data)
        total = self.order.get_total_price()
        self.lbl_total.configure(text=f"TOTAL: ${total:,.0f}")

    def _load_csv_action(self):
      filepath = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
      if not filepath: return
      
      # Llamamos al servicio para procesar (map/filter) sin guardar aún
      success, data_list, message = self.ingredient_service.process_csv(filepath)
      self._show_msg("Carga CSV", message)
      
      if success:
        self.temp_csv_ingredients = data_list # Guardamos en memoria temporal de la UI
        # Preparamos datos visuales
        visual_data = [[d['name'], d['unit'], f"{d['quantity']:,.2f}"] for d in data_list]
        self.load_tree_manager.load_data(visual_data)

    def _add_stock_action(self):
      if not self.temp_csv_ingredients:
          self._show_msg("Error", "No hay ingredientes cargados para agregar.")
          return

      # Guardamos la lista temporal en la BD real
      success, msg = self.ingredient_service.save_bulk_ingredients(self.temp_csv_ingredients)
      self._show_msg("Stock Actualizado", msg)
      
      if success:
          self.load_tree_manager.clear_data()
          self.temp_csv_ingredients = [] # Limpiar temporal
          self._update_stock_treeview() # Refrescar tabla principal desde BD
          self.btn_container and self._update_order_buttons() # Refrescar botones de pedido
          self._generate_menu_action() # Refrescar menú disponible

    def _add_single_ingredient_action(self):
        name = self.entry_nombre.get()
        unit = self.unit_selector.get()
        quantity_str = self.entry_cantidad.get()
        
        if not all([name, unit, quantity_str]):
            self._show_msg("Error", "Todos los campos son obligatorios.")
            return

        try:
            quantity = float(quantity_str)
            # Llamada al servicio
            success, msg = self.ingredient_service.add_ingredient(name, unit, quantity)
            
            if success:
                print(f'Item agregado/actualizado en BD: {name}')
                self._update_stock_treeview()
                self.entry_nombre.delete(0, END)
                self.entry_cantidad.delete(0, END)
            else:
                self._show_msg("Error", msg)
                
        except ValueError:
            self._show_msg("Error", "La cantidad debe ser un número válido.")

    def _delete_ingredient_action(self):
      selected = self.stock_tree_manager.get_selected_item_values()
      if not selected:
          self._show_msg("Error", "Seleccione un ingrediente para eliminar.")
          return
          
      name = selected[0]
      # Llamada al servicio
      success, msg = self.ingredient_service.delete_ingredient(name)
      print(f"Intento eliminación: {name} -> {success}")
      
      if success:
          self._update_stock_treeview()
      else:
          self._show_msg("Error", msg)

    def _generate_menu_action(self):
      # Usamos el servicio para obtener el estado (Disponible / No Disponible)
        status = self.menu_service.get_menu_status()
        
        available_items = status["available"]
        unavailable_items = status["unavailable"]

        if not unavailable_items:
            msg = "¡Todos los menús están disponibles!"
        else:
            # Uso de map/join para formatear mensaje
            unavailable_names = ", ".join(map(lambda item: item.name, unavailable_items))
            msg = f"Menú actualizado. Faltan ingredientes para: {unavailable_names}."
      
        self._show_msg("Disponibilidad de Menú", msg)
      
        # Actualizar la tabla visual
        if hasattr(self, 'menu_tree_manager'):
            # Formateo de datos para la UI
            table_data = [[item.name, f"${item.price:,.0f}"] for item in available_items]
            self.menu_tree_manager.load_data(table_data)

        # Actualizar botones de pedido (si existen en la UI)
        if hasattr(self, 'btn_container'):
            self._update_order_buttons()

    def _generate_menu_pdf_action(self):
        status = self.menu_service.get_menu_status()
        available_items = status["available"]
        
        success, filepath = generate_menu_pdf(available_items)
        
        if success:
            self._show_msg("PDF Generado", f"Carta guardada exitosamente en:\n{filepath}")
            
            import os, webbrowser
            if os.path.exists(filepath):
                webbrowser.open(f'file:///{os.path.abspath(filepath)}')
        else:
            self._show_msg("Error", filepath)

    def _update_order_buttons(self, unavailable_menus:list = None):
        # Necesitamos refrescar la lista completa para verificar estado uno por uno
        # Nota: Esto podría optimizarse, pero para EV3 está bien llamar al servicio
        for item_name, btn in self.menu_buttons.items():

            if unavailable_menus is not None:
              for menu_name in unavailable_menus:
                if item_name == menu_name:
                  btn.configure(state="disabled")
                  break
              continue
            # Buscar el objeto menú en la BD (podríamos cachearlo, pero lo pedimos al servicio)
            # Como get_menu_status devuelve objetos, podemos usar lógica de servicio
            
            # Forma rápida: Traer todos y buscar localmente
            all_menus = self.menu_service.get_all_menus()
            # Filter para encontrar el item específico
            found_items = list(filter(lambda x: x.name == item_name, all_menus))
            
            if found_items:
                item = found_items[0]
                is_available = self.menu_service.check_availability(item)
                state = "normal" if is_available else "disabled"
                btn.configure(state=state)

    def _add_to_order_action(self, menu_item_name):
        item_to_add = self.menu.get_item(menu_item_name)
        success, message = self.order.add_item(item_to_add, self.stock)
        if success:
          self._update_order_treeview()
        else:    
          self._show_msg("Pedido", message)
   
    def _remove_from_cart_action(self):
        """Elimina el ítem seleccionado del carrito de compras temporal."""
        # 1. Obtener la selección de la tabla visual
        selected_values = self.order_tree_manager.get_selected_item_values()
        
        if not selected_values:
            self._show_msg("Atención", "Por favor, seleccione un ítem de la lista para eliminar.")
            return

        # La columna 0 corresponde al nombre del menú según definimos en las columnas
        menu_name = selected_values[0]

        # 2. Verificar y eliminar del diccionario del carrito
        if menu_name in self.shopping_cart:
            del self.shopping_cart[menu_name]
            
            # 3. Refrescar la vista y el total
            self._refresh_cart_display()
            self._update_order_buttons()
            print(f"Ítem '{menu_name}' eliminado del carrito.") # Log opcional
        else:
            self._show_msg("Error", "El ítem seleccionado no se encuentra en el carrito.")


    def _generate_receipt_action(self):
        if self.order.is_empty:
            self._show_msg("Error", "El pedido está vacío.")
            return

        receipt = Receipt(self.order)
    
        success_pdf, filepath = receipt.generate_pdf()
        
        if success_pdf:
            self.order.finalize_order(self.stock)
            self._show_msg("Boleta Generada", f"Boleta generada y guardada en: {filepath}")
            
            self._update_order_treeview()
            self._update_stock_treeview()
            self._generate_menu_action()
        else:
            self._show_msg("Error de PDF", f"No se pudo generar la boleta. {filepath}")
    
    def _show_receipt_pdf_action(self):
        filepath = "boleta.pdf"
        if os.path.exists(filepath):
            try:
                webbrowser.open(f'file:///{os.path.abspath(filepath)}')
            except Exception as e:
                self._show_msg("Error al Abrir", f"No se pudo abrir el PDF. Error: {e}")
        else:
            self._show_msg("Error", "Primero debe generar una boleta.")
            
    def _add_client_action(self):
        name = self.entry_client_name.get()
        email = self.entry_client_email.get()
        
        # Llamada al servicio con validaciones internas
        success, msg = self.client_service.register_client(name, email)
        
        self._show_msg("Registro Cliente", msg)
        
        if success:
            # Limpiar campos y actualizar tabla
            self.entry_client_name.delete(0, END)
            self.entry_client_email.delete(0, END)
            self._update_client_list()
            self._update_client_selector()

            # --- NUEVA LÍNEA ---
            if hasattr(self, 'history_client_selector'):
                self._update_history_client_selector() # Actualiza pestaña Historial

    def _update_client_list(self):
        clients = self.client_service.get_all_clients()
        data = [[c.id, c.name, c.email] for c in clients]
        self.client_tree.load_data(data)

    def _update_client_selector(self):
        clients = self.client_service.get_all_clients()
        # Guardamos referencia de ID por nombre/email para recuperarlo luego
        self.client_map = {f"{c.name} ({c.email})": c.id for c in clients}
        self.client_selector.configure(values=list(self.client_map.keys()))
        if self.client_map:
            self.client_selector.set(list(self.client_map.keys())[0])

    
    def _add_to_cart_action(self, menu_name):
        # Lógica de UI para agregar al carrito visual
        menu, ingredients = self.menu_service.get_menu(menu_name)
        
        if not menu: return

        qty = self.shopping_cart.get(menu_name, {}).get('quantity', 0) + 1
        
        success, msg, unavailable_menus = self.order_service.validate_stock(menu_name, qty, ingredients)
        
        if not success:
          self._show_msg('Stock Insuficiente', msg)
          self._update_order_buttons(unavailable_menus)
          return

        if menu_name in self.shopping_cart:
            self.shopping_cart[menu_name]['quantity'] += 1
        else:
            self.shopping_cart[menu_name] = {'quantity': 1, 'price': menu.price}
        
        self._refresh_cart_display()

    def _refresh_cart_display(self):
        data = []
        total = 0
        for name, info in self.shopping_cart.items():
            subtotal = info['quantity'] * info['price']
            total += subtotal
            data.append([name, info['quantity'], f"${info['price']}", f"${subtotal}"])
        
        self.order_tree_manager.load_data(data)
        self.lbl_total.configure(text=f"TOTAL: ${total:,.0f}")

    def _finalize_order_action(self):
        selected_client_str = self.client_selector.get()
        if not selected_client_str or selected_client_str not in self.client_map:
            self._show_msg("Error", "Seleccione un cliente válido.")
            return

        client_id = self.client_map[selected_client_str]
        
        # Transformar carrito de dict a lista para el servicio
        cart_list = [{'menu_name': k, 'quantity': v['quantity'], 'price': v['price']} for k, v in self.shopping_cart.items()]
        
        success, msg, pdf_path = self.order_service.process_order(client_id, cart_list)
        
        if success:
            self._show_msg("Éxito", msg)
            self.shopping_cart.clear()
            self._refresh_cart_display()
            self._generate_menu_action() # Actualizar disponibilidad visual
            self._update_stock_treeview()
            # Aquí podrías llamar al PDF generator real si quisieras
        else:
            self._show_msg("Error en Pedido", msg)
            
    def _setup_load_tab(self, master):
        frame = Frame(master, pack=sn(fill='both', expand=True, padx=20, pady=20))
        Label(frame, 'CARGA DE ARCHIVO CSV DE INGREDIENTES', font=Fonts.get('h1')).pack(pady=(10, 30))
        content_frame = Frame(frame, pack=sn(fill="both", expand=True, padx=10, pady=10))
        Button(content_frame, '📂 Cargar CSV', self._load_csv_action, height=40, font=Fonts.get('btn_primary'), fg_color="#3B82F6", hover_color="#2563EB").pack(pady=10, padx=20)
        stock_columns_config = {col: {'text': col.capitalize(), 'width': 150, 'anchor': 'center'} for col in STOCK_COLUMNS}
        self.load_tree_manager = TreeViewManager(content_frame, columns=stock_columns_config)
        self.load_tree_manager.pack(fill="x", padx=20, pady=(20, 10))
        Button(content_frame, '✅ Agregar al Stock', self._add_stock_action, height=40, font=Fonts.get('btn_primary'), fg_color="#4CAF50", hover_color="#45A049").pack(pady=20, padx=20)

    def _setup_stock_tab(self, master):
        stock_main_frame = Frame(master, pack=sn(fill="both", expand=True, padx=20, pady=20))
        Label(stock_main_frame, "GESTIÓN DE INVENTARIO Y RECETAS", font=Fonts.get('h1')).pack(pady=(10, 15))
        stock_table_frame = Frame(stock_main_frame, pack=sn(fill="x", padx=10, pady=(10, 10)))
        Label(stock_table_frame, "Stock Actual", font=Fonts.get('h2')).pack(pady=5)
        stock_columns_config = {col: {'text': col.capitalize(), 'width': 150, 'anchor': 'center'} for col in STOCK_COLUMNS}
        self.stock_tree_manager = TreeViewManager(stock_table_frame, columns=stock_columns_config)
        self.stock_tree_manager.pack(fill="x", expand=True)
        self.stock_tree = self.stock_tree_manager.tree
        control_frame = Frame(stock_main_frame, pack=sn(fill="x", padx=10, pady=10))
        input_frame = Frame(control_frame, pack=sn(side="left", padx=10, pady=10))
        Label(input_frame, "INGRESAR INGREDIENTE MANUALMENTE", font=Fonts.get('h3')).grid(row=0, column=0, columnspan=2, pady=(0, 10))

        Label(input_frame, text="Nombre:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.entry_nombre = ctk.CTkEntry(input_frame, width=150)
        self.entry_nombre.grid(row=1, column=1, padx=5, pady=5)

        Label(input_frame, text="Unidad:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.unit_selector = ctk.CTkComboBox(
            input_frame,
            values=[ "kg", "unid" ],
            width=150
        )
        self.unit_selector.set("kg")
        self.unit_selector.grid(row=2, column=1, padx=5, pady=5)

        Label(input_frame, text="Cantidad:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.entry_cantidad = ctk.CTkEntry(input_frame, width=150)
        self.entry_cantidad.grid(row=3, column=1, padx=5, pady=5)

        Button(input_frame, "➕ Ingresar Ingrediente", self._add_single_ingredient_action, fg_color="#FBC02D", hover_color="#F9A825", text_color="black").grid(row=4, column=0, columnspan=2, pady=10)
        action_frame = Frame(control_frame, pack=sn(side="right", padx=10, pady=10))
        Label(action_frame, "ACCIONES", font=Fonts.get('h3')).pack(pady=5)
        Button(action_frame, "🗑️ Eliminar Ingrediente", self._delete_ingredient_action, fg_color="#D32F2F", hover_color="#C62828").pack(pady=5, padx=10)
        Button(action_frame, "📋 Generar Menú", self._generate_menu_action, fg_color="#3F51B5", hover_color="#3949AB").pack(pady=5, padx=10)
        self._update_stock_treeview()

    def _setup_menu_tab(self, master):
        frame = Frame(master, pack=sn(fill="both", expand=True, padx=20, pady=20))
        Label(frame, "CARTA RESTAURANTE", font=Fonts.get('h1')).pack(pady=(10, 20))
        Button(frame, "📄 Generar Carta (PDF)", self._generate_menu_pdf_action, height=40, font=Fonts.get('btn_primary'), fg_color="#FBC02D", hover_color="#F9A825", text_color="black").pack(pady=10)
        Label(frame, "Menús Disponibles para Venta (según stock):", font=Fonts.get('label_normal')).pack(pady=(20, 10))
        menu_columns_config = {col: {'text': col.capitalize(), 'width': 200, 'anchor': 'center'} for col in MENU_COLUMNS}
        self.menu_tree_manager = TreeViewManager(frame, columns=menu_columns_config)
        self.menu_tree_manager.pack(fill="x", expand=True)
    
    def _setup_client_tab(self, master):
        frame = Frame(master, pack=sn(fill='both', expand=True, padx=20, pady=20))
        Label(frame, "REGISTRO DE CLIENTES", font=Fonts.get('h1')).pack(pady=10)
        
        # Área de Formulario
        input_frame = Frame(frame, pack=sn(fill="x", pady=10))
        
        Label(input_frame, "Nombre:").pack(side="left", padx=5)
        self.entry_client_name = ctk.CTkEntry(input_frame, width=200)
        self.entry_client_name.pack(side="left", padx=5)
        
        Label(input_frame, "Email:").pack(side="left", padx=5)
        self.entry_client_email = ctk.CTkEntry(input_frame, width=200)
        self.entry_client_email.pack(side="left", padx=5)
        
        # Botón Registrar
        Button(input_frame, "💾 Registrar", self._add_client_action, fg_color="#4CAF50", hover_color="#45A049").pack(side="left", padx=10)
        
        # Botón Eliminar (NUEVO)
        Button(input_frame, "🗑️ Eliminar Seleccionado", self._delete_client_action, fg_color="#D32F2F", hover_color="#C62828").pack(side="right", padx=10)
        
        # Tabla de Clientes
        # Definimos columnas: ID oculto o visible (útil para lógica)
        columns = {"id": {"text": "ID", "width": 50}, "name": {"text": "Nombre", "width": 200}, "email": {"text": "Email", "width": 250}}
        self.client_tree = TreeViewManager(frame, columns=columns)
        self.client_tree.pack(fill="both", expand=True, pady=10)
        
        self._update_client_list()
    
    def _delete_client_action(self):
        selected = self.client_tree.get_selected_item_values()
        if not selected:
            self._show_msg("Error", "Seleccione un cliente para eliminar.")
            return
        
        # La columna 0 es el ID según nuestra configuración de columnas
        client_id = selected[0] 
        client_name = selected[1]
        
        # Confirmación simple (opcional, pero recomendada)
        # Por ahora llamamos directo al servicio
        success, msg = self.client_service.delete_client(client_id)
        
        self._show_msg("Gestión Clientes", msg)
        
        if success:
            self._update_client_list()
            self._update_client_selector()

    def _setup_order_tab(self, master):
        Label(master, "CREACIÓN DE PEDIDO", font=Fonts.get('h1')).pack(pady=(10, 15))
        
        # --- Selector de Cliente ---
        client_frame = Frame(master, pack=sn(fill="x", padx=20, pady=5))
        Label(client_frame, "Cliente:").pack(side="left", padx=5)
        self.client_selector = ctk.CTkComboBox(client_frame, values=[], width=250)
        self.client_selector.pack(side="left", padx=5)
        self._update_client_selector()

        # --- Área de Botones de Menú ---
        menu_btn_frame = Frame(master, pack=sn(fill="x", padx=20, pady=10))
        Label(menu_btn_frame, text="Seleccionar Menú:", font=Fonts.get('h2')).pack(pady=5, padx=10, anchor="w")
        
        # Contenedor con scroll horizontal opcional si son muchos, por ahora frame simple
        self.btn_container = Frame(menu_btn_frame, pack=sn(fill="x", padx=10, pady=(0, 10)))
        
        # CARGA DINÁMICA DE BOTONES (CAMBIO AQUÍ)
        self._refresh_menu_buttons() 
        # ---------------------------------------

        # --- Tabla de Pedido ---
        order_frame = Frame(master, pack=sn(fill="x", padx=20, pady=10))
        cols = {"menu": {"text": "Menú", "width": 150}, "qty": {"text": "Cant.", "width": 50}, "price": {"text": "Precio", "width": 100}, "sub": {"text": "Subtotal", "width": 100}}
        self.order_tree_manager = TreeViewManager(order_frame, columns=cols)
        self.order_tree_manager.pack(fill="x", expand=True)

        # --- Acciones del Carrito ---
        actions_frame = Frame(master, pack=sn(fill="x", padx=20, pady=5))
        Button(actions_frame, "🗑️ Eliminar Seleccionado", self._remove_from_cart_action, fg_color="#D32F2F", hover_color="#C62828").pack(side="left", padx=5)
        Button(actions_frame, "🧾 Finalizar Compra", self._finalize_order_action, fg_color="green").pack(side="right", padx=5)
        
        self.lbl_total = Label(master, "TOTAL: $0", font=Fonts.get('total_price'))
        self.lbl_total.pack(pady=10)
    
    def _setup_receipt_tab(self, master):
        frame = Frame(master, pack=sn(fill="both", expand=True, padx=20, pady=20))
        Label(frame, "VISUALIZACIÓN DE BOLETA (PDF)", font=Fonts.get('h1')).pack(pady=(10, 20))
        Button(frame, "👁️ Mostrar Boleta (PDF)", self._show_receipt_pdf_action, height=40, font=Fonts.get('btn_primary'), fg_color="#673AB7", hover_color="#5E35B1").pack(pady=20)
        Label(frame, "Presione el botón para abrir 'boleta.pdf' en su visor predeterminado.", font=Fonts.get('label_note')).pack(pady=10)
        info_frame = Frame(frame, pack=sn(fill="x", padx=50, pady=30))
        Label(info_frame, "NOTA IMPORTANTE:", font=Fonts.get('label_important')).pack(pady=(10, 5))
        Label(info_frame, "La Boleta se genera en la carpeta del programa...\nEl botón 'Mostrar Boleta (PDF)' intentará abrir este archivo...", wraplength=450, justify="center").pack(pady=(0, 10))

    def _setup_stats_tab(self, master):
        # Frame de Controles
        control_frame = Frame(master, pack=sn(fill="x", padx=20, pady=10))
        Label(control_frame, "Estadísticas del Negocio", font=Fonts.get('h1')).pack(side="left", padx=10)
        
        # Selector de Tipo de Gráfico (ACTUALIZADO CON SEMANAL Y ANUAL)
        self.chart_type_selector = ctk.CTkComboBox(
            control_frame, 
            values=[
                "Ventas Diarias", 
                "Ventas Semanales", 
                "Ventas Mensuales", 
                "Ventas Anuales",
                "Menús Más Vendidos", 
                "Uso de Ingredientes"
            ],
            width=200,
            state="readonly"
        )
        self.chart_type_selector.set("Ventas Diarias")
        self.chart_type_selector.pack(side="left", padx=10)
        
        Button(control_frame, "📊 Generar Gráfico", self._generate_chart_action).pack(side="left", padx=10)
        
        # Área del Gráfico (Canvas)
        self.chart_frame = Frame(master, pack=sn(fill="both", expand=True, padx=20, pady=10))
        self.current_canvas_widget = None

    def _generate_chart_action(self):
        chart_type = self.chart_type_selector.get()
        
        # Limpiar gráfico anterior
        if self.current_canvas_widget:
            self.current_canvas_widget.destroy()
            
        # Configuración visual de Matplotlib (Tema Oscuro)
        fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
        fig.patch.set_facecolor('#2b2b2b') 
        ax.set_facecolor('#2b2b2b')
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        for spine in ax.spines.values():
            spine.set_color('white')
        ax.set_title(chart_type, color='white', fontsize=14)

        success = False
        msg = ""

        # Lógica de Gráficos de Ventas
        if "Ventas" in chart_type:
            success, data = self.stats_service.get_sales_data()
            if success:
                # Mapeo de lógica de agrupación
                if chart_type == "Ventas Diarias":
                    grouped = data.groupby(data['date'].dt.date)['total'].sum()
                    xlabel = "Día"
                elif chart_type == "Ventas Semanales":
                    grouped = data.groupby(data['date'].dt.to_period('W').apply(lambda r: r.start_time))['total'].sum()
                    xlabel = "Semana (Inicio)"
                elif chart_type == "Ventas Mensuales":
                    grouped = data.groupby(data['date'].dt.to_period('M').astype(str))['total'].sum()
                    xlabel = "Mes"
                elif chart_type == "Ventas Anuales":
                    grouped = data.groupby(data['date'].dt.to_period('Y').astype(str))['total'].sum()
                    xlabel = "Año"
                
                if not grouped.empty:
                    # Definir tipo y color
                    kind = 'line' if chart_type == "Ventas Diarias" else 'bar'
                    color = '#4CAF50' if kind == 'line' else '#2196F3'
                    
                    # --- CORRECCIÓN AQUÍ ---
                    # Preparamos los argumentos básicos
                    plot_kwargs = {
                        'kind': kind, 
                        'ax': ax, 
                        'color': color
                    }
                    # Solo agregamos 'marker' si es línea (evita error en barras)
                    if kind == 'line':
                        plot_kwargs['marker'] = 'o'
                    
                    # Desempaquetamos los argumentos con **
                    grouped.plot(**plot_kwargs)
                    # -----------------------

                    ax.set_ylabel("Total ($)", color='white')
                    ax.set_xlabel(xlabel, color='white')
                    ax.grid(True, linestyle='--', alpha=0.3)
                    
                    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
                else:
                    success = False
                    msg = "No hay datos para el periodo seleccionado."

        # Menús Populares
        elif chart_type == "Menús Más Vendidos":
            success, data = self.stats_service.get_popular_menus_data()
            if success:
                top_5 = data.head(5)
                # Pie chart no usa 'kind', usa función directa ax.pie
                ax.pie(top_5['total_qty'], labels=top_5['name'], autopct='%1.1f%%', 
                       startangle=90, textprops={'color':"white"})
            else:
                msg = data 

        # Ingredientes
        elif chart_type == "Uso de Ingredientes":
            success, data = self.stats_service.get_ingredient_usage_data()
            if success:
                top_10 = data.head(10)
                y_pos = range(len(top_10))
                ax.barh(y_pos, top_10['total_used'], color='#FF9800')
                ax.set_yticks(y_pos)
                ax.set_yticklabels(top_10['name'])
                ax.invert_yaxis()
                ax.set_xlabel("Cantidad (unid/kg)", color='white')
            else:
                msg = data

        # Renderizado final
        if success:
            plt.tight_layout()
            canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
            canvas.draw()
            self.current_canvas_widget = canvas.get_tk_widget()
            self.current_canvas_widget.pack(fill="both", expand=True)
        else:
            plt.close(fig)
            if not msg: msg = "No hay datos disponibles para mostrar."
            self.current_canvas_widget = Label(self.chart_frame, f"⚠️ {msg}", font=Fonts.get('h2'))
            self.current_canvas_widget.pack(pady=50)
    
    def _setup_order_history_tab(self, master):
        frame = Frame(master, pack=sn(fill='both', expand=True, padx=20, pady=20))
        Label(frame, "HISTORIAL Y GESTIÓN DE PEDIDOS", font=Fonts.get('h1')).pack(pady=10)

        # --- Filtros ---
        filter_frame = Frame(frame, pack=sn(fill="x", pady=10))
        Label(filter_frame, "Filtrar por Cliente:").pack(side="left", padx=5)
        
        self.history_client_selector = ctk.CTkComboBox(
            filter_frame, 
            values=["Todos"], 
            width=250,
            command=self._filter_history_action # Se activa al cambiar selección
        )
        self.history_client_selector.set("Todos")
        self.history_client_selector.pack(side="left", padx=5)
        
        Button(filter_frame, "🔄 Actualizar", self._update_history_treeview).pack(side="left", padx=10)
       
        # --- BOTÓN NUEVO: VER BOLETA ---
        Button(filter_frame, "📄 Ver Boleta", self._view_receipt_history_action, fg_color="#FF9800", hover_color="#F57C00").pack(side="left", padx=10)
        # -------------------------------
       
        Button(filter_frame, "❌ Eliminar Pedido", self._delete_order_action, fg_color="#D32F2F", hover_color="#C62828").pack(side="right", padx=10)

        # --- Tabla de Historial ---
        # Columnas solicitadas: ID, Fecha, Cliente, Descripción, Cantidad, Total
        columns = {
            "id": {"text": "ID", "width": 40, "anchor": "center"},
            "date": {"text": "Fecha", "width": 120, "anchor": "center"},
            "client": {"text": "Cliente", "width": 150},
            "desc": {"text": "Descripción", "width": 300},
            "qty": {"text": "Cant.", "width": 60, "anchor": "center"},
            "total": {"text": "Total", "width": 100, "anchor": "e"}
        }
        self.history_tree = TreeViewManager(frame, columns=columns)
        self.history_tree.pack(fill="both", expand=True, pady=10)
        
        # Cargar datos iniciales y selectores
        self._update_history_client_selector()
        self._update_history_treeview()

    def _view_receipt_history_action(self):
        selected = self.history_tree.get_selected_item_values()
        if not selected:
            self._show_msg("Atención", "Seleccione un pedido de la lista para ver su boleta.")
            return
        
        # El ID es la primera columna (index 0)
        order_id = selected[0]
        
        success, result = self.order_service.generate_receipt_pdf(order_id)
        
        if success:
            # Abrir automáticamente el PDF
            import os, webbrowser
            if os.path.exists(result):
                webbrowser.open(f'file:///{os.path.abspath(result)}')
            else:
                self._show_msg("Éxito", f"Boleta generada: {result}")
        else:
            self._show_msg("Error", result)

    def _update_history_client_selector(self):
        """Carga la lista de clientes en el filtro."""
        clients = self.client_service.get_all_clients()
        # Mapa para obtener ID desde el nombre seleccionado
        self.history_client_map = {f"{c.name}": c.id for c in clients}
        self.history_client_map["Todos"] = 0 # Opción especial
        
        values = ["Todos"] + list(self.history_client_map.keys())
        if "Todos" in values: values.remove("Todos"); values.insert(0, "Todos") # Asegurar orden
        
        self.history_client_selector.configure(values=values)

    def _filter_history_action(self, choice):
        """Callback al cambiar el combo de clientes."""
        self._update_history_treeview()

    def _update_history_treeview(self):
        """Consulta al servicio y llena la tabla."""
        selected_name = self.history_client_selector.get()
        client_id = self.history_client_map.get(selected_name, 0)
        
        # Llamada al servicio con el filtro (0 = todos)
        orders = self.order_service.get_formatted_orders(client_id)
        
        # Convertir lista de dicts a lista de listas para el TreeView
        data = []
        for o in orders:
            data.append([
                o['id'], 
                o['date'], 
                o['client'], 
                o['description'], 
                o['item_count'], 
                o['total']
            ])
        
        self.history_tree.load_data(data)

    def _delete_order_action(self):
        selected = self.history_tree.get_selected_item_values()
        if not selected:
            self._show_msg("Error", "Seleccione un pedido para eliminar.")
            return
        
        order_id = selected[0] # Columna ID
        
        # Confirmación implícita al pulsar borrar
        success, msg = self.order_service.delete_order(order_id)
        
        if success:
            self._show_msg("Éxito", msg)
            self._update_history_treeview()
            # También actualizamos las estadísticas si están abiertas, 
            # pero como es otra pestaña se refrescará sola al generar gráfico.
        else:
            self._show_msg("Error", msg)

    def _setup_menu_mgmt_tab(self, master):
        # Dividir pantalla: Izquierda (Formulario Menú) | Derecha (Constructor Receta)
        main_frame = Frame(master, pack=sn(fill="both", expand=True, padx=10, pady=10))
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)

        # --- COLUMNA IZQUIERDA: DATOS DEL MENÚ ---
        left_frame = Frame(main_frame, grid=sn(row=0, column=0, sticky="nsew", padx=5))
        Label(left_frame, "1. Datos del Nuevo Menú", font=Fonts.get('h2')).pack(pady=10)

        Label(left_frame, "Nombre del Menú:").pack(anchor="w", padx=10)
        self.entry_new_menu_name = ctk.CTkEntry(left_frame)
        self.entry_new_menu_name.pack(fill="x", padx=10, pady=(0, 10))

        Label(left_frame, "Precio de Venta ($):").pack(anchor="w", padx=10)
        self.entry_new_menu_price = ctk.CTkEntry(left_frame)
        self.entry_new_menu_price.pack(fill="x", padx=10, pady=(0, 10))

        Label(left_frame, "Descripción:").pack(anchor="w", padx=10)
        self.entry_new_menu_desc = ctk.CTkEntry(left_frame)
        self.entry_new_menu_desc.pack(fill="x", padx=10, pady=(0, 10))

        # --- COLUMNA DERECHA: INGREDIENTES (RECETA) ---
        right_frame = Frame(main_frame, grid=sn(row=0, column=1, sticky="nsew", padx=5))
        Label(right_frame, "2. Construir Receta", font=Fonts.get('h2')).pack(pady=10)

        # Selector de ingredientes existentes
        ing_select_frame = Frame(right_frame, pack=sn(fill="x", padx=5, pady=5))
        Label(ing_select_frame, "Ingrediente:").pack(side="left")
        
        self.combo_ingredients_mgmt = ctk.CTkComboBox(ing_select_frame, width=150)
        self.combo_ingredients_mgmt.pack(side="left", padx=5)
        
        self.entry_ing_qty_mgmt = ctk.CTkEntry(ing_select_frame, width=60, placeholder_text="Cant")
        self.entry_ing_qty_mgmt.pack(side="left", padx=5)
        
        Button(ing_select_frame, "➕ Añadir", self._add_ingredient_to_recipe_action, width=60).pack(side="left")

        # Tabla de ingredientes agregados
        Label(right_frame, "Ingredientes agregados:").pack(pady=(10,0))
        recipe_cols = {"name": {"text": "Ingrediente", "width": 150}, "qty": {"text": "Cant.", "width": 50}}
        self.recipe_builder_tree = TreeViewManager(right_frame, columns=recipe_cols, show_scrollbar=False)
        self.recipe_builder_tree.pack(fill="both", expand=True, padx=10, pady=5)
        
        Button(right_frame, "❌ Quitar Ingrediente", self._remove_ingredient_from_recipe_action, fg_color="#D32F2F").pack(pady=5)

        # --- BOTÓN FINAL ---
        Button(main_frame, "💾 GUARDAR MENÚ COMPLETO", self._save_new_menu_action, fg_color="green", height=40).grid(row=1, column=0, columnspan=2, pady=20, sticky="ew")

        # Cargar ingredientes en el combo
        self._refresh_ingredients_combo()

    def _refresh_ingredients_combo(self):
        """Carga los ingredientes de la BD en el combo box."""
        ings = self.ingredient_service.get_all_ingredients()
        names = [i.name for i in ings]
        if names:
            self.combo_ingredients_mgmt.configure(values=names)
            self.combo_ingredients_mgmt.set(names[0])
    
    def _refresh_menu_buttons(self):
        """
        Regenera los botones de menú en la pestaña Pedidos basándose en la Base de Datos.
        """
        # Verificar que el contenedor exista antes de intentar modificarlo
        if not hasattr(self, 'btn_container'):
            return

        # 1. Limpiar botones anteriores visualmente
        for widget in self.btn_container.winfo_children():
            widget.destroy()
        
        self.menu_buttons = {} # Reiniciar diccionario de referencias

        # 2. Obtener todos los menús reales de la BD
        all_menus = self.menu_service.get_all_menus()
        
        # 3. Crear un botón por cada menú
        for item in all_menus:
            # Intentar buscar imagen si existe en la configuración, sino usar None
            image_path = MENU_IMAGES.get(item.name, None)
            
            # Si no tiene imagen (menú nuevo), podríamos usar una genérica si tuviéramos
            # Por ahora, usaremos el mismo loader que maneja el error gracefully
            img = None
            if image_path:
                img = load_image_to_btn(image_path, size=(80, 80))
            
            # Crear Botón
            btn = Button(
                self.btn_container, 
                text=f"{item.name}\n${item.price:,.0f}", 
                image=img, 
                command=lambda i=item.name: self._add_to_cart_action(i), 
                width=120, 
                height=90, 
                compound="top", 
                font=Fonts.get('btn_menu_item')
            )
            btn.pack(side="left", padx=5, pady=5)
            
            # Guardar referencia para habilitar/deshabilitar según stock después
            self.menu_buttons[item.name] = btn
            
        # 4. Actualizar estado (Habilitado/Deshabilitado) según stock actual
        self._update_order_buttons()

    def _add_ingredient_to_recipe_action(self):
        """Agrega ingrediente a la lista temporal."""
        name = self.combo_ingredients_mgmt.get()
        qty_str = self.entry_ing_qty_mgmt.get()
        
        try:
            qty = float(qty_str)
            if qty <= 0: raise ValueError
            
            # Evitar duplicados en la lista visual
            for item in self.temp_recipe_builder:
                if item['name'] == name:
                    self._show_msg("Error", "El ingrediente ya está en la lista. Bórrelo para modificar.")
                    return

            self.temp_recipe_builder.append({'name': name, 'qty': qty})
            self._refresh_recipe_builder_tree()
            
        except ValueError:
            self._show_msg("Error", "Cantidad inválida.")

    def _remove_ingredient_from_recipe_action(self):
        selected = self.recipe_builder_tree.get_selected_item_values()
        if not selected: return
        
        name_to_remove = selected[0]
        # Filter para remover
        self.temp_recipe_builder = list(filter(lambda x: x['name'] != name_to_remove, self.temp_recipe_builder))
        self._refresh_recipe_builder_tree()

    def _refresh_recipe_builder_tree(self):
        data = [[i['name'], i['qty']] for i in self.temp_recipe_builder]
        self.recipe_builder_tree.load_data(data)

    def _save_new_menu_action(self):
        name = self.entry_new_menu_name.get()
        desc = self.entry_new_menu_desc.get()
        price_str = self.entry_new_menu_price.get()
        
        try:
            price = float(price_str)
            
            # Llamada al servicio
            success, msg = self.menu_service.create_custom_menu(name, price, desc, self.temp_recipe_builder)
            
            self._show_msg("Creación Menú", msg)
            
            if success:
                # Limpiar todo
                self.entry_new_menu_name.delete(0, END)
                self.entry_new_menu_desc.delete(0, END)
                self.entry_new_menu_price.delete(0, END)
                self.temp_recipe_builder = []
                self._refresh_recipe_builder_tree()
                self._generate_menu_action() # Actualizar la otra pestaña
                self._refresh_menu_buttons()
        except ValueError:
            self._show_msg("Error", "El precio debe ser un número válido.")