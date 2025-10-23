from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
import os

def generar_url_sas(blob_name, expira_en_min = 5):
    
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container_name = os.getenv("AZURE_CONTAINER_NAME")
    
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    account_name = blob_service_client.account_name
    account_key = blob_service_client.credential.account_key
    
    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=container_name,
        blob_name=blob_name,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(minutes=expira_en_min)
    )
    
    return f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"