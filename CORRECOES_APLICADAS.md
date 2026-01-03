# Correções Aplicadas - App Médico FastAPI

## Resumo das Correções

### ✅ Problema 1: QR Code PIX não aparecia para pagamento

**Causa:** O código original usava apenas a API de Checkout Preferences do Mercado Pago, que redireciona para uma página externa. Não havia código para exibir o QR Code PIX diretamente na aplicação.

**Solução:**
1. Adicionado novo método `create_pix_payment()` em `mercadopago_utils.py` que usa a API de Pagamentos PIX
2. Adicionados campos `qr_code` e `qr_code_base64` no modelo `Case`
3. Atualizado endpoint `/api/case/create` para retornar os dados do QR Code
4. Adicionado endpoint `/api/case/{case_id}/payment` para recuperar QR Code de casos existentes
5. Atualizado template `case_status.html` para exibir o QR Code PIX com botão de copiar
6. Atualizado template `patient_dashboard.html` com modal de pagamento PIX

### ✅ Problema 2: Webhook não atualizava status do pagamento

**Causa:** O endpoint `/api/mercadopago/notification` estava vazio e não processava as notificações do Mercado Pago.

**Solução:**
1. Implementado processamento completo do webhook em `/api/mercadopago/notification`
2. Adicionada função `get_payment_status()` para consultar status no Mercado Pago
3. Adicionado endpoint `/api/case/{case_id}/check-payment` para verificação manual
4. Adicionada verificação automática a cada 30 segundos na página de status

### ✅ Problema 3: Médico não conseguia acessar

**Causa:** Não havia usuário médico cadastrado no banco de dados.

**Solução:**
1. Adicionado evento `@app.on_event("startup")` que cria um médico padrão automaticamente
2. Credenciais do médico padrão:
   - **Email:** paulo.rech@arcelormittal.com.br
   - **Senha:** medico123

---

## Arquivos Modificados

| Arquivo | Alterações |
|---------|------------|
| `app/main.py` | Novos endpoints, webhook completo, criação de médico padrão |
| `app/models.py` | Campos `qr_code` e `qr_code_base64` no modelo Case |
| `app/mercadopago_utils.py` | Funções `create_pix_payment()` e `get_payment_status()` |
| `app/templates/case_status.html` | Exibição do QR Code PIX com botão de copiar |
| `app/templates/patient_dashboard.html` | Modal de pagamento PIX após criar solicitação |

---

## Como Fazer Deploy

### Opção 1: Render.com

1. Faça upload do código para um repositório GitHub
2. Crie um novo Web Service no Render
3. Configure as variáveis de ambiente:
   ```
   DATABASE_URL=postgresql://...
   SECRET_KEY=sua-chave-secreta
   MERCADOPAGO_ACCESS_TOKEN=seu-token
   RENDER_URL=https://seu-app.onrender.com
   ```
4. O Render detectará automaticamente o Dockerfile

### Opção 2: Local

```bash
# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
export DATABASE_URL=sqlite:///./app/database/app.db
export SECRET_KEY=sua-chave-secreta
export MERCADOPAGO_ACCESS_TOKEN=seu-token
export RENDER_URL=http://localhost:8000

# Executar
uvicorn app.main:app --reload
```

---

## Credenciais de Teste

### Médico (criado automaticamente)
- **Email:** paulo.rech@arcelormittal.com.br
- **Senha:** medico123

### Paciente (criar via registro)
- Acesse a página inicial e clique em "Registrar como Paciente"

---

## Fluxo de Uso

1. **Paciente** faz login e cria uma solicitação
2. **Sistema** gera QR Code PIX e exibe para pagamento
3. **Paciente** paga via PIX
4. **Webhook** do Mercado Pago atualiza o status para "PAID"
5. **Médico** acessa o dashboard e vê casos pendentes
6. **Médico** aprova e assina o documento
7. **Paciente** baixa o documento assinado

---

## Notas Importantes

- O webhook do Mercado Pago precisa ser configurado no painel do Mercado Pago
- URL do webhook: `https://seu-dominio.com/api/mercadopago/notification`
- Em ambiente de produção, use HTTPS e configure as variáveis de ambiente corretamente
