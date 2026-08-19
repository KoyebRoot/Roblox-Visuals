import requests
import ctypes
import time
import math
import numpy as np
import win32api
import win32gui
import win32con
import pymem
import pymem.process
import pyMeow as pme
import json
import re
import os
from ctypes import wintypes, POINTER, byref

OFFSETS_URL = "https://imtheo.lol/Offsets/Offsets.hpp"
OFFSETS_FILE = "offsets.json"

OFFSETS_TEMPLATE = {
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

OFFSETS_SUPPORT = """
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

def update_offsets():
    try:
        response = requests.get(OFFSETS_URL, timeout=5)
        response.raise_for_status()
        cpp_text = response.text
    except:
        cpp_text = OFFSETS_SUPPORT
    
    parsed = {}
    current_ns = None
    for line in cpp_text.splitlines():
        line = line.strip()
        ns_match = re.match(r'namespace (\w+)', line)
        if ns_match:
            current_ns = ns_match.group(1)
            continue
        offset_match = re.match(r'inline constexpr uintptr_t (\w+) = (0x[\da-fA-F]+);', line)
        if offset_match and current_ns:
            parsed[f"{current_ns}::{offset_match.group(1)}"] = offset_match.group(2)
        version_match = re.match(r'inline std::string ClientVersion = "([^"]+)";', line)
        if version_match:
            parsed["ClientVersion"] = version_match.group(1)
    
    offsets = OFFSETS_TEMPLATE.copy()
    
    key_map = {
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
    
    for json_key, cpp_key in key_map.items():
        if cpp_key in parsed:
            offsets[json_key] = parsed[cpp_key]
    
    if "ClientVersion" in parsed:
        offsets["RobloxVersion"] = f"Roblox Version: {parsed['ClientVersion']}"
    
    with open(OFFSETS_FILE, 'w') as f:
        json.dump(offsets, f, indent=2)
    
    return offsets

def load_offsets():
    if os.path.exists(OFFSETS_FILE):
        try:
            with open(OFFSETS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return update_offsets()

R15_PARTS = {"Head", "UpperTorso", "LowerTorso", "LeftUpperArm", "LeftLowerArm", "LeftHand", 
             "RightUpperArm", "RightLowerArm", "RightHand", "LeftUpperLeg", "LeftLowerLeg", 
             "LeftFoot", "RightUpperLeg", "RightLowerLeg", "RightFoot"}
R6_PARTS = {"Head", "Torso", "Left Arm", "Right Arm", "Left Leg", "Right Leg"}
R15_BONES = [("Head", "UpperTorso"), ("UpperTorso", "LowerTorso"), 
             ("UpperTorso", "LeftUpperArm"), ("LeftUpperArm", "LeftLowerArm"), ("LeftLowerArm", "LeftHand"),
             ("UpperTorso", "RightUpperArm"), ("RightUpperArm", "RightLowerArm"), ("RightLowerArm", "RightHand"),
             ("LowerTorso", "LeftUpperLeg"), ("LeftUpperLeg", "LeftLowerLeg"), ("LeftLowerLeg", "LeftFoot"),
             ("LowerTorso", "RightUpperLeg"), ("RightUpperLeg", "RightLowerLeg"), ("RightLowerLeg", "RightFoot")]
R6_BONES = [("Head", "Torso"), ("Torso", "Left Arm"), ("Torso", "Right Arm"), 
            ("Torso", "Left Leg"), ("Torso", "Right Leg")]

class MemoryManager:
    def __init__(self, pid):
        self.process_id = pid
        self.process_handle = ctypes.windll.kernel32.OpenProcess(0x0010 | 0x0020 | 0x0008 | 0x0400, False, pid)

    def read_bytes(self, address, size):
        buffer = (ctypes.c_byte * size)()
        bytes_read = ctypes.c_size_t(0)
        ctypes.windll.ntdll.NtReadVirtualMemory(self.process_handle, ctypes.c_void_p(address), 
                                                ctypes.byref(buffer), size, ctypes.byref(bytes_read))
        return bytes(buffer)

    def read_longlong(self, address):
        return int.from_bytes(self.read_bytes(address, 8), 'little', signed=True)

    def read_int(self, address):
        return int.from_bytes(self.read_bytes(address, 4), 'little', signed=True)

    def read_float(self, address):
        return np.frombuffer(self.read_bytes(address, 4), dtype=np.float32)[0]

    def read_string(self, address, length):
        try:
            return self.read_bytes(address, length).decode('utf-8').rstrip('\x00')
        except:
            return self.read_bytes(address, length).decode('latin-1').rstrip('\x00')

def get_module_base(pid):
    hProcess = ctypes.windll.kernel32.OpenProcess(0x0410, False, pid)
    if not hProcess:
        return None
    hModules = (ctypes.c_void_p * 1)()
    cbNeeded = ctypes.c_size_t()
    if ctypes.windll.psapi.EnumProcessModules(hProcess, byref(hModules), ctypes.sizeof(hModules), byref(cbNeeded)):
        return int(hModules[0])
    return None

def find_roblox_process():
    for p in pymem.process.list_processes():
        try:
            if b"RobloxPlayerBeta.exe" in p.szExeFile:
                return p.th32ProcessID
        except:
            continue
    return None

def DRP(addr):
    if not addr:
        return 0
    try:
        return pm.read_longlong(addr)
    except:
        return 0

def ReadRobloxString(addr):
    try:
        length = pm.read_int(addr + 0x10)
        if length > 15:
            return pm.read_string(DRP(addr), length)
        else:
            return pm.read_string(addr, length + 1)
    except:
        return ""

def GetName(instance):
    if not instance:
        return ""
    try:
        name_container = DRP(instance + int(offsets.get('NameContainer', '0x0'), 16))
        if name_container:
            return ReadRobloxString(name_container + int(offsets.get('Name', '0xb0'), 16))
    except:
        pass
    return ""

def GetChildren(instance):
    if not instance:
        return []
    try:
        start = DRP(instance + int(offsets.get('Children', '0x70'), 16))
        if not start:
            return []
        end = DRP(start + 8)
        children = []
        cur = DRP(start)
        while cur != end and len(children) < 2000:
            child = pm.read_longlong(cur)
            if child:
                children.append(child)
            cur += 0x10
        return children
    except:
        return []

def GetClassName(instance):
    if not instance:
        return ""
    try:
        ptr = pm.read_longlong(instance + 0x18)
        ptr = pm.read_longlong(ptr + 0x8)
        if pm.read_longlong(ptr + 0x18) == 0x1F:
            ptr = pm.read_longlong(ptr)
        return ReadRobloxString(ptr)
    except:
        return ""

def FindFirstChildOfClass(instance, class_name):
    for child in GetChildren(instance):
        try:
            if GetClassName(child) == class_name:
                return child
        except:
            pass
    return 0

def LocalPlayer(players_instance):
    try:
        return pm.read_longlong(players_instance + int(offsets.get('LocalPlayer', '0x130'), 16))
    except:
        return 0

def GetCharacter(player):
    try:
        return pm.read_longlong(player + int(offsets.get('ModelInstance', '0x380'), 16))
    except:
        return 0

def GetPrimitive(instance):
    try:
        return pm.read_longlong(instance + int(offsets.get('Primitive', '0x148'), 16))
    except:
        return 0

def Position(instance):
    prim = GetPrimitive(instance)
    if not prim:
        return np.zeros(3, dtype=np.float32)
    try:
        return np.frombuffer(pm.read_bytes(prim + int(offsets.get('Position', '0xe4'), 16), 12), dtype=np.float32).copy()
    except:
        return np.zeros(3, dtype=np.float32)

def GetCharacterData(char):
    if not char:
        return {}
    try:
        children = GetChildren(char)
        if not children:
            return {}
        child_names = [GetName(c) for c in children]
        is_r15 = "UpperTorso" in child_names
        part_set = R15_PARTS if is_r15 else R6_PARTS
        parts = {}
        for inst, name in zip(children, child_names):
            if name in part_set and name != "HumanoidRootPart":
                parts[name] = inst
        humanoid = FindFirstChildOfClass(char, "Humanoid")
        if not humanoid:
            return {}
        max_health = pm.read_float(humanoid + int(offsets.get('MaxHealth', '0x1b4'), 16))
        if max_health <= 0:
            return {}
        return {"parts": parts, "is_r15": is_r15, "humanoid": humanoid, "max_health": max_health}
    except:
        return {}

def get_roblox_window_rect():
    try:
        hwnd = win32gui.FindWindow(None, "Roblox")
        if hwnd:
            rect = win32gui.GetWindowRect(hwnd)
            return rect[0], rect[1], rect[2]-rect[0], rect[3]-rect[1]
    except:
        pass
    return 0, 0, win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)

def batch_world_to_screen(positions, view_matrix, half_w, half_h):
    if positions.shape[0] == 0:
        return [None] * positions.shape[0]
    ones = np.ones((positions.shape[0], 1), dtype=np.float32)
    clip = np.hstack((positions, ones)) @ view_matrix.T
    w = clip[:, 3]
    valid = w > 0.001
    with np.errstate(divide='ignore', invalid='ignore'):
        ndc_x = np.where(valid, clip[:, 0] / w, 0)
        ndc_y = np.where(valid, clip[:, 1] / w, 0)
    in_frustum = valid & (np.abs(ndc_x) <= 1.05) & (np.abs(ndc_y) <= 1.05)
    screen_x = (ndc_x + 1) * half_w
    screen_y = (1 - ndc_y) * half_h
    result = []
    for i in range(len(positions)):
        if in_frustum[i]:
            result.append((int(screen_x[i]), int(screen_y[i])))
        else:
            result.append(None)
    return result

def calculate_perfect_bounding_box(parts_dict, positions_np, name_to_idx, view_matrix, half_w, half_h, is_r15):
    if len(positions_np) == 0:
        return None
    min_3d = np.min(positions_np, axis=0)
    max_3d = np.max(positions_np, axis=0)
    corners_3d = np.array([
        [min_3d[0], min_3d[1], min_3d[2]], [max_3d[0], min_3d[1], min_3d[2]],
        [min_3d[0], max_3d[1], min_3d[2]], [max_3d[0], max_3d[1], min_3d[2]],
        [min_3d[0], min_3d[1], max_3d[2]], [max_3d[0], min_3d[1], max_3d[2]],
        [min_3d[0], max_3d[1], max_3d[2]], [max_3d[0], max_3d[1], max_3d[2]]
    ], dtype=np.float32)
    screen_corners = batch_world_to_screen(corners_3d, view_matrix, half_w, half_h)
    valid_corners = [pt for pt in screen_corners if pt is not None]
    if not valid_corners:
        return None
    xs, ys = zip(*valid_corners)
    padding = 4
    return {'x': min(xs)-padding, 'y': min(ys)-padding, 
            'w': max(xs)-min(xs)+padding*2, 'h': max(ys)-min(ys)+padding*2}

def main():
    global pm, baseAddr, DataModel, Workspace, Players, offsets
    
    print("[*] Loading offsets...")
    offsets = load_offsets()
    print(f"[*] {offsets.get('RobloxVersion', 'Unknown')}")
    
    print("[*] Finding Roblox...")
    pid = find_roblox_process()
    if not pid:
        print("[-] Roblox not found")
        return
    
    print("[*] Attaching to process...")
    pm = MemoryManager(pid)
    baseAddr = get_module_base(pid)
    
    print("[*] Reading memory...")
    fake_ptr = pm.read_longlong(baseAddr + int(offsets.get('FakeDataModelPointer', '0x7d909f8'), 16))
    DataModel = pm.read_longlong(fake_ptr + int(offsets.get('FakeDataModelToDataModel', '0x1c0'), 16))
    Workspace = FindFirstChildOfClass(DataModel, "Workspace")
    Players = FindFirstChildOfClass(DataModel, "Players")
    
    visualEngine = pm.read_longlong(baseAddr + int(offsets.get('VisualEnginePointer', '0x79449e0'), 16))
    matrixAddr = visualEngine + int(offsets.get('viewmatrix', '0x120'), 16)
    
    print("[*] Starting ESP...")
    pme.overlay_init(title="ESP", fps=60, exitKey=0)
    sw, sh = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
    
    while pme.overlay_loop():
        pme.begin_drawing()
        
        win_x, win_y, win_width, win_height = get_roblox_window_rect()
        if win_width <= 0 or win_height <= 0:
            win_width, win_height = sw, sh
        
        half_w, half_h = win_width * 0.5, win_height * 0.5
        
        try:
            raw_vm = pm.read_bytes(matrixAddr, 64)
            view_matrix = np.frombuffer(raw_vm, dtype=np.float32).reshape(4, 4)
        except:
            pme.end_drawing()
            time.sleep(0.01)
            continue
        
        local_player = LocalPlayer(Players)
        if not local_player:
            pme.end_drawing()
            time.sleep(0.01)
            continue
        
        for player in GetChildren(Players):
            if player == local_player:
                continue
            
            char = GetCharacter(player)
            if not char:
                continue
            
            char_data = GetCharacterData(char)
            if not char_data:
                continue
            
            humanoid = char_data.get("humanoid", 0)
            if not humanoid:
                continue
            
            health = pm.read_float(humanoid + int(offsets.get('Health', '0x194'), 16))
            if health <= 0:
                continue
            
            parts_dict = char_data["parts"]
            if not parts_dict:
                continue
            
            positions_np = np.array([Position(p) for p in parts_dict.values()], dtype=np.float32)
            name_to_idx = {name: i for i, name in enumerate(parts_dict.keys())}
            bones = R15_BONES if char_data["is_r15"] else R6_BONES
            
            screen_points = batch_world_to_screen(positions_np, view_matrix, half_w, half_h)
            screens = {}
            for name, idx in name_to_idx.items():
                if screen_points[idx] is not None:
                    screens[name] = screen_points[idx]
            
            if not screens:
                continue
            
            bbox = calculate_perfect_bounding_box(parts_dict, positions_np, name_to_idx, 
                                                   view_matrix, half_w, half_h, char_data["is_r15"])
            if not bbox:
                continue
            
            bx, by, bw, bh = bbox['x'], bbox['y'], bbox['w'], bbox['h']
            pme.draw_rectangle_lines(bx, by, bw, bh, pme.new_color(255, 255, 255, 255), 1.0)
            
            for a, b in bones:
                if a in screens and b in screens:
                    x1, y1 = screens[a]
                    x2, y2 = screens[b]
                    pme.draw_line(x1, y1, x2, y2, pme.new_color(0, 255, 0, 255))
        
        pme.end_drawing()
        time.sleep(0.001)
    
    pme.overlay_close()

if __name__ == "__main__":
    main()