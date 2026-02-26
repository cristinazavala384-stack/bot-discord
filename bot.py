import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import os

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

CANAL_ACTIVADOR_ID = 1476409404415807599
LIMITE_DEFAULT = 5

salas = {}
# {voice_id: {"owner": user_id, "text": text_channel_id}}

# ---------------- PANEL ----------------

class Panel(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def verificar_dueno(self, interaction):
        user = interaction.user

        if not user.voice:
            await interaction.response.send_message("❌ No estás en una sala.", ephemeral=True)
            return None

        canal = user.voice.channel

        if canal.id in salas and salas[canal.id]["owner"] == user.id:
            return canal

        await interaction.response.send_message("❌ Solo el dueño puede usar esto.", ephemeral=True)
        return None

    @discord.ui.button(label="🔒 Privada", style=discord.ButtonStyle.gray)
    async def privada(self, interaction: discord.Interaction, button: Button):
        canal = await self.verificar_dueno(interaction)
        if canal:
            await canal.set_permissions(interaction.guild.default_role, connect=False)
            await interaction.response.send_message("🔒 Sala privada activada.", ephemeral=True)

    @discord.ui.button(label="✏️ Renombrar", style=discord.ButtonStyle.blurple)
    async def renombrar(self, interaction: discord.Interaction, button: Button):
        canal = await self.verificar_dueno(interaction)
        if canal:
            await interaction.response.send_modal(RenombrarModal(canal))

    @discord.ui.button(label="⚡ Límite", style=discord.ButtonStyle.green)
    async def limite(self, interaction: discord.Interaction, button: Button):
        canal = await self.verificar_dueno(interaction)
        if canal:
            await interaction.response.send_modal(LimiteModal(canal))

    @discord.ui.button(label="🗑️ Eliminar", style=discord.ButtonStyle.red)
    async def eliminar(self, interaction: discord.Interaction, button: Button):
        canal = await self.verificar_dueno(interaction)
        if canal:
            text_id = salas[canal.id]["text"]
            text_channel = bot.get_channel(text_id)

            if text_channel:
                await text_channel.delete()

            await canal.delete()
            salas.pop(canal.id)

            await interaction.response.send_message("🗑️ Sala eliminada.", ephemeral=True)

# ---------------- MODALES ----------------

class RenombrarModal(Modal):
    def __init__(self, canal):
        super().__init__(title="Renombrar Sala")
        self.canal = canal
        self.nombre = TextInput(label="Nuevo nombre")
        self.add_item(self.nombre)

    async def on_submit(self, interaction: discord.Interaction):
        await self.canal.edit(name=self.nombre.value)
        await interaction.response.send_message("✅ Nombre cambiado.", ephemeral=True)

class LimiteModal(Modal):
    def __init__(self, canal):
        super().__init__(title="Cambiar Límite")
        self.canal = canal
        self.numero = TextInput(label="Nuevo límite (solo número)")
        self.add_item(self.numero)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            num = int(self.numero.value)
            await self.canal.edit(user_limit=num)
            await interaction.response.send_message("✅ Límite actualizado.", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Debes escribir solo números.", ephemeral=True)

# ---------------- BOT READY ----------------

@bot.event
async def on_ready():
    bot.add_view(Panel())
    print(f"Bot conectado como {bot.user}")

# ---------------- EVENTO VOICE ----------------

@bot.event
async def on_voice_state_update(member, before, after):

    # CREAR SALA
    if after.channel is not None and after.channel.id == CANAL_ACTIVADOR_ID:

        guild = after.channel.guild
        nombre = f"{member.display_name}-sala"

        voice = await guild.create_voice_channel(
            name=nombre,
            category=after.channel.category,
            user_limit=LIMITE_DEFAULT
        )

        await member.move_to(voice)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        text = await guild.create_text_channel(
            name=f"{member.display_name}-panel",
            category=after.channel.category,
            overwrites=overwrites
        )

        salas[voice.id] = {
            "owner": member.id,
            "text": text.id
        }

        await text.send(
            f"🎉 Bienvenido {member.mention}\nAdministra tu sala con los botones:",
            view=Panel()
        )

    # ELIMINAR SI QUEDA VACÍA
    if before.channel is not None and before.channel.id in salas:

        canal = before.channel

        if len(canal.members) == 0:

            text_id = salas[canal.id]["text"]
            text_channel = bot.get_channel(text_id)

            if text_channel:
                await text_channel.delete()

            await canal.delete()
            salas.pop(canal.id)

# ---------------- INICIAR BOT ----------------

TOKEN = os.getenv("TOKEN")

if TOKEN is None:
    print("❌ No se encontró la variable TOKEN.")
else:
    bot.run(TOKEN)