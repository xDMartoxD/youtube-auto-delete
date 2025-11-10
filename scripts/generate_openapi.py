#!/usr/bin/env python3
"""
Script para generar el esquema OpenAPI de FastAPI.
"""
import json
import sys
from pathlib import Path

# Agregar el directorio raíz al path para importar la app
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main import app

def generate_openapi(output_path: str = "openapi.json"):
    """Genera el esquema OpenAPI y lo guarda en un archivo."""
    openapi_schema = app.openapi()
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
    
    print(f"✅ OpenAPI schema generado exitosamente en: {output_file.absolute()}")
    return output_file

if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "openapi.json"
    generate_openapi(output)

