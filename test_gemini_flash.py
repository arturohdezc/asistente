#!/usr/bin/env python3
"""
Test rápido para verificar el modelo gemini-1.5-flash
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.gemini_service import GeminiService

async def test_flash_model():
    """Test the gemini-1.5-flash model"""
    print("🧪 Testing Gemini 1.5 Flash Model")
    print("=" * 40)
    
    try:
        gemini_service = GeminiService()
        print(f"✅ Modelo configurado: {gemini_service.model}")
        print(f"✅ Base delay: {gemini_service.base_delay}s")
        
        # Test simple
        print("\n🔍 Testing analyze_text...")
        result = await gemini_service.analyze_text(
            text="Comprar leche mañana",
            source="test_user"
        )
        
        print(f"✅ Análisis exitoso!")
        print(f"   Tareas encontradas: {len(result.tasks)}")
        print(f"   Contexto: {result.context}")
        
        if result.tasks:
            for i, task in enumerate(result.tasks):
                print(f"   Tarea {i+1}: {task.title} (Prioridad: {task.priority})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_flash_model())
    if success:
        print("\n🎉 ¡Gemini Flash está funcionando correctamente!")
    else:
        print("\n⚠️  Hay problemas con la configuración.")