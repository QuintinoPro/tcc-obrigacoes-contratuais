"""Corpus de avaliação: contratos FICTÍCIOS com redações variadas e gabarito manual.

Cada item do gabarito tem uma `chave` (trecho que identifica a obrigação no texto),
o responsável correto e o prazo correto (None quando o contrato não define data).
As variações de redação são propositais, para medir os limites do extrator.
"""
from samples.gerar_contrato_exemplo import GABARITO as GAB_MARKETING
from samples.gerar_contrato_exemplo import TEXTO as TXT_MARKETING

_CHAVES_MARKETING = {
    "2.1": "plano de mídia", "2.2": "12 peças", "2.3": "campanhas de mídia paga", "2.4": "relatório mensal",
    "3.1": "acesso às contas", "3.2": "aprovar ou solicitar", "3.3": "primeira parcela",
}

CORPUS = [
    {
        "id": "C01-marketing",
        "estilo": "padronizado: itens numerados, verbo 'deverá', datas dd/mm/aaaa",
        "texto": TXT_MARKETING,
        "gabarito": [{"chave": _CHAVES_MARKETING[g["clausula"]], **g} for g in GAB_MARKETING],
    },
    {
        "id": "C02-software",
        "estilo": "padronizado com verbos variados ('se obriga a', 'compromete-se a', 'caberá à')",
        "texto": [
            ("h", "CONTRATO DE DESENVOLVIMENTO DE SOFTWARE Nº 031/2026"),
            ("p", "CONTRATANTE: Gama Logística S.A., inscrita no CNPJ 22.222.222/0001-22."),
            ("p", "CONTRATADA: Delta Tecnologia Ltda., inscrita no CNPJ 33.333.333/0001-33."),
            ("p", "Instrumento assinado em 01/10/2026 pelas partes acima qualificadas."),
            ("h2", "CLÁUSULA 2 — OBRIGAÇÕES DA CONTRATADA"),
            ("p", "2.1 A CONTRATADA se obriga a entregar o documento de requisitos até 30/10/2026, mediante aceite formal por e-mail."),
            ("p", "2.2 A CONTRATADA compromete-se a disponibilizar a versão beta do sistema em ambiente de homologação até 15/12/2026."),
            ("p", "2.3 Caberá à CONTRATADA corrigir os defeitos críticos em até 48 horas após a notificação."),
            ("p", "2.4 A CONTRATADA deverá entregar o código-fonte e a documentação técnica até 31/01/2027, mediante termo de entrega assinado."),
            ("h2", "CLÁUSULA 3 — OBRIGAÇÕES DA CONTRATANTE"),
            ("p", "3.1 A CONTRATANTE deverá designar um responsável técnico até 10/10/2026."),
            ("p", "3.2 A CONTRATANTE se responsabiliza por homologar cada entrega em até 10 dias corridos após o recebimento."),
        ],
        "gabarito": [
            {"chave": "documento de requisitos", "responsavel": "CONTRATADA", "prazo": "2026-10-30"},
            {"chave": "versão beta", "responsavel": "CONTRATADA", "prazo": "2026-12-15"},
            {"chave": "defeitos críticos", "responsavel": "CONTRATADA", "prazo": None},
            {"chave": "código-fonte", "responsavel": "CONTRATADA", "prazo": "2027-01-31"},
            {"chave": "responsável técnico", "responsavel": "CONTRATANTE", "prazo": "2026-10-10"},
            {"chave": "homologar cada entrega", "responsavel": "CONTRATANTE", "prazo": None},
        ],
    },
    {
        "id": "C03-limpeza",
        "estilo": "datas por extenso e prazos relativos à assinatura",
        "texto": [
            ("h", "CONTRATO DE PRESTAÇÃO DE SERVIÇOS DE LIMPEZA Nº 007/2026"),
            ("p", "CONTRATANTE: Épsilon Educação Ltda., com sede em Niterói/RJ."),
            ("p", "CONTRATADA: Zeta Facilities Ltda., com sede no Rio de Janeiro/RJ."),
            ("p", "O presente contrato foi assinado em 02/09/2026."),
            ("h2", "CLÁUSULA 4 — DAS OBRIGAÇÕES"),
            ("p", "4.1 A CONTRATADA deverá alocar a equipe de quatro auxiliares de limpeza em até 15 dias contados da assinatura."),
            ("p", "4.2 A CONTRATADA deverá apresentar o plano de higienização até o dia 30 de setembro de 2026."),
            ("p", "4.3 A CONTRATADA obriga-se a fornecer os materiais de limpeza mensalmente, mediante nota de entrega assinada."),
            ("p", "4.4 A CONTRATANTE deverá disponibilizar espaço para guarda dos materiais em até 5 dias contados da assinatura."),
            ("p", "4.5 A CONTRATANTE obriga-se a pagar a fatura mensal até o quinto dia útil de cada mês."),
        ],
        "gabarito": [
            {"chave": "quatro auxiliares", "responsavel": "CONTRATADA", "prazo": "2026-09-17"},
            {"chave": "plano de higienização", "responsavel": "CONTRATADA", "prazo": "2026-09-30"},
            {"chave": "materiais de limpeza", "responsavel": "CONTRATADA", "prazo": None},
            {"chave": "guarda dos materiais", "responsavel": "CONTRATANTE", "prazo": "2026-09-07"},
            {"chave": "fatura mensal", "responsavel": "CONTRATANTE", "prazo": None},
        ],
    },
    {
        "id": "C04-consultoria",
        "estilo": "partes com outros nomes (PRESTADORA/CLIENTE) e voz passiva",
        "texto": [
            ("h", "CONTRATO DE CONSULTORIA EMPRESARIAL Nº 112/2026"),
            ("p", "CLIENTE: Eta Varejo Ltda., doravante denominada CONTRATANTE."),
            ("p", "PRESTADORA: Theta Consultoria Ltda., doravante denominada CONTRATADA."),
            ("p", "Firmado em 05/08/2026."),
            ("h2", "CLÁUSULA 2 — ENTREGAS"),
            ("p", "2.1 A PRESTADORA deverá entregar o diagnóstico organizacional até 05/09/2026."),
            ("p", "2.2 O plano de ação será entregue pela PRESTADORA até 05/10/2026."),
            ("p", "2.3 A PRESTADORA deverá conduzir três oficinas com a diretoria até 30/11/2026, mediante lista de presença assinada."),
            ("h2", "CLÁUSULA 3 — DEVERES DO CLIENTE"),
            ("p", "3.1 O CLIENTE deverá fornecer os dados financeiros dos últimos dois anos até 15/08/2026."),
            ("p", "3.2 O CLIENTE deverá garantir a presença dos diretores nas oficinas."),
        ],
        "gabarito": [
            {"chave": "diagnóstico organizacional", "responsavel": "CONTRATADA", "prazo": "2026-09-05"},
            {"chave": "plano de ação", "responsavel": "CONTRATADA", "prazo": "2026-10-05"},
            {"chave": "três oficinas", "responsavel": "CONTRATADA", "prazo": "2026-11-30"},
            {"chave": "dados financeiros", "responsavel": "CONTRATANTE", "prazo": "2026-08-15"},
            {"chave": "presença dos diretores", "responsavel": "CONTRATANTE", "prazo": None},
        ],
    },
    {
        "id": "C05-eventos",
        "estilo": "obrigações em alíneas sem numeração própria e texto corrido",
        "texto": [
            ("h", "CONTRATO DE ORGANIZAÇÃO DE EVENTO Nº 045/2026"),
            ("p", "CONTRATANTE: Iota Associação Comercial, com sede no Rio de Janeiro/RJ."),
            ("p", "CONTRATADA: Kappa Eventos Ltda., com sede no Rio de Janeiro/RJ."),
            ("p", "Contrato assinado em 10/07/2026."),
            ("h2", "CLÁUSULA 3 — DAS OBRIGAÇÕES DA CONTRATADA"),
            ("p", "3.1 São obrigações da CONTRATADA: a) reservar o local do evento até 01/08/2026; b) contratar o serviço de buffet até 15/08/2026; c) enviar o relatório de público até 30/09/2026."),
            ("h2", "CLÁUSULA 4 — DAS OBRIGAÇÕES DA CONTRATANTE"),
            ("p", "4.1 A CONTRATANTE deverá aprovar a lista de convidados até 20/08/2026. A CONTRATANTE deverá também efetuar o pagamento do sinal até 20/07/2026."),
        ],
        "gabarito": [
            {"chave": "local do evento", "responsavel": "CONTRATADA", "prazo": "2026-08-01"},
            {"chave": "buffet", "responsavel": "CONTRATADA", "prazo": "2026-08-15"},
            {"chave": "relatório de público", "responsavel": "CONTRATADA", "prazo": "2026-09-30"},
            {"chave": "lista de convidados", "responsavel": "CONTRATANTE", "prazo": "2026-08-20"},
            {"chave": "pagamento do sinal", "responsavel": "CONTRATANTE", "prazo": "2026-07-20"},
        ],
    },
]

