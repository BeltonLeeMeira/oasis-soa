from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..esquemas import SaudeSaida
from ..infra.banco import banco_responde

router = APIRouter(tags=["Saúde"])


@router.get("/health", response_model=SaudeSaida, summary="Situação da API (usada no monitoramento e no teste de falha)")
def saude(request: Request):
    estado = request.app.state
    banco_ok = banco_responde(estado.engine)
    coletor = estado.coletor
    if not estado.config.mqtt_habilitado:
        mqtt = "desligado"
    else:
        mqtt = "conectado" if coletor.conectado else "desconectado"
    modelo = f"carregado ({estado.modelo.versao})" if estado.modelo.disponivel else f"indisponível: {estado.modelo.problema}"
    corpo = SaudeSaida(
        status="ok" if banco_ok else "degradado",
        banco="ok" if banco_ok else "sem resposta",
        mqtt=mqtt,
        modelo=modelo,
        leituras_mqtt_aceitas=coletor.aceitas,
        leituras_mqtt_rejeitadas=coletor.rejeitadas,
    )
    return JSONResponse(corpo.model_dump(by_alias=True), status_code=200 if banco_ok else 503)
