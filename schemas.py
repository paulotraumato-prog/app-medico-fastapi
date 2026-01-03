from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# --- User Schemas ---

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    
class UserCreatePatient(UserBase):
    password: str
    
class UserCreateDoctor(UserBase):
    password: str
    crm: str

class UserInDBBase(UserBase):
    id: int
    role: str # Alterado de UserRole para str para simplicidade
    crm: Optional[str] = None
    
    class Config:
        from_attributes = True

class User(UserInDBBase):
    pass

# --- Case Schemas ---

class CaseBase(BaseModel):
    request_type: str
    description: str
    
class CaseCreate(CaseBase):
    pass

class CaseUpdate(BaseModel):
    status: Optional[str] = None # Alterado de CaseStatus para str
    doctor_id: Optional[int] = None
    payment_status: Optional[str] = None
    mercadopago_id: Optional[str] = None
    
class Case(CaseBase):
    id: int
    patient_id: int
    doctor_id: Optional[int] = None
    status: str # Alterado de CaseStatus para str
    payment_status: str
    payment_amount: float
    mercadopago_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# --- Document Schemas ---

class DocumentBase(BaseModel):
    content: Optional[str] = None
    
class DocumentCreate(DocumentBase):
    case_id: int
    
class Document(DocumentBase):
    id: int
    case_id: int
    signed_content: Optional[str] = None
    signed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# --- Auth Schemas ---

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None
