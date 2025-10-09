# fge-read-crime-conditions

Herramienta analítica interna para la Fiscalía General del Estado de Michoacán que permite evaluar en lote expedientes delictivos contra condiciones específicas solicitadas, utilizando LLMs alojados en Ollama y generando estadísticas estructuradas junto con reportes ejecutivos.

## Por qué existe este proyecto

Los equipos de procuración de justicia suelen necesitar respuestas rápidas a preguntas de investigación hechas a la medida (por ejemplo, «¿Qué casos de secuestro mencionan bloqueos carreteros?»). Este repositorio acelera ese flujo de trabajo al combinar:

- **Generación de prompts** para grandes volúmenes de narrativas delictivas tomadas desde Excel.
- **Evaluación con LLMs** usando modelos autoalojados en Ollama (como `gpt-oss`).
- **Agregación de resultados** que conserva los insumos originales y produce resúmenes auditables.

La arquitectura favorece la transparencia (prompts en markdown y respuestas en JSON) y puede adaptarse a nuevas condiciones legales con un esfuerzo mínimo.

## Funcionalidades

- Generador de prompts determinista con plantillas, delimitadores JSON y deduplicación por NUC.
- Cliente de Ollama con reintentos configurables, salvaguardas de parseo JSON y exportación de resúmenes.
- Conservación automática del contexto narrativo original en las respuestas posteriores.
- Exportador de resúmenes que convierte las decisiones del LLM en tablas analíticas listas para Excel.
- Estructura "src" con módulos auxiliares tipados, fáciles de extender y probar.

## Estructura del proyecto

```
├── src/
│   ├── 0_update_prompt_config.py  # Sincroniza la configuración del prompt desde archivos de referencia
│   ├── 1_generate_prompts.py      # Punto de entrada para crear prompts
│   ├── 2_process_ollama.py        # Procesa prompts en lote mediante Ollama
│   ├── 3_create_summary.py        # Extrae el resumen en Excel
│   └── utils/
│       ├── prompt_builder.py      # Funciones auxiliares compartidas para plantillas de prompts
│       └── ollama_client.py       # Orquestación de chat con Ollama
├── prompt/
│   ├── data/                    # Entradas de Excel excluidas del control de versiones (Git) por defecto
│   ├── reference/               # Archivos fuente editables con la condición y la plantilla
│   └── prompt_config.json       # Configuración serializada consumida por la herramienta
├── output/                      # Prompts generados, respuestas y exportaciones de resúmenes
├── requirements.txt             # Lista fija de dependencias (refleja pyproject)
├── pyproject.toml               # Empaquetado y metadatos para publicación/instalación
└── README.md
```

## Primeros pasos

### Requisitos previos

- Python 3.10 o superior (pandas ≥ 2.3 requiere Python 3.10+).
- [Ollama](https://ollama.com/) instalado localmente con el modelo de tu preferencia (por defecto `gpt-oss:latest`).
- Git LFS si planeas almacenar archivos de Excel o salidas de Ollama dentro del repositorio.

### Instalación

1. Clona el repositorio y entra a la carpeta del proyecto.
2. Crea y activa un entorno virtual:

   ```bash
   python -m venv .venv

   source .venv/bin/activate            # macOS / Linux
   source .venv/Scripts/activate        # Windows Git Bash / MSYS terminals (p. ej., con Starship)
   .venv\\Scripts\\activate             # Windows PowerShell
   ```

3. Instala el paquete en modo editable (recomendado para personas colaboradoras):

   ```bash
   pip install -e .
   ```

4. Verifica la instalación ejecutando alguno de los scripts numerados (ver más abajo), por ejemplo:

   ```bash
   python src/1_generate_prompts.py
   ```

### Insumos de configuración

Los activos configurables principales se encuentran en el directorio `prompt/`:

| Archivo                          | Propósito                                                                                                                |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `prompt/prompt_config.json`      | Configuración unificada con la condición, la plantilla del prompt, el nombre del modelo y un esquema opcional de salida. |
| `prompt/reference/condition.txt` | Referencia en texto plano para la condición de investigación vigente.                                                    |
| `prompt/reference/template.txt`  | Cuerpo del prompt con los marcadores `{{CONDITION}}`, `{{RECORD_JSON}}` y `{{OUTPUT_SCHEMA}}`.                           |
| `prompt/data/sample.xlsx`        | Ejemplo de entrada en Excel; reemplázalo con extractos específicos de cada campaña (ignorado por git).                   |

Sustituye `sample.xlsx` o replica la carpeta para cada campaña.

## Flujos desde la línea de comandos

Una vez instalado el paquete, ejecuta los scripts numerados directamente con Python:

| Comando                                | Descripción                                                                                                               |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `python src/0_update_prompt_config.py` | Actualiza `prompt/prompt_config.json` a partir de los archivos en `prompt/reference/`.                                    |
| `python src/1_generate_prompts.py`     | Lee `prompt/data/sample.xlsx`, deduplica por NUC y genera prompts en markdown dentro de `output/prompts/`.                |
| `python src/2_process_ollama.py`       | Envía los prompts generados a Ollama, escribe respuestas JSON en `output/responses/` y construye un resumen de ejecución. |
| `python src/3_create_summary.py`       | Recorre las respuestas y produce una hoja analítica en `output/summary/results.xlsx`.                                     |

Cada script acepta los valores predeterminados que se muestran en el código. Para rutas específicas de una campaña, duplica los scripts o añade análisis de argumentos (ver la sección «Mejoras futuras»).

## Ejecución del pipeline

1. **Preparar datos**: coloca tu fuente de Excel en `prompt/data/sample.xlsx` y confirma que `prompt_config.json` describa la condición y plantilla deseadas.
2. **Actualizar la configuración del prompt** (opcional, ejecútalo cuando cambie `prompt/reference`):

   ```bash
   python src/0_update_prompt_config.py
   ```

3. **Generar prompts**:

   ```bash
   python src/1_generate_prompts.py
   ```

4. **Procesar con Ollama** (asegúrate de que el daemon de Ollama esté en ejecución):

   ```bash
   ollama run gpt-oss:latest --help   # comprobación opcional
   python src/2_process_ollama.py
   ```

5. **Exportar resumen**:

   ```bash
   python src/3_create_summary.py
   ```

Los resultados se guardan en `output/` y reutilizan archivos existentes cuando se vuelve a ejecutar. Las peticiones fallidas se reintentan automáticamente; revisa los archivos `_response.json` para obtener el contexto completo.

## Manejo de datos y privacidad

- Nunca hagas commit de expedientes originales que contengan datos personales. El `.gitignore` raíz ya excluye `output/` y `prompt/data/` para mantener esos materiales fuera del control de versiones.
- Si compartes públicamente plantillas de prompts, redacta la redacción sensible de la condición y los ejemplos.
- El repositorio mantiene los prompts y respuestas en formato legible (markdown/JSON) para facilitar las auditorías.

## Contribuciones

1. Haz fork y crea una rama desde `main`
2. Ejecuta `pip install -e .`
3. Aplica formato y pruebas antes de abrir un PR.
4. Usa mensajes de commit convencionales cuando sea posible (`feat:`, `fix:`, etc.).

Por favor abre un issue para cambios arquitectónicos o mejoras.
