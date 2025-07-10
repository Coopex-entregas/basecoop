# Sistema de Entregas Coopex

Sistema de gestão de entregas para cooperativas.

## Funcionalidades

- ✅ Login de administrador e cooperados
- ✅ Cadastro de cooperados
- ✅ Cadastro de entregas com nome do cliente e valor
- ✅ Atribuição de entregas a cooperados
- ✅ Controle de status de pagamento (apenas admin)
- ✅ Controle de status de entrega (admin e cooperados)
- ✅ Exportação de entregas em CSV com totais por cooperado
- ✅ Armazenamento de valores diários

## Deploy no Render.com

### 1. Criar conta no Render.com
- Acesse https://render.com e crie uma conta
- Conecte sua conta do GitHub

### 2. Criar banco de dados PostgreSQL
1. No dashboard do Render, clique em "New +"
2. Selecione "PostgreSQL"
3. Configure:
   - Name: `coopex-db` (ou outro nome)
   - Database: `coopex`
   - User: `coopex`
   - Region: escolha a mais próxima
4. Clique em "Create Database"
5. **Importante**: Anote a "Internal Database URL" que será gerada

### 3. Fazer upload do código para GitHub
1. Crie um repositório no GitHub
2. Faça upload de todos os arquivos deste projeto
3. Certifique-se de que todos os arquivos estão no repositório

### 4. Criar Web Service no Render
1. No dashboard do Render, clique em "New +"
2. Selecione "Web Service"
3. Conecte ao seu repositório GitHub
4. Configure:
   - Name: `coopex-sistema-entregas`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Instance Type: `Free` (ou pago se preferir)

### 5. Configurar variáveis de ambiente
Na seção "Environment Variables", adicione:
- `DATABASE_URL`: Cole a "Internal Database URL" do banco PostgreSQL criado
- `SECRET_KEY`: Uma chave secreta aleatória (ex: `minha-chave-super-secreta-123`)

### 6. Deploy
1. Clique em "Create Web Service"
2. Aguarde o deploy (pode levar alguns minutos)
3. Quando concluído, você receberá uma URL pública

## Credenciais padrão
- **Usuário**: coopex
- **Senha**: 05062721

## Uso local (desenvolvimento)

```bash
pip install -r requirements.txt
python app.py
```

O sistema estará disponível em http://localhost:5000

## Estrutura do projeto

- `app.py` - Aplicação principal Flask
- `models.py` - Modelos do banco de dados
- `templates/` - Templates HTML
- `static/` - Arquivos CSS e JavaScript
- `requirements.txt` - Dependências Python
- `create_db.py` - Script para criar banco de dados

## Modificações realizadas

1. **Campo de valor**: Adicionado campo para valor da entrega
2. **Nome do cliente**: Campo "descrição" alterado para "cliente"
3. **Restrições de cooperado**: Cooperados não podem alterar status de pagamento
4. **Exportação**: Botão para exportar entregas em CSV com totais
5. **Persistência**: Valores são armazenados no banco de dados por data
6. **Compatibilidade**: Funciona com SQLite (local) e PostgreSQL (Render)

