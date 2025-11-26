import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Definimos Base a nivel de módulo para que los modelos puedan heredar de ella
# sin necesitar una instancia de la clase DatabaseManager (necesario por cómo funciona SQLAlchemy)
Base = declarative_base()

class DatabaseManager:
    def __init__(self, db_name="restaurante.db"):
        self._db_name = db_name
        self._base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self._db_path = os.path.join(self._base_dir, self._db_name)
        self._database_url = f"sqlite:///{self._db_path}"
        
        # Encapsulamiento del motor y la sesión
        self._engine = create_engine(self._database_url, echo=False)
        self._session_factory = sessionmaker(autocommit=False, autoflush=False, bind=self._engine)

    def create_tables(self):
        """Método público para inicializar la estructura de la BD."""
        # Importación local para registrar los modelos en Base.metadata antes de crear
        import src.models 
        print(f"Inicializando Base de Datos POO en: {self._database_url}")
        Base.metadata.create_all(bind=self._engine)

    def get_session(self):
        """
        Generador (Generator) para entregar sesiones controladas.
        Se usa con 'with' o inyecciones de dependencia.
        """
        session = self._session_factory()
        try:
            yield session
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

# Instancia global (Singleton implícito) para ser usada en el resto de la app
db = DatabaseManager()