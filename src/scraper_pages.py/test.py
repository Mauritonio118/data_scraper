import nest_asyncio
nest_asyncio.apply()

from model_builder import from_url_model
model = await from_url_model("https://reity.cl")
print(model)