"""Jarvis: asistente de voz para Termux (Android).

Flujo: micrófono (termux-api) -> ffmpeg (WAV) -> SpeechRecognition (voz a texto)
       -> Groq (LLM) -> gTTS (texto a voz) -> mpv (reproducción)
"""

import os
import re
import shutil
import subprocess
import sys
import time

import speech_recognition as sr
from groq import Groq
from gtts import gTTS

# ---------------------------------------------------------------------------
# Configuración (ajusta a tu gusto)
# ---------------------------------------------------------------------------
MODELO = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
IDIOMA_STT = "es-MX"  # Reconocimiento de voz: "es-MX", "es-ES", "es-AR"...
IDIOMA_TTS = "es"  # Idioma de la voz de gTTS
ACENTO_TTS = "com.mx"  # Acento de gTTS: "com.mx" (México), "es" (España), "com" (por defecto)
SEGUNDOS_GRABACION = 5
COMANDOS_SALIDA = ("adiós", "adios", "descansa")
PROMPT_SISTEMA = (
    "Eres JARVIS, un asistente de IA muy eficiente, educado y conciso. "
    "Responde siempre en español, de forma breve y sin markdown ni emojis."
)

# Archivos temporales (están en .gitignore)
RUTA_M4A = "input.m4a"
RUTA_WAV = "input.wav"
RUTA_MP3 = "respuesta.mp3"

# Programas externos que necesita Jarvis (el primero viene en el paquete termux-api)
HERRAMIENTAS = ("termux-microphone-record", "ffmpeg", "mpv")


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def ejecutar(comando, timeout=30):
    """Ejecuta un comando sin shell. Devuelve el resultado, o None si falla o expira."""
    try:
        return subprocess.run(
            comando,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None


def verificar_herramientas():
    faltantes = [h for h in HERRAMIENTAS if shutil.which(h) is None]
    if faltantes:
        sys.exit(
            f"Faltan herramientas: {', '.join(faltantes)}\n"
            "Instálalas con: pkg install termux-api ffmpeg mpv"
        )


def crear_cliente():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        sys.exit(
            "Falta la variable de entorno GROQ_API_KEY.\n"
            'Configúrala con: export GROQ_API_KEY="tu_api_key"'
        )
    return Groq(api_key=api_key, timeout=30.0)


def limpiar_texto(texto):
    """Quita markdown y emojis para que la voz no los lea en voz alta."""
    texto = re.sub(r"[\U00010000-\U0010FFFF]", "", texto)
    texto = re.sub(r"[*#`_~>|]", "", texto)
    return re.sub(r"\s+", " ", texto).strip()


# ---------------------------------------------------------------------------
# Salida de voz
# ---------------------------------------------------------------------------
def hablar(texto):
    print(f"JARVIS: {texto}")
    texto_voz = limpiar_texto(texto)
    if not texto_voz:
        return
    try:
        gTTS(text=texto_voz, lang=IDIOMA_TTS, tld=ACENTO_TTS).save(RUTA_MP3)
    except Exception as e:
        print(f"[Aviso] No pude generar la voz (¿sin internet?): {e}")
        return
    ejecutar(
        ["mpv", "--no-video", "--no-terminal", "--really-quiet", RUTA_MP3],
        timeout=300,
    )


# ---------------------------------------------------------------------------
# Entrada de voz
# ---------------------------------------------------------------------------
def grabar_audio():
    """Graba con termux-api y convierte a WAV (16 kHz, mono). True si todo salió bien."""
    for ruta in (RUTA_M4A, RUTA_WAV):
        if os.path.exists(ruta):
            os.remove(ruta)

    print(f"Escuchando (habla ahora por {SEGUNDOS_GRABACION} segundos)...")
    ejecutar(
        ["termux-microphone-record", "-f", RUTA_M4A, "-l", str(SEGUNDOS_GRABACION)],
        timeout=15,
    )
    time.sleep(SEGUNDOS_GRABACION + 1)

    # Cierra la grabación para que el archivo quede completo en disco.
    ejecutar(["termux-microphone-record", "-q"], timeout=15)
    time.sleep(1)

    if not os.path.exists(RUTA_M4A) or os.path.getsize(RUTA_M4A) == 0:
        print(
            "[Aviso] No se grabó audio. Revisa que la app Termux:API esté instalada "
            "y tenga permiso de micrófono."
        )
        return False

    conversion = ejecutar(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", RUTA_M4A,
         "-ar", "16000", "-ac", "1", RUTA_WAV],
        timeout=30,
    )
    if conversion is None or conversion.returncode != 0 or not os.path.exists(RUTA_WAV):
        print("[Aviso] ffmpeg no pudo convertir el audio a WAV.")
        return False
    return True


def transcribir():
    """Devuelve el texto reconocido, o None si no se pudo entender."""
    reconocedor = sr.Recognizer()
    try:
        with sr.AudioFile(RUTA_WAV) as fuente:
            audio = reconocedor.record(fuente)
        texto = reconocedor.recognize_google(audio, language=IDIOMA_STT)
    except sr.UnknownValueError:
        print("[Aviso] No se detectó voz clara.")
        return None
    except sr.RequestError as e:
        print(f"[Aviso] No pude contactar el reconocimiento de voz (¿sin internet?): {e}")
        return None
    except Exception as e:
        print(f"[Aviso] Error al leer el audio: {e}")
        return None
    print(f"Tú (voz): {texto}")
    return texto


def escuchar():
    """Intenta por voz; si falla, permite escribir la orden."""
    texto = transcribir() if grabar_audio() else None
    if texto:
        return texto
    orden = input("Escribe tu orden para JARVIS (o presiona Enter para reintentar): ")
    return orden.strip() or None


# ---------------------------------------------------------------------------
# Inteligencia (Groq)
# ---------------------------------------------------------------------------
def consultar_groq(cliente, orden):
    """Devuelve la respuesta del modelo, o None si la consulta falla."""
    try:
        respuesta = cliente.chat.completions.create(
            messages=[
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": orden},
            ],
            model=MODELO,
        )
        return respuesta.choices[0].message.content or ""
    except Exception as e:
        print(f"[Error] Falló la consulta a Groq: {e}")
        return None


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------
def main():
    verificar_herramientas()
    cliente = crear_cliente()

    print("JARVIS iniciado...")
    try:
        hablar("Sistemas en línea, señor. ¿En qué puedo ayudarle?")

        while True:
            orden = escuchar()
            if not orden:
                continue

            if any(palabra in orden.lower() for palabra in COMANDOS_SALIDA):
                hablar("Apagando sistemas. Buenas noches, señor.")
                break

            respuesta = consultar_groq(cliente, orden)
            if respuesta:
                hablar(respuesta)
            else:
                hablar("Lo siento, señor. No pude obtener una respuesta.")
    except KeyboardInterrupt:
        print("\nJARVIS detenido.")


if __name__ == "__main__":
    main()
