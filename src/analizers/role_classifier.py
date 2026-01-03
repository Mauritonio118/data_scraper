"""
Módulo de clasificación de roles para URLs.
Sistema flexible y extensible que permite agregar, modificar o eliminar criterios de clasificación.
"""

from typing import Optional, List, Set, Callable
from urllib.parse import urlparse
import re
from src.analizers import domain_lists


class RoleClassifier:
    """
    Clasificador de roles para URLs.
    Permite registrar criterios de clasificación y clasificar URLs según esos criterios.
    """
    
    def __init__(self):
        self._classifiers: dict[str, List[Callable[[str, str], bool]]] = {}
        self._setup_default_classifiers()
    
    def register_classifier(self, role: str, classifier_func: Callable[[str, str], bool]):
        """
        Registra una función clasificadora para un role específico.
        
        Args:
            role: Nombre del role (ej: "official_site")
            classifier_func: Función que recibe (url, primary_domain) y retorna bool
        """
        if role not in self._classifiers:
            self._classifiers[role] = []
        self._classifiers[role].append(classifier_func)
    
    def remove_classifier(self, role: str, classifier_func: Optional[Callable] = None):
        """
        Elimina un clasificador específico o todos los clasificadores de un role.
        
        Args:
            role: Nombre del role
            classifier_func: Si se proporciona, elimina solo esa función. Si es None, elimina todos.
        """
        if role not in self._classifiers:
            return
        
        if classifier_func is None:
            del self._classifiers[role]
        else:
            self._classifiers[role] = [
                f for f in self._classifiers[role] if f != classifier_func
            ]
            if not self._classifiers[role]:
                del self._classifiers[role]
    
    def get_available_roles(self) -> Set[str]:
        """Retorna el conjunto de roles disponibles."""
        return set(self._classifiers.keys())
    
    def classify(self, url: str, primary_domain: str, target_roles: Optional[List[str]] = None) -> Optional[str]:
        """
        Clasifica una URL y retorna el role correspondiente.
        
        Args:
            url: URL a clasificar
            primary_domain: Dominio primario de la empresa
            target_roles: Lista de roles a evaluar. Si es None, evalúa todos.
        
        Returns:
            Nombre del role si se encuentra una coincidencia, None si no se clasifica.
            Si ningún role coincide y "unclassified" está disponible, retorna "unclassified".
        """
        if not isinstance(url, str) or not url.strip():
            return None
        
        roles_to_check = target_roles if target_roles else list(self._classifiers.keys())
        
        # Primero intentar todos los roles excepto "unclassified"
        roles_to_try = [r for r in roles_to_check if r != "unclassified"]
        has_unclassified = "unclassified" in roles_to_check
        
        for role in roles_to_try:
            if role not in self._classifiers:
                continue
            
            for classifier in self._classifiers[role]:
                try:
                    if classifier(url, primary_domain):
                        return role
                except Exception:
                    # Si un clasificador falla, continuar con el siguiente
                    continue
        
        # Si no se encontró ningún role y "unclassified" está en target_roles, retornar "unclassified"
        # Nota: "unclassified" solo se aplica si está explícitamente en target_roles
        if has_unclassified:
            return "unclassified"
        
        return None
    
    def _setup_default_classifiers(self):
        """Configura los clasificadores por defecto según VERSION 2 del modelo."""
        
        # OFFICIAL_SITE: URLs del sitio oficial de la empresa
        self.register_classifier("official_site", self._is_official_site)
        
        # OFFICIAL_SOCIAL_PROFILE: Perfiles oficiales de la empresa en redes sociales
        self.register_classifier("official_social_profile", self._is_official_social_profile)
        
        # OFFICIAL_SOCIAL_CONTENT: Contenido oficial en redes sociales
        #self.register_classifier("official_social_content", self._is_official_social_content)
        
        # SOCIAL_PROFILE: Perfiles en redes sociales NO oficiales
        #self.register_classifier("social_profile", self._is_social_profile)
        
        # SOCIAL_CONTENT: Contenido en redes sociales NO oficial
        #self.register_classifier("social_content", self._is_social_content)
        
        # STORE_LISTING: Tiendas de aplicaciones
        self.register_classifier("store_listing", self._is_store_listing)
        
        # REGULATOR_PROFILE: Ficha/registro de la empresa en un regulador
        #self.register_classifier("regulator_profile", self._is_regulator_profile)
        
        # REGULATOR_REFERENCE: Páginas de regulación genérica
        #self.register_classifier("regulator_reference", self._is_regulator_reference)
        
        # NEWS_SITE: Portales de noticias y medios
        self.register_classifier("news_site", self._is_news_site)
        
        # THIRD_PARTY: Páginas de terceros que referencian a la empresa
        self.register_classifier("third_party", self._is_third_party)
        
        # SOCIAL_WEB_UTILITY: Rutas para compartir en redes sociales
        self.register_classifier("social_web_utility", self._is_social_web_utility)
        
        # WEB_UTILITIES: Recursos internos (imágenes, rutas internas, videos)
        self.register_classifier("web_utilities", self._is_web_utility)
        
        # DOCUMENTS: URLs para descargar archivos
        self.register_classifier("documents", self._is_document)
        
        # UNCLASSIFIED: Catch-all para URLs no clasificadas
        # Este se aplica automáticamente si ningún otro role coincide
        # No necesita un clasificador específico, se maneja en classify()
        # Pero lo registramos como disponible para que aparezca en get_available_roles()
        # Usamos una función que siempre retorna False porque la lógica está en classify()
        def _always_false(url: str, domain: str) -> bool:
            return False

        self.register_classifier("unclassified", _always_false) 
    

    # ============================================================
    # CLASIFICADORES POR ROLE
    # ============================================================
    
    def _is_official_site(self, url: str, primary_domain: str) -> bool:
        """Verifica si la URL pertenece al sitio oficial de la empresa."""
        url_host = self._extract_host(url)
        domain_host = self._normalize_domain(primary_domain)
        
        if not url_host or not domain_host:
            return False
        
        # Coincidencia exacta o subdominio
        return url_host == domain_host or url_host.endswith("." + domain_host)
    
    def _is_official_social_profile(self, url: str, primary_domain: str) -> bool:
        """Verifica si es un perfil oficial de la empresa en redes sociales."""
        url_lower = url.lower()

        # Check filter: if it is a social web utility (sharing link), it is NOT a profile
        if self._is_social_web_utility(url, primary_domain):
            return False
        
        # Verifica que sea una red social conocida con coincidencia exacta de dominio
        is_social = False
        for domain in domain_lists.SOCIAL_PROFILE_DOMAINS:
            idx = url_lower.find(domain)
            if idx != -1:
                # Verificar delimitadores para evitar falsos positivos (ej: box.com vs x.com)
                # El dominio debe estar al inicio o precedido por '.', '/', ':'
                if idx == 0 or url_lower[idx-1] in [".", "/", ":"]:
                    is_social = True
                    break
        
        if not is_social:
            return False
        
        # Para perfiles oficiales, típicamente el nombre de la empresa aparece en la URL
        # o el dominio de la empresa está referenciado
        domain_parts = self._normalize_domain(primary_domain).split(".")[0]
        if domain_parts and len(domain_parts) > 2:
            # Busca el nombre de la empresa en la URL
            return domain_parts.lower() in url_lower
    
    def _is_official_social_content(self, url: str, primary_domain: str) -> bool:
        """Verifica si es contenido oficial en redes sociales (posts, videos, etc)."""
        # Similar a official_social_profile pero para contenido específico
        if self._is_official_social_profile(url, primary_domain):
            # Si ya es un perfil oficial, verifica si es contenido específico
            return any(pattern in url.lower() for pattern in domain_lists.SOCIAL_CONTENT_PATTERNS)
        return False
    
    def _is_social_profile(self, url: str, primary_domain: str) -> bool:
        """Verifica si es un perfil en redes sociales pero NO oficial."""
        url_lower = url.lower()
        is_social = any(domain in url_lower for domain in domain_lists.SOCIAL_GENERIC_DOMAINS)
        
        if not is_social:
            return False
        
        # Si es social pero NO es oficial, entonces es social_profile
        return not self._is_official_social_profile(url, primary_domain)
    
    def _is_social_content(self, url: str, primary_domain: str) -> bool:
        """Verifica si es contenido en redes sociales NO oficial."""
        if self._is_social_profile(url, primary_domain):
            return any(pattern in url.lower() for pattern in domain_lists.SOCIAL_CONTENT_PATTERNS)
        return False

    def _is_social_web_utility(self, url: str, primary_domain: str) -> bool:
        """
        Verifica si es una utilidad de red social (ej: compartir, tweet intent).
        Generalmente tienen doble https o patrones específicos de compartir.
        """
        url_lower = url.lower()
        
        # Patrón 1: Doble https (común en redirects de compartir)
        if url_lower.count("http") > 1:
            return True
            
        # Patrón 2: Keywords de compartir
        return any(pattern in url_lower for pattern in domain_lists.SOCIAL_SHARING_PATTERNS)
    
    def _is_store_listing(self, url: str, primary_domain: str) -> bool:
        """Verifica si es una tienda de aplicaciones."""
        url_lower = url.lower()
        return any(domain in url_lower for domain in domain_lists.STORE_DOMAINS)
    
    def _is_regulator_profile(self, url: str, primary_domain: str) -> bool:
        """Verifica si es la ficha/registro de la empresa en un regulador."""
        url_lower = url.lower()
        is_regulator = any(domain in url_lower for domain in domain_lists.REGULATOR_DOMAINS)
        
        if not is_regulator:
            return False
        
        return any(indicator in url_lower for indicator in domain_lists.REGULATOR_PROFILE_INDICATORS)
    
    def _is_regulator_reference(self, url: str, primary_domain: str) -> bool:
        """Verifica si es una página de regulación genérica (no específica de la empresa)."""
        url_lower = url.lower()
        is_regulator = any(domain in url_lower for domain in domain_lists.REGULATOR_DOMAINS)
        
        if not is_regulator:
            return False
        
        # Si es regulador pero NO es un perfil específico, es referencia genérica
        return not self._is_regulator_profile(url, primary_domain)
    
    def _is_news_site(self, url: str, primary_domain: str) -> bool:
        """Verifica si es un portal de noticias o medio de comunicación."""
        url_lower = url.lower()
        return any(domain in url_lower for domain in domain_lists.NEWS_DOMAINS)
    
    def _is_third_party(self, url: str, primary_domain: str) -> bool:
        """Verifica si es una página de terceros que referencia a la empresa."""
        # Si no es oficial, no es social, no es regulador, no es noticias, etc.
        # y el dominio de la empresa aparece en la URL o contexto, podría ser third_party
        
        # Excluir categorías ya clasificadas
        excluded = [
            self._is_official_site(url, primary_domain),
            self._is_official_social_profile(url, primary_domain),
            self._is_social_profile(url, primary_domain),
            self._is_store_listing(url, primary_domain),
            self._is_regulator_profile(url, primary_domain),
            self._is_regulator_reference(url, primary_domain),
            self._is_news_site(url, primary_domain),
            self._is_web_utility(url, primary_domain),
            self._is_document(url, primary_domain)
        ]
        
        if any(excluded):
            return False
        
        url_lower = url.lower()
        return any(domain in url_lower for domain in domain_lists.THIRD_PARTY_DOMAINS)
    
    def _is_web_utility(self, url: str, primary_domain: str) -> bool:
        """Verifica si es un recurso interno (imágenes, videos, rutas internas)."""
        url_lower = url.lower()
        
        # Extensiones de imágenes
        if any(url_lower.endswith(ext) for ext in domain_lists.IMAGE_EXTENSIONS):
            return True
        
        # Extensiones de videos
        if any(url_lower.endswith(ext) for ext in domain_lists.VIDEO_EXTENSIONS):
            return True
        
        # Rutas de recursos comunes
        if any(path in url_lower for path in domain_lists.RESOURCE_PATHS):
            return True
        
        # URLs de CDN comunes
        url_host = self._extract_host(url)
        if url_host and any(cdn in url_host for cdn in domain_lists.CDN_DOMAINS):
            return True
        
        return False
    
    def _is_document(self, url: str, primary_domain: str) -> bool:
        """Verifica si es una URL para descargar documentos."""
        url_lower = url.lower()
        
        return any(url_lower.endswith(ext) for ext in domain_lists.DOCUMENT_EXTENSIONS)
    
    # ============================================================
    # UTILIDADES
    # ============================================================
    
    def _extract_host(self, url: str) -> str:
        """Extrae el host de una URL normalizado."""
        if not isinstance(url, str):
            return ""
        
        url = url.strip()
        if not url:
            return ""
        
        # Agregar protocolo si falta
        if "://" not in url:
            url = "https://" + url
        
        try:
            parsed = urlparse(url)
            host = (parsed.netloc or "").lower()
            
            # Remover puerto
            if ":" in host:
                host = host.split(":")[0]
            
            # Remover www.
            if host.startswith("www."):
                host = host[4:]
            
            return host.strip(".")
        except Exception:
            return ""
    
    def _normalize_domain(self, domain: str) -> str:
        """Normaliza un dominio removiendo protocolo y www."""
        if not isinstance(domain, str):
            return ""
        
        domain = domain.strip().lower()
        if not domain:
            return ""
        
        # Remover protocolo
        domain = domain.replace("https://", "").replace("http://", "")
        
        # Remover www.
        if domain.startswith("www."):
            domain = domain[4:]
        
        # Remover ruta si existe
        if "/" in domain:
            domain = domain.split("/")[0]
        
        # Remover puerto
        if ":" in domain:
            domain = domain.split(":")[0]
        
        return domain.strip(".")


# Instancia global del clasificador
_default_classifier = RoleClassifier()


def classify_url(url: str, primary_domain: str, target_roles: Optional[List[str]] = None) -> Optional[str]:
    """
    Función de conveniencia para clasificar una URL.
    
    Args:
        url: URL a clasificar
        primary_domain: Dominio primario de la empresa
        target_roles: Roles específicos a evaluar. Si es None, evalúa todos.
    
    Returns:
        Nombre del role si se encuentra, None si no se clasifica.
    """
    return _default_classifier.classify(url, primary_domain, target_roles)


def get_available_roles() -> Set[str]:
    """Retorna el conjunto de roles disponibles."""
    return _default_classifier.get_available_roles()


def register_custom_classifier(role: str, classifier_func: Callable[[str, str], bool]):
    """Registra un clasificador personalizado."""
    _default_classifier.register_classifier(role, classifier_func)


def remove_classifier(role: str, classifier_func: Optional[Callable] = None):
    """Elimina un clasificador."""
    _default_classifier.remove_classifier(role, classifier_func)

