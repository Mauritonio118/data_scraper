# DB/mongo.py
# Módulo mínimo para MongoDB que:
# 1) Lee APP_ENV
# 2) Construye variables según entorno DEV o PROD
# 3) Mantiene un MongoClient reutilizable en memoria
# 4) Entrega get_db() para usar colecciones
# 5) Permite ping y cierre limpio

import os
from dataclasses import dataclass
from typing import Optional

from pymongo import MongoClient
from pymongo.database import Database

from pathlib import Path
from dotenv import load_dotenv

#Habilitar a python para usar las variables de entorno
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# Config simple para Mongo
@dataclass(frozen=True)
class MongoConfig:
    uri: str
    db_name: str
    connect_timeout_ms: int = 10_000


# Cache del cliente para no abrir conexiones repetidas
_client: Optional[MongoClient] = None


def _get_env(name: str, default: Optional[str] = None) -> str:
    # Lee una variable de entorno con validación básica
    # Si no existe y no hay default levanta error
    value = os.getenv(name, default)
    if value is None or str(value).strip() == "":
        raise RuntimeError(f"Falta variable de entorno: {name}")
    return str(value).strip()


def load_mongo_config() -> MongoConfig:
    # Decide qué variables leer según APP_ENV
    # Ejemplo:
    # APP_ENV=dev  -> usa MONGO_URI_DEV y MONGO_DB_NAME_DEV
    # APP_ENV=prod -> usa MONGO_URI_PROD y MONGO_DB_NAME_PROD

    app_env = _get_env("APP_ENV", "dev").lower()
    suffix = app_env.upper()

    uri = _get_env(f"MONGO_URI_{suffix}")
    db_name = _get_env(f"MONGO_DB_NAME_{suffix}")

    timeout_raw = os.getenv("MONGO_CONNECT_TIMEOUT_MS", "10000")
    try:
        timeout = int(timeout_raw)
    except ValueError as e:
        raise RuntimeError("MONGO_CONNECT_TIMEOUT_MS debe ser un entero") from e

    return MongoConfig(uri=uri, db_name=db_name, connect_timeout_ms=timeout)


def get_client() -> MongoClient:
    # Devuelve un MongoClient singleton por proceso
    # Si ya existe devuelve el mismo
    # Si no existe crea uno usando la config del entorno actual

    global _client
    if _client is not None:
        return _client

    cfg = load_mongo_config()
    _client = MongoClient(
        cfg.uri,
        connectTimeoutMS=cfg.connect_timeout_ms,
    )
    return _client


def get_db() -> Database:
    # Devuelve el objeto Database apuntando a la DB del entorno
    # Ejemplo de uso:
    # db = get_db()
    # companies = db["companies"]
    cfg = load_mongo_config()
    return get_client()[cfg.db_name]


def ping() -> bool:
    # Verifica conectividad rápida
    # True si responde
    # False si falla por cualquier motivo
    try:
        get_client().admin.command("ping")
        return True
    except Exception:
        return False


def close_client() -> None:
    # Cierra el cliente si existe
    # Útil en scripts o al finalizar la app
    global _client
    if _client is not None:
        _client.close()
        _client = None

if __name__ == "__main__":
    print("Ping:", ping())
    db = get_db()
    print("Collections:", db.list_collection_names())
