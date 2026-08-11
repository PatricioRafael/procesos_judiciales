# Sistema de Gestión de Procesos Judiciales — GADP Potosí

Sistema en Django para que la Gobernación Autónoma Departamental de Potosí administre sus
procesos judiciales: expedientes, historial de actuaciones, acciones futuras, documentos
adjuntos y un calendario de audiencias/vencimientos.

## Requisitos

- Python 3.12+ (probado con 3.14)
- PostgreSQL 14+
- pip / venv

## Instalación local

```bash
git clone <url-del-repositorio>
cd SistemasProcesosJudiaciales

python -m venv venv
venv\Scripts\activate          # en Windows
# source venv/bin/activate     # en Linux/Mac

pip install -r requirements.txt
```

Copia `.env.example` a `.env` y completa los valores (ver la sección de abajo). Como mínimo,
para desarrollo local necesitas `SECRET_KEY` y los datos de tu base de datos PostgreSQL local.

```bash
copy .env.example .env         # en Windows
# cp .env.example .env         # en Linux/Mac
```

Crea la base de datos en PostgreSQL (el nombre debe coincidir con `DB_NAME` en tu `.env`), luego:

```bash
python manage.py migrate
python manage.py seed_catalogos      # carga categorías y estados iniciales
python manage.py createsuperuser     # tu primer usuario administrador
python manage.py runserver
```

Abre `http://127.0.0.1:8000/`.

## Variables de entorno

Todas están documentadas con un ejemplo en [`.env.example`](.env.example). El `.env` real
**nunca se sube a git** (ver `.gitignore`) porque contiene contraseñas y claves.

| Variable | Para qué sirve |
|---|---|
| `SECRET_KEY` | Clave interna de Django (firma de sesiones, tokens). Debe ser secreta y distinta por entorno. |
| `DEBUG` | `True` en desarrollo (muestra errores detallados), `False` en producción. |
| `ALLOWED_HOSTS` | Dominios/IPs desde los que se puede servir el sitio. |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Conexión a PostgreSQL. |
| `ADMIN_EMAIL` | Si lo configuras, recibes un correo automático cuando ocurre un error 500 en producción. |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL` | Datos del servidor SMTP para poder enviar ese correo. Si los dejas vacíos, el sistema funciona igual, solo no manda avisos por correo. |

## Roles del sistema

- **Administrador** (`is_superuser` de Django): gestiona usuarios y tiene acceso total.
- **Admin jurídico** (`Perfil.rol = ADMIN`): gestiona catálogos y todos los procesos.
- **Abogado** (`Perfil.rol = ABOGADO`): solo ve/edita los procesos que tiene asignados.

## Estructura del proyecto

- `gestion_procesos/` — configuración global (settings, URLs raíz).
- `usuarios/` — login, roles, auditoría.
- `catalogos/` — tablas de referencia (categorías, juzgados, estados, partes).
- `procesos/` — el núcleo: expedientes, historial, acciones futuras, documentos, calendario.
- `core_api/` — API REST (Django REST Framework) sobre los mismos datos, pensada para futuras
  integraciones (dashboards, notificaciones, otros sistemas).
- `common/` — utilidades compartidas entre apps (mixins).

## Pruebas

```bash
python manage.py test
```

Son pruebas de humo (no cubren cada caso posible): verifican que crear un proceso, cambiar su
estado, exportar a Excel/PDF y los permisos por rol siguen funcionando. Usan una base de datos
de prueba separada (`test_<DB_NAME>`) que Django crea y destruye solo — no tocan tus datos reales.

## Logs

En producción (`DEBUG=False`), los errores y advertencias quedan en `logs/django.log`
(se crea solo, no hace falta crearlo a mano) además de mostrarse en consola. Si configuraste
`ADMIN_EMAIL`, también llega un correo por cada error 500.

## Despliegue en un VPS

1. `DEBUG=False` y `ALLOWED_HOSTS` con tu dominio/IP real en el `.env` del servidor.
2. `python manage.py collectstatic` — junta los archivos estáticos (CSS/JS/imágenes) para que
   Whitenoise los sirva.
3. `python manage.py migrate`.
4. Servir con un servidor WSGI real (no `runserver`, que es solo para desarrollo), por ejemplo:
   ```bash
   gunicorn gestion_procesos.wsgi:application --bind 0.0.0.0:8000
   ```
   normalmente detrás de Nginx como proxy inverso.
5. Los documentos subidos (`media/`) y `logs/` quedan en el disco del servidor — al ser un VPS
   con disco persistente, sobreviven a reinicios, pero conviene incluirlos en tu rutina de
   respaldo de la base de datos.
