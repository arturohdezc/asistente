# 🔧 Replit Nix Troubleshooting Guide

## Error: "couldn't get nix env building nix env"

Este error es común en Replit cuando hay problemas con el canal Nix. Aquí están las soluciones:

## 🚀 Solución Rápida (Recomendada)

### Opción 1: Usar Configuración Sin Nix

1. **Renombrar archivos**:
   ```bash
   mv .replit .replit.old
   mv .replit.backup .replit
   ```

2. **Ejecutar instalación manual**:
   ```bash
   python install_replit.py
   ```

3. **Iniciar aplicación**:
   ```bash
   python start.py
   ```

### Opción 2: Actualizar Canal Nix

Si prefieres usar Nix, actualiza el canal:

1. **En Replit Shell, ejecuta**:
   ```bash
   nix-channel --update
   ```

2. **Si falla, cambia el canal**:
   ```bash
   nix-channel --add https://nixos.org/channels/nixos-23.11 nixpkgs
   nix-channel --update
   ```

3. **Reinicia el Repl** (Stop → Run)

## 🛠️ Soluciones Alternativas

### Método 1: Usar Python Module en lugar de Nix

Edita `.replit` para usar solo el módulo Python:

```toml
run = "python start.py"
modules = ["python-3.12"]

[deployment]
run = ["sh", "-c", "python start.py"]

[[ports]]
localPort = 8080
externalPort = 80

[env]
PYTHONPATH = "$REPL_HOME"
PYTHONUNBUFFERED = "1"
```

### Método 2: Instalación Manual Completa

Si todo falla, instala manualmente:

```bash
# 1. Instalar pip packages
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] aiosqlite pydantic pydantic-settings httpx python-dotenv structlog prometheus-client pytz

# 2. Configurar environment
export PYTHONPATH="$REPL_HOME"
export PYTHONUNBUFFERED="1"

# 3. Ejecutar aplicación
python start.py
```

## 🔍 Diagnóstico de Problemas

### Verificar Estado de Nix

```bash
# Verificar canal
nix-channel --list

# Verificar si Nix funciona
nix-shell --version

# Limpiar cache
nix-collect-garbage
```

### Verificar Python

```bash
# Verificar versión
python --version

# Verificar pip
pip --version

# Listar packages instalados
pip list
```

## 📋 Checklist de Troubleshooting

- [ ] ¿El canal Nix está actualizado?
- [ ] ¿Python 3.12 está disponible?
- [ ] ¿Pip funciona correctamente?
- [ ] ¿Las variables de entorno están configuradas?
- [ ] ¿Los Secrets están agregados en Replit?

## 🎯 Configuración Recomendada para Replit

Para máxima compatibilidad, usa esta configuración:

**`.replit`**:
```toml
run = "python start.py"
modules = ["python-3.12"]

[deployment]
run = ["sh", "-c", "python start.py"]

[[ports]]
localPort = 8080
externalPort = 80

[env]
PYTHONPATH = "$REPL_HOME"
PYTHONUNBUFFERED = "1"
```

**`replit.nix`** (mínimo):
```nix
{ pkgs }: {
  deps = [
    pkgs.python3
    pkgs.python3Packages.pip
    pkgs.sqlite
  ];
}
```

## 🆘 Si Nada Funciona

1. **Crear nuevo Repl** desde cero
2. **Copiar solo los archivos de código** (no .replit ni replit.nix)
3. **Usar configuración mínima** sin Nix
4. **Instalar dependencies manualmente**

## 📞 Contacto

Si sigues teniendo problemas:
1. Verifica que tengas Python 3.12+ disponible
2. Usa `python install_replit.py` para instalación manual
3. Consulta los logs en Replit Console para más detalles

---

**💡 Tip**: La configuración sin Nix suele ser más estable en Replit para proyectos Python simples.