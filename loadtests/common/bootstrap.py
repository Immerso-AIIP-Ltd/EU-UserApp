# This file contains the bootstrap logic for the load tests.

import threading
from typing import Any

from locust import events
from locust.contrib.fasthttp import FastHttpSession

BOOTSTRAP_LOCK = threading.Lock()
BOOTSTRAPPED = False


@events.test_start.add_listener
def bootstrap_all(environment: Any, **_: Any) -> None:
    """
    Master bootstrap function to run before tests begin.

    Currently performs minimal setup as user_app doesn't require
    external data fetching for countries/languages.
    """
    global BOOTSTRAPPED  # noqa: PLW0603
    with BOOTSTRAP_LOCK:
        if BOOTSTRAPPED:
            return

        FastHttpSession(
            environment=environment,
            base_url=environment.host,
            request_event=environment.events.request,
            user=None,
        )

        # Add any future bootstrap logic here
        # For example: fetching test data, warming up caches, etc.

        BOOTSTRAPPED = True
