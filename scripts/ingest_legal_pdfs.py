#!/usr/bin/env python
"""Script CLI para ingestão de PDFs jurídicos no sistema RAG.

Uso:
    python scripts/ingest_legal_pdfs.py <arquivo_ou_pasta> <category> <user_id>

Exemplos:
    python scripts/ingest_legal_pdfs.py data/concursos/legislacao/CP.pdf legal_legislacao 123abc
    python scripts/ingest_legal_pdfs.py data/concursos/legislacao legal_legislacao 123abc
"""

import asyncio
import sys
from pathlib import Path

import uvloop

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from src.config.settings import get_settings
from src.database.models import LEGAL_CATEGORIES
from src.knowledge.legal_pdf_ingestor import LegalPDFIngestor
from src.schemas.knowledge import IngestionResult, LegalPDFMetadata


async def ingest_single_file(
    file_path: Path, category: str, user_id: str, ingestor: LegalPDFIngestor
) -> IngestionResult:
    """Ingere um único arquivo PDF.

    Args:
        file_path: Caminho do PDF.
        category: Categoria legal.
        user_id: ID do usuário.

    Returns:
        Resultado da ingestão.
    """
    # Extrair metadados básicos do nome do arquivo
    fonte = file_path.stem
    area_direito = "geral"  # Pode ser refinado lendo o PDF

    metadata = LegalPDFMetadata(
        fonte=fonte,
        autor=None,
        area_direito=area_direito,
        ano_vigencia=None,
    )

    return await ingestor.ingest_pdf(file_path, user_id, category, metadata)


async def main():
    """Função principal do script."""
    if len(sys.argv) < 4:
        print(__doc__)
        print(f"\nCategorias disponíveis: {LEGAL_CATEGORIES}")
        sys.exit(1)

    target_path = Path(sys.argv[1])
    category = sys.argv[2]
    user_id = sys.argv[3]

    # Validações
    if category not in LEGAL_CATEGORIES:
        logger.error(f"Categoria inválida: {category}")
        logger.info(f"Use uma de: {LEGAL_CATEGORIES}")
        sys.exit(1)

    # Configura logger
    logger.remove()
    logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")

    # Configura ingestor
    settings = get_settings()

    # Cria pool de conexões
    import asyncpg

    db_pool = await asyncpg.create_pool(settings.SUPABASE_DB_URL)

    try:
        ingestor = LegalPDFIngestor(db_pool)

        # Processa arquivo ou pasta
        if target_path.is_file():
            if target_path.suffix.lower() != ".pdf":
                logger.error(f"Arquivo não é PDF: {target_path}")
                sys.exit(1)

            result = await ingest_single_file(target_path, category, user_id, ingestor)
            print(f"\n✅ {target_path.name}: {result.chunks_inserted}/{result.total_chunks} chunks inseridos")

        elif target_path.is_dir():
            # Processa todos os PDFs na pasta
            pdf_files = list(target_path.rglob("*.pdf"))

            if not pdf_files:
                logger.warning(f"Nenhum PDF encontrado em: {target_path}")
                sys.exit(0)

            print(f"\n📁 Processando {len(pdf_files)} PDFs de {target_path.name}:\n")

            for pdf_file in pdf_files:
                result = await ingest_single_file(pdf_file, category, user_id, ingestor)
                status = "✅" if result.chunks_inserted > 0 else "❌"
                print(f"{status} {pdf_file.name}: {result.chunks_inserted}/{result.total_chunks} chunks")

        else:
            logger.error(f"Caminho não encontrado: {target_path}")
            sys.exit(1)

    finally:
        await db_pool.close()
        logger.info("Conexões encerradas")


if __name__ == "__main__":
    uvloop.install()
    asyncio.run(main())
