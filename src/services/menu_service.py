from sqlalchemy.exc import SQLAlchemyError
from src.config.database import db
from src.crud.menu_crud import MenuCRUD
from src.crud.ingredient_crud import IngredientCRUD
from src.models import MenuItemModel, IngredientModel

class MenuService:
    """
    Gestor de lógica de negocio para Menús.
    Calcula disponibilidad basada en stock y gestiona recetas.
    """

    def get_all_menus(self):
        """Retorna todos los menús con sus recetas cargadas."""
        session_gen = db.get_session()
        session = next(session_gen)

        try:
            return MenuCRUD.get_all(session)
        finally:
            session.close()

    def check_availability(self, menu_item: MenuItemModel) -> bool:
        """
        Valida si un menú puede prepararse con el stock actual.
        Retorna True si TODOS los ingredientes tienen stock suficiente.
        """
        if not menu_item.recipe_links:
            return False # O True, dependiendo si permites vender items sin receta
            
        return all(link.ingredient.quantity >= link.required_quantity for link in menu_item.recipe_links)

    def get_menu_status(self) -> dict:
        """
        Clasifica los menús en Disponibles y No Disponibles usando FILTER (Requisito EV3).
        """
        all_menus = self.get_all_menus()
        
        # Si no hay menús, retornamos listas vacías para que la UI no se confunda
        if not all_menus:
            return {"available": [], "unavailable": []}

        # FILTER + LAMBDA: Separar lógica
        available = list(filter(lambda m: self.check_availability(m), all_menus))
        unavailable = list(filter(lambda m: not self.check_availability(m), all_menus))

        return {
            "available": available,
            "unavailable": unavailable
        }
    
    def create_custom_menu(self, name: str, price: float, description: str, recipe_list: list) -> tuple[bool, str]:
        """
        Crea un menú nuevo validando reglas de negocio.
        recipe_list: lista de diccionarios [{'name': 'Pan', 'qty': 1}, ...]
        """
        # 1. Validaciones básicas
        if not name or price <= 0:
            return False, "Nombre inválido o precio debe ser mayor a 0."
        
        if not recipe_list:
            return False, "El menú debe tener al menos un ingrediente."

        # 2. Validar cantidades negativas usando FILTER (Requisito EV3)
        invalid_qtys = list(filter(lambda x: float(x['qty']) <= 0, recipe_list))
        if invalid_qtys:
            return False, "Hay ingredientes con cantidad 0 o negativa."

        session_gen = db.get_session()
        session = next(session_gen)

        try:
            # 3. Validar Duplicado
            if MenuCRUD.get_by_name(session, name):
                return False, f"El menú '{name}' ya existe."

            # 4. Crear Cabecera
            new_menu = MenuCRUD.create_menu(session, name, price, description)
            
            # 5. Procesar Receta
            for item in recipe_list:
                ingredient = IngredientCRUD.get_by_name(session, item['name'])
                if not ingredient:
                    raise ValueError(f"El ingrediente '{item['name']}' no existe en BD.")
                
                MenuCRUD.add_recipe_item(session, new_menu, ingredient, float(item['qty']))
            
            session.commit()
            return True, f"Menú '{name}' creado exitosamente."
            
        except Exception as e:
            session.rollback()
            return False, f"Error al crear menú: {str(e)}"
        finally:
            session.close()

    def delete_menu(self, menu_name: str) -> tuple[bool, str]:
        session_gen = db.get_session()
        session = next(session_gen)
        try:
            menu = MenuCRUD.get_by_name(session, menu_name)
            if not menu:
                return False, "Menú no encontrado."
            
            MenuCRUD.delete_menu(session, menu)
            session.commit()
            return True, "Menú eliminado."
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()

    def get_menu(self, name) -> list:
        session_gen = db.get_session()
        session = next(session_gen)
        try:
            menu = MenuCRUD.get_by_name(session, name)
            if menu:
                ingredients = [link for link in menu.recipe_links]
                return menu, ingredients
            return None, []
        finally:
            session.close()

    def initialize_default_menus(self):
        """
        Carga los menús por defecto en la BD si no existen.
        Crea automáticamente los ingredientes necesarios con stock 0.
        """
        defaults = [
            {"name": "Papas Fritas", "price": 500, "recipe": [("Papas", 5)]},
            {"name": "Completo", "price": 1800, "recipe": [("Vienesa", 1), ("Pan de completo", 1), ("Tomate", 1), ("Palta", 1)]},
            {"name": "Hamburguesa", "price": 3500, "recipe": [("Pan de hamburguesa", 1), ("Lamina de queso", 1), ("Churrasco de carne", 1)]},
            {"name": "Pollo Frito", "price": 2500, "recipe": [("Presa de pollo", 1), ("Porcion de harina", 1), ("Porcion de aceite", 1)]},
            {"name": "Panqueques", "price": 2000, "recipe": [("Panqueques", 2), ("Manjar", 1), ("Azucar flor", 1)]},
            {"name": "Ensalada Mixta", "price": 1500, "recipe": [("Lechuga", 1), ("Tomate", 1), ("Zanahoria rallada", 1)]},
            {"name": "Pepsi", "price": 1100, "recipe": [("Pepsi", 1)]}
        ]

        defaults_unid = {
          'Papas': 'kg',
          'Vienesa': 'unid',
          'Pan de completo': 'unid',
          'Tomate': 'kg',
          'Palta': 'kg',
          'Pan de hamburguesa': 'unid',
          'Lamina de queso': 'unid',
          'Churrasco de carne': 'unid',
          'Presa de pollo': 'unid',
          'Porcion de harina': 'kg',
          'Porcion de aceite': 'unid',
          'Panqueques': 'unid',
          'Manjar': 'kg',
          'Azucar flor': 'kg',
          'Lechuga': 'kg',
          'Zanahoria rallada': 'kg',
          'Pepsi': 'unid',
        }

        session_gen = db.get_session()
        session = next(session_gen)
        
        try:
            for item in defaults:
                if not MenuCRUD.get_by_name(session, item["name"]):
                    print(f"Creando menú por defecto: {item['name']}")
                    menu = MenuCRUD.create_menu(session, item["name"], item["price"])
                    
                    # Crear Receta
                    for ing_name, qty in item["recipe"]:
                        # Buscar ingrediente
                        ingredient = IngredientCRUD.get_by_name(session, ing_name)
                        
                        # --- CORRECCIÓN AQUÍ ---
                        # Si el ingrediente no existe, lo creamos al vuelo.
                        if not ingredient:
                            ingredient = IngredientCRUD.create(session, ing_name, defaults_unid.get(ing_name, "unid"), 0.0)
                            # Flush es vital aquí: guarda el ingrediente en la transacción actual
                            # para que 'get_by_name' lo encuentre en la siguiente iteración del bucle
                            # (ej. si dos menús usan Tomate)
                            session.flush()
                        # -----------------------

                        MenuCRUD.add_recipe_item(session, menu, ingredient, qty)
            
            session.commit()
            print("Inicialización de menús completada correctamente.")
        except SQLAlchemyError as e:
            print(f"Error inicializando menús: {e}")
            session.rollback()
        finally:
            session.close()