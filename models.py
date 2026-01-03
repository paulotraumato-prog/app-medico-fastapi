from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class UserRole(enum.Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"

class CaseStatus(enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    APPROVED = "approved"
    SIGNED = "signed"
    REJECTED = "rejected"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    crm = Column(String, nullable=True) # Apenas para médicos
    
    cases_as_patient = relationship("Case", back_populates="patient", foreign_keys="[Case.patient_id]")
    cases_as_doctor = relationship("Case", back_populates="doctor", foreign_keys="[Case.doctor_id]")

class Case(Base):
    __tablename__ = "cases"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    request_type = Column(String, nullable=False) 
    description = Column(Text, nullable=False)
    
    status = Column(Enum(CaseStatus), default=CaseStatus.PENDING, nullable=False)
    
    # Pagamento
    payment_status = Column(String, default="pending", nullable=False)
    payment_amount = Column(Float, default=50.0, nullable=False)
    mercadopago_id = Column(String, nullable=True)
    
    # NOVOS CAMPOS: QR Code PIX
    qr_code = Column(Text, nullable=True)  # Código PIX copia e cola
    qr_code_base64 = Column(Text, nullable=True)  # Imagem do QR Code em base64
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    patient = relationship("User", back_populates="cases_as_patient", foreign_keys="[Case.patient_id]")
    doctor = relationship("User", back_populates="cases_as_doctor", foreign_keys="[Case.doctor_id]")
    
    document = relationship("Document", back_populates="case", uselist=False)

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), unique=True, nullable=False)
    
    content = Column(Text, nullable=True) # Conteúdo do documento (receita/relatório)
    signed_content = Column(Text, nullable=True) # Conteúdo assinado (PDF/HTML final)
    signed_at = Column(DateTime, nullable=True)
    
    case = relationship("Case", back_populates="document")
