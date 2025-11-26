from sqlalchemy.orm import Session, joinedload
from src.models import MenuItemModel, RecipeModel, IngredientModel
from typing import List, Optional

class MenuCRUD:
    """
    Operaciones de Base de Datos para Menús y Recetas.
    Utiliza 'joinedload' para traer los ingredientes relacionados eficientemente.
    """

    @staticmethod
    def get_all(session: Session) -> List[MenuItemModel]:
        # joinedload permite traer la receta y el ingrediente en la misma consulta (Eager Loading)
        return session.query(MenuItemModel).options(
            joinedload(MenuItemModel.recipe_links).joinedload(RecipeModel.ingredient)
        ).all()

    @staticmethod
    def get_by_name(session: Session, name: str) -> Optional[MenuItemModel]:
        return session.query(MenuItemModel).filter(MenuItemModel.name == name).first()

    @staticmethod
    def create_menu(session: Session, name: str, price: float, description: str = "") -> MenuItemModel:
        new_menu = MenuItemModel(name=name, price=price, description=description)
        session.add(new_menu)
        return new_menu

    @staticmethod
    def add_recipe_item(session: Session, menu: MenuItemModel, ingredient: IngredientModel, qty: float):
        """Crea el vínculo entre un menú y un ingrediente con su cantidad requerida."""
        recipe_item = RecipeModel(menu_item=menu, ingredient=ingredient, required_quantity=qty)
        session.add(recipe_item)
    
    @staticmethod
    def delete_menu(session: Session, menu: MenuItemModel):
        session.delete(menu)