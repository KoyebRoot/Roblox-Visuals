import requests as req
import ctypes as ct
import time as tm
import math as mth
import numpy as np
import win32api as w32api
import win32gui as w32gui
import win32con as w32con
import pymem as pmem
import pymem.process as pmproc
import pyMeow as pyow
import json as js
import re as regex
import os as oss
from ctypes import wintypes, POINTER, byref

REMOTE_SOURCE = "https://imtheo.lol/Offsets/Offsets.hpp"
CACHE_FILE = "offsets.json"

DEFAULT_OFFSETS = {
    "FakeDataModelPointer": "0x7d909f8",
    "FakeDataModelToDataModel": "0x1c0",
    "Workspace": "0x178",
    "Camera": "0x4a0",
    "CameraPos": "0x11c",
    "CameraRotation": "0xf8",
    "VisualEnginePointer": "0x79449e0",
    "viewmatrix": "0x120",
    "Children": "0x70",
    "Name": "0xb0",
    "NameContainer": "0x0",
    "ModelInstance": "0x380",
    "Health": "0x194",
    "MaxHealth": "0x1b4",
    "Position": "0xe4",
    "Rotation": "0xc0",
    "Primitive": "0x148",
    "LocalPlayer": "0x130",
    "Team": "0x290",
    "GravityContainer": "0x3d8",
    "MousePosition": "0xec",
    "CameraViewport": "0x2ac"
}

OFFSET_BACKUP = """
#pragma once
#include <cstdint>
#include <string>
namespace Offsets {
    inline std::string ClientVersion = "version-ce0bcd0fbd484804";

    namespace Camera {
         inline constexpr uintptr_t Position = 0xfc;
         inline constexpr uintptr_t Rotation = 0xd8;
         inline constexpr uintptr_t Viewport = 0x28c;
    }

    namespace DataModel {
         inline constexpr uintptr_t Workspace = 0x158;
    }

    namespace FakeDataModel {
         inline constexpr uintptr_t Pointer = 0x8c426f8;
         inline constexpr uintptr_t RealDataModel = 0x1d8;
    }

    namespace Humanoid {
         inline constexpr uintptr_t Health = 0x190;
         inline constexpr uintptr_t MaxHealth = 0x1a8;
    }

    namespace Instance {
         inline constexpr uintptr_t ChildrenStart = 0x78;
         inline constexpr uintptr_t Name = 0x8;
         inline constexpr uintptr_t NameContainer = 0x70;
    }

    namespace Player {
         inline constexpr uintptr_t LocalPlayer = 0x130;
         inline constexpr uintptr_t ModelInstance = 0x298;
         inline constexpr uintptr_t Team = 0x2d8;
    }

    namespace Primitive {
         inline constexpr uintptr_t Position = 0xec;
         inline constexpr uintptr_t Rotation = 0xc8;
    }

    namespace BasePart {
         inline constexpr uintptr_t Primitive = 0x188;
    }

    namespace VisualEngine {
         inline constexpr uintptr_t Pointer = 0x827dd88;
         inline constexpr uintptr_t ViewMatrix = 0x180;
    }

    namespace Workspace {
         inline constexpr uintptr_t CurrentCamera = 0x498;
         inline constexpr uintptr_t World = 0x3f0;
    }

    namespace MouseService {
         inline constexpr uintptr_t MousePosition = 0xd4;
    }
}
"""

class MemoryReader:
    def __init__(self, process_id):
        self.pid = process_id
        self.handle = ct.windll.kernel32.OpenProcess(
            0x0010 | 0x0020 | 0x0008 | 0x0400, False, process_id
        )

    def fetch(self, address, size):
        buffer = (ct.c_byte * size)()
        bytes_read = ct.c_size_t(0)
        ct.windll.ntdll.NtReadVirtualMemory(
            self.handle, ct.c_void_p(address),
            ct.byref(buffer), size, ct.byref(bytes_read)
        )
        return bytes(buffer)

    def get_qword(self, address):
        return int.from_bytes(self.fetch(address, 8), 'little', signed=True)

    def get_dword(self, address):
        return int.from_bytes(self.fetch(address, 4), 'little', signed=True)

    def get_float(self, address):
        return np.frombuffer(self.fetch(address, 4), dtype=np.float32)[0]

    def get_text(self, address, length):
        try:
            return self.fetch(address, length).decode('utf-8').rstrip('\x00')
        except:
            return self.fetch(address, length).decode('latin-1').rstrip('\x00')

