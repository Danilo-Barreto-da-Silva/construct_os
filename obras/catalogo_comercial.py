"""Tipologia de SALA COMERCIAL COM ACABAMENTO COMPLETO — perfil de ensaio.

NÃO representa quantitativos ou memorial da obra do usuário. Exemplos usuais:
piso, pintura, forro, alvenaria, elétrica, revestimentos e instalações.
A existência de pontos hidrossanitários, esquadrias internas e outros itens
depende do escopo real. Revisar ANTES de qualquer medição profissional.

Cada serviço: (código, nome, peso ilustrativo, lista de critérios).
Cada critério: (código, descrição, peso interno, método, orientação).
"""

SERVICOS_COMERCIAL = (
    ("ALV", "Alvenaria, vãos e arremates", 14, (
        ("LOC", "Marcação e locação de paredes", 10, "MEDICAO",
         "Conferir com a planta e instrumentos; não declarar alinhamento por vídeo."),
        ("PARE", "Paredes previstas erguidas", 50, "VISUAL",
         "Filmagem panorâmica de todas as paredes da sala; áreas não exibidas são desconhecidas."),
        ("VÃOS", "Vergas, contravergas e aberturas", 20, "VISUAL",
         "Mostrar vãos antes de serem revestidos; imagem não mede armaduras e dimensões."),
        ("ENC", "Encunhamento e arremates da alvenaria", 20, "VISUAL",
         "Mostrar a ligação entre parede e laje/vigas sem inferir resistência."),
    )),
    ("ELE", "Instalação elétrica e infraestrutura", 18, (
        ("CX", "Caixas elétricas embutidas e chumbadas", 25, "VISUAL",
         "Aproxime das caixas com contexto de ambiente, sem inferir quantidade total."),
        ("DUT", "Eletrodutos e passagens acessíveis", 25, "VISUAL",
         "Mostrar eletrodutos e entradas de caixas; os trechos embutidos permanecem não verificáveis."),
        ("QDG", "Quadro elétrico instalado", 10, "VISUAL",
         "Mostrar apenas a parte externa de quadros desenergizados, sem abrir painéis."),
        ("CAB", "Fiação/circuitos conforme execução documentada", 25, "DOCUMENTAL",
         "Exigir registros de instalação e identificação, não inferir cabos por caixas vazias."),
        ("TEST", "Ensaios e testes elétricos", 15, "TESTE",
         "Exigir testes por responsável habilitado; vídeo não substitui os resultados."),
    )),
    ("HID", "Pontos hidrossanitários previstos (se aplicáveis)", 6, (
        ("AGUA", "Pontos e ramais de alimentação visíveis", 40, "VISUAL",
         "Somente onde o memorial prever água. Se não houver, revisar a matriz ANTES de medir."),
        ("ESG", "Esperas e ramais de esgoto visíveis", 35, "VISUAL",
         "Mostrar shafts e pontos acessíveis, sem inferir caimento ou estanqueidade."),
        ("TEST", "Teste de pressão/estanqueidade documentado", 25, "TESTE",
         "Exigir registro do ensaio e responsável; não marcar como testado por narração."),
    )),
    ("REB", "Reboco e emboço das superfícies", 12, (
        ("PREP", "Preparação e chapisco da base", 20, "VISUAL",
         "Mostrar trechos antes de cobertura e quaisquer áreas pendentes."),
        ("EXEC", "Argamassa executada nas áreas previstas", 60, "VISUAL",
         "Filmar paredes inteiras; textura aparente não comprova espessura."),
        ("GEOM", "Prumo, espessura e planeza conferidos", 20, "MEDICAO",
         "Exigir aferição com instrumentos; vídeo é apenas registro auxiliar."),
    )),
    ("CTR", "Contrapiso", 7, (
        ("BASE", "Base preparada", 20, "VISUAL",
         "Documentar base antes da cobertura."),
        ("EXEC", "Contrapiso executado", 60, "VISUAL",
         "Filmar o piso por completo, sem deduzir área em metros quadrados."),
        ("NIV", "Nível e caimentos verificados", 20, "MEDICAO",
         "Exigir registros de nivelamento e caimento."),
    )),
    ("PISO", "Piso final e rodapés", 14, (
        ("PISO", "Revestimento de piso assentado", 65, "VISUAL",
         "Percorrer o piso final da sala, mostrando trechos não executados."),
        ("RODA", "Rodapés e arremates instalados", 20, "VISUAL",
         "Filmar encontros entre piso e parede."),
        ("QUAL", "Juntas, aderência e acabamento inspecionados", 15, "TESTE",
         "Exige inspeção técnica; não inferir aderência ou nivelamento pela imagem."),
    )),
    ("FOR", "Forro completo", 12, (
        ("EST", "Estrutura/suportes de forro", 30, "VISUAL",
         "Filmar a estrutura antes de fechar o teto; registro posterior é insuficiente."),
        ("PLAC", "Placas e fechamento do forro", 45, "VISUAL",
         "Mostrar todo teto, sem considerar não filmado como executado."),
        ("REC", "Recortes para luminárias e arremates", 15, "VISUAL",
         "Detalhar os recortes e a posição aparente dos pontos."),
        ("TEST", "Fixação, nível e integridade conferidos", 10, "MEDICAO",
         "Exigir inspeção das fixações e nivelamento, não apenas imagem."),
    )),
    ("PIN", "Pintura completa", 10, (
        ("PREP", "Massa/preparação de superfícies", 35, "VISUAL",
         "Mostrar superfícies em condições de iluminação uniforme."),
        ("DEM", "Demãos e pintura final aparentes", 50, "VISUAL",
         "Mostrar todas as paredes e tetos previstos. Aparência não comprova número de demãos."),
        ("QUAL", "Acabamento e aderência aprovados", 15, "DOCUMENTAL",
         "Exigir ficha de inspeção e registro de aprovação."),
    )),
    ("ESQ", "Portas, esquadrias e arremates", 7, (
        ("INST", "Portas e esquadrias previstas instaladas", 60, "VISUAL",
         "Filmar elementos previstos, com visão geral e detalhes."),
        ("ARRE", "Guarnições e arremates visíveis", 25, "VISUAL",
         "Mostrar detalhes de acabamento nas juntas."),
        ("FUNC", "Funcionamento e vedação verificados", 15, "TESTE",
         "Exigir teste/inspeção de operação e vedação."),
    )),
)

AMBIENTES_COMERCIAL = (
    ("SALA", "Sala comercial"),
    ("ENT", "Entrada e acesso"),
    ("TETO", "Forro/teto"),
    ("PISO", "Área de piso"),
    ("SHAFT", "Área técnica/shaft, se previsto"),
)

assert sum(s[2] for s in SERVICOS_COMERCIAL) == 100
assert all(sum(c[2] for c in s[3]) == 100 for s in SERVICOS_COMERCIAL)
