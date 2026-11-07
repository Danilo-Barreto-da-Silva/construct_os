import time
from django.conf import settings
from pydantic import BaseModel, Field

class LaudoIA(BaseModel):
    etapa_identificada: str = Field(description="Etapa atual identificada no vídeo")
    percentual_sugerido: int = Field(description="Percentual de 0 a 100")
    status_iso_sugerido: str = Field(description="CONFORME, PENDENTE ou NAO_CONFORME")
    resumo_tecnico: str = Field(description="Resumo do que foi visto no vídeo")

def analisar_video_obra(caminho_video: str, apto_numero: str, requisito_iso: str) -> LaudoIA:
    api_key = getattr(settings, "GEMINI_API_KEY", "MODO_SIMULACAO")

    # Modo Simulação para você testar sem chave de API
    if not api_key or api_key == "MODO_SIMULACAO":
        return LaudoIA(
            etapa_identificada="Reboco Interno e Contrapiso",
            percentual_sugerido=85,
            status_iso_sugerido="CONFORME",
            resumo_tecnico=f"[Diagnóstico IA - Apto {apto_numero}] Alvenaria 100%, caixas 4x2 chumbadas e reboco desempenado aprovado segundo {requisito_iso}."
        )

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    video_upload = client.files.upload(file=caminho_video)
    while video_upload.state.name == "PROCESSING":
        time.sleep(2)
        video_upload = client.files.get(name=video_upload.name)

    prompt = f"""
    Você é um engenheiro auditor da qualidade ISO 9001.
    Analise o vídeo do Apartamento {apto_numero} e avalie o requisito {requisito_iso}.
    Pesos: Alvenaria (30%), Instalações (20%), Reboco/Contrapiso (25%), Revestimento/Gesso (15%), Pintura (10%).
    Retorne a etapa, o percentual (0 a 100), o status (CONFORME, PENDENTE ou NAO_CONFORME) e o resumo técnico.
    """

    resposta = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[video_upload, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=LaudoIA,
            temperature=0.1,
        ),
    )
    client.files.delete(name=video_upload.name)
    return LaudoIA.model_validate_json(resposta.text)