def get_process_base(pid):
    handle = ct.windll.kernel32.OpenProcess(0x0410, False, pid)
    if not handle:
        return None
    modules = (ct.c_void_p * 1)()
    needed = ct.c_size_t()
    if ct.windll.psapi.EnumProcessModules(
        handle, ct.byref(modules),
        ct.sizeof(modules), ct.byref(needed)
    ):
        return int(modules[0])
    return None

def find_roblox():
    for proc in pmproc.list_processes():
        try:
            if b"RobloxPlayerBeta.exe" in proc.szExeFile:
                return proc.th32ProcessID
        except:
            continue
    return None

def follow_ptr(address):
    if not address:
        return 0
    try:
        return mem_reader.get_qword(address)
    except:
        return 0

def read_roblox_str(address):
    try:
        length = mem_reader.get_dword(address + 0x10)
        if length > 15:
            return mem_reader.get_text(follow_ptr(address), length)
        else:
            return mem_reader.get_text(address, length + 1)
    except:
        return ""

def get_name(instance):
    if not instance:
        return ""
    try:
        container = follow_ptr(instance + int(offsets.get('NameContainer', '0x0'), 16))
        if container:
            return read_roblox_str(container + int(offsets.get('Name', '0xb0'), 16))
    except:
        pass
    return ""

def get_children_list(instance):
    if not instance:
        return []
    try:
        start = follow_ptr(instance + int(offsets.get('Children', '0x70'), 16))
        if not start:
            return []
        end = follow_ptr(start + 8)
        children = []
        current = follow_ptr(start)
        while current != end and len(children) < 2000:
            child = mem_reader.get_qword(current)
            if child:
                children.append(child)
            current += 0x10
        return children
    except:
        return []

def get_class(instance):
    if not instance:
        return ""
    try:
        ptr = mem_reader.get_qword(instance + 0x18)
        ptr = mem_reader.get_qword(ptr + 0x8)
        if mem_reader.get_qword(ptr + 0x18) == 0x1F:
            ptr = mem_reader.get_qword(ptr)
        return read_roblox_str(ptr)
    except:
        return ""

def find_child_by_type(instance, target_class):
    for child in get_children_list(instance):
        try:
            if get_class(child) == target_class:
                return child
        except:
            pass
    return 0

def get_local(players_instance):
    try:
        return mem_reader.get_qword(
            players_instance + int(offsets.get('LocalPlayer', '0x130'), 16)
        )
    except:
        return 0

def get_model(player_instance):
    try:
        return mem_reader.get_qword(
            player_instance + int(offsets.get('ModelInstance', '0x380'), 16)
        )
    except:
        return 0

def get_primitive(instance):
    try:
        return mem_reader.get_qword(
            instance + int(offsets.get('Primitive', '0x148'), 16)
        )
    except:
        return 0

def get_world_pos(instance):
    prim = get_primitive(instance)
    if not prim:
        return np.zeros(3, dtype=np.float32)
    try:
        return np.frombuffer(
            mem_reader.fetch(
                prim + int(offsets.get('Position', '0xe4'), 16), 12
            ),
            dtype=np.float32
        ).copy()
    except:
        return np.zeros(3, dtype=np.float32)

def extract_character(character):
    if not character:
        return {}
    try:
        kids = get_children_list(character)
        if not kids:
            return {}
        names = [get_name(c) for c in kids]
        is_r15 = "UpperTorso" in names
        part_set = R15_BODY if is_r15 else R6_BODY
        parts = {}
        for inst, name in zip(kids, names):
            if name in part_set and name != "HumanoidRootPart":
                parts[name] = inst
        humanoid = find_child_by_type(character, "Humanoid")
        if not humanoid:
            return {}
        max_hp = mem_reader.get_float(
            humanoid + int(offsets.get('MaxHealth', '0x1b4'), 16)
        )
        if max_hp <= 0:
            return {}
        return {
            "parts": parts,
            "is_r15": is_r15,
            "humanoid": humanoid,
            "max_health": max_hp
        }
    except:
        return {}

