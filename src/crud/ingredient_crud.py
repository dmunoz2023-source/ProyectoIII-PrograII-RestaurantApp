from sqlalchemy.orm import Session
from sqlalchemy import func # <-- IMPORTANTE
from src.models import IngredientModel
from typing import List, Optional

class IngredientCRUD:
    """
    Clase responsable de las operaciones CRUD directas en la base de datos para Ingredientes.
    """

    @staticmethod
    def get_all(session: Session) -> List[IngredientModel]:
        return session.query(IngredientModel).all()

    @staticmethod
    def get_by_name(session: Session, name: str) -> Optional[IngredientModel]:
        # CAMBIO: Usamos func.lower para que 'Vienesa' sea igual a 'vienesa'
        return session.query(IngredientModel).filter(func.lower(IngredientModel.name) == name.lower()).first()

    @staticmethod
    def create(session: Session, name: str, unit: str, quantity: float) -> IngredientModel:
        new_ing = IngredientModel(name=name, unit=unit, quantity=quantity)
        session.add(new_ing)
        return new_ing

    @staticmethod
    def update_quantity(session: Session, ingredient: IngredientModel, amount: float):
        ingredient.quantity += amount
        session.add(ingredient)
    
    @staticmethod
    def delete(session: Session, ingredient: IngredientModel):
        session.delete(ingredient)