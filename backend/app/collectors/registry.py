from app.collectors.base import BaseCollector
from app.collectors.esfera import EsferaCollector
from app.collectors.livelo import LiveloCollector

_COLLECTORS: dict[str, BaseCollector] = {
    "livelo": LiveloCollector(),
    "esfera": EsferaCollector(),
}


def get_collector(source: str) -> BaseCollector:
    try:
        return _COLLECTORS[source]
    except KeyError as exc:
        raise KeyError(f"Collector desconhecido: {source}") from exc


def list_collectors() -> tuple[str, ...]:
    return tuple(_COLLECTORS)
