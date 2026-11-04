# PAES Lab (Camilo)
App Flask para practicar PAES M1 y M2 con ejercicios abiertos.

## Estructura
- `app.py` rutas y reglas de aprobación/repaso · `engine.py` plantillas de ejercicios y validación (SymPy)
- `db.py` base de datos: **Postgres (Supabase)** si hay `DATABASE_URL`, **SQLite** local si no
- `content/` unidades, teoría (`lessons.json`) y configuración · `templates/`, `static/` interfaz

## Local (Windows, PowerShell)
    pip install -r requirements.txt
    python app.py          # usa SQLite (paeslab.db); crea tu cuenta en /registro
Para probar contra Supabase desde tu PC: `$env:DATABASE_URL="postgresql://..."` antes de `python app.py`.

## Despliegue: GitHub + Supabase + Render
1. **Supabase**: New project. Botón *Connect* > **Session pooler** > copia la URI (puerto 5432, usuario `postgres.xxxx`) y reemplaza `[YOUR-PASSWORD]`. Usa el pooler, no la conexión directa: la directa es solo IPv6 en el plan gratuito. Si la clave tiene símbolos (@ : / #) conviene una sin ellos. Las tablas se crean solas al primer arranque.
2. **GitHub**: repositorio **privado**. `git init`, `git add .`, `git commit -m "PAES Lab"`, luego `git remote add origin ...` y `git push -u origin main`.
3. **Render**: New > **Blueprint**, elige el repo (lee `render.yaml`). Completa `DATABASE_URL` (la URI del paso 1) e `INVITE_CODE` (un código que solo les das a tus amigos). `SECRET_KEY` se genera sola.
4. Entra a la URL `*.onrender.com` con tu clave.

## Cosas a saber
- Render gratis se duerme tras 15 min sin uso; la primera visita tarda en despertar. El progreso NO se pierde porque vive en Supabase.
- Supabase gratis **pausa el proyecto tras ~1 semana sin actividad** (se reactiva desde su panel) y **no hace respaldos automáticos**.
- Cada persona crea su cuenta (usuario y clave) y tiene su propio progreso. Si no defines `INVITE_CODE`, **cualquiera** con el link puede registrarse y gastar recursos del servidor. Las claves se guardan con hash. No hay límite de intentos de login.
- Si usabas una versión anterior, borra el `paeslab.db` viejo: esta versión usa tablas nuevas.
Pendiente: simulacro con alternativas, rúbrica de autoevaluación, Suficiencia de Datos.
