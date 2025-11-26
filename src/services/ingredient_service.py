import csv
from sqlalchemy.exc import SQLAlchemyError
from src.config.database import db
from src.crud.ingredient_crud import IngredientCRUD
from src.models import IngredientModel

class IngredientService:
    """
    Gestor de lógica de negocio para Ingredientes.
    Maneja transacciones, validaciones y procesamiento de datos.
    """

    def get_all_ingredients(self):
        """Retorna todos los ingredientes disponibles."""
        # Usamos el generador de sesión de nuestra clase DatabaseManager
        session_gen = db.get_session()
        session = next(session_gen)
        try:
            return IngredientCRUD.get_all(session)
        finally:
            session.close()

    def add_ingredient(self, name: str, unit: str, quantity: float) -> tuple[bool, str]:
        """Agrega un ingrediente o actualiza su stock si ya existe."""
        if quantity < 0:
            return False, "El stock no puede ser negativo."
        
        name = name.strip().capitalize()
        
        session_gen = db.get_session()
        session = next(session_gen)
        
        try:
            existing = IngredientCRUD.get_by_name(session, name)
            
            if existing:
                IngredientCRUD.update_quantity(session, existing, quantity)
                msg = f"Stock actualizado para '{name}'. Nuevo total: {existing.quantity}"
            else:
                IngredientCRUD.create(session, name, unit, quantity)
                msg = f"Ingrediente '{name}' creado exitosamente."
            
            session.commit()
            return True, msg
        except SQLAlchemyError as e:
            session.rollback()
            return False, f"Error de base de datos: {str(e)}"
        finally:
            session.close()

    def delete_ingredient(self, name: str) -> tuple[bool, str]:
        session_gen = db.get_session()
        session = next(session_gen)
        try:
            existing = IngredientCRUD.get_by_name(session, name)
            if not existing:
                return False, f"Ingrediente '{name}' no encontrado."
            
            # Aquí podríamos validar si el ingrediente se usa en una receta antes de borrar
            # (Requisito futuro de integridad)
            
            IngredientCRUD.delete(session, existing)
            session.commit()
            return True, f"Ingrediente '{name}' eliminado."
        except SQLAlchemyError as e:
            session.rollback()
            return False, f"Error al eliminar: {str(e)}"
        finally:
            session.close()

    def process_csv(self, filepath: str) -> tuple[bool, list, str]:
        """
        Lee y procesa un CSV usando MAP y FILTER (Requisito EV3).
        No guarda en BD todavía, solo retorna la lista de objetos válidos para previsualización.
        """
        try:
            with open(filepath, mode='r', encoding='utf-8') as file:
                reader = csv.reader(file)
                next(reader, None)  # Saltar cabecera si existe

                raw_data = list(reader)

                # 1. FILTER: Filtramos filas vacías o incompletas (menos de 3 columnas)
                # Uso de lambda para validación rápida
                valid_rows = list(filter(lambda row: len(row) >= 3 and row[0].strip(), raw_data))

                if not valid_rows:
                    return False, [], "El archivo CSV está vacío o tiene formato incorrecto."

                # 2. MAP: Transformamos la lista de strings en diccionarios con tipos correctos
                # Aquí convertimos la cantidad a float y normalizamos el nombre
                def normalize_row(row):
                    try:
                        qty = float(row[2].replace(',', '.'))
                        return {
                            "name": row[0].strip().capitalize(),
                            "unit": row[1].strip(),
                            "quantity": qty
                        }
                    except ValueError:
                        return None # Marcamos filas con números inválidos

                processed_data = list(map(normalize_row, valid_rows))

                # Filtramos los None que pudieron salir del map (errores de conversión)
                clean_data = list(filter(lambda x: x is not None and x['quantity'] > 0, processed_data))

                return True, clean_data, f"{len(clean_data)} ingredientes válidos procesados."

        except Exception as e:
            return False, [], f"Error leyendo el archivo: {e}"

    def save_bulk_ingredients(self, ingredients_data: list) -> tuple[bool, str]:
        """Recibe la lista procesada del CSV y la guarda en BD en una sola transacción."""
        session_gen = db.get_session()
        session = next(session_gen)
        count = 0
        try:
            for item in ingredients_data:
                # Normalizamos el nombre aquí también por seguridad
                clean_name = item['name'].strip().capitalize()
                
                existing = IngredientCRUD.get_by_name(session, clean_name)
                
                if existing:
                    IngredientCRUD.update_quantity(session, existing, item['quantity'])
                else:
                    IngredientCRUD.create(session, clean_name, item['unit'], item['quantity'])
                    # CAMBIO CRÍTICO: flush() fuerza a que este nuevo ingrediente sea visible 
                    # para la siguiente iteración del bucle y para validaciones UNIQUE
                    session.flush() 
                    
                count += 1
            
            session.commit()
            return True, f"{count} ingredientes guardados correctamente en la Base de Datos."
        except SQLAlchemyError as e:
            session.rollback()
            # Mostramos el error original para depurar mejor
            return False, f"Error en transacción masiva: {str(e)}"
        finally:
            session.close()