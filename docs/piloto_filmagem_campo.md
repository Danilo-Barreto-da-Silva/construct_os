# SGO.IA — piloto de filmagem em campo (sem medição oficial)

**Situação: experimental.** Este piloto **não** transfere automaticamente a medição para os painéis oficiais, não certifica FVS/ISO, não aprova RNC, e não executa ensaios técnicos.

## De onde vêm os parâmetros

O catálogo `obras/catalogo_campo.py` contempla atividades usuais de apartamentos em execução e disciplinas observadas nos cinco PDFs estudados: arquitetura, elétrica, água, esgoto e estrutura/formas. Ele também inclui etapas de acabamentos que podem existir em outras plantas, mas **não foram confirmadas nesses desenhos como escopo da unidade escolhida**.

**Pesos percentuais são hipóteses experimentais, NÃO quantidades verificadas nos projetos, orçamento ou contrato.** Precisam ser redefinidos pelo profissional da obra a partir de escopo, levantamentos por ambiente, orçamento e revisão válida antes de uso real. Nenhuma quantidade de caixas, parede em m², comprimento de prumada ou tipo de unidade foi fabricada a partir dos PDFs.

### Serviços e pesos provisórios do LAB

| Serviço | Peso apenas do piloto | Conteúdo da vistoria |
|---|---:|---|
| Alvenaria e vãos | 17% | Marcação, elevação, vergas/contravergas, encunhamento |
| Elétrica | 14% | Caixas chumbadas, eletrodutos, cabos, ensaios |
| Água | 10% | Ramais, pontos e registros, testes |
| Esgoto e ventilação | 9% | Prumadas, ramais/esperas, ensaios |
| Reboco | 12% | Preparo, execução, conferências geométricas |
| Contrapiso | 9% | Base, execução e caimentos |
| Impermeabilização | 5% | Preparo, aplicação, teste |
| Revestimentos | 10% | Paredes, pisos, verificação técnica |
| Esquadrias | 5% | Marcos, instalação, operação |
| Pintura | 5% | Preparação, pintura, avaliação |
| Forros | 4% | Estrutura, fechamento, conferência |
| **Total** | **100%** | **Apenas modelo experimental** |

Cada serviço contém subetapas com pesos internos somando 100%. O perfil tem critérios `VISUAL`, `MEDICAO`, `TESTE` ou `DOCUMENTAL`. A IA pode registrar observações sobre um serviço, mas não pode provar os critérios instrumentais ou ensaios.

## Preparar o laboratório amanhã ou hoje

1. Abra seu Codespace existente na branch `refactor/auditoria-seguranca`, sem criar outro.
2. Pare o `runserver` com `Ctrl+C`, faça um backup antes de atualizar e instale atualizações:

```bash
cd /workspaces/construct_os
source .venv/bin/activate
git status --short
cp db.sqlite3 "$HOME/backup_sgoia_antes_piloto_campo.sqlite3"
git pull --ff-only origin refactor/auditoria-seguranca
python manage.py check
python manage.py test
```

3. Para criar somente a área de laboratório (uma vez), execute:

```bash
python manage.py preparar_piloto_campo --confirmar-teste
```

O comando cria uma torre **LAB — Vistoria experimental**, um apartamento **AMOSTRA-01**, tipologia **CAMPO-IA-V1** e os critérios do quadro. Não modifica as torres A/B/PilotoA, FVS, RNC ou medições históricas. Se o LAB já existir, o comando recusa a segunda execução sem apagar dados.

4. Configure as variáveis locais de desenvolvimento conforme o README e ligue o servidor:

```bash
export DJANGO_DEBUG=1
export DJANGO_SECRET_KEY="chave-temporaria-apenas-para-testes"
export DJANGO_CSRF_TRUSTED_ORIGINS="https://*.app.github.dev,https://localhost:8000"
python manage.py runserver 0.0.0.0:8000
```

