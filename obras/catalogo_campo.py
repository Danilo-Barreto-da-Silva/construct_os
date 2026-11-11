"""Catálogo de CRITÉRIOS DE CAMPO para um piloto exploratório (NÃO medição oficial).

Os itens seguem a sequência usual de serviços e as disciplinas observadas nos
PDFs fornecidos pelo usuário (arquitetura, elétrica, água, esgoto e formas).
As plantas NÃO foram quantificadas. Pesos são ilustrativos, pendentes de revisão
de orçamento, memorial, quantitativos e escopo específico da unidade.
A presença/ausência visual de um elemento não comprova sua conformidade.
"""

# codigo, nome, peso PROVISÓRIO de contribuição ao apartamento, critérios
# Cada critério: código, descrição, peso interno, método, orientação de captação.
SERVICOS_CAMPO = (
    ("ALV", "Alvenaria e vãos", 17, (
        ("MAR", "Marcação de paredes e vãos", 10, "VISUAL",
         "Percorra o ambiente mostrando bases e alinhamentos. A imagem não certifica esquadro ou locação."),
        ("ELEV", "Elevação das paredes previstas", 50, "VISUAL",
         "Mostre as paredes de cada ambiente do piso ao teto, indicando trechos faltantes. Não inferir áreas sem escala."),
        ("VERGA", "Vergas e contravergas nos vãos", 20, "VISUAL",
         "Mostre as aberturas antes dos revestimentos. A imagem pode indicar presença, não dimensão, armadura ou resistência."),
        ("ENC", "Encunhamento e arremates superiores", 20, "VISUAL",
         "Mostre o encontro entre parede e estrutura. Não inferir material/tempo de cura por aparência."),
    )),
    ("ELE", "Instalações elétricas aparentes e embutidas", 14, (
        ("CX", "Caixas elétricas posicionadas e chumbadas", 25, "VISUAL",
         "Mostre caixas de tomadas e interruptores de perto e o conjunto da parede. Narre o ambiente."),
        ("DUT", "Eletrodutos e passagens acessíveis", 25, "VISUAL",
         "Filme eletrodutos aparentes, rasgos e infraestrutura antes do fechamento; não adivinhar trechos ocultos."),
        ("CAB", "Passagem e identificação de condutores", 30, "DOCUMENTAL",
         "Relate somente o que estiver documentado ou acessível. Vídeo não comprova condutores embutidos."),
        ("TESTE", "Ensaios e testes dos circuitos", 20, "TESTE",
         "Exigir registros de teste por profissional habilitado; não concluir a partir do vídeo."),
    )),
    ("AGU", "Água fria e quente (pontos e ramais)", 10, (
        ("RAM", "Ramais e tubulações de alimentação acessíveis", 35, "VISUAL",
         "Mostre áreas molhadas e tubulações antes do fechamento; indique se é água fria ou quente."),
        ("PONT", "Pontos de consumo e registros", 35, "VISUAL",
         "Filme saída de pia, lavatório, chuveiro e registros visíveis; quantidades dependem do projeto."),
        ("PRESS", "Teste de pressão / estanqueidade da alimentação", 30, "TESTE",
         "Exigir registro de ensaio com pressão, duração e responsável, não apenas narração."),
    )),
    ("ESG", "Esgoto e ventilação sanitária", 9, (
        ("PRU", "Tubos de queda e prumadas acessíveis", 30, "VISUAL",
         "Mostre shafts e colunas acessíveis com referência de ambiente; partes embutidas são desconhecidas."),
        ("RAM", "Ramais, esperas e conexões aparentes", 45, "VISUAL",
         "Filme pontos de esgoto antes do fechamento e conexões visíveis; não inferir declividade."),
        ("TESTE", "Teste de estanqueidade e funcionamento", 25, "TESTE",
         "Exigir teste e evidência documental; presença de tubulação não significa aprovação."),
    )),
    ("REB", "Revestimento argamassado", 12, (
        ("PREP", "Preparo da base / chapisco", 20, "VISUAL",
         "Mostrar base sem encobrimento; reconhecer apenas superfícies visíveis."),
        ("EXEC", "Reboco ou emboço executado", 60, "VISUAL",
         "Percorrer todas as paredes; partes fora de câmera permanecem não verificadas."),
        ("GEOM", "Prumo, planeza e espessura aferidos", 20, "MEDICAO",
         "Exigir régua, nível ou outro instrumento e registro de medição técnica."),
    )),
    ("CTR", "Contrapiso e caimentos", 9, (
        ("BASE", "Preparação da base para contrapiso", 20, "VISUAL",
         "Mostrar a base antes de ser coberta, quando possível."),
        ("EXEC", "Execução visível do contrapiso", 55, "VISUAL",
         "Filmar o piso inteiro por ambiente; não extrapolar m² executados sem quantitativo."),
        ("NIV", "Níveis e caimentos verificados", 25, "MEDICAO",
         "Exigir aferição de nível/caimento e registro, especialmente em áreas molhadas."),
    )),
    ("IMP", "Impermeabilização de áreas molhadas", 5, (
        ("PREP", "Preparação dos substratos e encontros", 20, "VISUAL",
         "Filme ralos, rodapés e cantos, antes de encobrir."),
        ("APLI", "Camadas impermeabilizantes aparentes", 50, "VISUAL",
         "Identifique áreas e número de demãos declaradas; vídeo não prova espessura ou consumo."),
        ("EST", "Teste de estanqueidade de áreas impermeabilizadas", 30, "TESTE",
         "Exigir evidência de ensaio com duração e registro de aprovação."),
    )),
    ("REV", "Revestimentos cerâmicos e pisos", 10, (
        ("PARE", "Revestimento de parede instalado", 45, "VISUAL",
         "Mostrar todas as paredes previstas com revestimento, sem contar ambientes não filmados."),
        ("PISO", "Piso/revestimento de piso instalado", 40, "VISUAL",
         "Percorrer piso do ambiente; não inferir área em m² sem escala e projeto."),
        ("QUAL", "Aderência, alinhamento e juntas conferidos", 15, "TESTE",
         "Exigir inspeção/ensaios específicos, não inferir som cavo ou aderência por imagem."),
    )),
    ("ESQ", "Esquadrias e portas", 5, (
        ("MAR", "Marcos e contramarcos instalados", 40, "VISUAL",
         "Filmar vãos, marcos e detalhes de fixação visíveis."),
        ("INST", "Portas e esquadrias instaladas", 45, "VISUAL",
         "Mostre aberturas e indique elementos faltantes; confirme tipos com o quadro do projeto."),
        ("FUNC", "Funcionamento e vedação verificados", 15, "TESTE",
         "Exige verificação de operação/vedação e aceite técnico."),
    )),
    ("PIN", "Pintura e acabamento superficial", 5, (
        ("PREP", "Preparação de superfície e massa", 35, "VISUAL",
         "Mostrar paredes de perto antes da pintura final."),
        ("ACAB", "Aplicação final de pintura aparente", 45, "VISUAL",
         "Filme com iluminação uniforme; não concluir qualidade apenas por aparência."),
        ("FVS", "Inspeção técnica de acabamento", 20, "DOCUMENTAL",
         "Exigir FVS/documentação assinada, separada da aparência do vídeo."),
    )),
    ("FOR", "Forros e acabamentos de teto", 4, (
        ("EST", "Estrutura e suportes de forro", 35, "VISUAL",
         "Mostrar estrutura antes do fechamento quando houver forro previsto."),
        ("FECH", "Fechamento de forro e arremates", 45, "VISUAL",
         "Percorrer teto dos ambientes em que o projeto prevê forro."),
        ("CONF", "Fixação e acabamento de forro verificados", 20, "MEDICAO",
         "Exigir inspeção de fixações, alinhamentos e projetos específicos."),
    )),
)

AMBIENTES_CAMPO = (
    ("SALA", "Sala"),
    ("COZ", "Cozinha"),
    ("BWC", "Banheiro"),
    ("QUARTO", "Quarto"),
    ("SERV", "Área de serviço"),
    ("CIRC", "Circulação"),
)

ORIENTACOES_GERAIS = (
    "Identifique o apartamento/ambiente sem mostrar pessoas nem informações sigilosas.",
    "Faça uma tomada geral de cada ambiente e depois detalhes dos serviços aparentes.",
    "Narre o que foi EXECUTADO, o que está PARCIAL e o que NÃO foi feito; se não sabe, diga 'não verificado'.",
    "Diferencie o que você viu do que só foi informado por outra pessoa.",
    "Para conduítes, caixinhas chumbadas, prumadas e ramais, filme ANTES de fechar a parede.",
    "Não afirme prumo, estanqueidade, corrente elétrica, dimensionamento ou conformidade sem ensaio.",
    "Evite rostos, crachás, placas, documentos com dados e imagens de terceiros; peça autorização para filmar.",
)

assert sum(item[2] for item in SERVICOS_CAMPO) == 100
assert all(sum(crit[2] for crit in servico[3]) == 100 for servico in SERVICOS_CAMPO)