def get_roblox_rect():
    try:
        hwnd = w32gui.FindWindow(None, "Roblox")
        if hwnd:
            rect = w32gui.GetWindowRect(hwnd)
            return rect[0], rect[1], rect[2]-rect[0], rect[3]-rect[1]
    except:
        pass
    return 0, 0, w32api.GetSystemMetrics(0), w32api.GetSystemMetrics(1)

def world_to_screen(world_positions, view_matrix, half_w, half_h):
    if world_positions.shape[0] == 0:
        return [None] * world_positions.shape[0]
    ones = np.ones((world_positions.shape[0], 1), dtype=np.float32)
    clip = np.hstack((world_positions, ones)) @ view_matrix.T
    w = clip[:, 3]
    valid = w > 0.001
    with np.errstate(divide='ignore', invalid='ignore'):
        ndc_x = np.where(valid, clip[:, 0] / w, 0)
        ndc_y = np.where(valid, clip[:, 1] / w, 0)
    in_frustum = valid & (np.abs(ndc_x) <= 1.05) & (np.abs(ndc_y) <= 1.05)
    screen_x = (ndc_x + 1) * half_w
    screen_y = (1 - ndc_y) * half_h
    result = []
    for i in range(len(world_positions)):
        if in_frustum[i]:
            result.append((int(screen_x[i]), int(screen_y[i])))
        else:
            result.append(None)
    return result

def fetch_offsets():
    try:
        resp = req.get(REMOTE_SOURCE, timeout=5)
        resp.raise_for_status()
        raw = resp.text
    except:
        raw = OFFSET_BACKUP

    parsed = {}
    current_scope = None
    for line in raw.splitlines():
        line = line.strip()
        scope_match = regex.match(r'namespace (\w+)', line)
        if scope_match:
            current_scope = scope_match.group(1)
            continue
        offset_match = regex.match(r'inline constexpr uintptr_t (\w+) = (0x[\da-fA-F]+);', line)
        if offset_match and current_scope:
            parsed[f"{current_scope}::{offset_match.group(1)}"] = offset_match.group(2)
        version_match = regex.match(r'inline std::string ClientVersion = "([^"]+)";', line)
        if version_match:
            parsed["ClientVersion"] = version_match.group(1)

    final = DEFAULT_OFFSETS.copy()

    mapping = {
        "Camera": "Workspace::CurrentCamera",
        "CameraPos": "Camera::Position",
        "CameraRotation": "Camera::Rotation",
        "CameraViewport": "Camera::Viewport",
        "Children": "Instance::ChildrenStart",
        "FakeDataModelPointer": "FakeDataModel::Pointer",
        "FakeDataModelToDataModel": "FakeDataModel::RealDataModel",
        "GravityContainer": "Workspace::World",
        "Health": "Humanoid::Health",
        "LocalPlayer": "Player::LocalPlayer",
        "MaxHealth": "Humanoid::MaxHealth",
        "ModelInstance": "Player::ModelInstance",
        "MousePosition": "MouseService::MousePosition",
        "Name": "Instance::Name",
        "NameContainer": "Instance::NameContainer",
        "Position": "Primitive::Position",
        "Primitive": "BasePart::Primitive",
        "Rotation": "Primitive::Rotation",
        "Team": "Player::Team",
        "VisualEnginePointer": "VisualEngine::Pointer",
        "viewmatrix": "VisualEngine::ViewMatrix",
        "Workspace": "DataModel::Workspace"
    }

    for json_key, cpp_key in mapping.items():
        if cpp_key in parsed:
            final[json_key] = parsed[cpp_key]

    if "ClientVersion" in parsed:
        final["RobloxVersion"] = f"Roblox Version: {parsed['ClientVersion']}"

    with open(CACHE_FILE, 'w') as f:
        js.dump(final, f, indent=2)

    return final

def load_cached_offsets():
    if oss.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return js.load(f)
        except:
            pass
    return fetch_offsets()

R15_BODY = {"Head", "UpperTorso", "LowerTorso", "LeftUpperArm", "LeftLowerArm", "LeftHand", 
            "RightUpperArm", "RightLowerArm", "RightHand", "LeftUpperLeg", "LeftLowerLeg", 
            "LeftFoot", "RightUpperLeg", "RightLowerLeg", "RightFoot"}
