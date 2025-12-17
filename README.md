# EU-search-sync

This project was generated using fastapi_template.

## Poetry

This project uses poetry. It's a modern dependency management
tool.

To run the project use this set of commands:

```bash
poetry install
poetry run python -m app
```

This will start the server on the configured host.

You can find swagger documentation at `/api/docs`.

You can read more about poetry here: https://python-poetry.org/

## Docker

You can start the project with docker using this command:

```bash
docker-compose up --build
```

If you want to develop in docker with autoreload and exposed ports add `-f deploy/docker-compose.dev.yml` to your docker command.
Like this:

```bash
docker-compose -f docker-compose.yml -f deploy/docker-compose.dev.yml --project-directory . up --build
```

This command exposes the web application on port 8000, mounts current directory and enables autoreload.

But you have to rebuild image every time you modify `poetry.lock` or `pyproject.toml` with this command:

```bash
docker-compose build
```

## Project structure

```bash
$ tree "app"
app
├── conftest.py  # Fixtures for all tests.
├── db  # module contains db configurations
│   ├── dao  # Data Access Objects. Contains different classes to interact with database.
│   └── models  # Package contains different models for ORMs.
├── __main__.py  # Startup script. Starts uvicorn.
├── services  # Package for different external services such as rabbit or redis etc.
├── settings.py  # Main configuration settings for project.
├── static  # Static content.
├── tests  # Tests for project.
└── web  # Package contains web server. Handlers, startup config.
    ├── api  # Package with all handlers.
    │   └── router.py  # Main router.
    ├── application.py  # FastAPI application configuration.
    └── lifespan.py  # Contains actions to perform on startup and shutdown.
```

## Configuration

This application can be configured with environment variables.

You can create `.env` file in the root directory and place all
environment variables here. 

All environment variables should start with "APP_" prefix.

For example if you see in your "app/settings.py" a variable named like
`random_parameter`, you should provide the "APP_RANDOM_PARAMETER" 
variable to configure the value. This behaviour can be changed by overriding `env_prefix` property
in `app.settings.Settings.Config`.

An example of .env file:
```bash
APP_RELOAD="True"
APP_PORT="8000"
APP_ENVIRONMENT="dev"
```

You can read more about BaseSettings class here: https://pydantic-docs.helpmanual.io/usage/settings/

## Pre-commit

To install pre-commit simply run inside the shell:
```bash
pre-commit install
```

pre-commit is very useful to check your code before publishing it.
It's configured using .pre-commit-config.yaml file.

By default it runs:
* black (formats your code);
* mypy (validates types);
* ruff (spots possible bugs);


You can read more about pre-commit here: https://pre-commit.com/

## Migrations

If you want to migrate your database, you should run following commands:
```bash
# To run all migrations until the migration with revision_id.
alembic upgrade "<revision_id>"

# To perform all pending migrations.
alembic upgrade "head"
```

### Reverting migrations

If you want to revert migrations, you should run:
```bash
# revert all migrations up to: revision_id.
alembic downgrade <revision_id>

# Revert everything.
 alembic downgrade base
```

### Migration generation

To generate migrations you should run:
```bash
# For automatic change detection.
alembic revision --autogenerate

# For empty file generation.
alembic revision
```


## Running tests

If you want to run it in docker, simply run:

```bash
docker-compose run --build --rm api pytest -vv .
docker-compose down
```

For running tests on your local machine.
1. you need to start a database.

I prefer doing it with docker:
```
docker run -p "5432:5432" -e "POSTGRES_PASSWORD=app" -e "POSTGRES_USER=app" -e "POSTGRES_DB=app" postgres:16.3-bullseye
```


2. Run the pytest.
```bash
pytest -vv .
```

## Logging

