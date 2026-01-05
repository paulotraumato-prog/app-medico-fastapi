```python
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}  # Necessário para SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}
```
