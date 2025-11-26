from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from src.config.database import Base

# --- Entidad: Receta (Tabla intermedia con atributos) ---
class RecipeModel(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    required_quantity = Column(Float, nullable=False)

    # Relaciones Bidireccionales
    menu_item = relationship("MenuItemModel", back_populates="recipe_links")
    ingredient = relationship("IngredientModel", back_populates="recipe_links")

    def __repr__(self):
        return f"<RecipeModel(menu={self.menu_item_id}, ing={self.ingredient_id}, qty={self.required_quantity})>"

# --- Entidad: Ingrediente ---
class IngredientModel(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    unit = Column(String, nullable=False)  # 'kg', 'unid'
    quantity = Column(Float, default=0.0, nullable=False)

    # Relación inversa
    recipe_links = relationship("RecipeModel", back_populates="ingredient")

    def __repr__(self):
        return f"<IngredientModel(name='{self.name}', quantity={self.quantity})>"

# --- Entidad: Menú (Plato) ---
class MenuItemModel(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    price = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    
    # Relación uno a muchos (Receta)
    recipe_links = relationship("RecipeModel", back_populates="menu_item", cascade="all, delete-orphan")
    order_details = relationship("OrderDetailModel", back_populates="menu_item")

    def __repr__(self):
        return f"<MenuItemModel(name='{self.name}', price={self.price})>"

# --- Entidad: Cliente (Requerido por EV3) ---
class ClientModel(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    
    orders = relationship("OrderModel", back_populates="client")

    def __repr__(self):
        return f"<ClientModel(name='{self.name}', email='{self.email}')>"

# --- Entidad: Pedido (Cabecera) ---
class OrderModel(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    date = Column(DateTime, default=datetime.now)
    total = Column(Float, default=0.0)

    client = relationship("ClientModel", back_populates="orders")
    details = relationship("OrderDetailModel", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<OrderModel(id={self.id}, total={self.total})>"

# --- Entidad: Detalle de Pedido (Líneas) ---
class OrderDetailModel(Base):
    __tablename__ = "order_details"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    subtotal = Column(Float, nullable=False)

    order = relationship("OrderModel", back_populates="details")
    menu_item = relationship("MenuItemModel", back_populates="order_details")

    def __repr__(self):
        return f"<OrderDetailModel(order={self.order_id}, item={self.menu_item_id})>"