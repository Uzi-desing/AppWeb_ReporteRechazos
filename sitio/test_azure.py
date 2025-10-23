import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

# Cargar variables del entorno .env
load_dotenv()

# Obtener credenciales de Azure
connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

if not connection_string:
    print("❌ Falta la variable AZURE_STORAGE_CONNECTION_STRING en tu .env")
    exit()

try:
    # Crear el cliente de servicio
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)

    print("✅ Conexión exitosa a Azure Blob Storage.")
    print("📦 Contenedores disponibles:")

    # Listar contenedores
    for container in blob_service_client.list_containers():
        print(" -", container["name"])

except Exception as e:
    print("❌ Error al conectar con Azure Blob Storage:")
    print(e)
