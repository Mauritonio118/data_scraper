def page_deep_scraped_to_model(page_deep_scraped):
    pages_list = []
    for page in page_deep_scraped["pages"]:
        pages_list.append(page)


    dataSources = []
    for page_url in pages_list:
        dataSources.append({
            "url": page_url,
            "links": page_deep_scraped["pages"][page_url]["links"],
            "texts": page_deep_scraped["pages"][page_url]["texts"],
        })

    return dataSources


def page_object_to_model(page_object):
    pass

"""
company = {
  _id: ObjectId("675f0c1234567890abcdef01"),

  // Identidad básica
  slug: "realblocks",
  name: "RealBlocks",
  description: "Plataforma de tokenización inmobiliaria enfocada en inversores institucionales.",
  primaryDomain: "realblocks.com",


  dataSources: [
    {
      role: "official_site",
      kind: "website",
      url: "https://realblocks.com",
      links: {"head": [], "header": [], "main": [], "footer": []},
      texts: {"head": [], "header": [], "main": [], "footer": []},
      meta: {
        lastCheckedAt: ISODate("2025-01-09T00:00:00Z")
      }
    },
    {
      role: "social_profile",
      kind: "linkedin",
      url: "https://www.linkedin.com/company/realblocks",
      meta: {
        platform: "linkedin",
        lastCheckedAt: ISODate("2025-01-09T00:00:00Z")
      }
    }
  ]
}
"""