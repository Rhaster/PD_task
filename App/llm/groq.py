import groq  # Importuje oficjalną bibliotekę Groq do obsługi API
from Config.config import settings  # Importuje ustawienia konfiguracyjne z pliku config.py

# Wrapper around Groq client for chat completions
class GroqClient:  # Definicja klasy GroqClient, która jest opakowaniem dla klienta Groq
    def __init__(self):  # Konstruktor klasy GroqClient
        self._client = groq.Groq(  # Tworzy instancję klienta Groq z kluczem API i adresem URL
            api_key=settings.groq_api_key,  # Ustawia klucz API z konfiguracji
            base_url=str(settings.groq_base_url)  # Ustawia bazowy URL z konfiguracji
        )
    async def chat(self, messages: list[dict], **kwargs) -> dict:  # Asynchroniczna metoda do wysyłania zapytań czatu
        response = await self._client.chat.completions.create(  # Wywołuje metodę API Groq do generowania odpowiedzi czatu
            model=settings.groq_model,  # Używa modelu z konfiguracji
            messages=messages,  # Przekazuje listę wiadomości do modelu
            temperature=kwargs.get("temperature", 0.3),  # Ustawia temperaturę generowania (domyślnie 0.3)
            max_tokens=kwargs.get("max_tokens", 512),  # Ustawia maksymalną liczbę tokenów (domyślnie 512)
            stream=False  # Wyłącza strumieniowanie odpowiedzi
        )
        return response  # Zwraca odpowiedź z API Groq


    async def aclose(self):  # Asynchroniczna metoda zamykająca klienta (dla kompatybilności)
        # groq client does not require explicit close, but keep for compatibility  # Komentarz: klient Groq nie wymaga zamykania
        pass  # Nic nie robi, metoda pozostawiona dla zgodności