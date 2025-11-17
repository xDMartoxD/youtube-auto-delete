#!/usr/bin/env python3
"""Script para verificar y crear la tabla de DynamoDB localmente."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.infrastructure.persistence.dynamodb.table import ensure_table
from src.core.config import config
import logging

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    print(f"🔍 Verificando DynamoDB en: {config.dynamodb_endpoint or 'AWS default'}")
    print(f"📋 Nombre de tabla: {config.table_name}")
    print(f"🌍 Región: {config.aws_region}")
    print("-" * 50)
    
    try:
        ensure_table()
        print("✅ Tabla verificada/creada correctamente")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

