# 1. Usa un'immagine ufficiale leggera di Python
FROM python:3.13.14
# 2. Imposta la cartella di lavoro principale nel container
WORKDIR /app

# 3. Copia solo il file dei requisiti (per sfruttare la cache di Docker)
COPY requirements.txt .

# 4. Installa le dipendenze Python
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copia tutto il resto del progetto nel container
COPY . .

# 6. Informa Docker che il container ascolterà sulla porta 8501
EXPOSE 8501

# 7. Comando per avviare l'applicazione Streamlit
CMD ["streamlit", "run", "frontend.py", "--server.port=8501", "--server.address=0.0.0.0"]