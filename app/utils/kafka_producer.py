import json
from datetime import datetime
from typing import Any, Optional

from aiokafka import AIOKafkaProducer
from loguru import logger

from app.settings import settings


class KafkaProducerService:
    """Service to handle Kafka message publishing."""

    _producer: Optional[AIOKafkaProducer] = None

    @classmethod
    async def start(cls) -> None:
        """Initialize and start the Kafka producer."""
        if cls._producer is None:
            try:
                cls._producer = AIOKafkaProducer(
                    bootstrap_servers=settings.kafka_bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v, default=str).encode(
                        "utf-8",
                    ),
                )
                await cls._producer.start()
                logger.info("Kafka producer started successfully.")
            except Exception as e:
                logger.error(f"Failed to start Kafka producer: {e}")
                cls._producer = None

    @classmethod
    async def stop(cls) -> None:
        """Stop the Kafka producer."""
        if cls._producer:
            await cls._producer.stop()
            logger.info("Kafka producer stopped.")
            cls._producer = None

    @classmethod
    async def publish_event(
        cls,
        event_type: str,
        data: dict[str, Any],
        topic: Optional[str] = None,
    ) -> None:
        """
        Publish an event to a Kafka topic.

        :param event_type: Type of event (e.g., USER_CREATED, USER_UPDATED).
        :param data: The actual data to publish (e.g., user profile row).
        :param topic: Kafka topic to publish to (defaults to settings).
        """
        if cls._producer is None:
            logger.warning("Kafka producer not initialized. Attempting to start...")
            await cls.start()

        if cls._producer:
            topic = topic or settings.kafka_topic_user_profile

            # Ensure data is a dictionary (handle Pydantic models)
            if hasattr(data, "model_dump"):
                data = data.model_dump()
            elif hasattr(data, "dict"): # Fallback for Pydantic v1
                data = data.dict()

            message = {
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data,
            }
            try:
                await cls._producer.send_and_wait(topic, message)
                logger.info(f"Published {event_type} event to topic {topic}")
            except Exception as e:
                logger.error(f"Failed to publish event to Kafka: {e}")
        else:
            logger.error("Kafka producer is not available. Event dropped.")
