"""Gera um contrato FICTÍCIO de prestação de serviços em PDF para testes (RNF04)."""
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

OUT = Path(__file__).parent
SAMPLE_PATH = OUT / "contrato-exemplo.pdf"

TEXTO = [
    ("h", "CONTRATO DE PRESTAÇÃO DE SERVIÇOS DE MARKETING DIGITAL Nº 014/2026"),
    ("p", "CONTRATANTE: Alfa Comércio de Alimentos Ltda., inscrita no CNPJ 00.000.000/0001-00, com sede no Rio de Janeiro/RJ."),
    ("p", "CONTRATADA: Beta Serviços Digitais Ltda., inscrita no CNPJ 11.111.111/0001-11, com sede no Rio de Janeiro/RJ."),
    ("p", "As partes acima identificadas têm entre si justo e contratado o presente instrumento, assinado em 03/11/2026, que se regerá pelas cláusulas a seguir."),
    ("h2", "CLÁUSULA 1 — DO OBJETO"),
    ("p", "1.1 O objeto deste contrato é a prestação de serviços de planejamento e execução de campanhas de marketing digital para a CONTRATANTE durante o período de vigência."),
    ("h2", "CLÁUSULA 2 — DAS OBRIGAÇÕES DA CONTRATADA"),
    ("p", "2.1 A CONTRATADA deverá entregar o plano de mídia do trimestre até 20/11/2026, mediante envio do documento em PDF à CONTRATANTE."),
    ("p", "2.2 A CONTRATADA deverá produzir 12 peças criativas para redes sociais até 10/12/2026, comprovado por meio de link da pasta compartilhada com os arquivos finais."),
    ("p", "2.3 A CONTRATADA obriga-se a configurar as campanhas de mídia paga em até 30 dias contados da assinatura, mediante relatório de configuração com capturas de tela."),
    ("p", "2.4 A CONTRATADA deverá apresentar o relatório mensal de desempenho até 05/01/2027, mediante envio do relatório com os indicadores acordados."),
    ("h2", "CLÁUSULA 3 — DAS OBRIGAÇÕES DA CONTRATANTE"),
    ("p", "3.1 A CONTRATANTE deverá fornecer acesso às contas de anúncios e ao material de marca até 10/11/2026, mediante concessão de acesso registrada por e-mail."),
    ("p", "3.2 A CONTRATANTE deverá aprovar ou solicitar ajustes nas peças criativas em até 5 (cinco) dias úteis após cada entrega."),
    ("p", "3.3 A CONTRATANTE obriga-se a efetuar o pagamento da primeira parcela de R$ 8.500,00 até 15/12/2026, mediante comprovante de transferência bancária."),
    ("h2", "CLÁUSULA 4 — DO VALOR"),
    ("p", "4.1 O valor total deste contrato é de R$ 25.500,00, pago em três parcelas mensais iguais."),
    ("h2", "CLÁUSULA 5 — DO FORO"),
    ("p", "5.1 Fica eleito o foro da Comarca da Capital do Estado do Rio de Janeiro para dirimir quaisquer dúvidas oriundas deste contrato."),
    ("p", "Rio de Janeiro, 03/11/2026."),
    ("p", "<i>Documento fictício gerado para testes acadêmicos. Empresas, CNPJs e valores não são reais.</i>"),
]

# Gabarito usado nos testes de extração.
GABARITO = [
    {"clausula": "2.1", "responsavel": "CONTRATADA", "prazo": "2026-11-20"},
    {"clausula": "2.2", "responsavel": "CONTRATADA", "prazo": "2026-12-10"},
    {"clausula": "2.3", "responsavel": "CONTRATADA", "prazo": "2026-12-03"},
    {"clausula": "2.4", "responsavel": "CONTRATADA", "prazo": "2027-01-05"},
    {"clausula": "3.1", "responsavel": "CONTRATANTE", "prazo": "2026-11-10"},
    {"clausula": "3.2", "responsavel": "CONTRATANTE", "prazo": None},
    {"clausula": "3.3", "responsavel": "CONTRATANTE", "prazo": "2026-12-15"},
]


def gerar(path: Path, texto=TEXTO) -> Path:
    st = getSampleStyleSheet()
    styles = {"h": st["Title"], "h2": st["Heading3"], "p": st["BodyText"]}
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=2.5 * cm, rightMargin=2.5 * cm)
    flow = []
    for kind, txt in texto:
        flow += [Paragraph(txt, styles[kind]), Spacer(1, 6)]
    doc.build(flow)
    return path


if __name__ == "__main__":
    print(gerar(SAMPLE_PATH))
