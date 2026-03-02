"""Streaming ingestion package for fraud transactions."""
from .kinesis_consumer import KinesisConsumer
from .lambda_handler import lambda_handler

__all__ = ['KinesisConsumer', 'lambda_handler']
