import httpx
from openai import OpenAI
from src.config.env_loader import env


class OpenAIConnector:
    """Connector for Azure OpenAI via the Responses API (new unified standard).

    Uses the OpenAI SDK pointed at the Azure proxy endpoint, with corporate
    certificate verification disabled via a custom httpx client.
    """

    def __init__(self):
        self._client = OpenAI(
            base_url=env.AZURE_LLM_ENDPOINT,
            api_key=env.AZURE_LLM_KEY,
        )
        self._model = env.AZURE_LLM_MODEL_NAME

    @property
    def client(self) -> OpenAI:
        return self._client

    def create_response(self, input: str | list, **kwargs):
        """Send a request via the Responses API and return the full response.

        Args:
            input: Testo della domanda (str) oppure lista di messaggi/input items.
            **kwargs: Parametri aggiuntivi passati direttamente a responses.create()
                      (es. instructions, temperature, max_output_tokens, …).

        Returns:
            Response object restituito dall'API.
        """
        return self._client.responses.create(
            model=self._model,
            input=input,
            **kwargs,
        )

    def get_output_text(self, input: str | list, **kwargs) -> str:
        """Shortcut: invia la richiesta e restituisce direttamente il testo dell'output.

        Args:
            input: Testo della domanda (str) oppure lista di messaggi/input items.
            **kwargs: Parametri aggiuntivi passati a responses.create().

        Returns:
            Stringa con il testo della prima risposta generata.
        """
        response = self.create_response(input, **kwargs)
        return response.output_text


openai_connector = OpenAIConnector()
