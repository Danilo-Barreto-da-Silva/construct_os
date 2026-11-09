# Construct OS (SGO.IA)

Protótipo acadêmico de gestão de obras em **Django**, com medições mensais, controle de FVS, RNC, metas de planejamento, relatórios e análise experimental de vídeo com Gemini.

> **Não homologado para produção.** Registros de FVS e RNC representam acompanhamento administrativo interno; o sistema não gera uma certificação ISO 9001, laudo técnico assinado ou comprovação de responsabilidade profissional. A IA fornece sugestões que exigem validação humana.

## Funcionalidades

- **Painel:** avanço físico médio, torres, matriz de unidades, filtros de mês/torre/andar e histórico mensal baseado nas medições existentes. Indica quantas unidades possuem medição no mês; não projeta prazo nem compara metas quando a cobertura é incompleta.
- **Qualidade / FVS:** checklist por apartamento e mês, resultado e observação de cada inspeção, autor e histórico. Apenas `is_staff` pode marcar itens conformes e aprovar a FVS global. Itens pendentes e RNCs formais não resolvidas impedem a aprovação.
- **RNC:** criação vinculada à medição, prioridade, prazo e alerta de atraso, atribuição, ação corretiva, transição entre Aberta/Em tratamento/Resolvida e histórico de movimentações. Encerrar uma RNC **não** aprova a FVS automaticamente.
- **Metas simples:** metas mensais acumuladas por torre, inseridas manualmente e auditadas (valor anterior, novo, autor e data). O painel só compara grupos equivalentes e não inventa valores.
- **Curva S ponderada por serviços:** novo módulo em `/planejamento/fisico/`. Cada serviço possui peso, meta e avanço físico acumulado por mês. A curva só calcula se os pesos somarem **100%** e houver todos os lançamentos; caso contrário, informa cobertura incompleta. Inclui histórico de alterações, correção auditada de pesos antes do primeiro lançamento, integração com o painel filtrado por torre e exportação CSV.
- **Projetos + Vistoria Inteligente (novo MVP):** módulo em `/inteligencia/` para cadastrar tipologias, ambientes, serviços e critérios com pesos; vincular unidades; gerar QR Codes por apartamento; proteger PDFs de projetos e vídeos; registrar vídeo com áudio no celular; analisar vídeo e narração por Gemini em comando separado; e salvar avanço **somente após revisão humana**, com histórico. Esta medição por critério é independente da FVS e das medições mensais legadas. Veja [guia do módulo](docs/vistoria_pdf_qr.md).
- **Cadastros:** inclusão de torres, apartamentos e uma medição por apartamento/mês. Novas medições entram com FVS pendente. **Não há exclusão por essas telas.**
- **Relatórios:** resumo mensal por torre, comparação ponderada (quando completa) e exportação CSV de medições, RNCs e serviços (somente equipe autorizada). O CSV possui mitigação contra fórmulas maliciosas.
- **IA opcional:** `processar_vistorias --limite 1` usa por padrão **`gemini-3.8-flash` via Interactions API** (`GEMINI_MODEL` pode sobrescrever o ID). O modelo 2.5 pode aparecer na listagem, mas retorna **404** para projetos novos. O fluxo separa visual, áudio e incerteza, considera apenas referências de projetos conferidas e não atualiza FVS ou medições por conta própria. Consulte os limites e preços do projeto no AI Studio antes de gerar análises; vídeos de obra real não devem ser enviados sem autorização e análise das condições de tratamento de dados.
- **Testes:** verificação do Django, consistência de migrações, testes de permissões e de fluxos administrativos por GitHub Actions.

## Piloto de campo com filmagem real (experimental)

O comando `python manage.py preparar_piloto_campo --confirmar-teste` gera **uma torre de laboratório separada**, com 11 serviços e critérios que distinguem inspeção visual de ensaios/documentos. Os pesos são **estimativas provisórias**, e não foram extraídos como quantidades reais dos projetos. Nenhum dado das obras anteriores, FVS ou RNC é alterado.

Antes de filmar, leia o [roteiro de gravação e uso responsável](docs/piloto_filmagem_campo.md). A gravação pode ser feita offline com a câmera do celular e enviada mais tarde; o Gemini exige configuração explícita de chave e autorização para transferência do vídeo à API externa.

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
6. **Planejamento:** o módulo de metas simples continua disponível, mas é separado da nova **Curva S por serviços**. Cadastre os serviços de uma torre com peso físico total de 100%, depois os valores previstos e executados acumulados em cada mês. O gráfico próprio é ponderado por atividade; ainda **não** é uma Curva S financeira, EVM ou um cronograma contratual.
7. **Relatórios:** equipe autorizada consulta totais por mês e exporta dados em CSV, inclusive o progresso dos serviços. Os registros de exemplo não devem ser interpretados como dados reais de obra.

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

Para validar o fluxo de FVS/RNC, veja [Roteiro de testes](docs/roteiro_testes.md). Para os pesos, exemplos de atividades e cálculos da nova Curva S, consulte o [Guia de planejamento ponderado](docs/curva_s_fisica.md).

A workflow `.github/workflows/django-checks.yml` roda `manage.py check`, `makemigrations --check --dry-run` e `manage.py test` nas alterações da branch e nas pull requests. A execução no seu Codespaces é importante para confirmar o banco e as páginas locais.
