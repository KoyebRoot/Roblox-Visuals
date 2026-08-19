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

REMOTE_OFFSET_SOURCE = "https://imtheo.lol/Offsets/Offsets.hpp"
LOCAL_OFFSET_CACHE = "offsets.json"

BASE_OFFSET_DICT = {
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

def fetch_latest_offsets():
    try:
        resp = req.get(REMOTE_OFFSET_SOURCE, timeout=5)
        resp.raise_for_status()
        raw_cpp = resp.text
    except:
        raw_cpp = OFFSET_BACKUP
    
    parsed_data = {}
    current_scope = None
    for line in raw_cpp.splitlines():
        line = line.strip()
        scope_match = regex.match(r'namespace (\w+)', line)
        if scope_match:
            current_scope = scope_match.group(1)
            continue
        offset_match = regex.match(r'inline constexpr uintptr_t (\w+) = (0x[\da-fA-F]+);', line)
        if offset_match and current_scope:
            parsed_data[f"{current_scope}::{offset_match.group(1)}"] = offset_match.group(2)
        version_match = regex.match(r'inline std::string ClientVersion = "([^"]+)";', line)
        if version_match:
            parsed_data["ClientVersion"] = version_match.group(1)
    
    final_offsets = BASE_OFFSET_DICT.copy()
    
    mapping_table = {
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
    
    for json_key, cpp_key in mapping_table.items():
        if cpp_key in parsed_data:
            final_offsets[json_key] = parsed_data[cpp_key]
    
    if "ClientVersion" in parsed_data:
        final_offsets["RobloxVersion"] = f"Roblox Version: {parsed_data['ClientVersion']}"
    
    with open(LOCAL_OFFSET_CACHE, 'w') as f:
        js.dump(final_offsets, f, indent=2)
    
    return final_offsets

def load_saved_offsets():
    if oss.path.exists(LOCAL_OFFSET_CACHE):
        try:
            with open(LOCAL_OFFSET_CACHE, 'r') as f:
                return js.load(f)
        except:
            pass
    return fetch_latest_offsets()

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

class ProcessMemory:
    def __init__(self, proc_id):
        self.pid = proc_id
        self.handle = ct.windll.kernel32.OpenProcess(0x0010 | 0x0020 | 0x0008 | 0x0400, False, proc_id)

    def read_bytes(self, addr, size):
        buff = (ct.c_byte * size)()
        bytes_read = ct.c_size_t(0)
        ct.windll.ntdll.NtReadVirtualMemory(self.handle, ct.c_void_p(addr), 
                                            ct.byref(buff), size, ct.byref(bytes_read))
        return bytes(buff)

    def read_longlong(self, addr):
        return int.from_bytes(self.read_bytes(addr, 8), 'little', signed=True)

    def read_int(self, addr):
        return int.from_bytes(self.read_bytes(addr, 4), 'little', signed=True)

    def read_float(self, addr):
        return np.frombuffer(self.read_bytes(addr, 4), dtype=np.float32)[0]

    def read_string(self, addr, length):
        try:
            return self.read_bytes(addr, length).decode('utf-8').rstrip('\x00')
        except:
            return self.read_bytes(addr, length).decode('latin-1').rstrip('\x00')

def get_base_address(pid):
    hProc = ct.windll.kernel32.OpenProcess(0x0410, False, pid)
    if not hProc:
        return None
    modules = (ct.c_void_p * 1)()
    needed = ct.c_size_t()
    if ct.windll.psapi.EnumProcessModules(hProc, ct.byref(modules), ct.sizeof(modules), ct.byref(needed)):
        return int(modules[0])
    return None

def locate_roblox():
    for proc in pmproc.list_processes():
        try:
            if b"RobloxPlayerBeta.exe" in proc.szExeFile:
                return proc.th32ProcessID
        except:
            continue
    return None

def deref_ptr(addr):
    if not addr:
        return 0
    try:
        return mem.read_longlong(addr)
    except:
        return 0

def read_roblox_string(addr):
    try:
        length = mem.read_int(addr + 0x10)
        if length > 15:
            return mem.read_string(deref_ptr(addr), length)
        else:
            return mem.read_string(addr, length + 1)
    except:
        return ""

def get_instance_name(inst):
    if not inst:
        return ""
    try:
        container = deref_ptr(inst + int(offset_data.get('NameContainer', '0x0'), 16))
        if container:
            return read_roblox_string(container + int(offset_data.get('Name', '0xb0'), 16))
    except:
        pass
    return ""

def get_children(inst):
    if not inst:
        return []
    try:
        start = deref_ptr(inst + int(offset_data.get('Children', '0x70'), 16))
        if not start:
            return []
        end = deref_ptr(start + 8)
        children = []
        cur = deref_ptr(start)
        while cur != end and len(children) < 2000:
            child = mem.read_longlong(cur)
            if child:
                children.append(child)
            cur += 0x10
        return children
    except:
        return []

def get_class_name(inst):
    if not inst:
        return ""
    try:
        ptr = mem.read_longlong(inst + 0x18)
        ptr = mem.read_longlong(ptr + 0x8)
        if mem.read_longlong(ptr + 0x18) == 0x1F:
            ptr = mem.read_longlong(ptr)
        return read_roblox_string(ptr)
    except:
        return ""

def find_child_by_class(inst, class_name):
    for child in get_children(inst):
        try:
            if get_class_name(child) == class_name:
                return child
        except:
            pass
    return 0

def get_local_player(players_inst):
    try:
        return mem.read_longlong(players_inst + int(offset_data.get('LocalPlayer', '0x130'), 16))
    except:
        return 0

def get_character(player):
    try:
        return mem.read_longlong(player + int(offset_data.get('ModelInstance', '0x380'), 16))
    except:
        return 0

def get_primitive(inst):
    try:
        return mem.read_longlong(inst + int(offset_data.get('Primitive', '0x148'), 16))
    except:
        return 0

def get_position(inst):
    prim = get_primitive(inst)
    if not prim:
        return np.zeros(3, dtype=np.float32)
    try:
        return np.frombuffer(mem.read_bytes(prim + int(offset_data.get('Position', '0xe4'), 16), 12), dtype=np.float32).copy()
    except:
        return np.zeros(3, dtype=np.float32)

def extract_character_data(char):
    if not char:
        return {}
    try:
        children = get_children(char)
        if not children:
            return {}
        names = [get_instance_name(c) for c in children]
        is_r15 = "UpperTorso" in names
        part_set = R15_BODY if is_r15 else R6_BODY
        parts = {}
        for inst, name in zip(children, names):
            if name in part_set and name != "HumanoidRootPart":
                parts[name] = inst
        humanoid = find_child_by_class(char, "Humanoid")
        if not humanoid:
            return {}
        max_hp = mem.read_float(humanoid + int(offset_data.get('MaxHealth', '0x1b4'), 16))
        if max_hp <= 0:
            return {}
        return {"parts": parts, "is_r15": is_r15, "humanoid": humanoid, "max_health": max_hp}
    except:
        return {}

def get_roblox_window():
    try:
        hwnd = w32gui.FindWindow(None, "Roblox")
        if hwnd:
            rect = w32gui.GetWindowRect(hwnd)
            return rect[0], rect[1], rect[2]-rect[0], rect[3]-rect[1]
    except:
        pass
    return 0, 0, w32api.GetSystemMetrics(0), w32api.GetSystemMetrics(1)

def project_to_screen(positions, view_mat, half_w, half_h):
    if positions.shape[0] == 0:
        return [None] * positions.shape[0]
    ones = np.ones((positions.shape[0], 1), dtype=np.float32)
    clip = np.hstack((positions, ones)) @ view_mat.T
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

def main():
    global mem, base_addr, data_model, workspace, players, offset_data
    
    print("[*] Loading offset configuration...")
    offset_data = load_saved_offsets()
    print(f"[*] {offset_data.get('RobloxVersion', 'Unknown Version')}")
    
    print("[*] Searching for Roblox process...")
    proc_id = locate_roblox()
    if not proc_id:
        print("[-] Roblox process not detected")
        return
    
    print("[*] Attaching memory interface...")
    mem = ProcessMemory(proc_id)
    base_addr = get_base_address(proc_id)
    
    print("[*] Reading game memory...")
    fake_ptr = mem.read_longlong(base_addr + int(offset_data.get('FakeDataModelPointer', '0x7d909f8'), 16))
    data_model = mem.read_longlong(fake_ptr + int(offset_data.get('FakeDataModelToDataModel', '0x1c0'), 16))
    workspace = find_child_by_class(data_model, "Workspace")
    players = find_child_by_class(data_model, "Players")
    
    vis_engine = mem.read_longlong(base_addr + int(offset_data.get('VisualEnginePointer', '0x79449e0'), 16))
    view_matrix_addr = vis_engine + int(offset_data.get('viewmatrix', '0x120'), 16)
    
    print("[*] Activating overlay...")
    pyow.overlay_init(title="ESP", fps=60, exitKey=0)
    screen_w, screen_h = w32api.GetSystemMetrics(0), w32api.GetSystemMetrics(1)
    
    while pyow.overlay_loop():
        pyow.begin_drawing()
        
        win_x, win_y, win_width, win_height = get_roblox_window()
        if win_width <= 0 or win_height <= 0:
            win_width, win_height = screen_w, screen_h
        
        half_w, half_h = win_width * 0.5, win_height * 0.5
        
        try:
            raw_matrix = mem.read_bytes(view_matrix_addr, 64)
            view_matrix = np.frombuffer(raw_matrix, dtype=np.float32).reshape(4, 4)
        except:
            pyow.end_drawing()
            tm.sleep(0.01)
            continue
        
        local_player = get_local_player(players)
        if not local_player:
            pyow.end_drawing()
            tm.sleep(0.01)
            continue
        
        for player in get_children(players):
            if player == local_player:
                continue
            
            character = get_character(player)
            if not character:
                continue
            
            char_info = extract_character_data(character)
            if not char_info:
                continue
            
            humanoid = char_info.get("humanoid", 0)
            if not humanoid:
                continue
            
            hp = mem.read_float(humanoid + int(offset_data.get('Health', '0x194'), 16))
            if hp <= 0:
                continue
            
            body_parts = char_info["parts"]
            if not body_parts:
                continue
            
            positions = np.array([get_position(p) for p in body_parts.values()], dtype=np.float32)
            name_index = {name: i for i, name in enumerate(body_parts.keys())}
            skeleton = R15_CONNECT if char_info["is_r15"] else R6_CONNECT
            
            projected = project_to_screen(positions, view_matrix, half_w, half_h)
            visible_parts = {}
            for name, idx in name_index.items():
                if projected[idx] is not None:
                    visible_parts[name] = projected[idx]
            
            if not visible_parts:
                continue
            
            for a, b in skeleton:
                if a in visible_parts and b in visible_parts:
                    x1, y1 = visible_parts[a]
                    x2, y2 = visible_parts[b]
                    pyow.draw_line(x1, y1, x2, y2, pyow.new_color(0, 255, 0, 255))
        
        pyow.end_drawing()
        tm.sleep(0.001)
    
    pyow.overlay_close()

if __name__ == "__main__":
    main()