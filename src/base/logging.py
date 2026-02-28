"""Logger estruturado para Agnaldo.

Fornece logging em formato JSON para fácil parsing e análise.
Compatível com OpenTelemetry e sistemas de observabilidade.

Uso:
    from src.base import get_logger

    logger = get_logger(__name__)
    logger.info("Operation completed", user_id="user123", duration_ms=45)
"""

import json
import sys
from datetime import datetime, timezone
from typing import Any

from loguru import logger


class JSONSink:
    """Sink customizado para output JSON estruturado."""

    def __init__(self, file_path: str | None = None):
        """Inicializa o sink.

        Args:
            file_path: Caminho do arquivo de log. Se None, usa stdout.
        """
        self.file_path = file_path
        self._file = None
        if file_path:
            self._file = open(file_path, "a", encoding="utf-8")

    def write(self, message: str) -> None:
        """Escreve mensagem formatada como JSON."""
        try:
            record = json.loads(message.strip())
            output = json.dumps(record, ensure_ascii=False, default=str)

            if self._file:
                self._file.write(output + "\n")
                self._file.flush()
            else:
                print(output, file=sys.stdout)
        except (json.JSONDecodeError, KeyError):
            # Fallback para texto simples se não for JSON válido
            if self._file:
                self._file.write(message)
            else:
                print(message, file=sys.stdout, end="")

    def flush(self) -> None:
        """Flush do buffer."""
        if self._file:
            self._file.flush()

    def close(self) -> None:
        """Fecha o arquivo se estiver aberto."""
        if self._file:
            self._file.close()


def format_record(record: dict[str, Any]) -> str:
    """Formata um record de log como JSON estruturado.

    Args:
        record: Record do loguru com informações do log.

    Returns:
        String JSON formatada.
    """
    log_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": record["level"].name,
        "logger": record["name"],
        "message": record["message"],
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
    }

    # Adicionar dados extras do record
    if record.get("extra"):
        extra = record["extra"]
        # Mover campos conhecidos para nível superior
        for field in ["user_id", "operation", "duration_ms", "error", "context"]:
            if field in extra:
                log_data[field] = extra.pop(field)

        # Restante vai em extra
        if extra:
            log_data["extra"] = extra

    # Adicionar exception se existir
    if record.get("exception"):
        log_data["exception"] = {
            "type": record["exception"].type.__name__ if record["exception"].type else None,
            "value": str(record["exception"].value) if record["exception"].value else None,
            "traceback": record["exception"].traceback if record["exception"].traceback else None,
        }

    return json.dumps(log_data, ensure_ascii=False, default=str)


def setup_logging(
    level: str = "INFO",
    json_output: bool = True,
    log_file: str | None = None,
    enable_colors: bool = False,
) -> None:
    """Configura o sistema de logging do Agnaldo.

    Args:
        level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_output: Se True, usa formato JSON estruturado.
        log_file: Caminho do arquivo de log. Se None, só usa stdout.
        enable_colors: Se True, habilita cores no output (não usar com JSON).
    """
    # Remover handlers padrão
    logger.remove()

    # Configurar formato
    if json_output:
        # Formato JSON estruturado
        logger.add(
            JSONSink(log_file),
            format="{message}",
            level=level,
            serialize=False,
        )
    else:
        # Formato legível para desenvolvimento
        format_str = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
        if not enable_colors:
            format_str = format_str.replace("<green>", "").replace("</green>", "")
            format_str = format_str.replace("<level>", "").replace("</level>", "")
            format_str = format_str.replace("<cyan>", "").replace("</cyan>", "")

        logger.add(
            sys.stdout,
            format=format_str,
            level=level,
            colorize=enable_colors,
        )

        if log_file:
            logger.add(
                log_file,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
                level=level,
                rotation="10 MB",
                retention="7 days",
                compression="gz",
            )

    logger.info("Logging configurado", level=level, json_output=json_output)


def get_logger(name: str | None = None) -> Any:
    """Retorna um logger configurado.

    Args:
        name: Nome do logger (geralmente __name__).

    Returns:
        Logger configurado.

    Example:
        >>> from src.base import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("User logged in", user_id="123", ip="192.168.1.1")
    """
    if name:
        return logger.bind(name=name)
    return logger


# Configuração padrão na importação
# Pode ser sobrescrita chamando setup_logging()
_default_configured = False


def _ensure_default_logging() -> None:
    """Garante que o logging foi configurado pelo menos uma vez."""
    global _default_configured
    if not _default_configured:
        import os

        level = os.environ.get("AGNALDO_LOG_LEVEL", "INFO")
        json_output = os.environ.get("AGNALDO_LOG_JSON", "true").lower() == "true"
        setup_logging(level=level, json_output=json_output)
        _default_configured = True


_ensure_default_logging()
