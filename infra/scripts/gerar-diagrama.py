#!/usr/bin/env python3
"""Gera docs/pm04/arquitetura.png (diagrama da arquitetura). Requer matplotlib."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(12, 7.2), dpi=170)
ax.set_xlim(0, 120); ax.set_ylim(0, 72); ax.axis("off")
C = dict(vpc="#eef4fa", app="#ffffff", db="#ffffff", edge="#1f4e79", svc="#dbe8f5", db_svc="#e3f1e1",
         ext="#fff4e0", txt="#1b1b1b", sg="#c0392b", gray="#666666")

def box(x, y, w, h, fc, ec=C["edge"], lw=1.2, ls="-", r=1.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec, lw=lw, ls=ls))

def text(x, y, s, size=9, weight="normal", color=C["txt"], ha="center"):
    ax.text(x, y, s, fontsize=size, weight=weight, color=color, ha=ha, va="center", family="DejaVu Sans")

def arrow(p1, p2, label=None, color=C["edge"], ls="-", lx=0, ly=0, rad=0.0):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=12, lw=1.4, color=color, ls=ls,
                                 connectionstyle=f"arc3,rad={rad}"))
    if label:
        text((p1[0] + p2[0]) / 2 + lx, (p1[1] + p2[1]) / 2 + ly, label, 8, color=color)

# visitantes
box(46, 64, 28, 6, C["ext"], ec="#d39b2a")
text(60, 67, "Visitantes (navegador / celular)", 9.5, "bold")

# VPC
box(2, 14, 116, 46, C["vpc"], lw=1.5, ls="--")
text(5, 57.5, "AWS us-east-1 · VPC 10.20.0.0/16", 9, "bold", ha="left")

# app VM
box(5, 17, 52, 37, C["app"])
text(31, 51.5, "vm-pm04-app · t3.micro · sub-rede 10.20.1.0/24", 8.5, "bold")
text(31, 48.6, "Elastic IP → https://<ip>.sslip.io", 8, color=C["gray"])
for (y, t1, t2) in [(40, "Caddy  :443 / :80", "HTTPS automático (Let's Encrypt)"),
                    (31, "Nginx  :80  (frontend)", "React + proxy /todos, /todos/:id, /health"),
                    (22, "API Express  :5000", "/health testa a conexão com o banco")]:
    box(10, y, 42, 6.5, C["svc"])
    text(31, y + 4.3, t1, 9, "bold"); text(31, y + 1.8, t2, 7.5, color=C["gray"])
arrow((31, 40), (31, 37.6)); arrow((31, 31), (31, 28.6))
text(31, 18.8, "Docker · rede todo-net · restart unless-stopped · healthchecks", 7.2, color=C["gray"])

# db VM
box(63, 17, 52, 37, C["db"])
text(89, 51.5, "vm-pm04-db · t3.micro · sub-rede 10.20.2.0/24", 8.5, "bold")
text(89, 48.6, "VM exclusiva do banco · sem entrada da internet", 8, color=C["gray"])
box(68, 36, 42, 9, C["db_svc"], ec="#2e7d32")
text(89, 42.3, "MongoDB 7.0 (autenticado)", 9, "bold")
text(89, 39.6, "porta 27017 publicada só no IP privado", 7.5, color=C["gray"])
text(89, 37.4, "usuário todo_app: readWrite em todo-app", 7.5, color=C["gray"])
box(68, 25.5, 42, 7, "#f7f7f7", ec="#888888")
text(89, 30.3, "EBS gp3 dedicado → /data/mongo", 8.5, "bold")
text(89, 27.6, "dados persistem a recriações", 7.5, color=C["gray"])
box(68, 19, 42, 5, "#f7f7f7", ec="#888888")
text(89, 21.5, "cron 6/6 h: mongodump → S3 (IAM role)", 8)
arrow((89, 36), (89, 32.6), color="#2e7d32")

# arrows
arrow((52, 64), (48, 54.2), "HTTPS 443", lx=-8, ly=1.5)
arrow((52, 25.3), (68, 40.5), "rede privada\nTCP 27017", color="#2e7d32", lx=1, ly=-3.5, rad=-0.15)
arrow((84, 64), (95, 54.2), "porta 27017 bloqueada\n(Security Group)", color=C["sg"], ls="--", lx=19, ly=3.6)
ax.plot([93.4, 96.6], [57.5, 60.7], color=C["sg"], lw=2.2); ax.plot([93.4, 96.6], [60.7, 57.5], color=C["sg"], lw=2.2)

# bottom services
items = [(2, "GitHub Actions", "app-ci · infra · ops · destroy"),
         (31.5, "Terraform state", "S3 pm04-tfstate (versionado + lock)"),
         (61, "Backups", "S3 pm04-backups (retenção 30 dias)"),
         (90.5, "Imagens", "GHCR todo-app-backend / -frontend")]
for x, t1, t2 in items:
    box(x, 2, 27.5, 9, "#ffffff", ec="#888888")
    text(x + 13.75, 7.8, t1, 9, "bold"); text(x + 13.75, 4.6, t2, 7.3, color=C["gray"])
arrow((15.75, 11), (15.75, 17), color=C["gray"], ls=":")
text(19, 12.6, "Terraform → Ansible (SSH via runner / bastion)", 7.3, color=C["gray"], ha="left")

plt.savefig(str(__import__("pathlib").Path(__file__).resolve().parents[2] / "docs/pm04/arquitetura.png"), bbox_inches="tight", facecolor="white")