5. No menu **Projetos & Vistorias**, selecione **CAMPO-IA-V1** e clique no apartamento AMOSTRA-01. A página inclui **roteiro de filmagem**, câmera com microfone, upload e QR Code.

## Se for gravar na obra, com autorização

- Solicite autorização adequada da empresa e de eventuais pessoas envolvidas; evite rostos, nomes, crachás, placas e documentos confidenciais. **Não publique vídeos no GitHub ou em portais públicos.**
- Você pode **gravar com o aplicativo de câmera do próprio celular**, mantendo o arquivo local para posterior análise; isso evita depender de conexão do Codespaces dentro da obra.
- Preferir **1 ou 2 vídeos curtos** de 60–120 segundos cada, com voz clara e imagem estável. A interface web suporta 120 segundos via navegador e 30 MB por arquivo; vídeos da câmera nativa acima de 30 MB precisam ser comprimidos ou refeitos.
- Começar com uma **tomada geral**, indicar cada ambiente e depois mostrar detalhes, quando permitidos.
- Em alvenaria: vãos, paredes, topo/encunhamento. Em elétrica: caixas chumbadas e eletrodutos aparentes. Em água/esgoto: prumadas, esperas e ramais acessíveis. Não abrir painéis energizados nem entrar em áreas inseguras para obter imagens.
- Narrar de forma explícita: “na sala, consigo ver ___; na cozinha, vejo ___; a fiação está coberta e **não verificada**; testes de pressão **não foram apresentados**”.
- Não alegar que está “80% executado” sem áreas/quantidades verificadas. Deixar visível o que não foi mostrado.

**Exemplo de narração (adapte ao que existir):**

> “Esta é uma vistoria experimental de um ambiente em execução. Estou mostrando a sala: as caixas elétricas que aparecem aqui estão chumbadas; os eletrodutos visíveis passam por esta parede. Não confirmei cabeamento embutido nem teste elétrico. Agora, na área molhada, estas são as esperas aparentes. Não tenho evidência de ensaio hidráulico.”

A interpretação do áudio é uma **declaração humana**. O modelo deve diferenciar isso de evidência visual e marcar as partes que não podem ser avaliadas.

## Enviar e analisar depois da visita

1. Pelo celular ou computador, abra o link privado do Codespaces, entre no SGO.IA, abra a unidade do LAB e escolha o vídeo salvo. Não abra a porta como pública para contornar login.
2. Envie o arquivo. Deverá aparecer como **PENDENTE**. Sem chave de IA, isso é normal.
3. Para mandar o vídeo à **API externa do Google**, obtenha autorização, configure `GEMINI_API_KEY` num ambiente privado e, no Codespaces, execute **conscientemente**:

```bash
python manage.py processar_vistorias --limite 1
```

A chamada pode ser cobrada. O vídeo é transferido ao serviço externo para processamento; **isso não ocorre automaticamente no upload**. Não coloque chaves no repositório, no chat ou em capturas de tela.

4. Consulte a página da vistoria: sugestões por critério com informação visual, áudio e pendências de verificação. Se o modelo produzir porcentagem sem quantitativos e cobertura suficientes, **não aprove**.
5. Use a tela de medição humana apenas para testes e controle experimental. Não trate pesos e percentuais do LAB como medição oficial da obra.

## Sobre os PDFs

Os arquivos de arquitetura, elétrica, água, esgoto e formas enviados anteriormente foram estudados como referência para categorias de inspeção. **Nenhum desses PDFs foi copiado para o repositório ou convertido automaticamente em quantitativos.** O laboratório também não armazena os projetos reais. Se houver autorização para usar os documentos, anexe-os depois pelo cadastro privado e confira manualmente os itens esperados de cada folha.

## Limitações ainda abertas

A comparação precisa vídeo × desenho requer valores esperados realmente levantados do projeto; a sobreposição BIM/IFC exige outro módulo, calibração e posicionamento espacial. O protótipo também precisa de permissões por empresa/obra, proteção contra malware, política de retenção e proteção de dados, limites de custo, infraestrutura de produção e validação com gravações reais.
