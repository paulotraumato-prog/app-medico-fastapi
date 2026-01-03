import requests
from typing import Optional
from app.config import settings
from app.models import Case

# URL base da API do Mercado Pago
MP_API_BASE_URL = "https://api.mercadopago.com"

def create_pix_payment(case: Case, render_url: str) -> Optional[dict]:
    """
    Cria um pagamento PIX no Mercado Pago usando a API de Pagamentos.
    Retorna o JSON de resposta com qr_code e qr_code_base64.
    """
    
    # URL de notificação (webhook) que o Mercado Pago chamará
    notification_url = f"{render_url}/api/mercadopago/notification"
    
    # Dados do pagamento PIX
    payment_data = {
        "transaction_amount": case.payment_amount,
        "description": f"Solicitação Médica #{case.id} - {case.request_type}",
        "payment_method_id": "pix",
        "payer": {
            "email": case.patient.email,
            "first_name": case.patient.full_name.split()[0] if case.patient.full_name else "Paciente",
            "last_name": " ".join(case.patient.full_name.split()[1:]) if len(case.patient.full_name.split()) > 1 else "Usuario"
        },
        "external_reference": str(case.id),
        "notification_url": notification_url
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.MERCADOPAGO_ACCESS_TOKEN}",
        "X-Idempotency-Key": f"case-{case.id}-{case.created_at.timestamp()}"
    }
    
    try:
        response = requests.post(
            f"{MP_API_BASE_URL}/v1/payments",
            headers=headers,
            json=payment_data
        )
        response.raise_for_status()
        result = response.json()
        
        # Extrair dados do PIX
        pix_data = result.get("point_of_interaction", {}).get("transaction_data", {})
        
        return {
            "payment_id": result.get("id"),
            "status": result.get("status"),
            "qr_code": pix_data.get("qr_code"),
            "qr_code_base64": pix_data.get("qr_code_base64"),
            "ticket_url": pix_data.get("ticket_url")
        }
    except requests.exceptions.RequestException as e:
        print(f"Erro ao criar pagamento PIX no Mercado Pago: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Resposta do erro: {e.response.text}")
        return None


def create_pix_payment_preference(case: Case, render_url: str) -> Optional[dict]:
    """
    Cria uma preferência de pagamento Pix no Mercado Pago (método antigo).
    Mantido para compatibilidade.
    """
    
    # URL de notificação (webhook) que o Mercado Pago chamará
    notification_url = f"{render_url}/api/mercadopago/notification"
    
    # URL de retorno após o pagamento (para o paciente)
    back_url = f"{render_url}/patient/case/{case.id}/status"
    
    # Dados da preferência de pagamento
    preference_data = {
        "items": [
            {
                "title": f"Solicitação Médica #{case.id} - {case.request_type}",
                "description": case.description[:255] if case.description else "Solicitação médica",
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": case.payment_amount
            }
        ],
        "payer": {
            "email": case.patient.email,
            "name": case.patient.full_name
        },
        "external_reference": str(case.id),
        "notification_url": notification_url,
        "back_urls": {
            "success": back_url,
            "pending": back_url,
            "failure": back_url
        },
        "auto_return": "approved",
        "payment_methods": {
            "excluded_payment_types": [
                {"id": "credit_card"},
                {"id": "debit_card"},
                {"id": "ticket"}
            ],
            "installments": 1
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.MERCADOPAGO_ACCESS_TOKEN}"
    }
    
    try:
        response = requests.post(
            f"{MP_API_BASE_URL}/checkout/preferences",
            headers=headers,
            json=preference_data
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao criar preferência de pagamento no Mercado Pago: {e}")
        return None


def get_payment_status(payment_id: str) -> Optional[dict]:
    """
    Consulta o status de um pagamento no Mercado Pago.
    """
    headers = {
        "Authorization": f"Bearer {settings.MERCADOPAGO_ACCESS_TOKEN}"
    }
    
    try:
        response = requests.get(
            f"{MP_API_BASE_URL}/v1/payments/{payment_id}",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao consultar pagamento no Mercado Pago: {e}")
        return None
