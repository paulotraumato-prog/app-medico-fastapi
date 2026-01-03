# Use a imagem oficial do Python como base
FROM python:3.11-slim

# Define o diretório de trabalho
WORKDIR /code

# Copia o arquivo de requisitos e instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Cria a estrutura de pastas app/ e app/templates/
RUN mkdir -p app/templates

# Copia os arquivos Python para a pasta app/
COPY main.py ./app/
COPY config.py ./app/
COPY models.py ./app/
COPY schemas.py ./app/
COPY utils.py ./app/
COPY mercadopago_utils.py ./app/

# Cria o __init__.py para o pacote app
RUN touch app/__init__.py

# Copia os templates HTML para app/templates/
COPY *.html ./app/templates/

# Comando para rodar a aplicação com Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
