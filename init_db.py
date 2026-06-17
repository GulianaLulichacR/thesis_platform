"""
Script para inicializar la base de datos.
Ejecutar una vez antes de iniciar la aplicación:
    python init_db.py
"""

import sys
import os

# Asegurar que podemos importar desde app/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base
from app.models.thesis_model import Thesis  # Importar para registrar el modelo

def main():
    print("=" * 50)
    print("Inicializando base de datos...")
    print("=" * 50)
    
    # Crear todas las tablas
    Base.metadata.create_all(bind=engine)
    
    print("✅ Base de datos creada exitosamente")
    print(f"📁 Ubicación: {os.path.abspath('thesis_platform.db')}")
    print("=" * 50)

if __name__ == "__main__":
    main()