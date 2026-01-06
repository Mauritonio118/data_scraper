from src.DB.mongo import get_db
from typing import List, Dict, Any, Optional, Union
from urllib.parse import urlparse
from datetime import datetime, timezone

#Conectar con "companies" dentro de las colecciones de la DB
db = get_db()
companies = db["companies"]

def get_company_by_slug(slug: str, projection: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Retorna un documento de compañía por su slug.
    """
    return companies.find_one({"slug": slug}, projection)

######
#SLUG#
######

def get_all_slugs(include_empty: bool = False) -> List[str]:
    """
    Retorna todos los slugs desde la colección companies.
    Este resultado puede incluir repetición si existen documentos con el mismo slug.

    Parametros
    - include_empty: si es False filtra None y string vacio
                     si es True no aplica ese filtro

    Output
    - List[str] con slugs en el orden en que MongoDB los entrega
    """
    query = {"slug": {"$exists": True}}
    if not include_empty:
        query = {"slug": {"$exists": True, "$ne": None, "$ne": ""}}

    projection = {"_id": 0, "slug": 1}

    cursor = companies.find(query, projection)

    slugs = []
    for doc in cursor:
        slug = doc.get("slug")
        if isinstance(slug, str):
            if include_empty:
                slugs.append(slug)
            else:
                slug2 = slug.strip()
                if slug2:
                    slugs.append(slug2)

    return slugs

def get_unique_slugs(include_empty: bool = False) -> List[str]:
    """
    Retorna todos los slugs unicos usando distinct.
    Este enfoque es simple y rapido para listas unicas.

    Parametros
    - include_empty: si es False filtra None y string vacio
                     si es True no aplica ese filtro

    Output
    - List[str] con slugs unicos
      Nota: distinct no garantiza orden estable
    """
    query = {"slug": {"$exists": True}}
    if not include_empty:
        query = {"slug": {"$exists": True, "$ne": None, "$ne": ""}}

    slugs_unique = companies.distinct("slug", query)

    out = []
    for s in slugs_unique:
        if isinstance(s, str):
            if include_empty:
                out.append(s)
            else:
                s2 = s.strip()
                if s2:
                    out.append(s2)

    return out

def get_repeated_slugs(include_empty: bool = False) -> List[Dict[str, Any]]:

    """
    Retorna los slugs repetidos junto con su cantidad de apariciones.
    Usa aggregation para agrupar por slug y contar.

    Parametros
    - include_empty: si es False filtra None y string vacio
                     si es True no aplica ese filtro

    Output
    - List[dict] con el formato:
      [
        {"slug": "<valor>", "count": <int>},
        ...
      ]
    """
    match_stage = {"slug": {"$exists": True}}
    if not include_empty:
        match_stage = {"slug": {"$exists": True, "$ne": None, "$ne": ""}}

    pipeline = [
        {"$match": match_stage},
        {"$group": {"_id": "$slug", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}},
        {"$sort": {"count": -1, "_id": 1}},
        {"$project": {"_id": 0, "slug": "$_id", "count": 1}},
    ]

    result = list(companies.aggregate(pipeline))

    if include_empty:
        return result

    out = []
    for row in result:
        slug = row.get("slug")
        count = row.get("count")
        if isinstance(slug, str) and isinstance(count, int):
            slug2 = slug.strip()
            if slug2:
                out.append({"slug": slug2, "count": count})

    return out

def get_slugs_not_inactive() -> List[str]:
    """
    Retorna todos los slugs de empresas cuyo operational.status NO es 'inactive'.
    Incluye documentos con status distinto a 'inactive' y documentos donde el campo no existe.

    Output
    - List[str] con slugs.
    """
    query = {"operational.status": {"$ne": "inactive"}}
    projection = {"_id": 0, "slug": 1}

    cursor = companies.find(query, projection)

    slugs = []
    for doc in cursor:
        slug = doc.get("slug")
        if isinstance(slug, str):
            slug2 = slug.strip()
            if slug2:
                slugs.append(slug2)

    return slugs



####################
#OPERATIONAL STATUS#
####################

def manage_operational_status(slug: str, action: str = "get", status: Optional[str] = None, notes: Optional[str] = None) -> Union[Dict[str, Any], None]:
    """
    Gestiona el campo operational del documento.
    
    action:
      - "get": retorna el objeto operational (o None si no existe/compañia no existe)
      - "set" (o "update"): actualiza status y/o notes.
           * Si el campo no existe, lo crea.
           * Si los valores son idénticos a los existentes, NO actualiza nada (idempotente).
           * Solo actualiza updatedAt si hubo cambios reales o es creación.
           * Soporta partial updates: si status o notes es None, mantiene el valor previo.
      - "delete" (o "remove", "unset"): elimina el campo operational completo using $unset.
      
    Retorno:
      - get: dict operational o None
      - set/delete: dict con matched, modified, y opcionalmente message
    """
    query = {"slug": slug}
    action_norm = (action or "").strip().lower()

    # --- GET ---
    if action_norm == "get":
        doc = companies.find_one(query, {"_id": 0, "operational": 1})
        if not doc:
            return None
        return doc.get("operational")

    # --- DELETE ---
    if action_norm in {"delete", "remove", "unset"}:
        update = {"$unset": {"operational": ""}}
        res = companies.update_one(query, update)
        return {"matched": res.matched_count, "modified": res.modified_count}

    # --- SET / UPDATE ---
    if action_norm in {"set", "update"}:
        # 1. Leer estado actual para comparar
        doc = companies.find_one(query, {"operational": 1})
        if not doc:
            # Si la compañia no existe, no podemos hacer update (matched=0)
            return {"matched": 0, "modified": 0, "message": "Company not found"}

        current_op = doc.get("operational") or {}
        
        # 2. Determinar nuevos valores
        # Si el input es None, mantenemos el valor actual.
        # Si el current no tiene el field, y el input es None, remains None (pero al crear el objeto, quizas queramos guardar null o no guardar la keys. Segun modelo, son strings opcionales, pero status tiene enum).
        
        target_status = status if status is not None else current_op.get("status")
        target_notes = notes if notes is not None else current_op.get("notes")
        
        # 3. Comparar con lo existente
        # Verificamos igualdad estricta.
        # Ojo: si current_op vacio (ej. primera vez), y inputs None, target sera None.
        
        old_status = current_op.get("status")
        old_notes = current_op.get("notes")

        # Flag de cambio
        has_changes = False
        
        # Si no existia operational, y ahora vamos a escribir algo, cuenta como cambio (creacion)
        # PERO si target_status es None y target_notes es None, quizas no queremos crear un operational vacio?
        # Asumiremos que si se llama a set, se intuye intencion de crear/actualizar datos.
        # Aunque si status y notes son None, solo se actualizaria updatedAt? Eso podria ser valido "confirmacion de estado".
        # PERO el requerimiento dice: "Si no se entrega status y/o notes... no hay que modificar... La falta de datos implica que no hay que hacer ningun cambio... no hay que actualizar fecha"
        
        if "operational" not in doc:
            # Creando desde cero
            has_changes = True
        else:
            # Ya existe, comparamos campos
            if target_status != old_status:
                has_changes = True
            if target_notes != old_notes:
                has_changes = True
        
        if not has_changes:
            return {"matched": 1, "modified": 0, "message": "No changes needed"}

        # 4. Preparar update
        now_str = datetime.now(timezone.utc).isoformat()
        
        # Construimos el objeto operational completo o usamos dot notation?
        # Dot notation es mas seguro para preservar otros fields si existieran (el modelo no muestra mas, pero por si acaso).
        # Sin embargo, queremos asegurar que si status es None y antes no existia, no lo escribamos?
        # Simplificacion: $set de campos individuales.
        
        update_fields = {
            "operational.updatedAt": now_str
        }
        if target_status is not None:
            update_fields["operational.status"] = target_status
        if target_notes is not None:
            update_fields["operational.notes"] = target_notes

        # Caso borde: si queriamos borrar status pasando None? 
        # La funcion dice "si status es None, mantiene el valor previo".
        # Si quisiéramos borrar un valor especifico, necesitariamos otro mecanismo o asumir string vacio = borrar.
        # Por ahora nos apegamos a "None = no tocar".
            
        res = companies.update_one(query, {"$set": update_fields})
        return {"matched": res.matched_count, "modified": res.modified_count, "updatedAt": now_str}

    raise ValueError("action no valido. Usa get, set, delete")


#################
#PRIMARY DOMAINS#
#################

def get_all_primary_domains(include_empty: bool = False) -> List[str]:
    """
    Retorna todos los primaryDomain desde la colección companies.
    Este resultado puede incluir repetición si existen documentos con el mismo primaryDomain.
    """
    query = {"primaryDomain": {"$exists": True}}
    if not include_empty:
        query = {"primaryDomain": {"$exists": True, "$ne": None, "$ne": ""}}

    projection = {"_id": 0, "primaryDomain": 1}
    cursor = companies.find(query, projection)

    out = []
    for doc in cursor:
        pd = doc.get("primaryDomain")
        if isinstance(pd, str):
            if include_empty:
                out.append(pd)
            else:
                pd2 = pd.strip()
                if pd2:
                    out.append(pd2)

    return out

def get_unique_primary_domains(include_empty: bool = False) -> List[str]:
    """
    Retorna primaryDomain unicos usando distinct.
    """
    query = {"primaryDomain": {"$exists": True}}
    if not include_empty:
        query = {"primaryDomain": {"$exists": True, "$ne": None, "$ne": ""}}

    values = companies.distinct("primaryDomain", query)

    out = []
    for v in values:
        if isinstance(v, str):
            if include_empty:
                out.append(v)
            else:
                v2 = v.strip()
                if v2:
                    out.append(v2)

    return out

def get_repeated_primary_domains(include_empty: bool = False) -> List[Dict[str, Any]]:
    """
    Retorna primaryDomain repetidos con su count usando aggregation.
    """
    match_stage = {"primaryDomain": {"$exists": True}}
    if not include_empty:
        match_stage = {"primaryDomain": {"$exists": True, "$ne": None, "$ne": ""}}

    pipeline = [
        {"$match": match_stage},
        {"$group": {"_id": "$primaryDomain", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}},
        {"$sort": {"count": -1, "_id": 1}},
        {"$project": {"_id": 0, "primaryDomain": "$_id", "count": 1}},
    ]

    result = list(companies.aggregate(pipeline))

    if include_empty:
        return result

    out = []
    for row in result:
        pd = row.get("primaryDomain")
        count = row.get("count")
        if isinstance(pd, str) and isinstance(count, int):
            pd2 = pd.strip()
            if pd2:
                out.append({"primaryDomain": pd2, "count": count})

    return out


##############
#DATA SOURCES#
##############

def get_datasource_by_url(slug: str, datasource_url: str, projection: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Retorna un documento que contiene el dataSource específico.
    Usa la proyección posicional $ si no se especifica otra.
    """
    if projection is None:
        projection = {"_id": 0, "dataSources.$": 1}
    return companies.find_one({"slug": slug, "dataSources.url": datasource_url}, projection)

#URLS
def get_unique_datasource_urls(slug: str) -> list[str]:
    """
    Trae todas las urls dentro de dataSources.url para una company identificada por slug.
    El output es una lista unica sin repeticion.
    """
    """
    Pipeline
    1) match: selecciona el documento de la company por slug
    2) unwind: expande el array dataSources para procesar cada elemento por separado
    3) match: filtra dataSources.url validas (existe, no None, no vacio)
    4) group: agrupa por slug y deduplica urls con addToSet
    5) project: deja solo el campo uniqueUrls en el resultado final
    """
    pipeline = [
        {"$match": {"slug": slug}},
        {"$unwind": "$dataSources"},
        {"$match": {"dataSources.url": {"$exists": True, "$ne": None, "$ne": ""}}},
        {"$group": {"_id": "$slug", "uniqueUrls": {"$addToSet": "$dataSources.url"}}},
        {"$project": {"_id": 0, "uniqueUrls": 1}},
    ]

    """
    Ejecuta el pipeline en MongoDB.
    aggregate retorna una lista con 0 o 1 elementos porque agrupamos por slug.
    """
    result = list(companies.aggregate(pipeline))

    """
    Si existe resultado, retornamos la lista uniqueUrls.
    Si no existe, retornamos lista vacia.
    """
    return result[0]["uniqueUrls"] if result else []

def get_repeated_datasource_urls(slug: str) -> list[dict]:
    """
    Trae todas las urls repetidas dentro de dataSources.url para una company identificada por slug.
    El output incluye cada url repetida junto a su count.
    """
    """
    Pipeline
    1) match: selecciona el documento de la company por slug
    2) unwind: expande el array dataSources para procesar cada elemento por separado
    3) match: filtra dataSources.url validas (existe, no None, no vacio)
    4) group: agrupa por url y cuenta ocurrencias
    5) match: deja solo urls con count mayor a 1
    6) sort: ordena por count desc y luego por url asc
    7) project: formatea el output final como { url, count }
    """
    pipeline = [
        {"$match": {"slug": slug}},
        {"$unwind": "$dataSources"},
        {"$match": {"dataSources.url": {"$exists": True, "$ne": None, "$ne": ""}}},
        {"$group": {"_id": "$dataSources.url", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}},
        {"$sort": {"count": -1, "_id": 1}},
        {"$project": {"_id": 0, "url": "$_id", "count": 1}},
    ]

    """
    Ejecuta el pipeline en MongoDB.
    Retorna lista vacia si no hay urls repetidas.
    """
    return list(companies.aggregate(pipeline))

def unique_company_urls_from_primary_domain(slug: str, mode: str = "loose") -> list[str]:
    """
    Busca la company por slug y retorna una lista unica de urls de dataSources.url
    que pertenecen al primaryDomain.
    """
    doc = companies.find_one(
        {"slug": slug},
        {"_id": 0, "primaryDomain": 1, "dataSources.url": 1}
    )

    if not doc:
        return []

    primary_domain = doc.get("primaryDomain") or ""
    data_sources = doc.get("dataSources") or []

    unique = set()

    for ds in data_sources:
        if not isinstance(ds, dict):
            continue
        u = ds.get("url")
        if not isinstance(u, str):
            continue
        u = u.strip()
        if not u:
            continue
        if _belongs_to_company(u, primary_domain, mode=mode):
            unique.add(u)

    return sorted(unique)

#LINKS
def get_links_from_company_datasource(slug: str, datasource_url: str, sections=None) -> list[str]:
    """
    Trae todos los links de un dataSource especifico dentro de una company.

    Input:
      - slug: slug de la company
      - datasource_url: el campo dataSources.url que quieres seleccionar
      - sections: None para head header main y footer
                 "main" para uno solo
                 ["header", "footer"] para combinatoria

    Output:
      - lista unica sin duplicados con los links encontrados en las secciones pedidas
    """
    sections_norm = _normalize_sections(sections)
    if not sections_norm:
        return []

    doc = companies.find_one(
        {"slug": slug, "dataSources.url": datasource_url},
        {"_id": 0, "dataSources.$": 1}
    )

    if not doc or "dataSources" not in doc or not doc["dataSources"]:
        return []

    ds = doc["dataSources"][0]
    links_obj = ds.get("links") if isinstance(ds, dict) else None
    if not isinstance(links_obj, dict):
        return []

    collected = []
    for section in sections_norm:
        lst = links_obj.get(section)
        if isinstance(lst, list):
            collected.extend(lst)

    return _unique_preserve_order(collected)

#TEXTS
def get_texts_from_company_datasource(slug: str, datasource_url: str, sections=None, dedupe: bool = True) -> list[str]:
    """
    Trae todos los textos de un dataSource especifico dentro de una company.

    Input:
      - slug: slug de la company
      - datasource_url: el campo dataSources.url que quieres seleccionar
      - sections: None para head header main y footer
                 "main" para uno solo
                 ["header", "footer"] para combinatoria
      - dedupe: True entrega lista unica sin duplicados
                False entrega textos sin deduplicar

    Output:
      - lista de textos segun secciones elegidas
    """
    sections_norm = _normalize_sections(sections)
    if not sections_norm:
        return []

    doc = companies.find_one(
        {"slug": slug, "dataSources.url": datasource_url},
        {"_id": 0, "dataSources.$": 1}
    )

    if not doc or "dataSources" not in doc or not doc["dataSources"]:
        return []

    ds = doc["dataSources"][0]
    texts_obj = ds.get("texts") if isinstance(ds, dict) else None
    if not isinstance(texts_obj, dict):
        return []

    collected = []
    for section in sections_norm:
        lst = texts_obj.get(section)
        if isinstance(lst, list):
            collected.extend(lst)

    if dedupe:
        return _unique_preserve_order(collected)

    out = []
    for t in collected:
        if isinstance(t, str):
            t2 = t.strip()
            if t2:
                out.append(t2)
    return out

#ROLE
def datasource_role(slug: str, datasource_url: str, action: str = "get", role: str | None = None):
    """
    Gestiona el campo dataSources.role para una url dentro de dataSources.

    action soportado
    - "get": lee el role actual
    - "set": setea role al valor entregado
    - "update": alias de set
    - "delete": elimina el campo role usando unset

    Input
    - slug: slug de la company
    - datasource_url: valor exacto en dataSources.url
    - action: string con la operacion
    - role: string requerido en set o update

    Output
    - action "get": str o None
    - action "set" o "update" o "delete": dict con matched y modified
    """
    """
    Query base
    Encuentra el documento por slug y el elemento de dataSources por url.
    """
    query = {"slug": slug, "dataSources.url": datasource_url}

    action_norm = (action or "").strip().lower()

    if action_norm == "get":
        """
        Lee solo el elemento de dataSources que matchea usando projection posicional.
        """
        doc = companies.find_one(query, {"_id": 0, "dataSources.$": 1})
        if not doc:
            return None

        ds_list = doc.get("dataSources") or []
        if not ds_list or not isinstance(ds_list[0], dict):
            return None

        return ds_list[0].get("role")

    if action_norm in {"set", "update"}:
        """
        Valida role
        Setea dataSources.$.role en el elemento encontrado.
        """
        if not isinstance(role, str) or not role.strip():
            raise ValueError("role debe ser un string no vacio para action set o update")

        update = {"$set": {"dataSources.$.role": role.strip()}}
        res = companies.update_one(query, update)
        return {"matched": res.matched_count, "modified": res.modified_count}

    if action_norm in {"delete", "unset", "remove"}:
        """
        Elimina el campo role del elemento encontrado.
        """
        update = {"$unset": {"dataSources.$.role": ""}}
        res = companies.update_one(query, update)
        return {"matched": res.matched_count, "modified": res.modified_count}

    raise ValueError("action no valido. Usa get, set, update, delete")

#KIND
def datasource_kind(slug: str, datasource_url: str, action: str = "get", kind: str | None = None):
    """
    Gestiona el campo dataSources.kind para una url dentro de dataSources.

    action soportado
    - "get": lee el kind actual
    - "set": setea kind al valor entregado
    - "update": alias de set
    - "delete": elimina el campo kind usando unset

    Input
    - slug: slug de la company
    - datasource_url: valor exacto en dataSources.url
    - action: string con la operacion
    - kind: string requerido en set o update

    Output
    - action "get": str o None
    - action "set" o "update" o "delete": dict con matched y modified
    """
    """
    Query base
    Encuentra el documento por slug y el elemento de dataSources por url.
    """
    query = {"slug": slug, "dataSources.url": datasource_url}

    action_norm = (action or "").strip().lower()

    if action_norm == "get":
        """
        Lee solo el elemento de dataSources que matchea usando projection posicional.
        """
        doc = companies.find_one(query, {"_id": 0, "dataSources.$": 1})
        if not doc:
            return None

        ds_list = doc.get("dataSources") or []
        if not ds_list or not isinstance(ds_list[0], dict):
            return None

        return ds_list[0].get("kind")

    if action_norm in {"set", "update"}:
        """
        Valida kind
        Setea dataSources.$.kind en el elemento encontrado.
        """
        if not isinstance(kind, str) or not kind.strip():
            raise ValueError("kind debe ser un string no vacio para action set o update")

        update = {"$set": {"dataSources.$.kind": kind.strip()}}
        res = companies.update_one(query, update)
        return {"matched": res.matched_count, "modified": res.modified_count}

    if action_norm in {"delete", "unset", "remove"}:
        """
        Elimina el campo kind del elemento encontrado.
        """
        update = {"$unset": {"dataSources.$.kind": ""}}
        res = companies.update_one(query, update)
        return {"matched": res.matched_count, "modified": res.modified_count}

    raise ValueError("action no valido. Usa get, set, update, delete")


#############
#MOBILE APPS#
#############

def upsert_mobile_app(slug: str, url: str, store: str) -> Dict[str, int]:
    """
    Agrega o actualiza una mobileApp en el array mobileApps.
    - Si la url ya existe, actualiza el store.
    - Si no existe, agrega el objeto {url, store}.
    - Si el array mobileApps no existe, lo crea.
    """
    # 1. Intentar actualizar si existe
    query = {"slug": slug, "mobileApps.url": url}
    update = {"$set": {"mobileApps.$.store": store}}
    
    result = companies.update_one(query, update)
    
    if result.matched_count > 0:
        return {"matched": result.matched_count, "modified": result.modified_count}
        
    # 2. Si no existe (matched_count == 0), hacemos push
    # Usamos addToSet para evitar duplicados si corre en paralelo, aunque la logica de arriba ya cubre update.
    # Pero para ser consistentes con "agregar si no existe", push es lo estandar tras fallo de update por url.
    
    query_push = {"slug": slug}
    update_push = {"$push": {"mobileApps": {"url": url, "store": store}}}
    
    result_push = companies.update_one(query_push, update_push)
    
    return {"matched": result_push.matched_count, "modified": result_push.modified_count}

def get_mobile_apps(slug: str, store: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retorna la lista de mobileApps para un slug.
    Opcionalmente filtra por store.
    """
    project = {"_id": 0, "mobileApps": 1}
    doc = companies.find_one({"slug": slug}, project)
    
    if not doc or "mobileApps" not in doc:
        return []
        
    apps = doc["mobileApps"]
    if not isinstance(apps, list):
        return []
        
    if store:
        return [app for app in apps if isinstance(app, dict) and app.get("store") == store]
        
    return apps

def remove_mobile_app(slug: str, url: Optional[str] = None, store: Optional[str] = None) -> Dict[str, int]:
    """
    Elimina datos dentro de mobileApps.
    - Si url y store son None: Deja el campo mobileApps vacio ([]).
    - Si url existe: borra coincidencias de url.
    - Si store existe: borra coincidencias de store.
    - Si ambos existen: borra coincidencias exactas de url Y store.
    """
    query = {"slug": slug}
    
    if url is None and store is None:
        # Vaciar el array
        update = {"$set": {"mobileApps": []}}
    else:
        # Construir filtro para pull
        pull_filter = {}
        if url:
            pull_filter["url"] = url
        if store:
            pull_filter["store"] = store
            
        update = {"$pull": {"mobileApps": pull_filter}}
        
    result = companies.update_one(query, update)
    return {"matched": result.matched_count, "modified": result.modified_count}

def delete_mobile_apps_field(slug: str) -> Dict[str, int]:
    """
    Elimina completamente el campo mobileApps del documento.
    """
    query = {"slug": slug}
    update = {"$unset": {"mobileApps": ""}}
    
    result = companies.update_one(query, update)
    return {"matched": result.matched_count, "modified": result.modified_count}


#################
#SOCIAL PROFILES#
#################

def upsert_social_profile(slug: str, url: str, platform: str) -> Dict[str, int]:
    """
    Agrega o actualiza un socialProfile en el array socialProfiles.
    - Si la url ya existe, actualiza la platform.
    - Si no existe, agrega el objeto {url, platform}.
    - Si el array socialProfiles no existe, lo crea.
    """
    # 1. Intentar actualizar si existe
    query = {"slug": slug, "socialProfiles.url": url}
    update = {"$set": {"socialProfiles.$.platform": platform}}
    
    result = companies.update_one(query, update)
    
    if result.matched_count > 0:
        return {"matched": result.matched_count, "modified": result.modified_count}
        
    # 2. Si no existe (matched_count == 0), hacemos push
    query_push = {"slug": slug}
    update_push = {"$push": {"socialProfiles": {"url": url, "platform": platform}}}
    
    result_push = companies.update_one(query_push, update_push)
    
    return {"matched": result_push.matched_count, "modified": result_push.modified_count}

def get_social_profiles(slug: str, platform: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retorna la lista de socialProfiles para un slug.
    Opcionalmente filtra por platform.
    """
    project = {"_id": 0, "socialProfiles": 1}
    doc = companies.find_one({"slug": slug}, project)
    
    if not doc or "socialProfiles" not in doc:
        return []
        
    profiles = doc["socialProfiles"]
    if not isinstance(profiles, list):
        return []
        
    if platform:
        return [p for p in profiles if isinstance(p, dict) and p.get("platform") == platform]
        
    return profiles

def remove_social_profile(slug: str, url: Optional[str] = None, platform: Optional[str] = None) -> Dict[str, int]:
    """
    Elimina datos dentro de socialProfiles.
    - Si url y platform son None: Deja el campo socialProfiles vacio ([]).
    - Si url existe: borra coincidencias de url.
    - Si platform existe: borra coincidencias de platform.
    - Si ambos existen: borra coincidencias exactas de url Y platform.
    """
    query = {"slug": slug}
    
    if url is None and platform is None:
        # Vaciar el array
        update = {"$set": {"socialProfiles": []}}
    else:
        # Construir filtro para pull
        pull_filter = {}
        if url:
            pull_filter["url"] = url
        if platform:
            pull_filter["platform"] = platform
            
        update = {"$pull": {"socialProfiles": pull_filter}}
        
    result = companies.update_one(query, update)
    return {"matched": result.matched_count, "modified": result.modified_count}

def delete_social_profiles_field(slug: str) -> Dict[str, int]:
    """
    Elimina completamente el campo socialProfiles del documento.
    """
    query = {"slug": slug}
    update = {"$unset": {"socialProfiles": ""}}
    
    result = companies.update_one(query, update)
    return {"matched": result.matched_count, "modified": result.modified_count}


####################
#INTERNAL UTILITIES#
####################

def _to_host(value: str) -> str:
    """
    Convierte un string a host normalizado.
    Normaliza mayusculas, elimina scheme faltante, quita puerto y remueve www.
    Retorna string vacio si no puede parsear.
    """
    if not isinstance(value, str):
        return ""

    s = value.strip().lower()
    if not s:
        return ""

    if "://" not in s:
        s = "https://" + s

    try:
        p = urlparse(s)
    except Exception:
        return ""

    host = (p.netloc or "").lower()

    if "@" in host:
        host = host.split("@", 1)[1]

    if ":" in host:
        host = host.split(":", 1)[0]

    if host.startswith("www."):
        host = host[4:]

    return host.strip(".")

def _belongs_to_company(url: str, primary_domain: str, mode: str = "loose") -> bool:
    """
    Valida si una url pertenece a la empresa segun primary_domain.

    mode strict:
      - host exacto
      - subdominios del primary_domain

    mode loose:
      - incluye strict
      - acepta casos donde el label base aparece como label completo
        ejemplo.com -> ejemplo.algo.com
    """
    h = _to_host(url)
    pd = _to_host(primary_domain)

    if not h or not pd:
        return False

    if h == pd or h.endswith("." + pd):
        return True

    if mode == "strict":
        return False

    base_label = pd.split(".")[0] if "." in pd else pd
    if not base_label:
        return False

    labels = [part for part in h.split(".") if part]
    return base_label in labels

def _normalize_sections(sections):
    """
    Normaliza el input sections para aceptar:
    - None: usa head header main y footer
    - str: un solo campo
    - list tuple set: combinatoria de campos

    Retorna lista de secciones validas.
    """
    ALLOWED_SECTIONS = {"head", "header", "main", "footer"}

    if sections is None:
        return ["head", "header", "main", "footer"]

    if isinstance(sections, str):
        sections_list = [sections]
    else:
        sections_list = list(sections)

    out = []
    for s in sections_list:
        if not isinstance(s, str):
            continue
        s2 = s.strip().lower()
        if s2 in ALLOWED_SECTIONS:
            out.append(s2)

    return out

def _unique_preserve_order(values):
    """
    Deduplica preservando el orden de aparicion.
    Solo conserva strings no vacios.
    """
    seen = set()
    out = []
    for v in values:
        if not isinstance(v, str):
            continue
        v2 = v.strip()
        if not v2:
            continue
        if v2 in seen:
            continue
        seen.add(v2)
        out.append(v2)
    return out
