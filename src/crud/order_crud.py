from sqlalchemy.orm import Session, joinedload
from src.models import OrderModel, OrderDetailModel, ClientModel
from typing import List, Optional

class OrderCRUD:
    @staticmethod
    def create_order(session: Session, client_id: int, total: float) -> OrderModel:
        order = OrderModel(client_id=client_id, total=total)
        session.add(order)
        return order

    @staticmethod
    def add_detail(session: Session, order_id: int, menu_item_id: int, quantity: int, subtotal: float):
        detail = OrderDetailModel(
            order_id=order_id,
            menu_item_id=menu_item_id,
            quantity=quantity,
            subtotal=subtotal
        )
        session.add(detail)
    
    # --- NUEVOS MÉTODOS ---
    @staticmethod
    def get_all(session: Session) -> List[OrderModel]:
        # joinedload trae los datos relacionados en una sola consulta (Eager Loading)
        return session.query(OrderModel).options(
            joinedload(OrderModel.client),
            joinedload(OrderModel.details).joinedload(OrderDetailModel.menu_item)
        ).order_by(OrderModel.date.desc()).all()

    @staticmethod
    def get_orders_by_client(session: Session, client_id: int) -> List[OrderModel]:
        return session.query(OrderModel).options(
            joinedload(OrderModel.client),
            joinedload(OrderModel.details).joinedload(OrderDetailModel.menu_item)
        ).filter(OrderModel.client_id == client_id).order_by(OrderModel.date.desc()).all()

    @staticmethod
    def get_by_id(session: Session, order_id: int) -> Optional[OrderModel]:
        return session.query(OrderModel).filter(OrderModel.id == order_id).first()

    @staticmethod
    def delete(session: Session, order: OrderModel):
        session.delete(order)
    # ----------------------