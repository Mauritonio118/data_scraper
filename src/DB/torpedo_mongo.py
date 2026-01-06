"""
mongo_use.py
Torpedo PyMongo para copiar y pegar usando la colección "platforms".
No está pensado para ejecutarse tal cual.

Idea general:
- db["platforms"] devuelve una Collection
- En una Collection haces CRUD: insert find update delete
- Casi todas las operaciones usan un "filter" para elegir qué documentos afectan
"""

# -----------------------------
# CONEXIÓN
# -----------------------------
# get_db() devuelve la base seleccionada según APP_ENV en tu .env
# db["platforms"] devuelve la colección "platforms"
from src.DB.mongo import get_db, ping

db = get_db()
platforms = db["platforms"]

# ping() confirma que el server de Mongo está respondiendo
ping()


# -----------------------------
# FILTROS
# -----------------------------
# Un "filter" es un dict que describe condiciones para matchear documentos
# Forma general: {"campo": valor} o {"campo": {"$operador": valor}}
#
# Ejemplos simples
# {"slug": "reity"}             -> campo slug es exactamente "reity"
# {"active": True}             -> campo active es True
#
# Operadores típicos
# {"visits": {"$gt": 10}}       -> visits mayor que 10
# {"visits": {"$gte": 10}}      -> mayor o igual
# {"visits": {"$lt": 10}}       -> menor
# {"visits": {"$lte": 10}}      -> menor o igual
# {"slug": {"$in": ["a", "b"]}} -> slug está en lista
# {"slug": {"$nin": ["a"]}}     -> slug no está en lista
#
# AND implícito
# {"active": True, "country": "CL"} -> ambas condiciones deben cumplirse
#
# OR explícito
# {"$or": [{"country": "CL"}, {"country": "AR"}]}
#
# Match por existencia de campo
# {"primaryDomain": {"$exists": True}}
#
# Match por arrays
# {"tags": "tokenization"} -> matchea si "tokenization" está dentro del array tags


# -----------------------------
# PROJECTION
# -----------------------------
# "projection" decide qué campos vuelven en el resultado
# Incluir campos: {"name": 1, "slug": 1}
# Excluir campos: {"bigField": 0}
# Regla práctica: no mezcles incluir y excluir salvo "_id"
# Para excluir _id: {"_id": 0, "name": 1}
#
# Nota: projection no afecta lo que hay en la DB solo afecta lo que te retorna


# -----------------------------
# INSERTS
# -----------------------------
# insert_one(document)
# - document: dict con el documento a insertar
# - crea _id automáticamente si no lo incluyes
platforms.insert_one({"slug": "reity", "name": "Reity"})

# insert_many(documents)
# - documents: lista de dicts
# - ordered=True inserta en orden y se detiene si hay error
# - ordered=False intenta insertar todos aunque alguno falle
platforms.insert_many(
    [
        {"slug": "a", "name": "A"},
        {"slug": "b", "name": "B"},
    ],
    ordered=True,
)


# -----------------------------
# FINDS
# -----------------------------
# find_one(filter=None, projection=None)
# - filter: condiciones para buscar
# - projection: campos a retornar
# Retorna: un dict del documento o None
platforms.find_one({"slug": "reity"})
platforms.find_one({"slug": "reity"}, {"_id": 0, "slug": 1, "name": 1})

# find(filter=None, projection=None)
# - retorna un cursor iterable
platforms.find({"active": True})
platforms.find({"active": True}, {"slug": 1, "name": 1})

# sort(field, direction)
# - field: nombre del campo por el que ordenas
# - direction: 1 ascendente, -1 descendente
platforms.find({}).sort("updatedAt", -1)

# skip(n) y limit(n)
# - skip: salta n documentos
# - limit: máximo de documentos retornados
platforms.find({}).skip(20).limit(10)

# count_documents(filter)
# - cuenta documentos que matchean el filter
platforms.count_documents({"active": True})


# -----------------------------
# UPDATES
# -----------------------------
# update_one(filter, update, upsert=False)
# - filter: qué documento actualizar
# - update: dict con operadores $set, $inc, etc.
# - upsert: si True inserta si no existe match
platforms.update_one({"slug": "reity"}, {"$set": {"name": "Reity SpA"}})

