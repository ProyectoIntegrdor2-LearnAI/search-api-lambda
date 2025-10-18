"""Cliente ligero para AWS Bedrock (Titan Text Embeddings)."""

from __future__ import annotations

import json
import logging
import os
import random
import time
from functools import lru_cache
from typing import List

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
import numpy as np

logger = logging.getLogger(__name__)


class BedrockClient:
    def __init__(self) -> None:
        model = os.getenv("EMBEDDING_MODEL", "amazon.titan-embed-text-v2:0")
        region = os.getenv("AWS_REGION", "us-east-2")

        self._embedding_model = model
        self._expected_dim = int(os.getenv("EMBEDDING_DIM", "1024"))
        config = Config(
            region_name=region,
            retries={"max_attempts": 3, "mode": "standard"},
            read_timeout=25,
            connect_timeout=5,
        )
        self._client = boto3.client("bedrock-runtime", config=config)

    def generate_embedding(self, text: str) -> List[float]:
        return self._cached_embedding(text)

    @lru_cache(maxsize=512)
    def _cached_embedding(self, text: str) -> List[float]:
        return self._invoke_with_retry(self._invoke_embedding, text)

    def _invoke_with_retry(self, func, *args):
        last_error: Exception | None = None
        for attempt in range(4):
            try:
                return func(*args)
            except (ClientError, BotoCoreError) as exc:
                last_error = exc
                sleep_for = (2 ** attempt) * random.uniform(0.75, 1.25)
                logger.warning(
                    "Bedrock request failed (attempt %s): %s. Retrying in %.2fs",
                    attempt + 1,
                    exc,
                    sleep_for,
                )
                time.sleep(sleep_for)
        assert last_error is not None
        raise last_error

    def _invoke_embedding(self, text: str) -> List[float]:
        payload = json.dumps({"inputText": text})
        response = self._client.invoke_model(
            modelId=self._embedding_model,
            contentType="application/json",
            accept="application/json",
            body=payload,
        )
        data = json.loads(response["body"].read())
        embedding = data.get("embedding")
        if not embedding:
            raise ValueError("Respuesta de Bedrock sin campo 'embedding'")
        if len(embedding) != self._expected_dim:
            raise ValueError(
                f"Dimensión inesperada: {len(embedding)} (esperada {self._expected_dim})"
            )
        vector = np.asarray(embedding, dtype=np.float32)
        norm = float(np.linalg.norm(vector))
        if norm == 0.0:
            raise ValueError("La norma del embedding es cero")
        return (vector / norm).tolist()


_client_instance: BedrockClient | None = None


def get_bedrock_client() -> BedrockClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = BedrockClient()
    return _client_instance
