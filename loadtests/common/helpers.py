# This file contains helper functions for the load tests.
import random


def get_random_request_id_header():
    """Generates a header with a random request ID."""
    return {"x-request-id": f"locust-{random.randint(1000, 9999)}"}
