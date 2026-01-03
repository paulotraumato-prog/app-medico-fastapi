from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User, Case, Document, UserRole, CaseStatus

# --- Configuração de Segurança ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# --- Funções de Token JWT ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "sub": str(data["user_id"])})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# --- Funções de CRUD de Usuário ---
def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

# --- Funções de CRUD de Case ---
def get_case_by_id(db: Session, case_id: int):
    return db.query(Case).filter(Case.id == case_id).first()

def create_case(db: Session, patient_id: int, request_type: str, description: str):
    db_case = Case(
        patient_id=patient_id,
        request_type=request_type,
        description=description,
        status=CaseStatus.PENDING,
        payment_status="pending"
    )
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    return db_case

def update_case_status(db: Session, case_id: int, status: CaseStatus, doctor_id: Optional[int] = None):
    db_case = get_case_by_id(db, case_id)
    if db_case:
        db_case.status = status
        if doctor_id:
            db_case.doctor_id = doctor_id
        db.commit()
        db.refresh(db_case)
    return db_case

def get_cases_by_patient(db: Session, patient_id: int):
    return db.query(Case).filter(Case.patient_id == patient_id).all()

def get_pending_cases_for_doctor(db: Session):
    return db.query(Case).filter(Case.status == CaseStatus.PAID).all() # Médicos só veem casos pagos

# --- Funções de CRUD de Documento ---
def create_document(db: Session, case_id: int, content: str):
    db_document = Document(case_id=case_id, content=content)
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document