# update_many(filter, update, upsert=False)
# - igual que update_one pero aplica a todos los matches
platforms.update_many({"active": False}, {"$set": {"archived": True}})

# Operadores comunes en "update"
# $set: setea campos
platforms.update_one({"slug": "reity"}, {"$set": {"country": "CL"}})

# $unset: elimina campos
platforms.update_one({"slug": "reity"}, {"$unset": {"fieldToRemove": ""}})

# $inc: incrementa un número
platforms.update_one({"slug": "reity"}, {"$inc": {"visits": 1}})

# $push: agrega a un array permitiendo duplicados
platforms.update_one({"slug": "reity"}, {"$push": {"tags": "tokenization"}})

# $addToSet: agrega a un array evitando duplicados
platforms.update_one({"slug": "reity"}, {"$addToSet": {"tags": "tokenization"}})

# $pull: elimina del array lo que matchee
platforms.update_one({"slug": "reity"}, {"$pull": {"tags": "old"}})

# $currentDate: setea fecha actual en campos
platforms.update_one({"slug": "reity"}, {"$currentDate": {"updatedAt": True}})

# Upsert típico
# - $setOnInsert solo se aplica cuando se inserta
platforms.update_one(
    {"slug": "new-company"},
    {"$set": {"name": "New Company"}, "$setOnInsert": {"createdAt": "now"}},
    upsert=True,
)


# -----------------------------
# REPLACE
# -----------------------------
# replace_one(filter, replacement, upsert=False)
# Reemplaza el documento completo excepto _id
# Útil cuando tienes un "documento final" y quieres sobrescribir todo
platforms.replace_one(
    {"slug": "reity"},
    {"slug": "reity", "name": "Reity Final", "active": True},
    upsert=True,
)


# -----------------------------
# DELETES
# -----------------------------
# DELETE elimina documentos
# delete_one(filter): elimina el primer match
# delete_many(filter): elimina todos los matches
platforms.delete_one({"slug": "reity"})
platforms.delete_many({"archived": True})


# -----------------------------
# INDEXES
# -----------------------------
# Un índice mejora velocidad de búsqueda y puede imponer unicidad
# create_index("field", unique=True) evita duplicados en ese campo
# Los índices correctos hacen que find y sort sean mucho más rápidos
platforms.create_index("slug", unique=True)
platforms.create_index([("primaryDomain", 1), ("slug", 1)], unique=True)

# list_indexes() lista los índices existentes
platforms.list_indexes()


# -----------------------------
# AGGREGATE
# -----------------------------
# aggregate(pipeline) ejecuta un "pipeline" de etapas
# Pipeline: lista de dicts, cada dict es una etapa tipo $match $group $sort $project $lookup
#
# Piensa aggregate como consultas avanzadas:
# - filtrar
# - agrupar y contar
# - transformar campos
# - join con otras colecciones usando $lookup
#
# $match filtra como un find pero dentro del pipeline
# $group agrupa como GROUP BY
# $sort ordena
platforms.aggregate(
    [
        {"$match": {"active": True}},
        {"$group": {"_id": "$country", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
)


# -----------------------------
# BULK WRITE
# -----------------------------
# bulk_write sirve para enviar muchas operaciones juntas
# Ventajas:
# - más rápido que llamar update_one mil veces
# - útil en scraping para upserts masivos
#
# ordered=False sigue aunque alguna operación falle
from pymongo import UpdateOne

platforms.bulk_write(
    [
        UpdateOne({"slug": "a"}, {"$set": {"name": "A"}}, upsert=True),
        UpdateOne({"slug": "b"}, {"$set": {"name": "B"}}, upsert=True),
    ],
    ordered=False,
)


# -----------------------------
# OBJECTID
# -----------------------------
# Mongo usa _id tipo ObjectId por defecto
# Si tienes el _id como string debes convertirlo a ObjectId para buscar
from bson import ObjectId

platforms.find_one({"_id": ObjectId("6560f0f0f0f0f0f0f0f0f0f0")})
