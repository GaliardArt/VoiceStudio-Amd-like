"""Hardware-independent AMD Vulkan routing tests for audio.cpp.

These tests exercise device parsing and routing only. They do not claim that
Vulkan inference has been validated on physical Radeon hardware.
"""
from __future__ import annotations

import importlib


def _bootstrap():
    return importlib.import_module("engines.audiocpp.bootstrap")


def test_rx580_is_selected_as_a_discrete_vulkan_gpu():
    bootstrap = _bootstrap()
    devices = bootstrap.parse_device_list("""
Vulkan:0 "AMD Radeon RX 580 (RADV POLARIS10)" [GPU]
CPU:0 "Host CPU" [CPU]
""")

    selected = bootstrap.select_device(devices)

    assert selected.device.backend == "vulkan"
    assert selected.device.target == "vulkan"
    assert selected.device.hardware_family == "rocm"
    assert selected.device.name == "AMD Radeon RX 580 (RADV POLARIS10)"
    assert selected.fallback_reason is None
    assert bootstrap.runtime_targets(devices) == ("vulkan", "cpu")


def test_newer_radeon_can_be_selected_without_rocm_backend():
    bootstrap = _bootstrap()
    devices = bootstrap.parse_device_list("""
Vulkan:0 "AMD Radeon RX 7600" [GPU]
CPU:0 "Host CPU" [CPU]
""")

    selected = bootstrap.select_device(devices, requested_family="rocm")

    # "rocm" here is the hardware family label, not a requirement for the
    # ROCm runtime. The actual execution backend remains Vulkan.
    assert selected.device.backend == "vulkan"
    assert selected.device.target == "vulkan"
    assert selected.device.hardware_family == "rocm"
    assert bootstrap.runtime_targets(devices) == ("vulkan", "cpu")


def test_cpu_remains_available_when_no_radeon_vulkan_device_is_exposed():
    bootstrap = _bootstrap()
    devices = bootstrap.parse_device_list('CPU:0 "Host CPU" [CPU]')

    selected = bootstrap.select_device(devices)

    assert selected.device.backend == "cpu"
    assert selected.device.target == "cpu"
    assert selected.fallback_reason is None



def test_software_vulkan_adapter_does_not_beat_native_cpu_in_auto_mode():
    bootstrap = _bootstrap()
    devices = bootstrap.parse_device_list("""
Vulkan:0 "llvmpipe (LLVM 19.1.7, 256 bits)" [GPU]
CPU:0 "Host CPU" [CPU]
""")

    selected = bootstrap.select_device(devices)

    assert selected.device.backend == "cpu"
    assert selected.device.target == "cpu"
    assert selected.device.hardware_family == "cpu"
    assert bootstrap.runtime_targets(devices) == ("cpu",)


def test_native_radeon_beats_software_vulkan_when_both_are_exposed():
    bootstrap = _bootstrap()
    # Deliberately list the software adapter first to prove selection depends
    # on device classification/priority, not the registry's output order.
    devices = bootstrap.parse_device_list(""" 
Vulkan:0 "llvmpipe (LLVM 19.1.7, 256 bits)" [GPU]
Vulkan:1 "AMD Radeon RX 580 (RADV POLARIS10)" [GPU]
CPU:0 "Host CPU" [CPU]
""".strip())

    selected = bootstrap.select_device(devices)

    assert selected.device.name == "AMD Radeon RX 580 (RADV POLARIS10)"
    assert selected.device.backend == "vulkan"
    assert selected.device.target == "vulkan"
