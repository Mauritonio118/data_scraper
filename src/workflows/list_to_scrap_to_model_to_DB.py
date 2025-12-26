#CORRER CODIGO: python -m src.workflows.list_to_scrap_to_model_to_DB

import pandas as pd
import csv
import asyncio
from src.DB.mongo import get_db
from src.scrapers.model_builder import from_url_model
from pathlib import Path
from datetime import datetime
import logging
from src.utils.logger import setup_logger

#Coneccion MongoDB
db = get_db()
companiesDB = db["companies"]

#PATH de datos
HERE = Path(__file__).resolve().parent
INPUT_PATH = HERE / "companies_list.csv"
OUTPUT_PATH = HERE / "companies_list_out.csv"
#Lecrura de datos entrada
df = pd.read_csv(INPUT_PATH, dtype=str, keep_default_na=False)


#Estructura salida
output_cols = ["ID", "Nombre", "Page", "Slug", "In_mongo"]

async def main():
    # Configurar logger
    # Se guardará en logs/scraping_process.log
    logger = setup_logger(__name__, log_file="logs/scraping_process.log", level=logging.INFO)
    
    logger.info(f"Iniciando proceso. Input: {INPUT_PATH}, Output: {OUTPUT_PATH}")

    #Coneccion con el Output
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=output_cols)
        writer.writeheader()

        #Iteracion df de entrada
        total_rows = len(df)
        for index, row in enumerate(df.itertuples(index=False), 1):

            #Estructura de Salida por default
            out_row = {"ID": getattr(row, "ID", ""), "Nombre": getattr(row, "Nombre", ""), "Page": getattr(row, "Page", ""), "Slug": "", "In_mongo": "No"}

            #Extraccion datos base
            primary_domain = row.Page
            name = row.Nombre
            
            logger.info(f"[{index}/{total_rows}] Procesando ID: {row.ID} | Compañía: {name} | Page: {primary_domain}")
            
            #Intentar scrapeo
            try:
                if pd.notna(primary_domain) and pd.notna(name):

                    #Creacion url para scrapeo
                    url = "https://" + primary_domain

                    #Escrapeo profundo
                    logger.info(f"Scraping iniciado para: {url}")
                    model = await from_url_model(url=url, name=name, primary_domain=primary_domain)
                    
                    #Guardar modelo en DB
                    companiesDB.insert_one(model)
                    logger.info("Modelo guardado exitosamente en Mongo")

                    #Ajuste del output
                    out_row["Slug"] = model["slug"]
                    out_row["In_mongo"] = "SI"

                    #Guardado del output
                    writer.writerow(out_row)
                    f.flush()  # fuerza guardado inmediato en disco
                
                elif pd.notna(primary_domain):

                    #Creacion url para scrapeo
                    url = "https://" + primary_domain

                    #Escrapeo profundo
                    logger.info(f"Scraping iniciado (sin nombre) para: {url}")
                    model = await from_url_model(url=url, primary_domain=primary_domain)

                    #Guardar modelo en DB
                    companiesDB.insert_one(model)
                    logger.info("Modelo guardado exitosamente en Mongo")

                    #Ajuste del output
                    out_row["Slug"] = model["slug"]
                    out_row["In_mongo"] = "SI"

                    #Guardado del output
                    writer.writerow(out_row)
                    f.flush()  # fuerza guardado inmediato en disco

                
                else:
                    logger.warning(f"Fila saltada: No hay URL válida para ID {row.ID}")

                    #Ajuste del output
                    out_row["In_mongo"] = "NO. Sin url."

                    #Guardado del output
                    writer.writerow(out_row)
                    f.flush()  # fuerza guardado inmediato en disco                    

            #Abordar error
            except Exception as e:
                logger.error(f"Error procesando {name or primary_domain}", exc_info=True)

                #Ajuste del output.
                out_row["In_mongo"] = "NO, excepción. Tipo: " + str(type(e)) + ". Mensaje: " + str(e)
                
                #Guardado del output
                writer.writerow(out_row)
                f.flush()  # fuerza guardado inmediato en disco
            
            finally:
                logger.info("-" * 50)


if __name__ == "__main__":
    asyncio.run(main())