This application uses [Loguru](https://loguru.readthedocs.io/en/stable/) for structured and configurable logging.

### Log Files and Rotation

Logs are stored in the `logs/` directory at the root of the project. The following log files are generated:

*   `logs/access.log`: Contains access logs for all incoming HTTP requests.
*   `logs/error.log`: Records all logs with a severity level of `ERROR` or higher.
*   `logs/debug.log`: Contains debug-level logs. This file is only created when debug mode is enabled.

All log files are automatically rotated on a daily basis.

### Configuration

You can enable debug logging by setting the following environment variable in your `.env` file:

```bash
APP_DEBUG="True"
```

When `APP_DEBUG` is set to `True`, detailed debug messages will be written to `logs/debug.log`.

### How to Use the Logger

To add logging to your code, import the `logger` object from `loguru` and call the appropriate method for the desired severity level.

```python
from loguru import logger

def my_function():
    logger.info("This is an informational message.")
    logger.debug("This is a debug message.")
    logger.warning("This is a warning.")
    logger.error("An error occurred.")
```

### Access Logs

Access logs are generated automatically for every incoming HTTP request. They are formatted to include detailed information about the request:

```
<client_ip> - "<method> <path>?<query_params> HTTP/1.1" <status_code> - Headers: <headers> - Process Time: <process_time>
```

An example log entry looks like this:

```
127.0.0.1 - "GET /api/v1/monitoring/health HTTP/1.1" 200 - Headers: {'host': 'localhost:8000', ...} - Process Time: 0.45ms
```


## Load Testing with Locust

This project uses [Locust](https://locust.io/) to simulate user traffic and test the performance of the application under load. The load testing scripts are located in the `loadtests/` directory.

### File Structure

The `loadtests/` directory is organized as follows:
```bash
loadtests/
├── __init__.py                # Makes 'loadtests' a Python package.
├── locustfile.py              # Main entry point for Locust, collects all user tasks.
├── common/
│   ├── bootstrap.py           # Logic to fetch initial data before tests run.
│   ├── helpers.py             # Utility functions for tests.
│   └── test_constants.py      # Shared constants and configuration for tests.
└── users/
    ├── games.py      # Tasks for the configurations API endpoint.
    ├── progress.py           # Tasks for the progress API endpoint.
    ├── vendor.py           # Tasks for the vendor API endpoint.
    └── translations.py        # Tasks for the translations API endpoint.
```

### How to Run Load Tests

To run the load tests, you can use the `locust` command from your terminal. Ensure that the application is running, as the tests will make live requests to it.

#### Headless Mode

Here is an example command to run the tests in headless mode for one minute, which is ideal for automated environments:
```bash
locust -f loadtests/locustfile.py --host http://127.0.0.1:8880/search --users 50 --spawn-rate 10 --run-time 1m --headless --exit-code-on-error 1 --html report.html --csv report
```

#### Running with the Web GUI

For a more interactive experience, you can run Locust with its web-based GUI. This allows you to start and stop tests, change the number of users, and see real-time statistics in your browser.

1.  **Start the Locust web server:**
    ```bash
    locust -f loadtests/locustfile.py --host http://127.0.0.1:8880/search
    ```

2.  **Open your web browser** and navigate to `http://localhost:8089`.

3.  **Start a new load test:**
    *   Enter the number of users to simulate and the spawn rate (users per second).
    *   Click the "Start swarming" button.

From the web interface, you can monitor the test in real-time, view charts, and stop the test when you are finished.

### Command-Line Options

*   `-f`: Specifies the path to the main locust file.
*   `--host`: The base URL of the application to be tested.
*   `--users`: The total number of concurrent users to simulate.
*   `--spawn-rate`: The number of users to spawn per second.
*   `--run-time`: The total duration for the test (e.g., `30s`, `1m`, `2h`).
*   `--headless`: Runs Locust without the web UI, which is ideal for CI/CD environments.
*   `--exit-code-on-error`: Sets the exit code to 1 if any requests fail during the test run.
*   `--html`: Generates an HTML report of the test results.
*   `--csv`: Generates CSV files containing detailed statistics.

### Test Reports

After the test run completes, the following report files will be generated in the root directory:

*   `report.html`: A detailed HTML report with charts and statistics.
*   `report_stats.csv`: A CSV file with the overall statistics.
*   `report_stats_history.csv`: A CSV file with periodic statistics throughout the test run.
*   `report_failures.csv`: A CSV file with details of any failed requests.