R6_BODY = {"Head", "Torso", "Left Arm", "Right Arm", "Left Leg", "Right Leg"}
R15_CONNECT = [("Head", "UpperTorso"), ("UpperTorso", "LowerTorso"), 
               ("UpperTorso", "LeftUpperArm"), ("LeftUpperArm", "LeftLowerArm"), ("LeftLowerArm", "LeftHand"),
               ("UpperTorso", "RightUpperArm"), ("RightUpperArm", "RightLowerArm"), ("RightLowerArm", "RightHand"),
               ("LowerTorso", "LeftUpperLeg"), ("LeftUpperLeg", "LeftLowerLeg"), ("LeftLowerLeg", "LeftFoot"),
               ("LowerTorso", "RightUpperLeg"), ("RightUpperLeg", "RightLowerLeg"), ("RightLowerLeg", "RightFoot")]
R6_CONNECT = [("Head", "Torso"), ("Torso", "Left Arm"), ("Torso", "Right Arm"), 
              ("Torso", "Left Leg"), ("Torso", "Right Leg")]

def main():
    global mem_reader, base_addr, data_model, workspace, players, offsets

    print("[*] Loading offsets...")
    offsets = load_cached_offsets()
    print(f"[*] {offsets.get('RobloxVersion', 'Unknown')}")

    print("[*] Looking for Roblox...")
    pid = find_roblox()
    if not pid:
        print("[-] Roblox not found")
        return

    print("[*] Connecting to memory...")
    mem_reader = MemoryReader(pid)
    base_addr = get_process_base(pid)

    print("[*] Reading game state...")
    fake_ptr = mem_reader.get_qword(
        base_addr + int(offsets.get('FakeDataModelPointer', '0x7d909f8'), 16)
    )
    data_model = mem_reader.get_qword(
        fake_ptr + int(offsets.get('FakeDataModelToDataModel', '0x1c0'), 16)
    )
    workspace = find_child_by_type(data_model, "Workspace")
    players = find_child_by_type(data_model, "Players")

    vis_engine = mem_reader.get_qword(
        base_addr + int(offsets.get('VisualEnginePointer', '0x79449e0'), 16)
    )
    view_matrix_addr = vis_engine + int(offsets.get('viewmatrix', '0x120'), 16)

    print("[*] Starting overlay...")
    pyow.overlay_init(title="ESP", fps=60, exitKey=0)
    screen_w, screen_h = w32api.GetSystemMetrics(0), w32api.GetSystemMetrics(1)

    while pyow.overlay_loop():
        pyow.begin_drawing()

        win_x, win_y, win_w, win_h = get_roblox_rect()
        if win_w <= 0 or win_h <= 0:
            win_w, win_h = screen_w, screen_h

        half_w, half_h = win_w * 0.5, win_h * 0.5

        try:
            raw_matrix = mem_reader.fetch(view_matrix_addr, 64)
            view_matrix = np.frombuffer(raw_matrix, dtype=np.float32).reshape(4, 4)
        except:
            pyow.end_drawing()
            tm.sleep(0.01)
            continue

        local_player = get_local(players)
        if not local_player:
            pyow.end_drawing()
            tm.sleep(0.01)
            continue

        for player in get_children_list(players):
            if player == local_player:
                continue

            character = get_model(player)
            if not character:
                continue

            char_data = extract_character(character)
            if not char_data:
                continue

            humanoid = char_data.get("humanoid", 0)
            if not humanoid:
                continue

            health = mem_reader.get_float(
                humanoid + int(offsets.get('Health', '0x194'), 16)
            )
            if health <= 0:
                continue

            body_parts = char_data["parts"]
            if not body_parts:
                continue

            positions = np.array(
                [get_world_pos(p) for p in body_parts.values()],
                dtype=np.float32
            )
            name_index = {name: i for i, name in enumerate(body_parts.keys())}
            skeleton = R15_CONNECT if char_data["is_r15"] else R6_CONNECT

            projected = world_to_screen(positions, view_matrix, half_w, half_h)
            visible = {}
            for name, idx in name_index.items():
                if projected[idx] is not None:
                    visible[name] = projected[idx]

            if not visible:
                continue

            for a, b in skeleton:
                if a in visible and b in visible:
                    x1, y1 = visible[a]
                    x2, y2 = visible[b]
                    pyow.draw_line(x1, y1, x2, y2, pyow.new_color(0, 255, 0, 255))

        pyow.end_drawing()
        tm.sleep(0.001)

    pyow.overlay_close()

if __name__ == "__main__":
    main()
