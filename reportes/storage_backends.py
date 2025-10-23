from storages.backends.azure_storage import AzureStorage
import os

class AzureMediaStorage(AzureStorage):
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    azure_container_name = os.getenv("AZURE_CONTAINER_NAME")
    expiration_secs = None

    def _save(self, name, content):
        print(f"→ AzureMediaStorage._save name={name}; size={getattr(content, 'size', 'n/a')}")
        result = super()._save(name, content)
        print(f"✔ AzureMediaStorage._save returned: {result}")
        return result
