import logging
import requests
import time

logger = logging.getLogger(__name__)


class CourseValidator:
    """
    Service to validate course existence by calling Course Service
    Implements retry logic with timeout for resilience
    """

    def __init__(self, course_service_url: str):
        self.course_service_url = course_service_url
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        self.timeout = 5  # seconds

    def validate_course_exists(self, course_id: str):
        """
        Validate that a course exists by calling the Course Service
        Implements retry logic for resilience

        Args:
            course_id: The ID of the course to validate

        Returns:
            bool: True if course exists, False otherwise
        """
        url = f"{self.course_service_url}/courses/{course_id}"

        for attempt in range(self.max_retries):
            try:
                logger.info(f"Validating course {course_id} with Course Service (attempt {attempt + 1})")

                response = requests.get(
                    url,
                    timeout=self.timeout,
                    headers={'Content-Type': 'application/json'}
                )

                if response.status_code == 200:
                    logger.info(f"Course {course_id} validation successful")
                    return True
                elif response.status_code == 404:
                    logger.warning(f"Course {course_id} not found")
                    return False
                else:
                    logger.warning(f"Course Service returned status {response.status_code}")

            except requests.exceptions.RequestException as e:
                logger.error(f"Error calling Course Service (attempt {attempt + 1}): {str(e)}")

                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying in {self.retry_delay} seconds.")
                    time.sleep(self.retry_delay)
                    self.retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Failed to validate course {course_id} after {self.max_retries} attempts")
                    return False

        return False