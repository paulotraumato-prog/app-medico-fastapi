from fastapi import FastAPI, Depends, HTTPException, status, Request, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from typing import Annotated
from datetime import datetime, timedelta
import json

from app.config import settings
from app.models import Base, User, UserRole, Case, Document, CaseStatus
from app.schemas import UserCreatePatient, UserCreateDoctor, User as UserSchema, TokenData, CaseCreate, Case as CaseSchema
from app.utils import get_password_hash, verify_password, create_access_token, get_user_by_email, get_user_by_id, get_cases_by_patient, get_pending_cases_for_doctor, create_case, get_case_by_id, update_case_status, create_document
from app.mercadopago_utils import create_pix_payment, create_pix_payment_preference, get_payment_status

# --- Configuração do Banco de Dados ---
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Cria as tabelas (se não existirem) - Importante para o primeiro deploy
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Configuração do FastAPI ---
app = FastAPI()
templates = Jinja2Templates(directory="app/templates")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Dependência para obter o usuário logado ---
async def get_current_user_from_cookie(request: Request, db: Annotated[Session, Depends(get_db)]):
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            return None
        token_data = TokenData(user_id=user_id)
    except JWTError:
        return None
    
    user = get_user_by_id(db, user_id=token_data.user_id)
    return user

# --- Rotas de Autenticação (HTML/Templates) ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/token")
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Annotated[Session, Depends(get_db)]):
    user = get_user_by_email(db, email=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user_id": user.id, "role": user.role.value}, expires_delta=access_token_expires
    )
    
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="Lax")
    return response

@app.get("/dashboard")
async def dashboard_redirect(request: Request, current_user: Annotated[User, Depends(get_current_user_from_cookie)]):
    if not current_user:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    if current_user.role == UserRole.PATIENT:
        return RedirectResponse(url="/patient/dashboard", status_code=status.HTTP_302_FOUND)
    elif current_user.role == UserRole.DOCTOR:
        return RedirectResponse(url="/doctor/dashboard", status_code=status.HTTP_302_FOUND)
    
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token")
    return response

# --- Rotas de Paciente ---

@app.get("/patient/dashboard", response_class=HTMLResponse)
async def patient_dashboard(request: Request, current_user: Annotated[User, Depends(get_current_user_from_cookie)], db: Annotated[Session, Depends(get_db)]):
    if not current_user or current_user.role != UserRole.PATIENT:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    cases = get_cases_by_patient(db, patient_id=current_user.id)
    
    return templates.TemplateResponse("patient_dashboard.html", {"request": request, "user": current_user, "cases": cases})

@app.get("/patient/case/{case_id}/status", response_class=HTMLResponse)
async def patient_case_status(request: Request, case_id: int, current_user: Annotated[User, Depends(get_current_user_from_cookie)], db: Annotated[Session, Depends(get_db)]):
    if not current_user or current_user.role != UserRole.PATIENT:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    case = get_case_by_id(db, case_id)
    if not case or case.patient_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caso não encontrado")
    
    return templates.TemplateResponse("case_status.html", {"request": request, "user": current_user, "case": case})

# --- Rotas de Médico ---

@app.get("/doctor/dashboard", response_class=HTMLResponse)
async def doctor_dashboard(request: Request, current_user: Annotated[User, Depends(get_current_user_from_cookie)], db: Annotated[Session, Depends(get_db)]):
    if not current_user or current_user.role != UserRole.DOCTOR:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    pending_cases = get_pending_cases_for_doctor(db)
    
    return templates.TemplateResponse("doctor_dashboard.html", {"request": request, "user": current_user, "pending_cases": pending_cases})

# --- Rotas de API (Autenticação e Registro) ---

@app.post("/api/register/patient", response_model=UserSchema)
async def register_patient_api(user_data: UserCreatePatient, db: Annotated[Session, Depends(get_db)]):
    if get_user_by_email(db, email=user_data.email):
        raise HTTPException(status_code=400, detail="Email já registrado")
    
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role=UserRole.PATIENT
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/api/register/doctor", response_model=UserSchema)
async def register_doctor_api(user_data: UserCreateDoctor, db: Annotated[Session, Depends(get_db)]):
    if get_user_by_email(db, email=user_data.email):
        raise HTTPException(status_code=400, detail="Email já registrado")
    
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role=UserRole.DOCTOR,
        crm=user_data.crm
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- Rotas de API (Casos e Pagamento) ---

