import os
import sys
import glob

# --- DETECTAR AUTOMÁTICAMENTE EL PATH BASE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- DETECTAR AUTOMÁTICAMENTE EL ENTORNO VIRTUAL ---
# Busca la carpeta del entorno virtual creada por cPanel (en /home/usuario/virtualenv/)
project_name = os.path.basename(BASE_DIR)
venv_pattern = f'/home/{os.environ.get("USER")}/virtualenv/{os.path.relpath(BASE_DIR, "/home/"+os.environ.get("USER"))}/*/bin/activate_this.py'
venv_list = glob.glob(venv_pattern)

if venv_list:
    venv_path = venv_list[0]
    with open(venv_path) as f:
        exec(f.read(), {'__file__': venv_path})
else:
    print(f"No se encontró entorno virtual en: {venv_pattern}")

# --- AGREGAR EL PROYECTO AL PYTHONPATH ---
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# --- CONFIGURAR EL MÓDULO DE SETTINGS DJANGO ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto.settings')

# --- INICIAR LA APLICACIÓN WSGI ---
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
