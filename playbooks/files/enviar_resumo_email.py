#!/usr/bin/env python3
"""Envia por e-mail o resumo da execução agendada de SNMPv3/trap nos switches."""
import json
import os
import smtplib
import socket
from datetime import datetime
from email.message import EmailMessage

resumo = json.loads(os.environ["SNMPV3_RESUMO"])
destinos = [e.strip() for e in os.environ["SNMPV3_EMAIL_PARA"].split(",") if e.strip()]
remetente = os.environ["SNMPV3_EMAIL_DE"]
smtp_host = os.environ.get("SNMPV3_SMTP_HOST", "localhost")
smtp_port = int(os.environ.get("SNMPV3_SMTP_PORT", "25"))
ambiente = os.environ.get("SNMPV3_AMBIENTE", "production")
log_file = os.environ.get("SNMPV3_LOG_FILE", "")


def lista(titulo, itens):
    linhas = [f"{titulo} ({len(itens)}):"]
    linhas += [f"  - {i}" for i in itens] or ["  (nenhum)"]
    return "\n".join(linhas)


aplicados = len(resumo["aplicado"])
falhas = len(resumo["falhou"])
assunto = f"[SNMPv3 switches] {aplicados} configurado(s) agora"
if falhas:
    assunto += f", {falhas} com falha"
assunto += f" ({ambiente}, {datetime.now():%d/%m/%Y})"

corpo = "\n\n".join([
    f"Execução agendada da automação SNMPv3/trap ({ambiente}) em "
    f"{datetime.now():%d/%m/%Y %H:%M}, control host {socket.gethostname()}.",
    "\n".join([
        f"Configurados agora (não tinham SNMPv3/trap): {aplicados}",
        f"Faltando config, não aplicados (modo só verificar): {len(resumo['pendente'])}",
        f"Já estavam configurados (pulados): {len(resumo['pulado'])}",
        f"Falharam: {falhas}",
        f"Fabricante não reconhecido: {len(resumo['desconhecido'])}",
        f"Sem SSH (IP vazio ou porta 22 fechada): {len(resumo['sem_ssh'])}",
    ]),
    lista("Configurados agora, com o que faltava", resumo["aplicado"]),
    lista("Faltando config, não aplicados (modo só verificar)", resumo["pendente"]),
    lista("Falharam", resumo["falhou"]),
    lista("Fabricante não reconhecido (não foram alterados)", resumo["desconhecido"]),
    f"Log completo no control host: {log_file}" if log_file else "",
])

msg = EmailMessage()
msg["Subject"] = assunto
msg["From"] = remetente
msg["To"] = ", ".join(destinos)
msg.set_content(corpo)

with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
    smtp.send_message(msg, from_addr=remetente, to_addrs=destinos)
print(f"E-mail enviado para {', '.join(destinos)}: {assunto}")
