"""Integration test fixtures — uses testcontainers to start Firestore and Datastore emulators."""

import os
import warnings

import pytest
from google.cloud.firestore import Client
from testcontainers.core.container import DockerContainer  # type: ignore[import-untyped]
from testcontainers.core.waiting_utils import wait_for_logs  # type: ignore[import-untyped]

PROJECT_ID = "cendry-test"
EMULATOR_PORT = 8080
DATASTORE_EMULATOR_PORT = 8081


@pytest.fixture(scope="session")
def firestore_emulator():
    """Start a Firestore emulator container for the test session."""
    container = (
        DockerContainer("google/cloud-sdk:emulators")
        .with_command(
            "gcloud emulators firestore start"
            f" --host-port=0.0.0.0:{EMULATOR_PORT}"
            f" --project={PROJECT_ID}"
        )
        .with_exposed_ports(EMULATOR_PORT)
    )
    container.start()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        wait_for_logs(container, "Dev App Server is now running", timeout=30)
    host = container.get_container_host_ip()
    port = container.get_exposed_port(EMULATOR_PORT)
    emulator_host = f"{host}:{port}"
    os.environ["FIRESTORE_EMULATOR_HOST"] = emulator_host
    yield emulator_host
    container.stop()


@pytest.fixture
def firestore_client(firestore_emulator):
    """Sync Firestore client connected to the emulator."""
    client = Client(project=PROJECT_ID)
    yield client
    client.close()


@pytest.fixture
def clean_collection(firestore_client):
    """Delete all docs in a collection after the test."""
    collections_to_clean: list[str] = []

    def _register(name: str) -> str:
        collections_to_clean.append(name)
        return name

    yield _register

    for col_name in collections_to_clean:
        for doc in firestore_client.collection(col_name).stream():
            doc.reference.delete()


# ---------------------------------------------------------------------------
# Datastore emulator
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def datastore_emulator():
    """Start a Datastore emulator container for the test session."""
    container = (
        DockerContainer("google/cloud-sdk:emulators")
        .with_command(
            "gcloud beta emulators datastore start"
            f" --host-port=0.0.0.0:{DATASTORE_EMULATOR_PORT}"
            f" --project={PROJECT_ID}"
            " --no-store-on-disk"
            " --consistency=1.0"
        )
        .with_exposed_ports(DATASTORE_EMULATOR_PORT)
    )
    container.start()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        wait_for_logs(container, "Dev App Server is now running", timeout=60)
    host = container.get_container_host_ip()
    port = container.get_exposed_port(DATASTORE_EMULATOR_PORT)
    emulator_host = f"{host}:{port}"
    os.environ["DATASTORE_EMULATOR_HOST"] = emulator_host
    yield emulator_host
    container.stop()


@pytest.fixture
def datastore_client(datastore_emulator):
    """Sync Datastore client connected to the emulator."""
    from google.cloud import datastore

    return datastore.Client(project=PROJECT_ID)


@pytest.fixture
def clean_datastore(datastore_client):
    """Delete all entities of registered Kinds after each test."""
    kinds_to_clean: list[str] = []

    def _register(name: str) -> str:
        kinds_to_clean.append(name)
        return name

    yield _register

    for kind_name in kinds_to_clean:
        query = datastore_client.query(kind=kind_name)
        query.keys_only()
        keys = [entity.key for entity in query.fetch()]
        if keys:
            datastore_client.delete_multi(keys)
