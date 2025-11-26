# 🍽️ Sistema de Gestión de Restaurante

Aplicación de escritorio para la administración integral de un restaurante, desarrollada en **Python** con arquitectura por capas y base de datos SQL.

## ✨ Características Principales

* **📦 Stock:** Control de inventario y carga masiva desde CSV.
* **🍔 Menús:** Creación visual de recetas y cálculo automático de disponibilidad.
* **🛒 Ventas:** Carrito de compras con selección de clientes y validación de stock.
* **👥 Clientes:** Registro y gestión con validación de datos.
* **📊 Reportes:** Dashboard de estadísticas (Ventas, Top Productos) y generación de **PDF** (Boletas y Carta).

## 🛠️ Tecnologías

* **GUI:** `customtkinter` (Interfaz moderna).
* **Datos:** `SQLAlchemy` + `SQLite` (Persistencia y ORM).
* **Análisis:** `pandas` + `matplotlib` (Gráficos).
* **Reportes:** `reportlab` (PDF).

## 🚀 Instalación y Ejecución

1.  **Clonar el repositorio:**
    ```bash
    git clone [https://github.com/TU_USUARIO/TU_REPOSITORIO.git](https://github.com/TU_USUARIO/TU_REPOSITORIO.git)
    cd TU_REPOSITORIO
    ```

2.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Iniciar la aplicación:**
    ```bash
    python main.py
    ```

> **Nota:** La base de datos `restaurante.db` se creará automáticamente al iniciar el programa por primera vez.

## 📖 Flujo de Uso Rápido

1.  Ve a la pestaña **Carga de Ingredientes** para subir tu stock inicial (CSV) o agrégalos manualmente en **Stock**.
2.  Crea tus platos en **Gestión de Menús** asignando sus recetas.
3.  Registra un cliente en **Gestión Clientes**.
4.  ¡Listo! Ve a **Pedido** para realizar ventas y generar boletas.

---
**Asignatura:** Programación II
**Evaluación:** 3