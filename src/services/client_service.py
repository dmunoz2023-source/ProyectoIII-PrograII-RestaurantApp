import re # Para expresiones regulares
from sqlalchemy.exc import SQLAlchemyError
from src.config.database import db
from src.crud.client_crud import ClientCRUD

class ClientService:
    def get_all_clients(self):
        session_gen = db.get_session()
        session = next(session_gen)
        try:
            return ClientCRUD.get_all(session)
        finally:
            session.close()

    def register_client(self, name: str, email: str) -> tuple[bool, str]:
        # 1. Validar campos vacíos (strip elimina espacios en blanco)
        if not name or not name.strip():
            return False, "El nombre no puede estar vacío."
        
        if not email or not email.strip():
            return False, "El correo no puede estar vacío."
        
        # 2. Validar formato de correo electrónico con Regex
        # Estructura: texto + @ + texto + . + texto
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            return False, "El formato del correo electrónico no es válido."

        session_gen = db.get_session()
        session = next(session_gen)
        try:
            # 3. Validar Unicidad
            if ClientCRUD.get_by_email(session, email):
                return False, "El correo electrónico ya está registrado."
            
            ClientCRUD.create(session, name.strip(), email.strip())
            session.commit()
            return True, f"Cliente {name} registrado correctamente."
        except SQLAlchemyError as e:
            session.rollback()
            return False, f"Error de base de datos: {e}"
        finally:
            session.close()

    def delete_client(self, client_id: int) -> tuple[bool, str]:
        """
        Elimina un cliente SOLO si no tiene pedidos asociados.
        """
        session_gen = db.get_session()
        session = next(session_gen)
        try:
            client = ClientCRUD.get_by_id(session, client_id)
            
            if not client:
                return False, "Cliente no encontrado."
            
            # 4. Validar Integridad Referencial (Pedidos Asociados)
            # Al acceder a client.orders, SQLAlchemy hace la consulta gracias a la relación
            if client.orders:
                return False, f"No se puede eliminar a '{client.name}': Tiene {len(client.orders)} pedidos históricos asociados."
            
            ClientCRUD.delete(session, client)
            session.commit()
            return True, f"Cliente '{client.name}' eliminado correctamente."
            
        except SQLAlchemyError as e:
            session.rollback()
            return False, f"Error al eliminar: {e}"
        finally:
            session.close()