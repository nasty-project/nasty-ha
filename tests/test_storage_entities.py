"""Tests for storage entity presentation."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from nasty.coordinator import NastyStorageData
from nasty.entity import disk_display_name
from nasty.sensor import NastyFilesystemSizeSensor


def test_disk_display_name_distinguishes_identical_models() -> None:
    disk = {"device": "/dev/sda", "model": "KIOXIA-EXCERIA SATA SSD"}

    assert disk_display_name(disk) == "KIOXIA-EXCERIA SATA SSD (sda)"


def test_filesystem_size_sensors_expose_total_and_free_bytes() -> None:
    filesystem = {
        "uuid": "filesystem-id",
        "name": "first",
        "total_bytes": 1_000,
        "available_bytes": 400,
    }
    coordinator = SimpleNamespace(
        data=NastyStorageData(filesystems=[filesystem], disks=[]),
        last_update_success=True,
    )
    entry = SimpleNamespace(entry_id="entry-id")

    total = NastyFilesystemSizeSensor(
        cast(Any, entry), cast(Any, coordinator), filesystem, "total_bytes", "total space"
    )
    free = NastyFilesystemSizeSensor(
        cast(Any, entry),
        cast(Any, coordinator),
        filesystem,
        "available_bytes",
        "free space",
    )

    assert total.native_value == 1_000
    assert free.native_value == 400
    assert total.available
    assert free.available
