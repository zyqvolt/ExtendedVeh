#!/usr/bin/env python3
"""Run the real PC collision callback/selector bodies with a simulated engine."""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
plugin = (ROOT / 'Client/Plugin.cpp').read_text()
bindings = (ROOT / 'Client/CustomVehicleBindingManager.cpp').read_text()


def function(source, name):
    pos = source.index(name + '(')
    start = source.rfind('\n', 0, pos) + 1
    brace = source.index('{', pos)
    # These four functions contain no braces in string literals.
    depth = 1
    end = brace + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end] + '\n'


assert not re.search(r'MH_(?:Create|Enable|Disable|Remove)Hook\([^;\n]*0x41B1D0', plugin)
init = plugin[plugin.index('Events::initRwEvent.Add'):plugin.index('Events::shutdownRwEvent.Add')]
assert 'RegisterClumpCollisionReader(true);' in init
shutdown = plugin[plugin.index('Events::shutdownRwEvent.Add'):]
assert 'RegisterClumpCollisionReader(false);' in shutdown

prefix = r'''
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <mutex>
#include <shared_mutex>
#include <unordered_map>
#include <cstdlib>
#define __cdecl
#define __fastcall
using RwInt32 = int32_t;
using RwUInt32 = uint32_t;
struct RwStream { unsigned skipped = 0; };
using RwPluginDataChunkReadCallBack = RwStream*(*)(RwStream*, RwInt32, void*, RwInt32, RwInt32);
using RwPluginDataChunkWriteCallBack = RwStream*(*)(RwStream*, RwInt32, const void*, RwInt32, RwInt32);
using RwPluginDataChunkGetSizeCallBack = RwInt32(*)(const void*, RwInt32, RwInt32);
static int checks, originalReads, registrations, errors, registryResult;
#define CHECK(condition) do { ++checks; if (!(condition)) { std::fprintf(stderr, "line %d: %s\n", __LINE__, #condition); std::abort(); } } while (false)
static RwStream* expectedStream;
static void* expectedObject;
static RwStream* OriginalRead(RwStream* stream, RwInt32 len, void* obj, RwInt32 offset, RwInt32 size) {
    CHECK(stream == expectedStream && obj == expectedObject && len == 64 && offset == 23 && size == 37);
    ++originalReads;
    return stream;
}
static const auto g_origClumpCollisionRead = OriginalRead;
static bool s_bLoadingCustomVehicleDff, s_collisionReaderRegistered;
static RwPluginDataChunkReadCallBack registeredRead;
static RwInt32 RpClumpRegisterPluginStream(RwUInt32 id, RwPluginDataChunkReadCallBack read,
    RwPluginDataChunkWriteCallBack write, RwPluginDataChunkGetSizeCallBack size) {
    CHECK(id == 0x253F2FA && write == reinterpret_cast<RwPluginDataChunkWriteCallBack>(0x41B2F0)
        && size == reinterpret_cast<RwPluginDataChunkGetSizeCallBack>(0x41B300));
    ++registrations;
    if (registryResult >= 0) registeredRead = read;
    return registryResult;
}
static RwStream* RwStreamSkip(RwStream* stream, unsigned length) { stream->skipped += length; return stream; }
enum class LogLevel { Error };
static void ClientLog(LogLevel, const char*) { ++errors; }
struct ColData { int m_nNumLines; void* m_pLines; };
struct CColModel { ColData* m_pColData; };
constexpr int ENTITY_TYPE_VEHICLE = 2;
struct CEntity { int m_nType = 0; };
struct CVehicle : CEntity { unsigned char m_nSpecialColModel = 255; };
static std::unordered_map<CVehicle*, CColModel*> s_fastVehicleColMap;
static std::shared_mutex s_fastColMutex;
static std::atomic<bool> s_hasCustomCols{false};
class CustomVehicleBindingManager { public: static CColModel* GetCollisionForVehicle(CVehicle*); };
static CColModel baseCol{}, specialCol{};
static int originalGets;
static CColModel* OriginalGet(CEntity* entity) {
    ++originalGets;
    if (entity && entity->m_nType == ENTITY_TYPE_VEHICLE
        && static_cast<signed char>(reinterpret_cast<CVehicle*>(entity)->m_nSpecialColModel) > -1) return &specialCol;
    return &baseCol;
}
using GetColModelFn = CColModel*(*)(CEntity*);
static GetColModelFn g_origGetColModel = OriginalGet;
'''
main = r'''
int main() {
    RwStream stream; int object; expectedStream = &stream; expectedObject = &object;
    RegisterClumpCollisionReader(false); CHECK(registrations == 0);
    RegisterClumpCollisionReader(true); CHECK(s_collisionReaderRegistered && registeredRead == Hooked_ClumpCollisionRead);
    CHECK(registeredRead(&stream, 64, &object, 23, 37) == &stream && originalReads == 1 && !stream.skipped);
    s_bLoadingCustomVehicleDff = true;
    CHECK(registeredRead(&stream, 64, &object, 23, 37) == &stream && originalReads == 1 && stream.skipped == 64);
    s_bLoadingCustomVehicleDff = false;
    CHECK(registeredRead(&stream, 64, &object, 23, 37) == &stream && originalReads == 2);
    RegisterClumpCollisionReader(false); CHECK(!s_collisionReaderRegistered && registeredRead == OriginalRead);
    int previous = registrations;
    RegisterClumpCollisionReader(false); CHECK(registrations == previous);
    registryResult = -1; RegisterClumpCollisionReader(true); CHECK(!s_collisionReaderRegistered && errors == 1);

    CVehicle car; car.m_nType = ENTITY_TYPE_VEHICLE;
    ColData data{4, &object}; CColModel custom{&data};
    CHECK(Hooked_GetColModel(&car, nullptr) == &baseCol);
    s_fastVehicleColMap[&car] = &custom; s_hasCustomCols = true;
    CHECK(Hooked_GetColModel(&car, nullptr) == &custom);
    // GTA masks suspension lines in collision tests. The body must not become the base car.
    data.m_nNumLines = 0; CHECK(Hooked_GetColModel(&car, nullptr) == &custom);
    data.m_nNumLines = 4; CHECK(Hooked_GetColModel(&car, nullptr) == &custom);
    for (unsigned char slot = 0; slot < 4; ++slot) {
        car.m_nSpecialColModel = slot;
        CHECK(Hooked_GetColModel(&car, nullptr) == &specialCol);
    }
    car.m_nSpecialColModel = 255;
    CHECK(Hooked_GetColModel(&car, nullptr) == &custom);
    CVehicle unbound; unbound.m_nType = ENTITY_TYPE_VEHICLE;
    CHECK(Hooked_GetColModel(&unbound, nullptr) == &baseCol);
    CEntity ped; ped.m_nType = 3;
    CHECK(Hooked_GetColModel(&ped, nullptr) == &baseCol);
    custom.m_pColData = nullptr; CHECK(Hooked_GetColModel(&car, nullptr) == &baseCol);
    custom.m_pColData = &data; s_fastVehicleColMap.erase(&car);
    CHECK(Hooked_GetColModel(&car, nullptr) == &baseCol);
    CHECK(CustomVehicleBindingManager::GetCollisionForVehicle(nullptr) == nullptr);
    CHECK(Hooked_GetColModel(nullptr, nullptr) == &baseCol);
    std::printf("PC collision callbacks and selection: %d checks passed\n", checks);
}
'''
code = prefix + function(plugin, 'Hooked_ClumpCollisionRead') + function(plugin, 'RegisterClumpCollisionReader')
code += function(bindings, 'CustomVehicleBindingManager::GetCollisionForVehicle')
code += function(plugin, 'Hooked_GetColModel') + main
with tempfile.TemporaryDirectory(prefix='extendedveh-collision-') as directory:
    source = Path(directory) / 'collision.cpp'
    executable = Path(directory) / 'collision-test'
    source.write_text(code)
    subprocess.run(['c++', '-std=c++20', '-Wall', '-Wextra', '-Werror', str(source), '-o', str(executable)], check=True)
    subprocess.run([str(executable)], check=True)
