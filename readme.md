# NPC Generation System

Aplikacja do generowania NPC (Non-Player Characters) w oparciu o historię, kontekst FAISS RAG store i LLM. Współpracuje z MongoDB i API Groq.

---

## Spis treści

- [Wymagania](#wymagania)
- [Opis architektury](#opis-architektury)
- [Konfiguracja](#konfiguracja)
- [Uruchomienie lokalne](#uruchomienie-lokalne)
- [Uruchomienie w Docker](#uruchomienie-w-docker)
- [Endpoints API](#endpoints-api)
- [Przykłady użycia](#przykłady-użycia)
- [Moduły i funkcjonalności](#moduły-i-funkcjonalności)
- [Uwagi](#uwagi)
- [Rozwój i testowanie](#rozwój-i-testowanie)

---

## Wymagania

- Python >= 3.11
- MongoDB >= 7
- Docker (opcjonalnie)
- `.env` z kluczami i konfiguracją API Groq
- Upewnij się, że porty 8000 (aplikacja) i 27017 (MongoDB) są wolne

---

## Opis architektury

Aplikacja składa się z kilku modułów:

1. **FAISS RAG Store** – przechowuje fragmenty historii w indeksie FAISS i umożliwia szybkie wyszukiwanie kontekstu.
2. **NPC Pipeline** – generuje postacie NPC na podstawie podanego promptu, dba o unikalność imion i waliduje dane.
3. **QA Pipeline** – odpowiada na pytania w oparciu o kontekst FAISS i zapisane informacje.
4. **General Pipeline** – router, który klasyfikuje zapytanie (NPC lub QA) i deleguje je do odpowiedniego pipeline.
5. **ContextCache** – pamięć podręczna ostatnich pytań i odpowiedzi z mechanizmem podsumowania.
6. **MongoDB** – baza danych do przechowywania wygenerowanych NPC i sesji czatu.
7. **Testy jednostkowe** – weryfikują endpointy FastAPI oraz funkcjonalności pipeline'ów.

---

## Konfiguracja

1. Skopiuj plik `.env.example` do `.env`:

```bash
cp .env.example .env
```

2. Uzupełnij zmienne środowiskowe w `.env`:

```env.example
APP_ENV=local
GROQ_API_KEY=TWOJ_KLUCZ_API z groq
GROQ_BASE_URL=https://api.groq.com
GROQ_MODEL=Dowolny_model
MONGO_URI=mongodb://localhost:27017
MONGO_DB=npc_system_db
```

---

## Uruchomienie lokalne

1. Zainstaluj zależności:

```bash
pip install -r requirements.txt
```

2. Uruchom MongoDB lokalnie (jeśli nie korzystasz z Dockera):

```bash
mongod --dbpath ./data/db
```

3. Uruchom aplikację FastAPI:

```bash
uvicorn main:app --reload
```

Aplikacja będzie dostępna pod: `http://127.0.0.1:8000`

---

## Uruchomienie w Docker

### Z Dockerfile

```bash
docker build -t npc-system:latest .
docker run --env-file .env -p 8000:8000 npc-system:latest
```

### Z docker-compose

```yaml
version: '3.9'

services:
  mongo:
    image: mongo:7
    container_name: npc_mongo
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_DATABASE: npc_system_db
    volumes:
      - mongo_data:/data/db

  app:
    build: .
    container_name: npc_app
    env_file:
      - .env
    ports:
      - "8000:8000"
    depends_on:
      - mongo

volumes:
  mongo_data:
```

Uruchom wszystko:

```bash
docker-compose up --build
```

---

## Endpoints API

| Endpoint                         | Metoda | Opis |
|---------------------------------|--------|------|
| `/api/v1/faiss/run_faiss`       | POST   | Buduje FAISS index z pliku historii |
| `/api/v1/qa/qa`                 | POST   | Endpoint QA |
| `/api/v1/npcs`                  | GET    | Pobiera listę NPC |
| `/api/v1/chat`                  | POST   | Czat z NPC lub QA (routing przez GeneralPipeline) |

---

## Przykłady użycia

### Pobranie listy NPC

```bash
curl http://127.0.0.1:8000/api/v1/npcs
```

### Generowanie NPC przez czat

```bash
curl -X POST http://127.0.0.1:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Generate 5 NPCs for the new campaign"}'
```

---

## Moduły i funkcjonalności

### FAISS Index Builder

- Dzieli pliki markdown na sekcje wg nagłówków i dzieli na chunki słów.
- Tworzy embeddingi tekstów przy pomocy SentenceTransformer.
- Zapisuje FAISS index i plik meta w formacie JSONL.
- Obsługuje konfiguracje chunków i overlap.

### GeneralPipeline

- Klasyfikuje zapytania jako `NPC` lub `QA`.
- Wysyła odpowiednio do `NPCPipeline` lub `QAPipeline`.
- Obsługuje błędy klasyfikatora i defaultuje do `QA` w przypadku niejednoznaczności.

### NPCPipeline

- Pobiera kontekst z FAISS i cache.
- Generuje propozycje NPC przy pomocy LLM.
- Waliduje i usuwa duplikaty.
- Jeśli imiona kolidują, próbuje je automatycznie zmienić lub używa fallbackowych nazw.
- Zapisuje oczyszczone NPC do MongoDB.

### QAPipeline

- Pobiera kontekst z FAISS i cache.
- Wysyła zapytania do LLM, generuje odpowiedzi i źródła.
- Zapisuje pytania i odpowiedzi do cache.

### ContextCache

- Przechowuje ostatnie pytania i odpowiedzi w pamięci podręcznej.
- Automatyczne podsumowuje pamięć po przekroczeniu limitu 5 wpisów.
- Używany do wzbogacania promptów dla LLM.

### LLM Client (Groq)

- Obsługuje połączenia z API Groq.
- Zapewnia mechanizm sesji i retry dla `chat_json`.
- Zapisuje historię rozmowy w MongoDB.

### Testy

- Testują FastAPI endpoints: `/`, `/npcs`, `/reset_chat`, `/upload_story`, `/faiss/run_faiss`, `/chat`.
- Testują routing GeneralPipeline do NPC lub QA.
- Weryfikują poprawność działania FAISS i NPCPipeline.

---

## Uwagi

- `.env` powinien być prywatny i nie dodawany do repozytorium.
- MongoDB i FAISS są wymagane dla poprawnego działania systemu.
- System weryfikuje odpowiedzi modelu poprzez Pydantic.
- Mechanizmy retry i unikalności nazw NPC są zaimplementowane w NPCPipeline.
- ContextCache zwiększa wydajność zapytań QA poprzez krótką pamięć podręczną.

---

## Rozwój i testowanie

1. Uruchamiaj serwer w trybie `--reload` podczas rozwoju:

```bash
uvicorn main:app --reload
```

2. Logi aplikacji zapisują się w konsoli – używaj `logging_function` w kodzie.

3. Testy uruchamiaj przez pytest:

```bash
pytest tests/
```

4. Można rozbudowywać NPCPipeline i QAPipeline o nowe klasy, walidacje i typy danych.

---

