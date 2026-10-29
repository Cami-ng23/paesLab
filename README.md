# PAES Lab (MVP)
Local, sin internet ni cuentas.
    pip install -r requirements.txt
    python app.py   ->  http://127.0.0.1:5000
- `content/units.json`: unidades (temario DEMRE Admisión 2027). `content/config.json`: umbral 80%, nº de preguntas, repasos.
- `engine.py`: plantillas de ejercicios (se agregan con `@tpl('ID-UNIDAD')`) y validación con SymPy.
- `app.py`: rutas, SQLite (`paeslab.db`), estados y repaso espaciado.
Pendiente: rúbrica de autoevaluación, Suficiencia de Datos, simulacro, plantillas de la mayoría de las unidades.

## Subirla a internet (solo si de verdad la necesitas fuera de tu PC)
Variables de entorno: `APP_PASSWORD` (clave de entrada), `SECRET_KEY` (texto largo aleatorio), `DATA_DIR` (carpeta donde guardar paeslab.db).
Inicio: `gunicorn app:app`. IMPORTANTE: si el hosting borra el disco al reiniciar, pierdes el progreso. Elige uno con disco persistente.
Es una app de un solo usuario: todos los que entren con la clave comparten el mismo progreso.
