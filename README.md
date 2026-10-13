# Jarvis

Asistente personal de voz que se ejecuta en Android dentro de **Termux**. Captura tu voz con el micrófono del teléfono, la transcribe, consulta un modelo de lenguaje a través de la API de **Groq** y te responde hablando.

```text
Micrófono → termux-microphone-record → ffmpeg → SpeechRecognition → Groq → gTTS → mpv
```

## Cómo funciona

| Etapa | Herramienta |
|---|---|
| Captura de audio | `termux-microphone-record` (Termux:API) |
| Conversión a WAV (16 kHz, mono) | `ffmpeg` |
| Voz a texto | `SpeechRecognition` (reconocimiento de Google) |
| Respuesta del asistente | API de Groq (`groq`) |
| Texto a voz | `gTTS` |
| Reproducción | `mpv` |

## Requisitos

- Android con [Termux](https://f-droid.org/packages/com.termux/) y [Termux:API](https://f-droid.org/packages/com.termux.api/). Instala ambas desde la misma fuente (se recomienda F-Droid); si mezclas fuentes, Termux:API no funcionará.
- Permiso de **micrófono** concedido a la app Termux:API.
- Una API key de Groq, que se genera en <https://console.groq.com/keys>.
- Conexión a internet.

## Instalación

```bash
pkg update && pkg upgrade
pkg install python git ffmpeg mpv termux-api
git clone https://github.com/CarlLince/jarvis.git
cd jarvis
pip install -r requirements.txt
```

## Configuración

Jarvis lee la clave de la variable de entorno `GROQ_API_KEY`. **No la escribas en el código ni la subas al repositorio.**

```bash
echo 'export GROQ_API_KEY="tu_api_key"' >> ~/.bashrc
source ~/.bashrc
```

Opciones:

- `GROQ_MODEL`: modelo a usar (por defecto `openai/gpt-oss-20b`).
- Idioma de reconocimiento, idioma y acento de la voz, y duración de la grabación se ajustan en las constantes al inicio de `jarvis.py`.

## Uso

```bash
python jarvis.py
```

1. Cuando aparezca `Escuchando...`, habla durante 5 segundos.
2. Jarvis responde en voz alta.
3. Di **"adiós"** o **"descansa"** para apagarlo (o presiona `Ctrl+C`).

Si no detecta voz clara, te permite escribir la orden por teclado.

## Solución de problemas

| Síntoma | Qué revisar |
|---|---|
| `Faltan herramientas` | Ejecuta `pkg install termux-api ffmpeg mpv`. |
| `No se grabó audio` | Instala la app Termux:API y concédele permiso de micrófono. Prueba: `termux-microphone-record -f prueba.m4a -l 3`. |
| `No pude contactar el reconocimiento de voz` | Sin internet, o límite temporal del servicio gratuito de Google. |
| `Falló la consulta a Groq` | Revisa `GROQ_API_KEY`, tu conexión y que el modelo de `GROQ_MODEL` siga disponible. |
| No se escucha la respuesta | Revisa el volumen del teléfono y prueba `mpv --no-video respuesta.mp3`. |

## Privacidad y límites

- Tu audio se envía a Google para transcribirlo, tu texto a Groq para generar la respuesta y esa respuesta a Google (gTTS) para convertirla en voz.
- El reconocimiento de voz usa el servicio gratuito de Google, que puede limitar las solicitudes.
- La grabación es de duración fija y Jarvis no conserva memoria entre preguntas.

## Estructura del repositorio

```text
jarvis/
├── jarvis.py
├── requirements.txt
├── .gitignore
└── README.md
```
