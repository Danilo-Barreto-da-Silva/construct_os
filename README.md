# Construct OS (SGO.IA)

Protótipo acadêmico de gestão de obras em **Django**, com medições mensais, controle de FVS, RNC, metas de planejamento, relatórios e análise experimental de vídeo com Gemini.

> **Não homologado para produção.** Registros de FVS e RNC representam acompanhamento administrativo interno; o sistema não gera uma certificação ISO 9001, laudo técnico assinado ou comprovação de responsabilidade profissional. A IA fornece sugestões que exigem validação humana.

## Funcionalidades

- **Painel:** avanço físico médio, torres, matriz de unidades, filtros de mês/torre/andar e histórico mensal baseado nas medições existentes.
- **Qualidade / FVS:** checklist por apartamento e mês, resultado e observação de cada inspeção, autor e histórico. Apenas `is_staff` pode marcar itens conformes e aprovar a FVS global. Itens pendentes e RNCs formais não resolvidas impedem a aprovação.
- **RNC:** criação vinculada à medição, prioridade, prazo, atribuição, ação corretiva, transição entre Aberta/Em tratamento/Resolvida e histórico de movimentações. Encerrar uma RNC **não** aprova a FVS automaticamente.
- **Planejamento:** metas mensais acumuladas por torre, inseridas manualmente. O painel compara meta versus realizado quando houver dados correspondentes; sem metas, não inventa valores.
- **Cadastros:** inclusão de torres, apartamentos e uma medição por apartamento/mês. Novas medições entram com FVS pendente. **Não há exclusão por essas telas.**
- **Relatórios:** resumo mensal por torre e exportação CSV de medições e RNCs (somente equipe autorizada). O CSV possui mitigação contra fórmulas maliciosas.
- **IA opcional:** Gemini recebe vídeo apenas quando a chave é configurada; o resultado fica como sugestão e não altera automaticamente as medições nem libera a FVS.
- **Testes:** verificação do Django, consistência de migrações, testes de permissões e de fluxos administrativos por GitHub Actions.

## Instalação e Codespaces

Ative o ambiente do projeto (Python e dependências conforme `requirements.txt`):

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

**Nunca reutilize uma chave de produção** e não publique chaves no Git:

```bash
export DJANGO_DEBUG=1
export DJANGO_SECRET_KEY="$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')"
# Em Codespaces, adapte a origem ao endereço HTTPS do seu Codespace.
export DJANGO_CSRF_TRUSTED_ORIGINS="https://*.app.github.dev,https://localhost:8000"
python manage.py migrate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py runserver 0.0.0.0:8000
```

O endereço exato do Codespaces deve ser permitido em `DJANGO_ALLOWED_HOSTS` se não for acessado via localhost. A origem curinga acima é apenas uma conveniência de desenvolvimento; em implantação real, configure as origens exatas. Veja `.env.example`. O Django **não** carrega um arquivo `.env` automaticamente; as variáveis devem estar no ambiente.

Acesse `/login/`. Crie o administrador com `python manage.py createsuperuser`, se necessário. O usuário `adm` **não** é mais criado automaticamente. Para autorizar um usuário a aprovar FVS ou editar RNC, um administrador pode conceder `is_staff` no admin Django. **Essa permissão não valida formação profissional**; é apenas um controle técnico provisório.

## Como usar

1. **Cadastros:** equipe autorizada cria torre, apartamento e uma medição mensal de referência. As medições de demonstração de outubro/novembro de 2026 continuam no banco até você decidir removê-las por um processo separado e seguro.
2. **Painel:** filtre mês, torre e andar. Clique num apartamento para editar a execução física e o status da FVS. Percentual físico e decisão de qualidade são independentes.
3. **Checklist FVS:** no modal de vistoria, clique em *Checklist FVS* para registrar itens verificáveis. Mudanças após uma aprovação tornam a FVS pendente novamente.
4. **RNC:** para registrar uma falha formal, use *Registrar RNC*. Abertura mantém o percentual físico e sinaliza FVS não conforme. Trate, atribua e encerre a RNC na página de detalhes.
5. **Aprovação:** para declarar FVS conforme, use uma conta `is_staff`, após tratar RNCs formais e eventuais itens pendentes. Consulte a autoria no histórico.
6. **Planejamento:** registre metas físicas acumuladas por torre/mês. O gráfico usa dados reais e oculta metas ausentes. **Não é ainda uma Curva S físico-financeira ponderada por serviços.**
7. **Relatórios:** equipe autorizada consulta totais por mês e exporta dados em CSV. Os registros de exemplo não devem ser interpretados como dados reais de obra.

## Segurança e dados

- `.venv/`, `db.sqlite3`, `.env` e `media/` são ignorados pelo Git. Os arquivos já versionados foram retirados do estado atual por commit sem apagar as cópias do Codespaces. Isso **não elimina conteúdo de commits antigos**.
- A pasta virtual e o banco de dados devem ser mantidos e copiados separadamente. Antes de migrações, faça backup de `db.sqlite3` com o servidor parado.
- O gerador de demonstração funciona somente em `DJANGO_DEBUG=1`, por superusuário, com confirmação, e **se o banco não tiver torres**. Nunca use com dados de clientes.
- O projeto inicialmente publicou credenciais de demonstração, uma SECRET_KEY e o SQLite no histórico Git. Troque qualquer senha reutilizada e credencial real; um planejamento específico de limpeza do histórico será necessário antes de qualquer exposição pública.
- O controle `is_staff` não faz isolamento por empresa/obra e não substitui papéis granulares. A trilha de auditoria registra ações após sua implantação, não o passado, e não é imutável contra administradores com acesso ao banco.
- Os uploads e o uso da IA ainda exigem avaliação de privacidade, consentimento e retenção antes de vídeos reais de clientes. Evite gravar pessoas sem autorização.
- Os templates ainda dependem de bibliotecas por CDN em desenvolvimento; o empacotamento local, cabeçalhos de segurança e revisão de infraestrutura ficam para implantação.
- Backups automatizados, isolamento multiobra, credenciamento profissional, evidências fotográficas e assinatura digital formal são etapas futuras.

## Testes e referências

Para validação funcional da nova etapa, veja [Roteiro de testes](docs/roteiro_testes.md).

A workflow `.github/workflows/django-checks.yml` roda `manage.py check`, `makemigrations --check --dry-run` e `manage.py test` nas alterações da branch e nas pull requests. A execução no seu Codespaces é importante para confirmar o banco e as páginas locais.
