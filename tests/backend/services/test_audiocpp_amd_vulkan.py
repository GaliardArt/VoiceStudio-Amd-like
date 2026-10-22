"""AMD Vulkan proof-of-concept coverage for the native audio.cpp runtime.

These tests are hardware-independent: they pin the device discovery/routing
contract for older Polaris and newer Radeon devices without claiming that a
particular driver/GPU has been exercised on real hardware. The native runtime
must still be validated on each target machine.
"""
from __future__ import annotations

import importlib
from types import SimpleNamespace


def _modules():
    return SimpleNamespace(
        audiocpp=importlib.import_module("engines.audiocpp"),
        bootstrap=importlib.import_module("engines.audiocpp.bootstrap"),
    )


def test_rx580_is_selected_as_a_discrete_vulkan_gpu(monkeypatch):
    """An RX 580 must use Vulkan, not be mistaken for a ROCm requirement."""
    from core.device_caps import HostCaps

    modules = _modules()
    devices = modules.bootstrap.parse_device_list(
        'Vulkan:0 "AMD Radeon RX 580 (RADV POLARIS10)" [GPU]\\n'
        'CPU:0 "Host CPU" [CPU]'
    )
    monkeypatch.setattr(modules.bootstrap, "probe_devices", lambda: devices)
    caps = HostCaps(
        family="cpu",
        available_families=("cpu",),
        device_name="AMD Radeon RX 580 (RADV POLARIS10)",
        vram_gb=8.0,
        notes=(),
    )

    profile = modules.audiocpp.AudioCPPBackend.runtime_compute_profile(caps)

    assert profile["effective_device"] == "vulkan"
    assert profile["routing_status"] == "accelerated"
    assert profile["runtime_backend"] == "vulkan"
    assert profile["runtime_device_name"] == "AMD Radeon RX 580 (RADV POLARIS10)"
    assert profile["runtime_hardware_family"] == "rocm"
    assert profile["runtime_device_verified"] is True
    assert profile["runtime_vram_gb"] == 8.0
    assert profile["gpu_compat"] == ("vulkan", "cpu")


def test_radeon_vulkan_selection_does_not_require_rocm(monkeypatch):
    """Windows Vulkan-capable Radeon devices remain eligible without ROCm."""
    modules = _modules()
    devices = modules.bootstrap.parse_device_list(
        'Vulkan:0 "AMD Radeon RX 7600" [GPU]\\n'
        'CPU:0 "Host CPU" [CPU]'
    )
    monkeypatch.setattr(modules.bootstrap, "probe_devices", lambda: devices)

    selection = modules.bootstrap.resolve_compute_selection(
        SimpleNamespace(
            family="cpu",
            available_families=("cpu",),
            device_name="",
            vram_gb=0.0,
            requested_family="auto",
            notes=(),
        )
    )

    assert selection.device.backend == "vulkan"
    assert selection.device.target == "vulkan"
    assert selection.device.hardware_family == "rocm"
    assert selection.fallback_reason is None


def test_rx580_with_4gb_vram_is_accelerated_but_warns_about_memory(monkeypatch):
    """A 4 GB variant should not be silently blocked, but should be cautioned."""
    from core.device_caps import HostCaps

    modules = _modules()
    name = "AMD Radeon RX 580"
    devices = modules.bootstrap.parse_device_list(
        f'Vulkan:0 "{name}" [GPU]\\nCPU:0 "Host CPU" [CPU]'
    )
    monkeypatch.setattr(modules.bootstrap, "probe_devices", lambda: devices)
    caps = HostCaps(
        family="cpu",
        available_families=("cpu",),
        device_name=name,
        vram_gb=4.0,
        notes=(),
    )

    profile = modules.audiocpp.AudioCPPBackend.runtime_compute_profile(caps)

    assert profile["routing_status"] == "accelerated"
    assert profile["effective_device"] == "vulkan"
    assert profile["runtime_vram_gb"] == 4.0
    assert "4.0 GB VRAM" in profile["routing_reason"]
