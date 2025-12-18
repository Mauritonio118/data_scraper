from utils.data_filter import is_in_root_domain


root_links = set()
from model_builder import page_deep_scraped_to_model
result = page_deep_scraped_to_model(reity)
for r in result:
    for link in r["links"]["head"]:
        if is_in_root_domain(link, reity["rootDomain"]):
            root_links.add(link)

    for link in r["links"]["header"]:
        if is_in_root_domain(link, reity["rootDomain"]):
            root_links.add(link)
    
    for link in r["links"]["main"]:
        if is_in_root_domain(link, reity["rootDomain"]):
            root_links.add(link)
    
    for link in r["links"]["footer"]:
        if is_in_root_domain(link, reity["rootDomain"]):
            root_links.add(link)
    
for link in root_links:
    print(link)