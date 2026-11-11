# Construct OS (SGO.IA)

Protótipo acadêmico de gestão de obras em **Django**, com medições mensais, controle de FVS, RNC, metas de planejamento, relatórios e análise experimental de vídeo com Gemini.

> **Não homologado para produção.** Registros de FVS e RNC representam acompanhamento administrativo interno; o sistema não gera uma certificação ISO 9001, laudo técnico assinado ou comprovação de responsabilidade profissional. A IA fornece sugestões que exigem validação humana.

## Funcionalidades

- **Painel:** avanço físico médio, torres, matriz de unidades, filtros de mês/torre/andar e histórico mensal baseado nas medições existentes. Indica quantas unidades possuem medição no mês; não projeta prazo nem compara metas quando a cobertura é incompleta.
- **Qualidade / FVS:** checklist por apartamento e mês, resultado e observação de cada inspeção, autor e histórico. Apenas `is_staff` pode marcar itens conformes e aprovar a FVS global. Itens pendentes e RNCs formais não resolvidas impedem a aprovação.
- **RNC:** qualquer usuário autenticado pode comunicar uma não conformidade formal. A abertura registra autoria, muda a FVS para **NÃO CONFORME** e revoga uma aprovação anterior, **sem alterar o percentual físico**. Somente `is_staff` pode tratar ou encerrar a RNC. O encerramento **não** reaprova a FVS: é necessária nova conferência e aprovação pela equipe autorizada. O formulário informa explicitamente essa consequência.
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

## Processamento de vídeo com IA (fluxo único)

Use a página de **Vistorias Inteligentes** (em `/inteligencia/`) para armazenar a gravação, e processe-a separadamente pelo comando `python manage.py processar_vistorias --limite 1`. A análise utiliza o Gemini via Interactions API; a medição, a FVS e o checklist não são aprovados pela IA.

**O antigo upload Gemini dentro do modal de medição foi desativado.** Registros históricos de sugestões permanecem preservados, mas não são produzidos novos dados naquele campo.

Se o Codespaces ou o processo da análise for interrompido, um registro pode permanecer em `PROCESSANDO`. A recuperação é **manual e não reenvia vídeo**:

```bash
python manage.py recuperar_vistoria --listar
# Confirme que não existe processar_vistorias em execução:
ps -ef | grep '[p]rocessar_vistorias'
# Somente para uma vistoria específica cuja execução anterior terminou:
python manage.py recuperar_vistoria --vistoria-id ID --confirmar
```

O último comando muda o status para `ERRO`, sem apagar arquivo, relatório nem modificar medições. Se houver dúvida se a requisição anterior ainda está sendo processada pelo Google, verifique o uso da API antes de pedir nova análise. Uma nova tentativa é uma **decisão explícita** na tela da vistoria, que pode consumir cota ou gerar custo. Nunca execute a recuperação enquanto o processo anterior ainda estiver ativo.

## Controles de segurança no Codespaces (fase de desenvolvimento)

- **Autenticação:** tanto o acesso principal (`/login/`) quanto o Django Admin (`/admin/login/`) têm limite. Após 5 senhas incorretas por combinação de usuário/IP (ou 20 por IP), o login é temporariamente bloqueado por até 15 minutos, inclusive para senha correta naquele período. O sistema utiliza mensagens genéricas e chaves HMAC no cache — não grava senhas nem usernames no identificador. Para testes em um único processo, o cache padrão do Django é suficiente. **Não considerar essa proteção pronta para produção com vários workers:** antes de publicar, configurar Redis/Memcached compartilhado, validar identificação confiável do IP atrás do proxy e acrescentar monitoramento.
- **Logs:** falhas de vídeo/PDF e início, fim ou erro de processamento da IA geram registros técnicos no console do servidor. Os textos de log adicionados não incluem senha, chave da API, nome dos arquivos nem narração. Em produção, proteger o acesso aos logs e avaliar a retenção.
- **RNC e FVS:** qualquer usuário autenticado pode abrir RNC, mesmo sobre FVS já aprovada; isso revoga a aprovação e deixa a FVS como não conforme. A equipe técnica autorizada trata/encerra RNC e confirma a nova inspeção. Alteração de percentual e aprovação exigem ações independentes.
- **Credenciais históricas:** a primeira versão pública do projeto continha uma conta de demonstração e uma chave Django no histórico do Git. Considere ambas comprometidas permanentemente. Antes de compartilhar qualquer instalação, revisar a lista de usuários no painel administrativo, desativar a conta de demonstração caso exista, alterar senhas reutilizadas e substituir a `DJANGO_SECRET_KEY` por um segredo único armazenado nas configurações seguras do Codespaces/servidor. Trocar a chave invalida sessões existentes. Não colar segredos no chat, no README ou em commits.
- **Ambiente:** mantenha a porta `8000` **Private**. `DJANGO_DEBUG=1` é apenas para desenvolvimento no Codespaces; não publicar uma instância com esse valor. A limpeza do histórico Git e o merge na `main` ficam para uma operação separada, planejada e com cópias de segurança.

## Etapa 3 — assets locais e configuração para futura implantação

