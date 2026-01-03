# Use a imagem oficial do Python como base
FROM python:3.11-slim

# Define o diretório de trabalho
WORKDIR /code

# Copia o arquivo de requisitos e instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código (arquivos Python na raiz)
COPY *.py ./
COPY *.html ./templates/

# Cria a estrutura de pastas necessária
RUN mkdir -p templates

# Comando para rodar a aplicação com Uvicorn
# O Render usará este comando se não houver um Build Command ou Start Command específico
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
