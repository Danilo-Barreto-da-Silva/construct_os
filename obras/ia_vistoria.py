"""Gemini propõe observações; não certifica serviços nem aprova FVS."""
import time
from typing import Literal

from django.conf import settings
from pydantic import BaseModel, Field


class LaudoIA(BaseModel):
    etapa_identificada: str = Field(min_length=3, max_length=100)
    percentual_sugerido: int = Field(ge=0, le=100)
    status_iso_sugerido: Literal['CONFORME', 'PENDENTE', 'NAO_CONFORME']
    resumo_tecnico: str = Field(min_length=10, max_length=2500)


def analisar_video_obra(caminho_video: str, apto_numero: str, requisito_iso: str) -> LaudoIA:
    api_key = getattr(settings, 'GEMINI_API_KEY', 'MODO_SIMULACAO')
    if not api_key or api_key == 'MODO_SIMULACAO':
        raise RuntimeError('Configure GEMINI_API_KEY para utilizar análise real.')

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    nome_arquivo_remoto = None
    try:
        upload = client.files.upload(file=caminho_video)
        nome_arquivo_remoto = upload.name
        limite = time.monotonic() + 120
        while upload.state.name == 'PROCESSING':
            if time.monotonic() >= limite:
                raise TimeoutError('O vídeo demorou mais que o prazo de processamento.')
            time.sleep(2)
            upload = client.files.get(name=nome_arquivo_remoto)

        if upload.state.name != 'ACTIVE':
            raise RuntimeError('O vídeo não pôde ser processado pelo serviço de IA.')

        prompt = f"""
        Assuma o papel de assistente de inspeção de qualidade, não de certificador.
        Analise SOMENTE o que é visualmente perceptível no vídeo do apartamento
        {apto_numero}; requisito informado: {requisito_iso}.
        Quando não for possível verificar um serviço, informe a limitação;
        não presuma que foi executado ou aprovado.
        Referência ilustrativa para distribuição do avanço físico:
        alvenaria 30%, instalações 20%, reboco/contrapiso 25%,
        revestimento/gesso 15%, pintura 10%. Não é cronograma ponderado da obra.
        Sugira uma etapa, percentual (0–100), status
        (CONFORME, PENDENTE ou NAO_CONFORME) e resumo técnico conciso.
        O resultado é sugestão provisória sujeita à validação de responsável técnico.
        """

        resposta = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[upload, prompt],
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                response_schema=LaudoIA,
                temperature=0.1,
            ),
        )
        if not resposta.text:
            raise RuntimeError('O serviço de IA não retornou um resultado estruturado.')
        return LaudoIA.model_validate_json(resposta.text)
    finally:
        if nome_arquivo_remoto:
            try:
                client.files.delete(name=nome_arquivo_remoto)
            except Exception:
                # O serviço remoto pode estar indisponível; cabe monitorar esse caso
                # antes de processar vídeos de clientes reais.
                pass
