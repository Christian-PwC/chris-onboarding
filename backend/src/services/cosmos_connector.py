from azure.cosmos import CosmosClient, PartitionKey, exceptions
from src.config.env_loader import env
import httpx

class CosmosConnector:
    def __init__(self):
        self._client = CosmosClient(
            url=env.AZURE_COSMOS_ENDPOINT,
            credential=env.AZURE_COSMOS_KEY,
        )

    def get_database(self, database_name: str):
        return self._client.get_database_client(database_name)

    def get_container(self, database_name: str, container_name: str):
        db = self.get_database(database_name)
        return db.get_container_client(container_name)

    def create_database_if_not_exists(self, database_name: str):
        return self._client.create_database_if_not_exists(id=database_name)

    def create_container_if_not_exists(
        self,
        database_name: str,
        container_name: str,
        partition_key_path: str = "/id",
    ):
        db = self.get_database(database_name)
        return db.create_container_if_not_exists(
            id=container_name,
            partition_key=PartitionKey(path=partition_key_path),
        )

    def upsert_item(self, database_name: str, container_name: str, item: dict) -> dict:
        container = self.get_container(database_name, container_name)
        return container.upsert_item(body=item)

    def get_item(self, database_name: str, container_name: str, item_id: str, partition_key: str) -> dict:
        container = self.get_container(database_name, container_name)
        return container.read_item(item=item_id, partition_key=partition_key)

    def delete_item(self, database_name: str, container_name: str, item_id: str, partition_key: str) -> None:
        container = self.get_container(database_name, container_name)
        container.delete_item(item=item_id, partition_key=partition_key)

    def query_items(
        self,
        database_name: str,
        container_name: str,
        query: str,
        parameters: list[dict] | None = None,
        enable_cross_partition_query: bool = True,
    ) -> list[dict]:
        container = self.get_container(database_name, container_name)
        items = container.query_items(
            query=query,
            parameters=parameters or [],
            enable_cross_partition_query=enable_cross_partition_query,
        )
        return list(items)

    def list_items(self, database_name: str, container_name: str) -> list[dict]:
        container = self.get_container(database_name, container_name)
        return list(container.read_all_items())


cosmos_connector = CosmosConnector()
