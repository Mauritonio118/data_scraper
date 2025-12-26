import asyncio
from src.scrapers.page_deep_scraper import page_deep_scraper
from src.scrapers.model_builder import page_deep_scraped_to_model
import data_filter as filter

async def main():
    root_links = set()
    social_links = set()
    multimedia_links = set()
    app_links = set()
    news_links = set()
    property_links = set()
    legal_links = set()

    none_links = set()

    to_be_ignored_links = set()

    deep_scrap = await page_deep_scraper("https://reity.cl")
    root_domain = deep_scrap["rootDomain"]
    result = page_deep_scraped_to_model(deep_scrap) #toDataSource

    for r in result:
        for section in ("head", "header", "main", "footer"):
            for link in r["links"].get(section, []):
                if filter.is_in_root_domain(link, root_domain):
                    root_links.add(link)
                elif filter.is_app_store(link):
                    app_links.add(link)
                elif filter.is_youtube_profile(link) or filter.is_social_media(link):
                    social_links.add(link)
                elif filter.is_youtube_video(link) or filter.is_multimedia(link):
                    multimedia_links.add(link)
                elif filter.is_news(link):
                    news_links.add(link)
                elif filter.is_property(link):
                    property_links.add(link)
                elif filter.is_legal(link):
                    legal_links.add(link)
                elif filter.is_to_be_ignored(link):
                    to_be_ignored_links.add(link)
                else:
                    none_links.add(link)

    print(f"\nROOT: {len(root_links)}")
    for l in sorted(root_links): print(l)

    print(f"\nSOCIAL: {len(social_links)}")
    for l in sorted(social_links): print(l)

    print(f"\nMULTIMEDIA: {len(multimedia_links)}")
    for l in sorted(multimedia_links): print(l)

    print(f"\nAPPS: {len(app_links)}")
    for l in sorted(app_links): print(l)

    print(f"\nNEWS: {len(news_links)}")
    for l in sorted(news_links): print(l)

    print(f"\nPROPERTY: {len(property_links)}")
    for l in sorted(property_links): print(l)

    print(f"\nLEGAL: {len(legal_links)}")
    for l in sorted(legal_links): print(l)

    # FLAG INTERNO
    print(f"\nTO BE IGNORED: {len(to_be_ignored_links)}")
    for l in sorted(to_be_ignored_links): print(l)

    print(f"\nMISCELANEOUS: {len(none_links)}")
    for l in sorted(none_links): print(l)


if __name__ == "__main__":
    asyncio.run(main())