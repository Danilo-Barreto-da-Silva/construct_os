# Construct OS (SGO.IA)

Protótipo acadêmico Django para acompanhamento físico e inspeções de obras, com integração experimental com Gemini.

> **Atenção:** o projeto ainda não está homologado para produção. Laudos de IA são sugestões, não certificações ISO 9001 nem pareceres de engenharia.

## Instalação local

Requer Python compatível com Django 6.1 e um ambiente virtual próprio.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
```

Defina as variáveis de `.env.example` no ambiente (o Django não carrega `.env` automaticamente). **Não use a chave de exemplo em produção.**

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py check
python manage.py test
python manage.py runserver
```

Acesse `/login/`. O usuário administrador **não é mais criado automaticamente**.

## Segurança

- `DJANGO_SECRET_KEY` deve ser nova e secreta; `DJANGO_DEBUG=0` por padrão.
- Defina `DJANGO_ALLOWED_HOSTS` para os domínios reais; não use `*`.
- Nunca publique `.env`, `.venv`, `db.sqlite3` ou mídias de clientes.
- O endpoint de dados fictícios só pode ser acionado por superusuário em `DEBUG=1`, com confirmação explícita, e **apaga dados do banco local**. Não utilize com dados reais.
- Se o usuário `adm` existia em ambiente publicado, troque sua senha imediatamente; a senha anterior foi exposta no histórico Git.
- O histórico anterior ainda contém arquivos sensíveis: remover do estado atual não apaga commits antigos. Uma limpeza do histórico exige planejamento separado.

## Próximas etapas

Validação de entradas, isolamento do gerador de demonstração, fluxo de aprovação humana para IA, trilha de auditoria, métricas reais e testes de integração.
