import discord
from discord.ext import commands, tasks
import requests
from bs4 import BeautifulSoup
import json
import os

TOKEN = os.getenv("DISCORD_TOKEN")
CANAL_ID = int(os.getenv("CANAL_ID"))
CANAL_MORTES_ID = int(os.getenv("CANAL_MORTES_ID"))

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

personagens_file = "personagens.json"
mensagem_id_file = "mensagem_id.txt"
mortes_file = "mortes.json"
config_file = "config.json"

def carregar_personagens():
    if not os.path.exists(personagens_file):
        return []
    with open(personagens_file, "r") as f:
        return json.load(f)

def salvar_personagens(personagens):
    with open(personagens_file, "w") as f:
        json.dump(personagens, f)

def carregar_mortes():
    if not os.path.exists(mortes_file):
        return {}
    with open(mortes_file, "r") as f:
        return json.load(f)

def salvar_mortes(mortes):
    with open(mortes_file, "w") as f:
        json.dump(mortes, f)

def carregar_config():
    if not os.path.exists(config_file):
        return {"verificar_mortes": False}
    with open(config_file, "r") as f:
        return json.load(f)

def salvar_config(config):
    with open(config_file, "w") as f:
        json.dump(config, f)

def verificar_status(nome):
    url = f"https://miracle74.com/?subtopic=characters&name={nome}"
    resposta = requests.get(url)
    soup = BeautifulSoup(resposta.text, "html.parser")

    if "Currently Offline" in soup.text:
        return "🔴 Offline"
    elif "Currently Online" in soup.text:
        return "🟢 Online"
    else:
        return "❓ Não encontrado"

def verificar_ultima_morte(nome):
    url = f"https://miracle74.com/?subtopic=characters&name={nome}"
    resposta = requests.get(url)
    soup = BeautifulSoup(resposta.text, "html.parser")

    tabela = soup.find("table", {"class": "Table3"})
    if not tabela:
        return None

    textos = tabela.get_text(separator="\n").split("\n")
    mortes = [linha.strip() for linha in textos if "Died at Level" in linha]
    return mortes[0] if mortes else None

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    checar_status.start()

@tasks.loop(minutes=3)
async def checar_status():
    personagens = carregar_personagens()
    mortes_anteriores = carregar_mortes()
    config = carregar_config()
    status_msg = "**📋 Status dos personagens monitorados:**\n\n"
    canal_status = bot.get_channel(CANAL_ID)
    canal_mortes = bot.get_channel(CANAL_MORTES_ID)

    for nome in personagens:
        status = verificar_status(nome)
        status_msg += f"**{nome}**: {status}\n"

        if config.get("verificar_mortes"):
            ultima_morte = verificar_ultima_morte(nome)
            if ultima_morte and mortes_anteriores.get(nome) != ultima_morte:
                mortes_anteriores[nome] = ultima_morte
                await canal_mortes.send(f"☠️ **{nome} morreu!**\n{ultima_morte}")

    salvar_mortes(mortes_anteriores)

    if not os.path.exists(mensagem_id_file):
        mensagem = await canal_status.send(status_msg)
        with open(mensagem_id_file, "w") as f:
            f.write(str(mensagem.id))
    else:
        with open(mensagem_id_file, "r") as f:
            msg_id = int(f.read())
        try:
            mensagem = await canal_status.fetch_message(msg_id)
            await mensagem.edit(content=status_msg)
        except:
            mensagem = await canal_status.send(status_msg)
            with open(mensagem_id_file, "w") as f:
                f.write(str(mensagem.id))

@bot.command()
async def add(ctx, *, nome):
    nome = nome.strip()
    personagens = carregar_personagens()
    if nome in personagens:
        await ctx.send(f"O personagem **{nome}** já está na lista.")
    else:
        personagens.append(nome)
        salvar_personagens(personagens)
        await ctx.send(f"Personagem **{nome}** adicionado com sucesso!")

@bot.command()
async def remove(ctx, *, nome):
    nome = nome.strip()
    personagens = carregar_personagens()
    if nome not in personagens:
        await ctx.send(f"O personagem **{nome}** não está na lista.")
    else:
        personagens.remove(nome)
        salvar_personagens(personagens)
        await ctx.send(f"Personagem **{nome}** removido com sucesso!")

@bot.command()
async def listar(ctx):
    personagens = carregar_personagens()
    if personagens:
        await ctx.send("**👥 Personagens monitorados:**\n" + "\n".join(personagens))
    else:
        await ctx.send("Nenhum personagem está sendo monitorado no momento.")

@bot.command()
async def togglemortes(ctx):
    config = carregar_config()
    config["verificar_mortes"] = not config.get("verificar_mortes", False)
    salvar_config(config)
    estado = "ativado" if config["verificar_mortes"] else "desativado"
    await ctx.send(f"☠️ Monitoramento de mortes foi **{estado}**.")

bot.run(TOKEN)
