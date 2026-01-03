import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Configurações do Banco de Dados
    # Render usa a variável DATABASE_URL para a conexão externa
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./app/database/app.db")
    
    # Configurações de Autenticação
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key-for-fastapi-app-medico")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Credenciais do Mercado Pago
    MERCADOPAGO_PUBLIC_KEY: str = os.getenv("MERCADOPAGO_PUBLIC_KEY", "APP_USR-e26cf360-6f4a-4588-89f3-899b9f283751")
    MERCADOPAGO_ACCESS_TOKEN: str = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "APP_USR-3456910448095867-110919-6d520c5518f5ed7c381d8c5bd0f6a4e0-2977405322")
    
    # URL de retorno após o pagamento (Render URL)
    RENDER_URL: str = os.getenv("RENDER_URL", "http://localhost:8000")

settings = Settings()
