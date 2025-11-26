from src.restaurant import RestaurantApp
# Importamos la instancia de la clase DatabaseManager
from src.config.database import db

if __name__ == '__main__':
    print("--- Sistema de Gestión de Restaurante (POO + SQLAlchemy) ---")
    
    # Llamamos al método de la instancia de clase para crear tablas
    db.create_tables()
    print("Infraestructura de base de datos lista.")

    app = RestaurantApp()
    app.mainloop()