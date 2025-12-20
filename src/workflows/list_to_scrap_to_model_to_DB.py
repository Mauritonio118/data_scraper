import pandas as pd
import csv
import asyncio
from src.DB.mongo import get_db
from src.scrapers.model_builder import from_url_model
from pathlib import Path
from datetime import datetime

#Coneccion MongoDB
db = get_db()
companiesDB = db["companies"]

#PATH de datos
HERE = Path(__file__).resolve().parent
INPUT_PATH = HERE / "companies_list.csv"
OUTPUT_PATH = HERE / "companies_list_out.csv"
#Lecrura de datos entrada
df = pd.read_csv(INPUT_PATH)


#Estructura salida
output_cols = ["ID", "Nombre", "Page", "Slug", "In_mongo"]

async def main():
    #Coneccion con el Output
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=output_cols)
        writer.writeheader()

        #Iteracion df de entrada
        for row in df.itertuples(index=False):

            #Estructura de Salida por default
            out_row = {"ID": getattr(row, "ID", ""), "Nombre": getattr(row, "Nombre", ""), "Page": getattr(row, "Page", ""), "Slug": "", "In_mongo": "No"}

            #Extraccion datos base
            primary_domain = row.Page
            name = row.Nombre
            print("ID: " + str(row.ID) + "  Companie: "+ name + "  Page: " + primary_domain)
            
            #Intentar scrapeo
            try:
                if pd.notna(primary_domain) and pd.notna(name):

                    #Creacion url para scrapeo
                    url = "https://" + primary_domain

                    #Escrapeo profundo
                    #from_url_model(url=None, name=None, slug=None, primary_domain=None)
                    print("Sraping start: " + datetime.now().strftime("%H:%M:%S.%f") + "  url: " + url)
                    model = await from_url_model(url=url, name=name, primary_domain=primary_domain)
                    
                    #Guardar modelo en DB
                    companiesDB.insert_one(model)
                    print("Model in Mongo")

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
                    print("Sraping start: " + datetime.now().strftime("%H:%M:%S.%f") + "  url: " + url)
                    model = await from_url_model(url=url, primary_domain=primary_domain)

                    #Guardar modelo en DB
                    companiesDB.insert_one(model)
                    print("Model in Mongo")

                    #Ajuste del output
                    out_row["Slug"] = model["slug"]
                    out_row["In_mongo"] = "SI"

                    #Guardado del output
                    writer.writerow(out_row)
                    f.flush()  # fuerza guardado inmediato en disco

                
                else:
                    print("No hay url")

                    #Ajuste del output
                    out_row["In_mongo"] = "NO. Sin url."

                    #Guardado del output
                    writer.writerow(out_row)
                    f.flush()  # fuerza guardado inmediato en disco                    

            #Abordar error
            except Exception as e:

                print("ERROR  Tipo: " + str(type(e)) + "  Mensaje: " + str(e))

                #Ajuste del output.
                out_row["In_mongo"] = "NO, excepción. Tipo: " + str(type(e)) + ". Mensaje: " + str(e)
                
                #Guardado del output
                writer.writerow(out_row)
                f.flush()  # fuerza guardado inmediato en disco
            
            finally:
                print("")
                print("-----------------------------------------------")


if __name__ == "__main__":
    asyncio.run(main())