# Conjunto de VALIDAÇÃO (held-out): escrito depois do extrator v2 e não usado para ajustá-lo.
HOLDOUT = [
    {
        "id": "V01-manutencao",
        "estilo": "ordem inversa ('Fica a CONTRATADA obrigada'), 'É responsabilidade da', futuro simples",
        "texto": [
            ("h", "CONTRATO DE MANUTENÇÃO PREDIAL Nº 088/2026"),
            ("p", "CONTRATANTE: Lambda Shopping Center Ltda., inscrita no CNPJ 44.444.444/0001-44."),
            ("p", "CONTRATADA: Mu Engenharia Ltda., inscrita no CNPJ 55.555.555/0001-55."),
            ("p", "Contrato assinado em 14/10/2026."),
            ("h2", "CLÁUSULA 5 — DAS RESPONSABILIDADES"),
            ("p", "5.1 Fica a CONTRATADA obrigada a realizar a vistoria inicial das instalações até 31/10/2026."),
            ("p", "5.2 A CONTRATADA deverá emitir laudo técnico das instalações elétricas até o dia 15 de novembro de 2026, mediante laudo assinado por engenheiro responsável."),
            ("p", "5.3 A CONTRATADA manterá técnico de plantão durante o horário de funcionamento do shopping."),
            ("p", "5.4 É responsabilidade da CONTRATANTE liberar o acesso às áreas técnicas no prazo de 3 dias a contar da assinatura."),
            ("p", "5.5 A CONTRATANTE deverá pagar as notas fiscais em até 30 dias após o recebimento."),
        ],
        "gabarito": [
            {"chave": "vistoria inicial", "responsavel": "CONTRATADA", "prazo": "2026-10-31"},
            {"chave": "laudo técnico", "responsavel": "CONTRATADA", "prazo": "2026-11-15"},
            {"chave": "técnico de plantão", "responsavel": "CONTRATADA", "prazo": None},
            {"chave": "áreas técnicas", "responsavel": "CONTRATANTE", "prazo": "2026-10-17"},
            {"chave": "notas fiscais", "responsavel": "CONTRATANTE", "prazo": None},
        ],
    },
    {
        "id": "V02-treinamento",
        "estilo": "parte no masculino (CONTRATADO), data com pontos (dd.mm.aaaa)",
        "texto": [
            ("h", "CONTRATO DE PRESTAÇÃO DE SERVIÇOS DE TREINAMENTO Nº 019/2026"),
            ("p", "CONTRATANTE: Nu Seguros S.A., com sede no Rio de Janeiro/RJ."),
            ("p", "PRESTADOR: João Exemplo da Silva, doravante denominado simplesmente CONTRATADO."),
            ("p", "Assinado em 20/09/2026."),
            ("h2", "CLÁUSULA 2 — OBRIGAÇÕES"),
            ("p", "2.1 O CONTRATADO deverá ministrar 4 turmas do curso de atendimento ao cliente até 15/12/2026."),
            ("p", "2.2 O CONTRATADO deverá entregar o material didático até 10.10.2026."),
            ("p", "2.3 O CONTRATADO deverá aplicar avaliação de reação ao final de cada turma, mediante formulário preenchido pelos participantes."),
            ("p", "2.4 A CONTRATANTE deverá reservar sala com projetor para cada turma."),
            ("p", "2.5 A CONTRATANTE deverá enviar a lista de participantes até 05/10/2026."),
        ],
        "gabarito": [
            {"chave": "4 turmas", "responsavel": "CONTRATADA", "prazo": "2026-12-15"},
            {"chave": "material didático", "responsavel": "CONTRATADA", "prazo": "2026-10-10"},
            {"chave": "avaliação de reação", "responsavel": "CONTRATADA", "prazo": None},
            {"chave": "sala com projetor", "responsavel": "CONTRATANTE", "prazo": None},
            {"chave": "lista de participantes", "responsavel": "CONTRATANTE", "prazo": "2026-10-05"},
        ],
    },
    {
        "id": "V03-conteudo",
        "estilo": "redação padronizada com cláusulas sem obrigação misturadas",
        "texto": [
            ("h", "CONTRATO DE PRODUÇÃO DE CONTEÚDO Nº 052/2026"),
            ("p", "CONTRATANTE: Xi Educação Online Ltda., inscrita no CNPJ 66.666.666/0001-66."),
            ("p", "CONTRATADA: Ômicron Conteúdo Ltda., inscrita no CNPJ 77.777.777/0001-77."),
            ("p", "As partes firmaram o presente instrumento em 01/11/2026."),
            ("h2", "CLÁUSULA 1 — DO OBJETO"),
            ("p", "1.1 O objeto é a produção de videoaulas para a plataforma da CONTRATANTE."),
            ("h2", "CLÁUSULA 2 — DAS OBRIGAÇÕES"),
            ("p", "2.1 A CONTRATADA deverá entregar o roteiro das 10 videoaulas até 20/11/2026."),
            ("p", "2.2 A CONTRATADA compromete-se a gravar e editar as videoaulas até 18/12/2026, mediante envio dos arquivos em alta resolução."),
            ("p", "2.3 A CONTRATANTE deverá revisar os roteiros em até 7 dias após o recebimento."),
            ("p", "2.4 A CONTRATANTE obriga-se a pagar 50% do valor na assinatura deste contrato."),
            ("h2", "CLÁUSULA 3 — DA PROPRIEDADE INTELECTUAL"),
            ("p", "3.1 Os direitos patrimoniais sobre as videoaulas pertencem à CONTRATANTE após o pagamento integral."),
            ("p", "3.2 A rescisão poderá ocorrer por qualquer das partes, mediante aviso prévio de 30 dias."),
        ],
        "gabarito": [
            {"chave": "roteiro das 10", "responsavel": "CONTRATADA", "prazo": "2026-11-20"},
            {"chave": "gravar e editar", "responsavel": "CONTRATADA", "prazo": "2026-12-18"},
            {"chave": "revisar os roteiros", "responsavel": "CONTRATANTE", "prazo": None},
            {"chave": "50% do valor", "responsavel": "CONTRATANTE", "prazo": "2026-11-01"},
        ],
    },
]
