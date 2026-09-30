# tests/test_zip_uploads.py
"""
Issue #34: a zip with one folder per device, each holding a file of the same
name, must yield one device per folder. Keying members by basename kept only
the last one.
"""
import io
import zipfile

from fastapi.testclient import TestClient

from src.app import app

client = TestClient(app)


def _config(hostname: str | None, ip: str) -> str:
    head = f"hostname {hostname}\n" if hostname else ""
    return head + f"interface GigabitEthernet0/0\n ip address {ip} 255.255.255.0\n no shutdown\n!\n"


def _analyze_zip(members: dict[str, str]):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, text in members.items():
            archive.writestr(name, text)
    return client.post("/api/analyze", files=[("files", ("lab.zip", buffer.getvalue(), "application/zip"))])


def test_same_filename_in_different_folders_keeps_every_device():
    response = _analyze_zip({
        "R1/running-config.txt": _config("R1", "10.0.0.1"),
        "R2/running-config.txt": _config("R2", "10.0.0.2"),
        "SW1/running-config.txt": _config("SW1", "10.0.0.3"),
    })
    assert response.status_code == 200
    assert set(response.json()["devices"]) == {"R1", "R2", "SW1"}


def test_generic_filename_without_hostname_is_named_after_its_folder():
    response = _analyze_zip({
        "R1/running-config.txt": _config(None, "10.0.0.1"),
        "R2/running-config.txt": _config(None, "10.0.0.2"),
    })
    assert response.status_code == 200
    assert set(response.json()["devices"]) == {"R1", "R2"}


def test_two_files_claiming_one_hostname_are_reported():
    response = _analyze_zip({
        "a/R1.txt": _config("R1", "10.0.0.1"),
        "b/R1-copy.txt": _config("R1", "10.0.0.9"),
    })
    assert response.status_code == 200
    conflicts = response.json()["conflicts"]
    assert any("R1" in c["description"] and "a/R1.txt" in c["description"] for c in conflicts)