@app.post("/api/case/create")
async def create_new_case_api(case_data: CaseCreate, request: Request, db: Annotated[Session, Depends(get_db)]):
    current_user = await get_current_user_from_cookie(request, db)
    if not current_user or current_user.role != UserRole.PATIENT:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Acesso negado")
    
    # 1. Cria o caso no banco de dados com status PENDING
    db_case = create_case(db, patient_id=current_user.id, request_type=case_data.request_type, description=case_data.description)
    
    # 2. Cria o pagamento PIX no Mercado Pago (com QR Code)
    pix_response = create_pix_payment(db_case, settings.RENDER_URL)
    
    if pix_response and pix_response.get("qr_code"):
        # Sucesso - temos o QR Code PIX
        db_case.mercadopago_id = str(pix_response.get("payment_id"))
        db_case.qr_code = pix_response.get("qr_code")
        db_case.qr_code_base64 = pix_response.get("qr_code_base64")
        db.commit()
        db.refresh(db_case)
        
        return JSONResponse(content={
            "case_id": db_case.id,
            "qr_code": pix_response.get("qr_code"),
            "qr_code_base64": pix_response.get("qr_code_base64"),
            "payment_amount": db_case.payment_amount
        })
    
    # Fallback: Tenta criar preferência de pagamento (redirecionamento)
    mp_response = create_pix_payment_preference(db_case, settings.RENDER_URL)
    
    if not mp_response or not mp_response.get("init_point"):
        # Se falhar, reverte a criação do caso
        db.delete(db_case)
        db.commit()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao gerar pagamento no Mercado Pago.")
    
    # Atualiza o caso com o ID do Mercado Pago
    db_case.mercadopago_id = mp_response.get("id")
    db.commit()
    db.refresh(db_case)
    
    # Retorna o link de pagamento para o frontend
    return JSONResponse(content={
        "case_id": db_case.id,
        "payment_link": mp_response.get("init_point")
    })

@app.get("/api/case/{case_id}/payment")
async def get_case_payment(case_id: int, request: Request, db: Annotated[Session, Depends(get_db)]):
    """Retorna os dados de pagamento PIX para um caso específico"""
    current_user = await get_current_user_from_cookie(request, db)
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Acesso negado")
    
    db_case = get_case_by_id(db, case_id)
    if not db_case or db_case.patient_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caso não encontrado")
    
    if db_case.status != CaseStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Caso não está pendente de pagamento")
    
    # Se já temos o QR Code salvo, retorna
    if db_case.qr_code and db_case.qr_code_base64:
        return JSONResponse(content={
            "case_id": db_case.id,
            "qr_code": db_case.qr_code,
            "qr_code_base64": db_case.qr_code_base64,
            "payment_amount": db_case.payment_amount
        })
    
    # Se não temos, tenta gerar novamente
    pix_response = create_pix_payment(db_case, settings.RENDER_URL)
    
    if pix_response and pix_response.get("qr_code"):
        db_case.mercadopago_id = str(pix_response.get("payment_id"))
        db_case.qr_code = pix_response.get("qr_code")
        db_case.qr_code_base64 = pix_response.get("qr_code_base64")
        db.commit()
        
        return JSONResponse(content={
            "case_id": db_case.id,
            "qr_code": pix_response.get("qr_code"),
            "qr_code_base64": pix_response.get("qr_code_base64"),
            "payment_amount": db_case.payment_amount
        })
    
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao gerar QR Code PIX")

