# App Médico - Sistema de Renovação de Documentos Médicos

Este projeto é um sistema de gerenciamento de solicitações médicas (receitas e relatórios) construído com **FastAPI**, **SQLAlchemy** e **PostgreSQL**, com integração de pagamento via **Mercado Pago (Pix)**.

## Estrutura do Projeto

\`\`\`
.
├── app/
│   ├── templates/
│   │   ├── index.html
│   │   ├── patient_dashboard.html
│   │   ├── doctor_dashboard.html
│   │   └── case_status.html
│   ├── database/
│   ├── __init__.py
│   ├── main.py             # Rotas principais e lógica do FastAPI
│   ├── models.py           # Definição das tabelas (SQLAlchemy)
│   ├── schemas.py          # Definição dos schemas (Pydantic)
│   ├── config.py           # Configurações e variáveis de ambiente
│   ├── utils.py            # Funções utilitárias (auth, CRUD)
│   └── mercadopago_utils.py # Lógica de integração com Mercado Pago
├── Dockerfile              # Configuração para deploy com Docker
├── requirements.txt        # Dependências do Python
├── .gitignore              # Arquivos a serem ignorados pelo Git
└── README.md
\`\`\`

## Instruções de Deploy no Render

Siga os passos abaixo para implantar a aplicação no Render:

### 1. Configuração do Repositório

1.  Crie um novo repositório no GitHub/GitLab/Bitbucket.
2.  Faça o upload de todos os arquivos corrigidos para este repositório.

### 2. Configuração do Banco de Dados (PostgreSQL)

O Render já possui um serviço de banco de dados chamado \`app-medico-db\`.

1.  Acesse o painel do Render e vá para o serviço \`app-medico-db\`.
2.  Copie a **External Database URL**.

### 3. Configuração do Web Service (FastAPI)

1.  Crie um novo **Web Service** no Render, conectando-o ao seu repositório Git.
2.  **Environment:** Python
3.  **Build Command:** \`pip install -r requirements.txt\`
4.  **Start Command:** \`uvicorn app.main:app --host 0.0.0.0 --port $PORT\`
5.  **Variáveis de Ambiente (Environment Variables):**

| Chave | Valor | Observações |
| :--- | :--- | :--- |
| \`DATABASE_URL\` | **Cole a External Database URL aqui.** | **CRÍTICO:** Garante a conexão com o PostgreSQL. |
| \`MERCADOPAGO_PUBLIC_KEY\` | \`APP_USR-e26cf360-6f4a-4588-89f3-899b9f283751\` | Credencial fornecida. |
| \`MERCADOPAGO_ACCESS_TOKEN\` | \`APP_USR-3456910448095867-110919-6d520c5518f5ed7c381d8c5bd0f6a4e0-2977405322\` | Credencial fornecida. |
| \`RENDER_URL\` | **URL pública do seu Web Service (ex: \`https://app-medico-hfb0.onrender.com\`)** | **CRÍTICO:** Usado para callbacks do Mercado Pago. |
| \`SECRET_KEY\` | \`super-secret-key-for-fastapi-app-medico\` | Chave secreta para JWT. |

### 4. Inicialização do Banco de Dados

O arquivo \`app/main.py\` contém a linha \`Base.metadata.create_all(bind=engine)\`. **Isso garantirá que as tabelas \`users\`, \`cases\` e \`documents\` sejam criadas automaticamente no PostgreSQL na primeira execução**, resolvendo o problema de \`UndefinedColumn\`.

## Credenciais de Teste (Após o Deploy)

Para validar o fluxo completo:

| Usuário | E-mail | Senha | CRM |
| :--- | :--- | :--- | :--- |
| **Paciente** | \`paciente@teste.com\` | \`senha123\` | N/A |
| **Médico** | \`medico@teste.com\` | \`senha123\` | \`CRM/SP 123456\` |

**Passos de Validação:**

1.  Acesse a URL do Render.
2.  Registre o **Paciente**.
3.  Faça o login como **Paciente** (deve ir para \`/patient/dashboard\`).
4.  Crie um novo caso (será gerado um link de pagamento do Mercado Pago).
5.  Registre o **Médico**.
6.  Faça o login como **Médico** (deve ir para \`/doctor/dashboard\`).
7.  O **Médico** deve ver o caso pendente (após o pagamento ser simulado/realizado).
\`\`\`
