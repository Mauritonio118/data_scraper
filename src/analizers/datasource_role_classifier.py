"""
Módulo para clasificar los roles de los dataSources de una compañía.
Clasifica la URL principal de cada objeto en dataSources y asigna el role correspondiente.
"""

from typing import List, Dict, Any, Optional
from src.DB.companies_querys import (
    get_company_by_slug,
    get_datasource_by_url,
    get_unique_datasource_urls,
    datasource_role
)
from src.analizers.role_classifier import classify_url, get_available_roles


def classify_role_company_datasources(
    slug: str,
    target_roles: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Clasifica los roles de todos los dataSources de una compañía.
    Analiza la URL principal de cada objeto en dataSources y asigna el role correspondiente.
    
    Input:
      - slug: slug de la company
      - target_roles: Lista de roles a buscar. Si es None, busca todos los roles disponibles.
                      Si se especifica, solo clasifica esos roles específicos.
    
    Output:
      - Dict con estadísticas:
        {
          "processed": <int>,  # Total de dataSources procesados
          "classified": <int>, # DataSources que recibieron un role
          "not_classified": <int>, # DataSources sin role
          "roles_found": {<role>: <count>}, # Contador por role
          "updated": <int> # Cantidad de dataSources actualizados en la DB
        }
    """
    # Obtener el documento de la compañía
    doc = get_company_by_slug(
        slug=slug,
        projection={"_id": 0, "primaryDomain": 1, "dataSources.url": 1, "dataSources.role": 1}
    )
    
    if not doc:
        return {
            "processed": 0,
            "classified": 0,
            "not_classified": 0,
            "roles_found": {},
            "updated": 0,
            "error": "Company no encontrada"
        }
    
    primary_domain = doc.get("primaryDomain") or ""
    data_sources = doc.get("dataSources") or []
    
    if not data_sources:
        return {
            "processed": 0,
            "classified": 0,
            "not_classified": 0,
            "roles_found": {},
            "updated": 0,
            "error": "No se encontraron dataSources"
        }
    
    # Validar target_roles
    available_roles = get_available_roles()
    if target_roles:
        target_roles = [r for r in target_roles if r in available_roles]
        if not target_roles:
            target_roles = None  # Si ninguno es válido, usar todos
    
    stats = {
        "processed": 0,
        "classified": 0,
        "not_classified": 0,
        "roles_found": {},
        "updated": 0
    }
    
    # Procesar cada dataSource
    for ds in data_sources:
        if not isinstance(ds, dict):
            continue
        
        datasource_url = ds.get("url")
        if not isinstance(datasource_url, str) or not datasource_url.strip():
            continue
        
        stats["processed"] += 1
        
        # Clasificar la URL principal del dataSource
        role = classify_url(datasource_url.strip(), primary_domain, target_roles)
        
        if role:
            stats["classified"] += 1
            stats["roles_found"][role] = stats["roles_found"].get(role, 0) + 1
            
            # Actualizar el role en la DB usando la función existente
            result = datasource_role(
                slug=slug,
                datasource_url=datasource_url,
                action="set",
                role=role
            )
            
            if result.get("modified", 0) > 0:
                stats["updated"] += 1
        else:
            stats["not_classified"] += 1
    
    return stats


def classify_role_single_datasource(
    slug: str,
    datasource_url: str,
    target_roles: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Clasifica el role de un dataSource específico.
    
    Input:
      - slug: slug de la company
      - datasource_url: URL del dataSource a clasificar
      - target_roles: Lista de roles a buscar. Si es None, busca todos.
    
    Output:
      - Dict con estadísticas:
        {
          "processed": <int>,  # Siempre 1 si se encuentra
          "classified": <int>, # 1 si se clasificó, 0 si no
          "not_classified": <int>, # 0 si se clasificó, 1 si no
          "role": <str|None>, # Role encontrado o None
          "updated": <bool> # Si se actualizó la DB
        }
    """
    # Obtener el documento de la compañía
    doc = get_datasource_by_url(
        slug=slug,
        datasource_url=datasource_url,
        projection={"_id": 0, "primaryDomain": 1, "dataSources.$": 1}
    )
    
    if not doc or "dataSources" not in doc or not doc["dataSources"]:
        return {
            "processed": 0,
            "classified": 0,
            "not_classified": 0,
            "role": None,
            "updated": False,
            "error": "Company o dataSource no encontrado"
        }
    
    primary_domain = doc.get("primaryDomain") or ""
    
    # Validar target_roles
    available_roles = get_available_roles()
    if target_roles:
        target_roles = [r for r in target_roles if r in available_roles]
        if not target_roles:
            target_roles = None
    
    # Clasificar la URL
    role = classify_url(datasource_url.strip(), primary_domain, target_roles)
    
    stats = {
        "processed": 1,
        "classified": 0,
        "not_classified": 0,
        "role": role,
        "updated": False
    }
    
    if role:
        stats["classified"] = 1
        
        # Actualizar el role en la DB
        result = datasource_role(
            slug=slug,
            datasource_url=datasource_url,
            action="set",
            role=role
        )
        
        stats["updated"] = result.get("modified", 0) > 0
    else:
        stats["not_classified"] = 1
    
    return stats


def get_datasources_by_role(
    slug: str,
    role: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Obtiene los dataSources de una compañía, opcionalmente filtrados por role.
    
    Input:
      - slug: slug de la company
      - role: Si se proporciona, solo retorna dataSources con ese role
    
    Output:
      - Lista de dicts con formato [{"url": "...", "role": "..."}, ...]
    """
    doc = get_company_by_slug(
        slug=slug,
        projection={"_id": 0, "dataSources.url": 1, "dataSources.role": 1}
    )
    
    if not doc or "dataSources" not in doc:
        return []
    
    data_sources = doc.get("dataSources") or []
    result = []
    
    for ds in data_sources:
        if not isinstance(ds, dict):
            continue
        
        datasource_url = ds.get("url")
        datasource_role_value = ds.get("role")
        
        if not isinstance(datasource_url, str) or not datasource_url.strip():
            continue
        
        # Filtrar por role si se especifica
        if role is not None:
            if datasource_role_value != role:
                continue
        
        result.append({
            "url": datasource_url.strip(),
            "role": datasource_role_value
        })
    
    return result


def clear_all_company_roles(slug: str, target_roles: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Elimina roles de los dataSources de una compañía.
    Por defecto elimina TODOS los roles. Si se especifica target_roles, solo elimina esos.
    
    Input:
      - slug: slug de la company
      - target_roles: Lista de roles específicos a eliminar (opcional)
    
    Output:
      - Dict con estadísticas:
        {
          "processed": <int>,  # Total de dataSources procesados
          "cleared": <int>,     # DataSources que tenían role y fueron limpiados
          "not_found": <int>,   # DataSources que no tenían role (o no coincidían con target)
          "updated": <int>      # Cantidad de dataSources actualizados en la DB
        }
    """
    # Obtener el documento de la compañía
    doc = get_company_by_slug(
        slug=slug,
        projection={"_id": 0, "dataSources.url": 1, "dataSources.role": 1}
    )
    
    if not doc:
        return {
            "processed": 0,
            "cleared": 0,
            "not_found": 0,
            "updated": 0,
            "error": "Company no encontrada"
        }
    
    data_sources = doc.get("dataSources") or []
    
    if not data_sources:
        return {
            "processed": 0,
            "cleared": 0,
            "not_found": 0,
            "updated": 0,
            "error": "No se encontraron dataSources"
        }
    
    stats = {
        "processed": 0,
        "cleared": 0,
        "not_found": 0,
        "updated": 0
    }
    
    # Procesar cada dataSource
    for ds in data_sources:
        if not isinstance(ds, dict):
            continue
        
        datasource_url = ds.get("url")
        if not isinstance(datasource_url, str) or not datasource_url.strip():
            continue
        
        stats["processed"] += 1
        
        # Verificar si tiene role
        has_role = ds.get("role") is not None
        current_role = ds.get("role")
        
        if has_role:
            # Si se especificaron target_roles, verificar si el role actual está en la lista
            if target_roles is not None and current_role not in target_roles:
                stats["not_found"] += 1
                continue

            stats["cleared"] += 1
            
            # Eliminar el role usando datasource_role con action="delete"
            result = datasource_role(
                slug=slug,
                datasource_url=datasource_url,
                action="delete"
            )
            
            if result.get("modified", 0) > 0:
                stats["updated"] += 1
        else:
            stats["not_found"] += 1
    
    return stats


def clear_single_datasource_role(slug: str, datasource_url: str) -> Dict[str, Any]:
    """
    Elimina el role de un dataSource específico de una compañía.
    Limpia solo una URL, no todo el dataSource.
    
    Input:
      - slug: slug de la company
      - datasource_url: URL del dataSource a limpiar
    
    Output:
      - Dict con estadísticas:
        {
          "processed": <int>,  # Siempre 1 si se encuentra
          "cleared": <int>,     # 1 si tenía role y fue limpiado, 0 si no
          "not_found": <int>,   # 0 si tenía role, 1 si no tenía
          "updated": <bool>     # Si se actualizó la DB
        }
    """
    # Obtener el documento de la compañía
    doc = get_datasource_by_url(
        slug=slug,
        datasource_url=datasource_url,
        projection={"_id": 0, "dataSources.$": 1}
    )
    
    if not doc or "dataSources" not in doc or not doc["dataSources"]:
        return {
            "processed": 0,
            "cleared": 0,
            "not_found": 0,
            "updated": False,
            "error": "Company o dataSource no encontrado"
        }
    
    # Verificar si tiene role
    ds = doc["dataSources"][0]
    has_role = ds.get("role") is not None
    
    stats = {
        "processed": 1,
        "cleared": 0,
        "not_found": 0,
        "updated": False
    }
    
    if has_role:
        stats["cleared"] = 1
        
        # Eliminar el role usando datasource_role con action="delete"
        result = datasource_role(
            slug=slug,
            datasource_url=datasource_url,
            action="delete"
        )
        
        stats["updated"] = result.get("modified", 0) > 0
    else:
        stats["not_found"] = 1
    
    return stats