**Desenvolvimento no Codespaces:** os templates deixaram de carregar Tailwind, ApexCharts, Font Awesome e Three.js via CDN. Os arquivos não são baixados nem enviados pelo Gemini; são produzidos localmente a partir das dependências travadas em `package-lock.json`. **Depois de cada atualização dessas dependências**, compile os assets antes de abrir o sistema:

```bash
cd /workspaces/construct_os
npm ci
npm run build:assets
source .venv/bin/activate
python manage.py check
python manage.py test
```

Use o servidor Django normalmente com `DJANGO_DEBUG=1`, mantendo a porta `8000` privada. Se abrir o sistema sem compilar os assets após esta atualização, o layout, os gráficos e a visualização 3D poderão não carregar. Não execute `migrate` por causa desses arquivos.

**Pipeline:** GitHub Actions usa Node 22, `npm ci`, compilação de CSS e bibliotecas locais, `collectstatic`, testes Django e `check --deploy`. A geração não altera medições ou dados da obra. O build usa Tailwind 3.4.19, ApexCharts 3.54.1, Font Awesome 6.4.0 e Three.js 0.170.0. Antes de oferecer o produto comercialmente, verificar as condições de licença das bibliotecas, especialmente ApexCharts.

**Implantação futura (não executada):** configurar em um gerenciador seguro de segredos `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY` exclusiva de pelo menos 50 caracteres, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `DJANGO_SMTP_HOST` e as opções `DJANGO_SMTP_USER`, `DJANGO_SMTP_PASSWORD` e `DJANGO_SMTP_PORT` conforme o fornecedor. O backend SMTP usa TLS por padrão. Compilar com `npm ci && npm run build:assets`, executar `python manage.py collectstatic --noinput` e configurar o servidor HTTPS/proxy para servir `STATIC_ROOT`. O projeto usa armazenamento estático com manifesto quando `DEBUG=0`; sem `collectstatic`, faltam arquivos.

**HTTPS:** redirecionamento SSL, cookies seguros e HSTS inicial de 1 hora são ativados fora de `DEBUG`. `DJANGO_TRUST_PROXY_HTTPS=1` só é permitido atrás de proxy confiável que substitui o cabeçalho `X-Forwarded-Proto`; nunca confiar nesse cabeçalho enviado diretamente pelo cliente. As opções HSTS `includeSubDomains` e `preload` permanecem desligadas até todos os subdomínios serem auditados — por isso `check --deploy` ainda avisa sobre W005/W021. Ativá-las sem validação é perigoso. O pipeline verifica que não há **erros** de segurança, mas não afirma que a implantação esteja pronta.

**Bloqueios para produção:** ainda é necessário migrar o SQLite para um banco adequado a múltiplos usuários, usar cache compartilhado no bloqueio de login, auditar segredos antigos no histórico Git, ajustar backup/restauração, revisar privacidade dos vídeos e configurar hospedagem real. A branch `main` não foi alterada nesta etapa.

## Segurança e dados

- `.venv/`, `db.sqlite3`, `.env` e `media/` são ignorados pelo Git. Os arquivos já versionados foram retirados do estado atual por commit sem apagar as cópias do Codespaces. Isso **não elimina conteúdo de commits antigos**.
- A pasta virtual e o banco de dados devem ser mantidos e copiados separadamente. Antes de migrações, faça backup de `db.sqlite3` com o servidor parado.
- O gerador de demonstração funciona somente em `DJANGO_DEBUG=1`, por superusuário, com confirmação, e **se o banco não tiver torres**. Nunca use com dados de clientes.
- O projeto inicialmente publicou credenciais de demonstração, uma SECRET_KEY e o SQLite no histórico Git. Troque qualquer senha reutilizada e credencial real; um planejamento específico de limpeza do histórico será necessário antes de qualquer exposição pública.
- O controle `is_staff` não faz isolamento por empresa/obra e não substitui papéis granulares. A trilha de auditoria registra ações após sua implantação, não o passado, e não é imutável contra administradores com acesso ao banco.
- Os uploads e o uso da IA ainda exigem avaliação de privacidade, consentimento e retenção antes de vídeos reais de clientes. Evite gravar pessoas sem autorização.
- Os assets CSS/JS principais são compilados e servidos localmente após `npm ci && npm run build:assets`; a hospedagem estática pública, política de cabeçalhos e revisão de infraestrutura permanecem tarefas de implantação.
- Backups automatizados, isolamento multiobra, credenciamento profissional, evidências fotográficas e assinatura digital formal são etapas futuras.

## Testes e referências

Para validar o fluxo de FVS/RNC, veja [Roteiro de testes](docs/roteiro_testes.md). Para os pesos, exemplos de atividades e cálculos da nova Curva S, consulte o [Guia de planejamento ponderado](docs/curva_s_fisica.md).

A workflow `.github/workflows/django-checks.yml` roda `manage.py check`, `makemigrations --check --dry-run` e `manage.py test` nas alterações da branch e nas pull requests. A execução no seu Codespaces é importante para confirmar o banco e as páginas locais.
