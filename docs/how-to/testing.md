# Test with the Firestore Emulator

Run integration tests against a real Firestore emulator — no Google Cloud account needed.

---

## Quick start

```bash
uv run pytest tests/integration/ -v
```

That's it. [Testcontainers](https://testcontainers-python.readthedocs.io/) automatically pulls and starts a Firestore emulator Docker container, runs the tests, and cleans up.

!!! note "Requires Docker"
    Docker must be running on your machine. The first run pulls the `google/cloud-sdk:emulators` image (~1GB).

## How it works

The `firestore_emulator` fixture (session-scoped) starts a container with the official Google Cloud SDK emulator:

```python
from testcontainers.core.container import DockerContainer

container = (
    DockerContainer("google/cloud-sdk:emulators")
    .with_command("gcloud emulators firestore start --host-port=0.0.0.0:8080")
    .with_exposed_ports(8080)
)
container.start()
```

It sets `FIRESTORE_EMULATOR_HOST` automatically — the `google-cloud-firestore` Python SDK reads this environment variable and connects to the emulator instead of real Firestore.

## Writing integration tests

```python
from cendry import Cendry, Field, Model


class City(Model, collection="test_cities"):
    name: Field[str]
    population: Field[int]


def test_save_and_get(firestore_client, clean_collection):
    clean_collection("test_cities")  # register for cleanup
    ctx = Cendry(client=firestore_client)

    city = City(name="SF", population=870_000)
    ctx.save(city)

    fetched = ctx.get(City, city.id)
    assert fetched.name == "SF"
```

### Available fixtures

| Fixture | Scope | Description |
|---------|-------|-------------|
| `firestore_emulator` | session | Starts the emulator container, yields `host:port` |
| `firestore_client` | function | Sync `Client` connected to the emulator |
| `clean_collection(name)` | function | Registers a collection for cleanup after the test |

## Unit tests vs integration tests

| | Unit tests | Integration tests |
|---|-----------|-------------------|
| **Location** | `tests/` | `tests/integration/` |
| **Dependencies** | None (mocked) | Docker |
| **Speed** | ~0.3s | ~20-90s (container startup) |
| **Coverage** | 100% required | Not included in coverage |
| **CI** | Always | Optional (needs Docker in CI) |
| **Run** | `uv run pytest` | `uv run pytest tests/integration/ -v` |

## Adding integration tests to CI

To run integration tests in GitHub Actions, add Docker support:

```yaml
jobs:
  integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - run: uv python install 3.13
      - run: uv sync
      - run: uv run pytest tests/integration/ -v
```

Ubuntu runners have Docker pre-installed, so testcontainers works out of the box.