@app.post("/api/mercadopago/notification")
async def mercadopago_notification(request: Request, db: Annotated[Session, Depends(get_db)]):
    """
    Webhook do Mercado Pago para notificações de pagamento.
    """
    try:
        # Tenta ler o corpo da requisição
        body = await request.body()
        data = json.loads(body) if body else {}
        
        # Também verifica query params (Mercado Pago pode enviar de ambas formas)
        topic = request.query_params.get("topic") or data.get("type")
        resource_id = request.query_params.get("id") or data.get("data", {}).get("id")
        
        print(f"Webhook recebido - Topic: {topic}, ID: {resource_id}")
        print(f"Body: {data}")
        
        if topic == "payment" and resource_id:
            # Consulta o pagamento no Mercado Pago
            payment_info = get_payment_status(str(resource_id))
            
            if payment_info:
                payment_status = payment_info.get("status")
                external_reference = payment_info.get("external_reference")
                
                print(f"Payment Status: {payment_status}, Case ID: {external_reference}")
                
                if external_reference and payment_status == "approved":
                    # Atualiza o status do caso para PAID
                    case_id = int(external_reference)
                    db_case = get_case_by_id(db, case_id)
                    
                    if db_case and db_case.status == CaseStatus.PENDING:
                        db_case.status = CaseStatus.PAID
                        db_case.payment_status = "approved"
                        db.commit()
                        print(f"Caso #{case_id} atualizado para PAID")
        
        return JSONResponse(content={"status": "ok"})
    
    except Exception as e:
        print(f"Erro no webhook: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)})

@app.get("/api/case/{case_id}/check-payment")
async def check_payment_status(case_id: int, request: Request, db: Annotated[Session, Depends(get_db)]):
    """Verifica o status do pagamento de um caso"""
    current_user = await get_current_user_from_cookie(request, db)
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Acesso negado")
    
    db_case = get_case_by_id(db, case_id)
    if not db_case or db_case.patient_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caso não encontrado")
    
    # Se já está pago, retorna
    if db_case.status != CaseStatus.PENDING:
        return JSONResponse(content={
            "case_id": db_case.id,
            "status": db_case.status.value,
            "payment_status": db_case.payment_status
        })
    
    # Consulta o status no Mercado Pago
    if db_case.mercadopago_id:
        payment_info = get_payment_status(db_case.mercadopago_id)
        
        if payment_info and payment_info.get("status") == "approved":
            db_case.status = CaseStatus.PAID
            db_case.payment_status = "approved"
            db.commit()
    
    return JSONResponse(content={
        "case_id": db_case.id,
        "status": db_case.status.value,
        "payment_status": db_case.payment_status
    })

@app.post("/api/case/{case_id}/approve")
async def approve_case(case_id: int, request: Request, db: Annotated[Session, Depends(get_db)]):
    current_user = await get_current_user_from_cookie(request, db)
    if not current_user or current_user.role != UserRole.DOCTOR:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Acesso negado")
    
    # Tenta ler o conteúdo do corpo
    try:
        body = await request.body()
        data = json.loads(body) if body else {}
        content = data.get("content", "")
    except:
        content = ""
    
    db_case = get_case_by_id(db, case_id)
    if not db_case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caso não encontrado")
    
    if db_case.status != CaseStatus.PAID:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Caso não está pago para aprovação")
    
    # 1. Aprova o caso e associa ao médico
    db_case.status = CaseStatus.APPROVED
    db_case.doctor_id = current_user.id
    db.commit()
    db.refresh(db_case)
    
    # 2. Cria o documento (simulando a assinatura digital)
    signed_content = f"""## Documento Médico Assinado

**Tipo:** {db_case.request_type}
**Paciente:** {db_case.patient.full_name}
**Médico:** Dr. {current_user.full_name} ({current_user.crm})

---

{content}

---

**Assinatura Digital:** {datetime.utcnow().isoformat()}
"""
    
    db_document = create_document(db, case_id=case_id, content=content)
    db_document.signed_content = signed_content
    db_document.signed_at = datetime.utcnow()
    db.commit()
    
    # 3. Atualiza o status final
    db_case.status = CaseStatus.SIGNED
    db.commit()
    
    return JSONResponse(content={"status": "ok", "message": "Caso aprovado e documento assinado com sucesso."})

@app.get("/api/case/{case_id}/document")
async def download_document(case_id: int, request: Request, db: Annotated[Session, Depends(get_db)]):
    current_user = await get_current_user_from_cookie(request, db)
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Acesso negado")
    
    db_case = get_case_by_id(db, case_id)
    if not db_case or (db_case.patient_id != current_user.id and db_case.doctor_id != current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caso não encontrado ou acesso negado")
    
    if db_case.status != CaseStatus.SIGNED or not db_case.document or not db_case.document.signed_content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Documento não finalizado ou assinado.")
    
    # Retorna o documento como um arquivo Markdown
    return Response(
        content=db_case.document.signed_content,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=documento_medico_{case_id}.md"}
    )

# --- Script para criar usuário médico padrão ---
@app.on_event("startup")
async def create_default_doctor():
    """Cria um usuário médico padrão se não existir"""
    db = SessionLocal()
    try:
        # Verifica se já existe um médico
        doctor = db.query(User).filter(User.role == UserRole.DOCTOR).first()
        if not doctor:
            # Cria médico padrão
            hashed_password = pwd_context.hash("medico123")
            default_doctor = User(
                email="paulo.rech@arcelormittal.com.br",
                hashed_password=hashed_password,
                full_name="Paulo Renato Rech",
                role=UserRole.DOCTOR,
                crm="CRM-12345"
            )
            db.add(default_doctor)
            db.commit()
            print("Médico padrão criado: paulo.rech@arcelormittal.com.br / medico123")
    finally:
        db.close()
