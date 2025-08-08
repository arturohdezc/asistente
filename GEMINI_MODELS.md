# Guía de Modelos Gemini Flash

## 🚀 Modelos Disponibles

### 1. **gemini-1.5-flash** (Recomendado)
- **Estado:** Estable
- **Velocidad:** Muy rápida
- **Límites:** Generosos (1000 RPM)
- **Uso:** Producción
- **Configuración:** `GEMINI_MODEL=gemini-1.5-flash`

### 2. **gemini-2.0-flash-exp** (Experimental)
- **Estado:** Experimental
- **Velocidad:** Muy rápida
- **Límites:** Pueden ser más restrictivos
- **Uso:** Testing de nuevas funcionalidades
- **Configuración:** `GEMINI_MODEL=gemini-2.0-flash-exp`

### 3. **gemini-2.0-flash-thinking-exp** (No recomendado)
- **Estado:** Experimental
- **Velocidad:** Variable
- **Límites:** Muy restrictivos
- **Uso:** Casos específicos de razonamiento
- **Configuración:** `GEMINI_MODEL=gemini-2.0-flash-thinking-exp`

## 🔧 Configuración

### En Replit Secrets:
```
GEMINI_API_KEY=tu_api_key_real
GEMINI_MODEL=gemini-1.5-flash
```

### En archivo .env (desarrollo):
```
GEMINI_MODEL=gemini-1.5-flash
```

## 📊 Recomendaciones por Uso

| Caso de Uso | Modelo Recomendado | Razón |
|-------------|-------------------|-------|
| **Producción** | `gemini-1.5-flash` | Estable, límites generosos |
| **Testing** | `gemini-2.0-flash-exp` | Nuevas funcionalidades |
| **Desarrollo** | `gemini-1.5-flash` | Confiable y rápido |

## 🚨 Solución de Problemas

### Error 429 (Too Many Requests)
1. Usar `gemini-1.5-flash` (mejores límites)
2. Verificar rate limiter (5 req/min)
3. Aumentar delays entre reintentos

### Error 400 (Invalid Model)
1. Verificar que el modelo esté en la lista de válidos
2. El sistema automáticamente fallback a `gemini-1.5-flash`

### Error 401 (Invalid API Key)
1. Verificar que `GEMINI_API_KEY` esté configurada
2. Verificar que la API key sea válida en Google AI Studio