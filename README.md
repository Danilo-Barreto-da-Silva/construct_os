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
- O gerador de demonstração só funciona com superusuário em `DEBUG=1`, exige confirmação e **recusa gerar caso já existam torres**. Nunca execute em um banco de produção.
- Se o usuário `adm` existia em ambiente publicado, troque sua senha imediatamente; a senha anterior foi exposta no histórico Git.
- O histórico anterior ainda contém arquivos sensíveis: remover do estado atual não apaga commits antigos. Uma limpeza do histórico exige planejamento separado.

## Próximas etapas

O dashboard já mostra evolução mensal baseada nas medições existentes (média simples, sem ponderação por serviços). Ainda não é uma Curva S de planejamento físico-financeiro.

## Histórico de medição e FVS

- Cada atualização manual que realmente muda a medição gera um registro com usuário, data, execução anterior/nova, situação anterior/nova da FVS e observação.
- O botão **Ver histórico desta medição** na janela do apartamento abre a página de rastreabilidade.
- Somente usuários com `is_staff=True` podem registrar uma FVS como `CONFORME`; o autor e a data da aprovação administrativa ficam registrados. Isso não equivale a assinatura digital ou à qualificação profissional do usuário.
- Vídeos avaliados por IA geram **sugestões**, sem alterar o avanço físico ou aprovar a FVS automaticamente.
- O histórico vale para **alterações realizadas depois da migração 0003**; registros anteriores não recebem autoria retroativa. Uma trilha de auditoria com validade regulatória exige controles adicionais.

## Próximas etapas

- Planejamento físico com atividades e pesos para Curva S real; estrutura própria para FVS/RNC, responsáveis técnicos e evidências.
- Papéis e permissões por obra (além de `is_staff`), validação de arquivos e avaliação de segurança antes de qualquer publicação externa.
- Remover a pasta `.venv` e o banco `db.sqlite3` do rastreamento Git sem excluir os dados locais. O `.gitignore` atual **não remove automaticamente arquivos já versionados**.
- Os arquivos sensíveis que já estiveram em commits antigos continuam no histórico do Git e exigem tratamento separado antes de uma publicação pública em produção.
