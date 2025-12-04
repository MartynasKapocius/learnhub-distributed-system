import logging
import json
import pika

logger = logging.getLogger(__name__)


class MessagePublisher:
    """
    Service to publish events to RabbitMQ message queue
    Implements communication pattern for async events
    """

    def __init__(self, rabbitmq_url: str):
        self.rabbitmq_url = rabbitmq_url
        self.exchange_name = 'quiz_events'
        self.routing_key = 'quiz.submitted'

    def publish_quiz_event(self, event_data):
        """
        Publish quiz submission event to message queue

        Args:
            event_data: Dictionary containing event information

        Returns:
            bool: True if published successfully, False otherwise
        """
        connection = None
        try:
            # Establish connection to RabbitMQ
            connection = pika.BlockingConnection(
                pika.URLParameters(self.rabbitmq_url)
            )
            channel = connection.channel()

            # Declare idempotent exchange
            channel.exchange_declare(
                exchange=self.exchange_name,
                exchange_type='topic',
                durable=True
            )

            # Publish message
            message = json.dumps(event_data)
            channel.basic_publish(
                exchange=self.exchange_name,
                routing_key=self.routing_key,
                body=message,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )

            logger.info(f"Event published successfully: {self.routing_key}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish event: {str(e)}")
            return False

        finally:
            if connection and not connection.is_closed:
                connection.close()

    def publish_quiz_updated_event(self, event_data):
        """
        Publish quiz updated event to message queue

        Args:
            event_data: Dictionary containing event information

        Returns:
            bool: True if published successfully, False otherwise
        """
        connection = None
        try:
            connection = pika.BlockingConnection(
                pika.URLParameters(self.rabbitmq_url)
            )
            channel = connection.channel()

            # Declare exchange
            channel.exchange_declare(
                exchange=self.exchange_name,
                exchange_type='topic',
                durable=True
            )

            # Publish message
            message = json.dumps(event_data)
            channel.basic_publish(
                exchange=self.exchange_name,
                routing_key='quiz.updated',
                body=message,
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type='application/json'
                )
            )

            logger.info("Quiz updated event published successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to publish quiz updated event: {str(e)}")
            return False

        finally:
            if connection and not connection.is_closed:
                connection.close()