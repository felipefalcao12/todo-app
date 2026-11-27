#!/usr/bin/env python3
"""Gera o PDF de entrega do PM04 a partir da documentação e das evidências.

Uso:
    python3 infra/scripts/gerar-entrega-pdf.py [--integrantes "Nome 1;Nome 2;Nome 3"] [--saida PM04-entrega.pdf]

- Conteúdo técnico: docs/pm04/arquitetura.md (mesmo texto do repositório).
- Evidências: imagens em evidencias/ com os nomes do roteiro de testes
  (docs/pm04/roteiro-testes.md). Imagem ausente vira um quadro "pendente".
Dependência: reportlab (pip install reportlab).
"""
import argparse
import datetime as dt
import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, Preformatted,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parents[2]
REPO_URL = "https://github.com/felipefalcao12/todo-app"

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
if (FONT_DIR / "DejaVuSans.ttf").exists():
    pdfmetrics.registerFont(TTFont("Sans", str(FONT_DIR / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("Sans-Bold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("Mono", str(FONT_DIR / "DejaVuSansMono.ttf")))
    from reportlab.pdfbase.pdfmetrics import registerFontFamily
    registerFontFamily("Sans", normal="Sans", bold="Sans-Bold", italic="Sans", boldItalic="Sans-Bold")
    BASE, BOLD, MONO = "Sans", "Sans-Bold", "Mono"
else:
    BASE, BOLD, MONO = "Helvetica", "Helvetica-Bold", "Courier"

ACCENT = colors.HexColor("#1f4e79")
ss = getSampleStyleSheet()
S = {
    "body": ParagraphStyle("body", parent=ss["BodyText"], fontName=BASE, fontSize=10, leading=14),
    "cell": ParagraphStyle("cell", fontName=BASE, fontSize=8, leading=10),
    "cellh": ParagraphStyle("cellh", fontName=BOLD, fontSize=8, leading=10, textColor=colors.white),
    "h1": ParagraphStyle("h1", fontName=BOLD, fontSize=16, leading=20, textColor=ACCENT, spaceBefore=6, spaceAfter=8, keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName=BOLD, fontSize=13, leading=17, textColor=ACCENT, spaceBefore=10, spaceAfter=6, keepWithNext=1),
    "h3": ParagraphStyle("h3", fontName=BOLD, fontSize=11, leading=14, spaceBefore=8, spaceAfter=4, keepWithNext=1),
    "bullet": ParagraphStyle("bullet", fontName=BASE, fontSize=10, leading=14, leftIndent=14, bulletIndent=4),
    "quote": ParagraphStyle("quote", fontName=BASE, fontSize=9.5, leading=13, leftIndent=10,
                            textColor=colors.HexColor("#444444"), backColor=colors.HexColor("#f2f6fa"),
                            borderPadding=5, spaceBefore=4, spaceAfter=6),
    "code": ParagraphStyle("code", fontName=MONO, fontSize=6.6, leading=8.2, backColor=colors.HexColor("#f5f5f5"),
                           borderPadding=4, spaceBefore=4, spaceAfter=6),
    "title": ParagraphStyle("title", fontName=BOLD, fontSize=24, leading=30, alignment=TA_CENTER, textColor=ACCENT),
    "subtitle": ParagraphStyle("subtitle", fontName=BASE, fontSize=13, leading=18, alignment=TA_CENTER),
    "center": ParagraphStyle("center", fontName=BASE, fontSize=10, leading=14, alignment=TA_CENTER),
    "caption": ParagraphStyle("caption", fontName=BASE, fontSize=8.5, leading=11, alignment=TA_CENTER,
                              textColor=colors.HexColor("#555555"), spaceAfter=8),
}
CONTENT_WIDTH = A4[0] - 3.6 * cm


def inline(text: str) -> str:
    """Markdown inline -> marcação do reportlab."""
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", rf'<font face="{MONO}" size="8.5">\1</font>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<i>\1</i>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                  lambda m: (f'<link href="{m.group(2)}" color="#1f4e79"><u>{m.group(1)}</u></link>'
                             if m.group(2).startswith("http") else m.group(1)), text)
    return text


def table(rows, col_widths=None):
    header, *body = rows
    data = [[Paragraph(inline(c), S["cellh"]) for c in header]]
    data += [[Paragraph(inline(c), S["cell"]) for c in r] for r in body]
    n = len(header)
    if col_widths is None:
        lens = [max(len(r[i]) if i < len(r) else 0 for r in rows) for i in range(n)]
        lens = [min(max(x, 12), 70) for x in lens]
        total = sum(lens)
        col_widths = [CONTENT_WIDTH * x / total for x in lens]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f6fa")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b8c7d6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return [t, Spacer(1, 6)]


def markdown(md: str, skip_title=True, base_dir=ROOT / "docs/pm04"):
    """Conversor simples de Markdown (títulos, parágrafos, listas, tabelas, código, citações)."""
    out, i = [], 0
    # Blocos indentados dentro de listas numeradas são tratados como blocos normais
    lines = [ln.strip() if re.match(r"^\s+(\||```|> )", ln) else ln for ln in md.splitlines()]
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            out.append(Preformatted("\n".join(lines[i + 1:j]), S["code"]))
            i = j + 1
            continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            out += table(rows)
            continue
        img = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)", line)
        if img:
            path = (base_dir / img.group(2)).resolve()
            iw, ih = ImageReader(str(path)).getSize()
            out += [Image(str(path), width=CONTENT_WIDTH, height=ih * CONTENT_WIDTH / iw),
                    Paragraph(inline(img.group(1)), S["caption"])]
            i += 1
            continue
        m = re.match(r"^(#{1,3}) (.*)", line)
        if m:
            level = len(m.group(1))
            if not (level == 1 and skip_title):
                out.append(Paragraph(inline(m.group(2)), S[f"h{level}"]))
        elif line.startswith("- "):
            out.append(Paragraph(inline(line[2:]), S["bullet"], bulletText="•"))
        elif line.startswith("> "):
            out.append(Paragraph(inline(line[2:]), S["quote"]))
        elif line.strip():
            para = [line]
            while i + 1 < len(lines) and lines[i + 1].strip() and not re.match(r"^(#|\||- |> |```|!\[)", lines[i + 1]):
                i += 1
                para.append(lines[i])
            out.append(Paragraph(inline(" ".join(para)), S["body"]))
            out.append(Spacer(1, 4))
        i += 1
    return out


EVIDENCIAS = [
    ("Preparação: segredos e pipeline da aplicação", [
        ("00-secrets", "Segredos cadastrados no GitHub Actions (somente nomes; valores criptografados)"),
        ("01-app-ci-v1.0.0", "Pipeline da aplicação: testes da API com MongoDB real e do frontend; imagens v1.0.0 publicadas no GHCR"),
        ("02-app-ci-v1.1.0", "Pipeline da aplicação: imagens v1.1.0 publicadas (usadas no Cenário 2)"),
        ("03-actions-execucoes", "Histórico de execuções: todas as mudanças operadas pelas pipelines"),
    ]),
    ("Cenário 1 — Criação inicial (Infra #2)", [
        ("10-c1-parametros", "Parâmetros informados na execução manual da pipeline"),
        ("11-c1-terraform-plan", "Terraform plan/apply: 24 recursos criados (VPC, sub-redes, security groups, 2 VMs, EBS, Elastic IP, IAM)"),
        ("12-c1-ansible-docker", "Ansible preparando as VMs do zero: repositório oficial e instalação do Docker nas duas VMs"),
        ("14-c1-ansible-https", "Ansible: contêineres em execução, proxy HTTPS e verificação pública /health e /todos"),
        ("13-c1-inventario-recap", "Inventário das 2 VMs (ACE-02), URL pública e PLAY RECAP sem falhas"),
    ]),
    ("Cenário 2 — Atualização do ambiente (Infra #4 e #8)", [
        ("24-c2-atualizacoes-so-pacotes", "Ansible (update_os=true): 17 atualizações do SO aplicadas em cada VM e novos pacotes extras"),
        ("23-c2-app-v1.0.0-para-v1.1.0", "Ansible: atualização controlada da aplicação v1.0.0 → v1.1.0 com health check"),
        ("20-c2-terraform-inplace", "Terraform: tipo da VM alterado no lugar (0 to add, 1 to change, 0 to destroy)"),
        ("22-c2-mongo-7.0.15", "Ansible: MongoDB 7.0.14 → 7.0.15 recriado mantendo o volume de dados"),
        ("21-c2-recap", "Resultado do Cenário 2: inventário atualizado e PLAY RECAP sem falhas"),
        ("25-c2-app-v1.1.0-dados-preservados", "Aplicação pública na v1.1.0 com as tarefas preservadas após as atualizações (ACE-04/05)"),
    ]),
    ("Cenário 3 — Reexecução sem alterações (Infra #10)", [
        ("30-c3-terraform-nochanges", "Terraform: No changes — infraestrutura igual ao código"),
        ("31-c3-ansible-idempotente", "Ansible idempotente: changed=0 nas duas VMs"),
    ]),
    ("Operação, segurança e recuperação", [
        ("15-app-health", "Saúde pública: API conectada ao MongoDB, versão implantada"),
        ("16-ace03-isolamento", "Isolamento (ACE-03): API→MongoDB pela rede privada e porta 27017 bloqueada a partir da internet"),
        ("17-ace07-backup", "Backup do MongoDB enviado ao S3 (ACE-07)"),
        ("19-ace07-backup-automatico-cron", "Backup automatizado: cron executou sozinho às 06:00 e enviou ao S3 (ACE-07)"),
        ("18-ace07-restore-test", "Restauração testada em ambiente isolado: contagem confere (ACE-07)"),
        ("40-ops-health", "Rotina de saúde: contêineres, API→banco e URL pública (ACE-08)"),
        ("41-ops-restart", "Reinício controlado dos serviços: banco primeiro, depois API e frontend; URL pública 200 (ACE-05/08)"),
        ("42-ops-reset-demo", "Preparação intencional da lista para a apresentação, com backup antes (ACE-10)"),
    ]),
]


def find_image(stem):
    for ext in (".png", ".jpg", ".jpeg"):
        p = ROOT / "evidencias" / f"{stem}{ext}"
        if p.exists():
            return p
    return None


def evidence_block(stem, caption, n):
    img_path = find_image(stem)
    cap = Paragraph(f"<b>Figura {n}</b> — {inline(caption)}", S["caption"])
    if img_path:
        iw, ih = ImageReader(str(img_path)).getSize()
        w = min(CONTENT_WIDTH, iw)
        h = ih * w / iw
        max_h = 17 * cm
        if h > max_h:
            w, h = w * max_h / h, max_h
        return KeepTogether([Image(str(img_path), width=w, height=h), Spacer(1, 3), cap]), True
    box = Table([[Paragraph(f"Evidência pendente: <font face='{MONO}'>evidencias/{stem}.png</font>", S["center"])]],
                colWidths=[CONTENT_WIDTH], rowHeights=[2.2 * cm])
    box.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#c0392b")),
                             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                             ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fdf2f0"))]))
    return KeepTogether([box, Spacer(1, 3), cap]), False


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont(BASE, 8)
    canvas.setFillColor(colors.HexColor("#777777"))
    canvas.drawString(1.8 * cm, 1.2 * cm, "PM04 · Projeto Final — Automação de infraestrutura com Terraform, Ansible e CI/CD")
    canvas.drawRightString(A4[0] - 1.8 * cm, 1.2 * cm, f"Página {doc.page}")
    canvas.restoreState()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--integrantes", default="", help='Nomes separados por ";"')
    ap.add_argument("--saida", default=str(ROOT / "PM04-entrega.pdf"))
    args = ap.parse_args()

    story = [Spacer(1, 3.5 * cm),
             Paragraph("PM04 · Projeto Final", S["title"]), Spacer(1, 6),
             Paragraph("Automação de infraestrutura com Terraform, Ansible e CI/CD", S["subtitle"]),
             Spacer(1, 8),
             Paragraph("ToDo App — implantação e operação em nuvem para a Feira de Profissões", S["subtitle"]),
             Spacer(1, 2.2 * cm)]

    nomes = [n.strip() for n in args.integrantes.split(";") if n.strip()]
    linhas = [["Integrantes", "<br/>".join(html.escape(n) for n in nomes) if nomes else
               "_______________________________<br/>_______________________________<br/>_______________________________"],
              ["Repositório Git", f'<link href="{REPO_URL}" color="#1f4e79"><u>{REPO_URL}</u></link>'],
              ["Provedor", "AWS (us-east-1) · Terraform · Ansible · GitHub Actions"],
              ["Data", dt.date.today().strftime("%d/%m/%Y")]]
    t = Table([[Paragraph(f"<b>{a}</b>", S["body"]), Paragraph(b, S["body"])] for a, b in linhas],
              colWidths=[4 * cm, CONTENT_WIDTH - 4 * cm])
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor("#b8c7d6")),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 6),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story += [t, PageBreak()]

    arq = (ROOT / "docs/pm04/arquitetura.md").read_text(encoding="utf-8")
    story += markdown(arq)

    resultados = (ROOT / "docs/pm04/resultados.md").read_text(encoding="utf-8")
    story += [PageBreak(), Paragraph("11. Resultados dos testes", S["h2"])]
    story += markdown(resultados)

    story += [PageBreak(), Paragraph("12. Evidências de execução", S["h2"]),
              Paragraph("Capturas das execuções reais na AWS, feitas exclusivamente pelas pipelines do GitHub "
                        "Actions (aba Actions do repositório), sem acesso manual aos servidores.", S["body"]),
              Spacer(1, 6)]
    n, faltando = 0, []
    for secao, itens in EVIDENCIAS:
        story.append(Paragraph(secao, S["h3"]))
        for stem, cap in itens:
            n += 1
            block, ok = evidence_block(stem, cap, n)
            story.append(block)
            if not ok:
                faltando.append(stem)

    roteiro = (ROOT / "docs/pm04/roteiro-testes.md").read_text(encoding="utf-8")
    val = roteiro[roteiro.index("## Validação da demanda"):]
    story += [Paragraph("13. Validação da demanda — critérios de aceite × evidências", S["h2"])]
    story += markdown(val.split("\n", 1)[1])

    checklist = (ROOT / "docs/pm04/checklist-entrega.md").read_text(encoding="utf-8")
    story += [PageBreak(), Paragraph("14. Checklist da entrega", S["h2"])]
    story += markdown(checklist)

    manual = (ROOT / "docs/pm04/manual-operacao.md").read_text(encoding="utf-8")
    story += [PageBreak(), Paragraph("Anexo — Manual de operação para os alunos", S["h2"])]
    story += markdown(manual)

    doc = SimpleDocTemplate(args.saida, pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
                            topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                            title="PM04 - Projeto Final - ToDo App", author="Equipe PM04")
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"PDF gerado: {args.saida}")
    if faltando:
        print(f"Evidências pendentes ({len(faltando)}): {', '.join(faltando)}")


if __name__ == "__main__":
    main()
