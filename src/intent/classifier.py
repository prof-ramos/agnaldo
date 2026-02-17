"""Intent classifier using sentence transformers."""

import asyncio
from pathlib import Path
from typing import Any, Literal

import numpy as np
from loguru import logger
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from .models import IntentCategory, IntentResult


class IntentClassifier:
    """Classify user intents using semantic similarity."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        dataset_path: str | None = None,
    ) -> None:
        """Initialize the classifier.

        Args:
            model_name: HuggingFace model name for sentence transformers.
            dataset_path: Path to intent dataset directory.
        """
        self.model_name = model_name
        self.dataset_path = Path(dataset_path or "data/intent_dataset")
        self.model: SentenceTransformer | None = None
        self._warmup_done = False
        self._intent_embeddings: dict[IntentCategory, np.ndarray] = {}
        self._intent_examples: dict[IntentCategory, list[str]] = {}

    async def initialize(self) -> None:
        """Initialize the model and perform warm-up.

        This loads the model and performs a dummy inference to warm up
        the model for subsequent classifications.
        """
        if self._warmup_done:
            return

        logger.info(f"Initializing IntentClassifier with model: {self.model_name}")

        # Load model in thread pool to avoid blocking
        loop = asyncio.get_running_loop()
        self.model = await loop.run_in_executor(
            None, lambda: SentenceTransformer(self.model_name)
        )

        # Warm-up inference
        await loop.run_in_executor(None, lambda: self.model.encode(["warmup"]))

        # Load intent examples from dataset
        await self._load_intent_examples()

        # Pre-compute embeddings for each intent category
        await self._compute_intent_embeddings()

        self._warmup_done = True
        logger.info("IntentClassifier warm-up complete")

    async def _load_intent_examples(self) -> None:
        """Load intent examples from dataset."""
        import json

        intents_path = self.dataset_path / "intents.json"
        if not intents_path.exists():
            logger.warning(f"No intents.json found at {intents_path}, using defaults")
            self._intent_examples = self._get_default_examples()
            return

        loop = asyncio.get_running_loop()
        content = await loop.run_in_executor(None, lambda: intents_path.read_text())
        intents_data = json.loads(content)

        for intent_name, examples in intents_data.items():
            try:
                category = IntentCategory(intent_name)
                self._intent_examples[category] = examples
            except ValueError:
                logger.warning(f"Unknown intent category: {intent_name}")

        if not self._intent_examples:
            self._intent_examples = self._get_default_examples()

    def _get_default_examples(self) -> dict[IntentCategory, list[str]]:
        """Get default examples when no dataset is available."""
        return {
            IntentCategory.KNOWLEDGE_QUERY: [
                "What do you know about",
                "Tell me about",
                "Explain",
                "Information on",
            ],
            IntentCategory.DEFINITION: [
                "What is",
                "Define",
                "Meaning of",
            ],
            IntentCategory.GREETING: ["hi", "hello", "hey", "greetings"],
            IntentCategory.HELP: ["help", "assist", "support", "how to use"],
            IntentCategory.STATUS: ["status", "health", "are you working"],
        }

    async def _compute_intent_embeddings(self) -> None:
        """Pre-compute embeddings for each intent category."""
        if self.model is None:
            raise RuntimeError("Model not initialized")

        loop = asyncio.get_running_loop()

        for category, examples in self._intent_examples.items():
            embeddings = await loop.run_in_executor(
                None, lambda examples=examples: self.model.encode(examples, convert_to_numpy=True)
            )
            # Use mean embedding as category centroid
            self._intent_embeddings[category] = np.mean(embeddings, axis=0)

    async def classify(
        self, text: str, threshold: float = 0.3
    ) -> IntentResult:
        """Classify the intent of a text message.

        Args:
            text: Input text to classify.
            threshold: Minimum confidence threshold for classification.

        Returns:
            IntentResult with detected intent and confidence.

        Raises:
            RuntimeError: If model is not initialized.
        """
        if not self._warmup_done:
            await self.initialize()

        if self.model is None:
            raise RuntimeError("Model not initialized")

        loop = asyncio.get_running_loop()

        # Encode input text
        text_embedding = await loop.run_in_executor(
            None, lambda: self.model.encode([text], convert_to_numpy=True)
        )

        # Compute similarities with each intent
        best_intent = IntentCategory.HELP
        best_confidence = 0.0

        for category, centroid in self._intent_embeddings.items():
            similarity = cosine_similarity(text_embedding, centroid.reshape(1, -1))[0][0]
            if similarity > best_confidence:
                best_confidence = similarity
                best_intent = category

        # Extract basic entities (could be extended with NER)
        entities = await self._extract_entities(text, best_intent)

        return IntentResult(
            intent=best_intent,
            confidence=float(best_confidence),
            entities=entities,
            raw_text=text,
        )

    async def _extract_entities(
        self, text: str, intent: IntentCategory
    ) -> dict[str, Any]:
        """Extract entities from text based on intent.

        This is a basic implementation. For production, consider using
        a dedicated NER model or LLM-based extraction.

        Args:
            text: Input text.
            intent: Detected intent category.

        Returns:
            Dictionary of extracted entities.
        """
        entities: dict[str, Any] = {"text": text}

        # Basic keyword extraction
        words = text.lower().split()
        entities["word_count"] = len(words)

        # Intent-specific extraction
        if intent == IntentCategory.KNOWLEDGE_QUERY:
            # Extract potential topic (words after "about", "on", etc.)
            for keyword in ["about", "regarding", "concerning", "on"]:
                if keyword in words:
                    idx = words.index(keyword)
                    if idx + 1 < len(words):
                        entities["topic"] = " ".join(words[idx + 1 :])
                        break

        elif intent == IntentCategory.GRAPH_QUERY:
            # Extract node names (basic pattern)
            import re
            patterns = re.findall(r'\b[A-Z][a-z]+\b', text)
            if patterns:
                entities["potential_nodes"] = patterns

        return entities

    async def classify_batch(
        self, texts: list[str], threshold: float = 0.3
    ) -> list[IntentResult]:
        """Classify multiple texts in batch for efficiency.

        Args:
            texts: List of input texts.
            threshold: Minimum confidence threshold.

        Returns:
            List of IntentResults.
        """
        if not self._warmup_done:
            await self.initialize()

        if self.model is None:
            raise RuntimeError("Model not initialized")

        loop = asyncio.get_running_loop()

        # Batch encode all texts
        embeddings = await loop.run_in_executor(
            None, lambda: self.model.encode(texts, convert_to_numpy=True)
        )

        results = []
        for text, embedding in zip(texts, embeddings):
            best_intent = IntentCategory.HELP
            best_confidence = 0.0

            for category, centroid in self._intent_embeddings.items():
                similarity = cosine_similarity(
                    embedding.reshape(1, -1), centroid.reshape(1, -1)
                )[0][0]
                if similarity > best_confidence:
                    best_confidence = similarity
                    best_intent = category

            entities = await self._extract_entities(text, best_intent)

            results.append(
                IntentResult(
                    intent=best_intent,
                    confidence=float(best_confidence),
                    entities=entities,
                    raw_text=text,
                )
            )

        return results

    def is_ready(self) -> bool:
        """Check if classifier is ready for classification."""
        return self._warmup_done and self.model is not None
