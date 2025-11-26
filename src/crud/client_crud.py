from sqlalchemy.orm import Session
from src.models import ClientModel
from typing import List, Optional

class ClientCRUD:
    @staticmethod
    def get_all(session: Session) -> List[ClientModel]:
        return session.query(ClientModel).all()

    @staticmethod
    def get_by_email(session: Session, email: str) -> Optional[ClientModel]:
        return session.query(ClientModel).filter(ClientModel.email == email).first()

    # --- NUEVO MÉTODO ---
    @staticmethod
    def get_by_id(session: Session, client_id: int) -> Optional[ClientModel]:
        return session.query(ClientModel).filter(ClientModel.id == client_id).first()
    # --------------------
    
    @staticmethod
    def create(session: Session, name: str, email: str) -> ClientModel:
        new_client = ClientModel(name=name, email=email)
        session.add(new_client)
        return new_client

    @staticmethod
    def delete(session: Session, client: ClientModel):
        session.delete(client)