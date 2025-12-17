# This file is the main entry point for Locust, collecting all user types.
# It also triggers the bootstrap process to fetch initial data.

# Import user classes to be included in the test
from loadtests.users.games import GamesApiUser
from loadtests.users.vendor import VendorApiUser
from loadtests.users.progress import ProgressApiUser

# Import and register the bootstrap function
from loadtests.common.bootstrap import bootstrap_all

# The bootstrap_all function is registered via the @events.test_start.add_listener
# decorator in the bootstrap module itself. Nothing further is needed here to
# ensure it runs at the start of the test.

# To run the tests, use the following command:
# locust -f loadtests/locustfile.py
