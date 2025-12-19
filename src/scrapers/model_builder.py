from urllib.parse import urlparse
from scrapers.page_deep_scraper import page_scraper, page_deep_scraper
import tldextract

#Agrega a la lista solo si el valor no se encuentra ya en la lista
def append_unique(lst, value):
    if value not in lst:
        lst.append(value)
        return True
    return False

#Entrega lista con todos los links unicos encontrados en en una pagina escrapeada a fondo
def all_links_in_deep_scraped_page(deep_scraped):

    scraped_urls_list = []
    for page in deep_scraped["pages"]:
        scraped_urls_list.append(page)
    
    all_links_in_deep_scraped_page = []
    for url in scraped_urls_list:

        for link_list in deep_scraped["pages"][url]["links"].values():

            for link in link_list:
                append_unique(all_links_in_deep_scraped_page, link)

    return all_links_in_deep_scraped_page


async def page_deep_scraped_to_dataSources(page_deep_scraped):
    
    #Crear lista con todos los links a los que se les extrajo links y textos.
    list_pages_scraped = []
    for page in page_deep_scraped["pages"]:
        list_pages_scraped.append(page)

    #Crear lista con todos los links de navegacion encontrados en la pagina (Escrapeados o no)
    links_in_deep_scraped_page = all_links_in_deep_scraped_page(page_deep_scraped)

    #Crear lista de links encontrados en la pagina que no han sido analizados.
    set_list_pages_scraped = set(list_pages_scraped)
    links_for_scrap = [x for x in links_in_deep_scraped_page if x not in set_list_pages_scraped]

    #crea lista de dataSources y agrega data de paginas escrapeadas
    dataSources = []
    for page_url in list_pages_scraped:
        dataSources.append({
            "url": page_url,
            "links": page_deep_scraped["pages"][page_url]["links"],
            "texts": page_deep_scraped["pages"][page_url]["texts"],
        })

    #Agrega a dataSources paginas que faltan por scrapear
    for links in links_for_scrap:

        try:
            page_object = await page_scraper(links)

            dataSources.append({
                "url": page_object["page"],
                "links": page_object["links"],
                "texts": page_object["texts"],
            })
        except:
            dataSources.append({
                "url": links,
            })
        
    return dataSources


def data_to_identity(url=None, name=None, slug=None, primary_domain=None):
    """
    Genera identidad para un documento en MongoDB.
    Output: slug, name, primaryDomain

    Regla clave:
    - Si el input es tipo "ejemplo.es/ruta" primaryDomain debe quedar "ejemplo.es"
    - Si hay subdominio tipo "blog.ejemplo.es" primaryDomain debe quedar "ejemplo.es"
    """

    # Fuente principal para deducir dominio
    source = (primary_domain or url or "").strip()

    # Normalizar a URL parseable
    parse_target = source
    if parse_target and "://" not in parse_target:
        parse_target = "https://" + parse_target

    parsed = urlparse(parse_target) if parse_target else None

    # Extraer host limpio
    host = ""
    if parsed:
        host = (parsed.hostname or "").strip().lower()
    if host.startswith("www."):
        host = host[4:]

    # Dominio base usando tldextract si existe, si no fallback
    base_domain = host
    if host:
        try:
            ext = tldextract.extract(host)
            base_domain = (ext.registered_domain or host).lower()
        except Exception:
            parts = [p for p in host.split(".") if p]
            base_domain = (parts[-2] + "." + parts[-1]).lower() if len(parts) >= 2 else host

    # Resolver primaryDomain final
    final_primary = (primary_domain or "").strip().lower()
    if final_primary:
        tmp = final_primary
        if "://" not in tmp:
            tmp = "https://" + tmp
        p2 = urlparse(tmp)
        tmp_host = (p2.hostname or final_primary).strip().lower()
        if tmp_host.startswith("www."):
            tmp_host = tmp_host[4:]

        try:
            ext2 = tldextract.extract(tmp_host)
            final_primary = (ext2.registered_domain or tmp_host).lower()
        except Exception:
            parts2 = [p for p in tmp_host.split(".") if p]
            final_primary = (parts2[-2] + "." + parts2[-1]).lower() if len(parts2) >= 2 else tmp_host
    else:
        final_primary = base_domain

    # Resolver slug final
    final_slug = (slug or "").strip().lower()
    if final_slug:
        final_slug = final_slug.replace(" ", "-").replace("_", "-")
    else:
        final_slug = final_primary.split(".")[0].lower() if final_primary else ""

    # Resolver name final
    final_name = (name or "").strip()
    if not final_name:
        words = final_slug.replace("-", " ").replace("_", " ").split()
        final_name = " ".join(w.capitalize() for w in words) if words else final_slug.capitalize()

    return {
        "slug": final_slug,
        "name": final_name,
        "primaryDomain": final_primary,
    }
# Ejemplo
# print(data_to_identity(url="ejemplo.es/ruta"))
# {'slug': 'ejemplo', 'name': 'Ejemplo', 'primaryDomain': 'ejemplo.es'}




async def from_url_model(url=None, name=None, slug=None, primary_domain=None):
  
    identity = data_to_identity(url=url, name=name, slug=slug, primary_domain=primary_domain)


    deep_scraped_page = await page_deep_scraper(url)
    dataSources = await page_deep_scraped_to_dataSources(deep_scraped_page)


    model = {
    "slug": identity["slug"],
    "name": identity["name"],
    "primaryDomain": identity["primaryDomain"],
    "dataSources": dataSources
    }

    return model