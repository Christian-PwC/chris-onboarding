# 1. Usa un'immagine ufficiale leggera di Python
FROM python:3.13.14
# 2. Imposta la cartella di lavoro principale nel container
WORKDIR /app

# 3. Copia solo il file dei requisiti (per sfruttare la cache di Docker)
COPY requirements.txt .

# 4. Installa le dipendenze del backend (FastAPI, Uvicorn, ecc.)
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copia tutto il resto del progetto nel container (app.py, la cartella src, ecc.)
COPY . .

# 6. Informa Docker che il backend ascolterà sulla porta 8080 (o la porta che usi per FastAPI)
EXPOSE 8080

# 7. Comando per avviare il server Uvicorn puntando ad app.py (supponendo che l'istanza FastAPI si chiami 'app')
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]