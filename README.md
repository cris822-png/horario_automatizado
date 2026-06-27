# TurnoDeportivo

Gestión de turnos para instalaciones deportivas. SaaS B2B multi-tenant:
coordinadores planifican, el motor valida convenios, los trabajadores aceptan
sustituciones desde la app.

## Prerrequisitos

- Docker & Docker Compose
- Flutter SDK ≥ 3.22 (Dart 3.4)
- Python 3.12 (solo para desarrollo sin Docker)

## Setup en 4 comandos

```bash
git clone <repo-url> turnodeportivo && cd turnodeportivo
cp backend/.env.example backend/.env
make up
# La BD se inicializa automáticamente con estructura_bbdd.sql
# Solo ejecutar si NO usas Docker para la BD:
# make migrate
```

## URLs

| Servicio | URL |
|---|---|
| API docs (Swagger) | http://localhost:8000/docs |
| Adminer (BD) | http://localhost:8080 |
| Flutter Web | `flutter run -d chrome` desde `frontend/` |

## Flujo de sustitución

```
Trabajador reporta baja
        │
        ▼
  Turno → DESCUBIERTO
        │
        ▼
Coordinador consulta candidatos
  (motor puntúa 0–100 por:
   titulación +40, horas libres +30,
   sin advertencias +20, contrato completo +10)
        │
        ▼
Coordinador propone sustituto
        │
        ▼
Trabajador acepta / rechaza
        │
  acepta ┤ rechaza
        │        │
        ▼        ▼
  Turno → CUBIERTO  (buscar otro candidato)
```

## Estructura (simplificada)

```
turnodeportivo/
├── backend/         # FastAPI + SQLAlchemy async
│   ├── app/
│   │   ├── api/v1/endpoints/   # auth, empleados, turnos, restricciones, sustituciones
│   │   ├── models/models.py    # 6 tablas ORM
│   │   ├── schemas/schemas.py  # Pydantic v2
│   │   └── services/           # MotorValidacion, MotorSustituciones, Notificaciones
│   └── tests/
├── frontend/        # Flutter + Riverpod + go_router
│   └── lib/
│       ├── data/    # models, repositories, api_client
│       ├── providers/
│       └── ui/      # screens + widgets
├── docker-compose.yml
└── Makefile
```

## Comandos útiles

```bash
make test-backend    # pytest -v
make logs            # docker-compose logs -f backend
make lint-backend    # ruff + mypy
```
