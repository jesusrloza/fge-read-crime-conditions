import os
import json
import pandas as pd


def extract_condition_from_prompt(prompt_file_path):
    """Extrae la condición del archivo de prompt."""
    try:
        with open(prompt_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Buscar la línea que contiene "Condición:"
            for line in content.split('\n'):
                if line.startswith('Condición:'):
                    return line.replace('Condición:', '').strip()
    except Exception as e:
        print(f"Error leyendo {prompt_file_path}: {e}")
    return ""


def main():
    responses_dir = 'output/responses'
    prompts_dir = 'output/prompts'
    output_file = 'output/summary/results.xlsx'

    # Crear directorio si no existe
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    data = []

    # Iterar sobre todos los archivos JSON en responses
    for filename in os.listdir(responses_dir):
        if filename.endswith('_response.json'):
            filepath = os.path.join(responses_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    response_data = json.load(f)

                success = response_data.get('success', False)
                prompt_file = response_data.get('prompt_file', '')

                if success:
                    # Extraer datos del response
                    resp = response_data.get('response', {})
                    nuc = resp.get('nuc', '')
                    condition = resp.get('condition', '')
                    meets_condition = resp.get('meets_condition', '')
                    confidence = resp.get('confidence', '')
                    rationale_short = resp.get('rationale_short', '')
                    hechos = resp.get('hechos', '')
                    ollama_success = 1
                else:
                    # Extraer nuc del nombre del archivo
                    # prompt_XXXXX_response.json -> XXXXX
                    nuc = filename.split('_')[1]
                    # Extraer condition del prompt
                    prompt_path = os.path.join(prompts_dir, prompt_file)
                    condition = extract_condition_from_prompt(prompt_path)
                    meets_condition = ''
                    confidence = ''
                    rationale_short = ''
                    hechos = ''
                    ollama_success = 0

                data.append({
                    'nuc': nuc,
                    'condition': condition,
                    'meets_condition': meets_condition,
                    'confidence': confidence,
                    'rationale_short': rationale_short,
                    'hechos': hechos,
                    'ollama_success': ollama_success
                })

            except Exception as e:
                print(f"Error procesando {filename}: {e}")

    # Crear DataFrame y escribir a Excel
    df = pd.DataFrame(data)
    df.to_excel(output_file, index=False)
    print(f"Resumen escrito en {output_file}")


if __name__ == '__main__':
    main()
