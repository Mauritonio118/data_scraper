from src.DB.mongo import get_db
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

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























