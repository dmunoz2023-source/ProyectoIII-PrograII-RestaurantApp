from functools import reduce
from sqlalchemy.exc import SQLAlchemyError
from src.config.database import db
from src.crud.order_crud import OrderCRUD
from src.crud.menu_crud import MenuCRUD
from src.crud.ingredient_crud import IngredientCRUD
from src.services.menu_service import MenuService
from src.utils.receipt import Receipt

class OrderService:
    """
    Gestiona el proceso de compra completo.
    Utiliza REDUCE para calcular totales (Requisito EV3).
    """

    def process_order(self, client_id: int, cart_items: list) -> tuple[bool, str, str]:
        """
        Procesa el carrito, descuenta stock y genera el pedido en UNA transacción atómica.
        cart_items structure: [{'menu_name': str, 'quantity': int, 'price': float}]
        Retorna: (Success, Message, Filepath_dummy)
        """
        if not cart_items:
            return False, "El carrito está vacío.", ""
        
        if not client_id:
            return False, "Debe seleccionar un cliente.", ""

        session_gen = db.get_session()
        session = next(session_gen)

        try:
            # 1. REDUCE: Calcular el total del pedido usando programación funcional
            total_order = reduce(lambda acc, item: acc + (item['price'] * item['quantity']), cart_items, 0.0)

            # 2. Crear la cabecera del pedido
            new_order = OrderCRUD.create_order(session, client_id, total_order)
            session.flush() # Para obtener el ID del pedido antes de commit

            # 3. Procesar cada item del carrito
            for item in cart_items:
                menu_obj, ingredients = MenuService().get_menu(item['menu_name'])
                if not menu_obj:
                    raise ValueError(f"Menú '{item['menu_name']}' no encontrado en BD.")
                print(ingredients)
                for ingr in ingredients:
                  ingr = session.merge(ingr)
                  ingr_stock = ingr.ingredient
                  print(ingr_stock)
                  print(ingr.required_quantity)
                  required_total = ingr.required_quantity * item['quantity']

                  if ingr_stock.quantity < required_total:
                    raise ValueError(f"Stock insuficiente de '{ingr_stock.name}' para preparar {item['menu_name']}.")

                  IngredientCRUD.update_quantity(session, ingr_stock, -required_total)

                # 5. Agregar detalle al pedido
                subtotal = item['price'] * item['quantity']
                OrderCRUD.add_detail(session, new_order.id, menu_obj.id, item['quantity'], subtotal)

            session.commit()
            return True, f"Pedido registrado con éxito. Total: ${total_order:,.0f}", "boleta_generada.pdf"

        except ValueError as ve:
            session.rollback()
            return False, str(ve), ""
        except SQLAlchemyError as e:
            session.rollback()
            return False, f"Error crítico en BD: {e}", ""
        finally:
            session.close()

    def validate_stock(self, menu_name, menu_quantity, ingredients):
      session_gen = db.get_session()
      session = next(session_gen)

      for ingr in ingredients:
        ingr = session.merge(ingr)
        ingr_stock = ingr.ingredient
        required_total = ingr.required_quantity * menu_quantity

        if ingr_stock.quantity < required_total:
          related_menus = [ link.menu_item.name for link in ingr_stock.recipe_links ]
          print(related_menus)
          return False, (f"Stock insuficiente de '{ingr_stock.name}' para preparar {menu_name}."), related_menus

      return True, 'Ingredientes actualizados correctamente.', []

    def get_formatted_orders(self, client_id: int = None) -> list:
        """
        Recupera pedidos y los formatea para mostrar en la tabla.
        Aplica lógica de negocio: Generar descripción resumen y conteo de ítems.
        """
        session_gen = db.get_session()
        session = next(session_gen)
        formatted_list = []

        try:
            # Filtrar por cliente si se especifica ID, si no traer todos
            if client_id and client_id > 0:
                orders = OrderCRUD.get_orders_by_client(session, client_id)
            else:
                orders = OrderCRUD.get_all(session)

            for order in orders:
                # Validar integridad básica (requisito pauta)
                if not order.client or not order.date:
                    continue # Saltamos registros corruptos si los hubiera

                # Generar Descripción: "2x Menu A, 1x Menu B..."
                # Usamos MAP para crear la lista de strings y JOIN para unirla
                desc_items = map(lambda d: f"{d.quantity}x {d.menu_item.name}", order.details)
                description = ", ".join(desc_items)
                
                # Calcular cantidad total de menús
                total_items = sum(d.quantity for d in order.details)

                formatted_list.append({
                    "id": order.id,
                    "date": order.date.strftime("%d/%m/%Y %H:%M"),
                    "client": order.client.name,
                    "description": description,
                    "item_count": total_items,
                    "total": f"${order.total:,.0f}"
                })
            
            return formatted_list
        finally:
            session.close()

    def delete_order(self, order_id: int) -> tuple[bool, str]:
        """Elimina un pedido por su ID."""
        session_gen = db.get_session()
        session = next(session_gen)
        try:
            order = OrderCRUD.get_by_id(session, order_id)
            if not order:
                return False, "El pedido no existe o ya fue eliminado."
            
            OrderCRUD.delete(session, order)
            session.commit()
            return True, "Pedido eliminado correctamente."
        except SQLAlchemyError as e:
            session.rollback()
            return False, f"Error al eliminar: {e}"
        finally:
            session.close()

    def generate_receipt_pdf(self, order_id: int) -> tuple[bool, str]:
        """
        Busca un pedido histórico por ID y genera su documento PDF.
        """
        session_gen = db.get_session()
        session = next(session_gen)
        try:
            order = OrderCRUD.get_by_id(session, order_id)
            if not order:
                return False, "El pedido solicitado no existe."
            
            # Generar PDF usando el objeto recuperado de la BD
            receipt_gen = Receipt(order)
            success, result = receipt_gen.generate_pdf()
            
            return success, result
        except Exception as e:
            return False, f"Error al procesar la solicitud: {e}"
        finally:
            session.close()