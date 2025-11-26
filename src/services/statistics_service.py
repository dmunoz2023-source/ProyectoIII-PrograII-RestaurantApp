import pandas as pd
from sqlalchemy import text
from src.config.database import db

class StatisticsService:
    def __init__(self):
        self.engine = db._engine # Acceso al motor para pandas

    def get_sales_data(self):
        """Obtiene datos de ventas (Fecha y Total)."""
        query = "SELECT date, total FROM orders"
        try:
            df = pd.read_sql(query, self.engine)
            if df.empty:
                return False, "No hay registros de ventas."
            
            # Asegurar formato fecha
            df['date'] = pd.to_datetime(df['date'])
            return True, df
        except Exception as e:
            return False, str(e)

    def get_popular_menus_data(self):
        """Obtiene cantidad vendida por menú."""
        query = """
        SELECT m.name, SUM(d.quantity) as total_qty
        FROM order_details d
        JOIN menu_items m ON d.menu_item_id = m.id
        GROUP BY m.name
        ORDER BY total_qty DESC
        """
        try:
            df = pd.read_sql(query, self.engine)
            if df.empty:
                return False, "No hay detalles de pedidos registrados."
            return True, df
        except Exception as e:
            return False, str(e)

    def get_ingredient_usage_data(self):
        """
        Calcula el uso de ingredientes basado en ventas y recetas.
        JOIN complejo: DetallePedido -> Menu -> Receta -> Ingrediente
        """
        query = """
        SELECT i.name, SUM(d.quantity * r.required_quantity) as total_used, i.unit
        FROM order_details d
        JOIN recipes r ON d.menu_item_id = r.menu_item_id
        JOIN ingredients i ON r.ingredient_id = i.id
        GROUP BY i.name
        ORDER BY total_used DESC
        """
        try:
            df = pd.read_sql(query, self.engine)
            if df.empty:
                return False, "No hay datos de consumo de ingredientes."
            return True, df
        except Exception as e:
            return False, str(e)