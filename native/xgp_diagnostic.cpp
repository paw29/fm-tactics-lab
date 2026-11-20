#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <appmodel.h>
#include <bcrypt.h>
#include <shobjidl.h>
#include <shellapi.h>
#include <tlhelp32.h>
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cwctype>
#include <deque>
#include <filesystem>
#include <optional>
#include <set>
#include <string>
#include <vector>

#pragma comment(lib, "advapi32.lib")
#pragma comment(lib, "bcrypt.lib")
#pragma comment(lib, "ole32.lib")
#pragma comment(lib, "shell32.lib")
#pragma comment(lib, "user32.lib")
#pragma comment(lib, "uuid.lib")
#pragma comment(lib, "version.lib")

namespace fs = std::filesystem;
constexpr char version[] = "1";
constexpr auto plugin_relative = L"fm_Data/Plugins/x86_64/game_plugin.dll";
constexpr char sample_hash[] = "ae60203e75be891a1911377d9fa6721628b34f6a689e598bc08f995367623f6a";

static std::string utf8(const std::wstring& value) {
    const int size = WideCharToMultiByte(CP_UTF8, 0, value.data(), int(value.size()), nullptr, 0, nullptr, nullptr);
    std::string result(size, '\0');
    WideCharToMultiByte(CP_UTF8, 0, value.data(), int(value.size()), result.data(), size, nullptr, nullptr);
    return result;
}

static std::wstring lower(std::wstring value) {
    std::transform(value.begin(), value.end(), value.begin(), [](wchar_t c) { return wchar_t(std::towlower(c)); });
    return value;
}

static bool is_file(const fs::path& path) {
    std::error_code error;
    return fs::is_regular_file(path, error);
}

static void log_line(HANDLE log, const std::string& line) {
    const auto record = std::to_string(GetTickCount64()) + " " + line + "\r\n";
    DWORD written = 0;
    WriteFile(log, record.data(), DWORD(record.size()), &written, nullptr);
    FlushFileBuffers(log);
}

static std::string hex(uint64_t number) {
    char buffer[24];
    sprintf_s(buffer, "0x%llX", static_cast<unsigned long long>(number));
    return buffer;
}

static std::string win_error(DWORD code) {
    wchar_t message[512]{};
    FormatMessageW(FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS, nullptr, code, 0,
                   message, ARRAYSIZE(message), nullptr);
    std::wstring text = message;
    while (!text.empty() && (text.back() == L'\r' || text.back() == L'\n')) text.pop_back();
    return "win32=" + std::to_string(code) + " (" + hex(code) + ") " + utf8(text);
}

static std::string file_version(const fs::path& file) {
    const DWORD size = GetFileVersionInfoSizeW(file.c_str(), nullptr);
    if (!size) return "unavailable";
    std::vector<unsigned char> data(size);
    if (!GetFileVersionInfoW(file.c_str(), 0, size, data.data())) return "unavailable";
    struct Translation { WORD language, codepage; };
    void* values = nullptr;
    UINT length = 0;
    if (VerQueryValueW(data.data(), L"\\VarFileInfo\\Translation", &values, &length) && length >= sizeof(Translation)) {
        const auto translation = *static_cast<Translation*>(values);
        wchar_t field[80];
        swprintf_s(field, L"\\StringFileInfo\\%04x%04x\\ProductVersion", translation.language, translation.codepage);
        if (VerQueryValueW(data.data(), field, &values, &length) && length)
            return utf8(static_cast<const wchar_t*>(values));
    }
    if (!VerQueryValueW(data.data(), L"\\", &values, &length) || length < sizeof(VS_FIXEDFILEINFO))
        return "unavailable";
    const auto info = *static_cast<VS_FIXEDFILEINFO*>(values);
    return std::to_string(HIWORD(info.dwProductVersionMS)) + "." + std::to_string(LOWORD(info.dwProductVersionMS))
        + "." + std::to_string(HIWORD(info.dwProductVersionLS)) + "." + std::to_string(LOWORD(info.dwProductVersionLS));
}

struct Image {
    HANDLE file = INVALID_HANDLE_VALUE, mapping = nullptr;
    const unsigned char* data = nullptr;
    size_t size = 0;
    IMAGE_NT_HEADERS64 nt{};
    std::vector<IMAGE_SECTION_HEADER> sections;

    ~Image() {
        if (data) UnmapViewOfFile(data);
        if (mapping) CloseHandle(mapping);
        if (file != INVALID_HANDLE_VALUE) CloseHandle(file);
    }

    const unsigned char* raw(size_t offset, size_t count) const {
        return offset <= size && count <= size - offset ? data + offset : nullptr;
    }

    const unsigned char* rva(uint32_t address, size_t count) const {
        if (address < nt.OptionalHeader.SizeOfHeaders) return raw(address, count);
        for (const auto& section : sections) {
            if (address < section.VirtualAddress) continue;
            const size_t offset = address - section.VirtualAddress;
            if (offset <= section.SizeOfRawData && count <= section.SizeOfRawData - offset)
                return raw(size_t(section.PointerToRawData) + offset, count);
        }
        return nullptr;
    }

    bool open(const fs::path& path, std::string& reason) {
        file = CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                           nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (file == INVALID_HANDLE_VALUE) { reason = win_error(GetLastError()); return false; }
        LARGE_INTEGER bytes{};
        if (!GetFileSizeEx(file, &bytes) || bytes.QuadPart < 64 || bytes.QuadPart > 1024LL * 1024 * 1024) {
            reason = "unsupported_file_size";
            return false;
        }
        size = size_t(bytes.QuadPart);
        mapping = CreateFileMappingW(file, nullptr, PAGE_READONLY, 0, 0, nullptr);
        if (mapping) data = static_cast<const unsigned char*>(MapViewOfFile(mapping, FILE_MAP_READ, 0, 0, 0));
        if (!data) { reason = win_error(GetLastError()); return false; }
        IMAGE_DOS_HEADER dos{};
        memcpy(&dos, data, sizeof(dos));
        if (dos.e_magic != IMAGE_DOS_SIGNATURE || dos.e_lfanew < 0 || !raw(dos.e_lfanew, sizeof(nt))) {
            reason = "invalid_PE_header";
            return false;
        }
        memcpy(&nt, raw(dos.e_lfanew, sizeof(nt)), sizeof(nt));
        if (nt.Signature != IMAGE_NT_SIGNATURE || nt.FileHeader.Machine != IMAGE_FILE_MACHINE_AMD64
            || nt.OptionalHeader.Magic != IMAGE_NT_OPTIONAL_HDR64_MAGIC
            || nt.FileHeader.NumberOfSections == 0 || nt.FileHeader.NumberOfSections > 96
            || nt.FileHeader.SizeOfOptionalHeader < sizeof(IMAGE_OPTIONAL_HEADER64)) {
            reason = "unsupported_layout_or_machine=" + hex(nt.FileHeader.Machine);
            return false;
        }
        const size_t table = size_t(dos.e_lfanew) + 24 + nt.FileHeader.SizeOfOptionalHeader;
        const size_t table_size = nt.FileHeader.NumberOfSections * sizeof(IMAGE_SECTION_HEADER);
        if (!raw(table, table_size)) { reason = "truncated_section_table"; return false; }
        sections.resize(nt.FileHeader.NumberOfSections);
        memcpy(sections.data(), raw(table, table_size), table_size);
        return true;
    }

    std::string string_at(uint32_t address) const {
        std::string result;
        for (unsigned i = 0; i < 256; ++i) {
            const auto byte = rva(address + i, 1);
            if (!byte || *byte == 0) return result;
            if (*byte < 32 || *byte > 126) return {};
            result.push_back(char(*byte));
        }
        return {};
    }

    std::string sha256() const {
        BCRYPT_ALG_HANDLE algorithm = nullptr;
        std::array<unsigned char, 32> digest{};
        if (BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, nullptr, 0) < 0)
            return "unavailable";
        const auto result = BCryptHash(algorithm, nullptr, 0, const_cast<unsigned char*>(data), ULONG(size),
                                       digest.data(), ULONG(digest.size()));
        BCryptCloseAlgorithmProvider(algorithm, 0);
        if (result < 0) return "unavailable";
        char buffer[65]{};
        for (size_t i = 0; i < digest.size(); ++i) sprintf_s(buffer + i * 2, 3, "%02x", digest[i]);
        return buffer;
    }

    uint32_t exported(const char* name, uint16_t import_ordinal = 0) const {
        const auto address = nt.OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXPORT].VirtualAddress;
        auto bytes = rva(address, sizeof(IMAGE_EXPORT_DIRECTORY));
        if (!address || !bytes) return 0;
        IMAGE_EXPORT_DIRECTORY directory{};
        memcpy(&directory, bytes, sizeof(directory));
        if (directory.NumberOfNames > 65536 || directory.NumberOfFunctions > 65536) return 0;
        if (!name) {
            if (import_ordinal < directory.Base || import_ordinal - directory.Base >= directory.NumberOfFunctions)
                return 0;
            const auto target = rva(directory.AddressOfFunctions + (import_ordinal - directory.Base) * 4, 4);
            uint32_t entry = 0;
            if (target) memcpy(&entry, target, sizeof(entry));
            return entry;
        }
        for (unsigned i = 0; i < directory.NumberOfNames; ++i) {
            bytes = rva(directory.AddressOfNames + i * sizeof(uint32_t), sizeof(uint32_t));
            if (!bytes) return 0;
            uint32_t entry = 0;
            memcpy(&entry, bytes, sizeof(entry));
            if (string_at(entry) != name) continue;
            uint16_t ordinal = 0;
            bytes = rva(directory.AddressOfNameOrdinals + i * sizeof(ordinal), sizeof(ordinal));
            if (!bytes) return 0;
            memcpy(&ordinal, bytes, sizeof(ordinal));
            if (ordinal >= directory.NumberOfFunctions) return 0;
            const auto target = rva(directory.AddressOfFunctions + ordinal * sizeof(uint32_t), sizeof(uint32_t));
            if (!target) return 0;
            memcpy(&entry, target, sizeof(entry));
            return entry;
        }
        return 0;
    }
};

struct Import { std::string name; bool delayed; uint32_t iat; uint32_t lookup; };

static std::vector<Import> imports(const Image& image) {
    std::vector<Import> result;
    for (const bool delayed : {false, true}) {
        const auto directory = image.nt.OptionalHeader.DataDirectory[
            delayed ? IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT : IMAGE_DIRECTORY_ENTRY_IMPORT];
        const uint32_t stride = delayed ? 32 : sizeof(IMAGE_IMPORT_DESCRIPTOR);
        for (uint32_t offset = 0; directory.VirtualAddress && offset + stride <= directory.Size
             && offset < 1024 * stride; offset += stride) {
            const auto raw = image.rva(directory.VirtualAddress + offset, stride);
            if (!raw) break;
            uint32_t name = 0, iat = 0, lookup = 0;
            if (delayed) {
                uint32_t attributes = 0;
                memcpy(&attributes, raw, 4);
                if (!(attributes & 1)) break;
                memcpy(&name, raw + 4, 4);
                memcpy(&iat, raw + 12, 4);
                memcpy(&lookup, raw + 16, 4);
            } else {
                IMAGE_IMPORT_DESCRIPTOR entry{};
                memcpy(&entry, raw, sizeof(entry));
                name = entry.Name;
                iat = entry.FirstThunk;
                lookup = entry.OriginalFirstThunk ? entry.OriginalFirstThunk : iat;
            }
            if (!name) break;
            const auto dll = image.string_at(name);
            if (!dll.empty() && dll.find_first_of("\\/:\"") == std::string::npos) result.push_back({dll, delayed, iat, lookup});
        }
    }
    return result;
}

static void check_gdk_exports(HANDLE log, const Image& consumer, const Import& dep, const fs::path& local) {
    if (!dep.lookup) return;
    Image library;
    std::string reason;
    if (!library.open(local, reason)) return;  // The recursive scan logs the file error.
    for (uint32_t index = 0; index < 4096; ++index) {
        const auto bytes = consumer.rva(dep.lookup + index * 8, 8);
        uint64_t thunk = 0;
        if (bytes) memcpy(&thunk, bytes, sizeof(thunk));
        if (!thunk) break;
        std::string symbol;
        bool found = false;
        if (thunk & IMAGE_ORDINAL_FLAG64) {
            const auto ordinal = uint16_t(thunk);
            symbol = "#" + std::to_string(ordinal);
            found = library.exported(nullptr, ordinal) != 0;
        } else {
            if (thunk > UINT32_MAX - 2) break;
            symbol = consumer.string_at(uint32_t(thunk) + 2);
            if (symbol.empty()) break;
            found = library.exported(symbol.c_str()) != 0;
        }
        if (!found) log_line(log, "dependency_export_missing dll=" + dep.name + " symbol=" + symbol);
    }
}

static std::optional<uint32_t> activation_flag(const unsigned char* bytes, uint32_t wait_rva, uint32_t image_size) {
    constexpr unsigned char prefix[] = {0x48,0x8d,0xa4,0x24,0xd8,0xff,0xff,0xff,0x83,0x3d};
    constexpr unsigned char suffix[] = {0,0x74,4,0xf3,0x90,0xeb,0xf3,0x48,0x8d,0xa4,0x24,0x28,0,0,0,0xc3};
    if (!bytes || memcmp(bytes, prefix, sizeof(prefix)) || memcmp(bytes + 14, suffix, sizeof(suffix))) return {};
    int32_t displacement = 0;
    memcpy(&displacement, bytes + sizeof(prefix), sizeof(displacement));
    const int64_t rva = int64_t(wait_rva) + 15 + displacement;
    if (rva < 0 || rva + sizeof(uint32_t) > image_size) return {};
    return uint32_t(rva);
}

static bool readable(const void* address, size_t size) {
    MEMORY_BASIC_INFORMATION region{};
    if (!VirtualQuery(address, &region, sizeof(region)) || region.State != MEM_COMMIT
        || (region.Protect & (PAGE_NOACCESS | PAGE_GUARD))) return false;
    const auto offset = uintptr_t(address) - uintptr_t(region.BaseAddress);
    return offset <= region.RegionSize && size <= region.RegionSize - offset;
}

static fs::path resolve_root(const fs::path& selected, HANDLE log = INVALID_HANDLE_VALUE) {
    auto candidate = selected;
    for (int depth = 0; depth < 5 && !candidate.empty(); ++depth) {
        for (const auto& folder : {candidate, candidate / L"Content"}) {
            const auto path = folder / plugin_relative;
            const auto attributes = GetFileAttributesW(path.c_str());
            if (attributes != INVALID_FILE_ATTRIBUTES && !(attributes & FILE_ATTRIBUTE_DIRECTORY)) return folder;
            const auto error = attributes == INVALID_FILE_ATTRIBUTES ? GetLastError() : ERROR_DIRECTORY;
            if (log != INVALID_HANDLE_VALUE)
                log_line(log, "candidate_plugin_unavailable path=" + utf8(path.wstring()) + " " + win_error(error));
        }
        const auto parent = candidate.parent_path();
        if (parent == candidate) break;
        candidate = parent;
    }
    return {};
}

static std::wstring choose_folder() {
    const HRESULT initialized = CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED | COINIT_DISABLE_OLE1DDE);
    if (FAILED(initialized)) return {};
    IFileOpenDialog* dialog = nullptr;
    std::wstring selected;
    if (SUCCEEDED(CoCreateInstance(CLSID_FileOpenDialog, nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&dialog)))) {
        dialog->SetOptions(FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM);
        dialog->SetTitle(L"选择 Xbox 应用中 FM27 的安装文件夹（或 Content 文件夹）");
        if (SUCCEEDED(dialog->Show(nullptr))) {
            IShellItem* item = nullptr;
            if (SUCCEEDED(dialog->GetResult(&item))) {
                PWSTR path = nullptr;
                if (SUCCEEDED(item->GetDisplayName(SIGDN_FILESYSPATH, &path))) {
                    selected = path;
                    CoTaskMemFree(path);
                }
                item->Release();
            }
        }
        dialog->Release();
    }
    CoUninitialize();
    return selected;
}

static std::set<fs::path> discover(HANDLE log) {
    std::set<fs::path> found;
    const DWORD drives = GetLogicalDrives();
    for (int i = 0; i < 26; ++i) {
        if (!(drives & (1u << i))) continue;
        const wchar_t drive[]{wchar_t(L'A' + i), L':', L'\\', 0};
        if (GetDriveTypeW(drive) != DRIVE_FIXED) continue;
        const fs::path library = fs::path(drive) / L"XboxGames";
        std::error_code error;
        for (fs::directory_iterator it(library, fs::directory_options::skip_permission_denied, error), end;
             !error && it != end; it.increment(error)) {
            if (lower(it->path().filename().wstring()).find(L"football manager 27") != std::wstring::npos) {
                const auto path = resolve_root(it->path());
                if (!path.empty()) found.insert(path);
            }
        }
    }
    for (const auto& path : found) log_line(log, "candidate_game_root=" + utf8(path.wstring()));
    return found;
}

static void services(HANDLE log) {
    const auto scm = OpenSCManagerW(nullptr, nullptr, SC_MANAGER_CONNECT);
    if (!scm) { log_line(log, "service_query_failed " + win_error(GetLastError())); return; }
    for (const auto name : {L"GamingServices", L"GamingServicesNet", L"XblAuthManager"}) {
        const auto service = OpenServiceW(scm, name, SERVICE_QUERY_STATUS);
        SERVICE_STATUS status{};
        const bool queried = service && QueryServiceStatus(service, &status);
        log_line(log, "service=" + utf8(name) + (queried ? " state=" + std::to_string(status.dwCurrentState)
                                                        : " " + win_error(GetLastError())));
        if (service) CloseServiceHandle(service);
    }
    CloseServiceHandle(scm);
}

static bool inspect(HANDLE log, const fs::path& dll, const fs::path& root) {
    Image image;
    std::string reason;
    if (!image.open(dll, reason)) {
        log_line(log, "stage=pe_invalid " + reason);
        return false;
    }
    const auto hash = image.sha256();
    log_line(log, "stage=pe_ok path=" + utf8(dll.wstring()) + " bytes=" + std::to_string(image.size)
             + " version=" + file_version(dll) + " sha256=" + hash
             + " reference_2494687=" + (hash == sample_hash ? "yes" : "no"));
    log_line(log, "image_base=" + hex(image.nt.OptionalHeader.ImageBase)
             + " image_size=" + hex(image.nt.OptionalHeader.SizeOfImage)
             + " entry_rva=" + hex(image.nt.OptionalHeader.AddressOfEntryPoint)
             + " machine=" + hex(image.nt.FileHeader.Machine));
    for (const auto& section : image.sections) {
        const std::string name(reinterpret_cast<const char*>(section.Name),
                               strnlen_s(reinterpret_cast<const char*>(section.Name), sizeof(section.Name)));
        log_line(log, "section=" + name + " rva=" + hex(section.VirtualAddress) + " size=" + hex(section.Misc.VirtualSize)
                 + " flags=" + hex(section.Characteristics));
    }
    const auto wait_rva = image.exported("WaitForActivation");
    const auto unity_rva = image.exported("UnityPluginLoad");
    const auto flag = wait_rva ? activation_flag(image.rva(wait_rva, 30), wait_rva, image.nt.OptionalHeader.SizeOfImage) : std::nullopt;
    log_line(log, "exports WaitForActivation=" + hex(wait_rva) + " UnityPluginLoad=" + hex(unity_rva)
             + " activation_flag_rva=" + (flag ? hex(*flag) : "signature_unknown"));
    for (const auto relative : {L"fm.exe", L"MicrosoftGame.config", L"AppxManifest.xml", L"icudt65l.dat",
                                L"shared/data/simatch.fmf", L"shared/data/simatchshared.fmf"}) {
        const auto path = root / relative;
        std::error_code error;
        const auto bytes = fs::file_size(path, error);
        log_line(log, "resource=" + utf8(relative) + (error ? " unavailable error=" + std::to_string(error.value())
                                                            : " bytes=" + std::to_string(bytes)));
    }
    wchar_t system[MAX_PATH]{};
    GetSystemDirectoryW(system, ARRAYSIZE(system));
    auto entries = imports(image);
    std::set<fs::path> visited{dll};
    std::deque<fs::path> pending;
    unsigned missing = 0;
    const auto scan = [&](const Image& consumer, const fs::path& owner, const std::vector<Import>& dependencies) {
        for (const auto& dep : dependencies) {
            const auto filename = fs::path(dep.name).wstring();
            const auto folded = lower(filename);
            std::string status;
            if (folded.starts_with(L"api-ms-win-") || folded.starts_with(L"ext-ms-win-")) {
                status = "api_set";
            } else {
                fs::path local;
                for (const auto& folder : {owner.parent_path(), dll.parent_path(), root}) {
                    if (is_file(folder / filename)) { local = folder / filename; break; }
                }
                if (!local.empty()) {
                    status = "game_local path=" + utf8(local.wstring());
                    if (visited.insert(local).second) pending.push_back(local);
                    if (folded == L"xcurl.dll" || folded == L"party.dll" || folded == L"playfabmultiplayergdk.dll"
                        || folded == L"libhttpclient.gdk.dll")
                        check_gdk_exports(log, consumer, dep, local);
                } else if (is_file(fs::path(system) / filename)) {
                    status = "system";
                } else {
                    if (!dep.delayed) ++missing;
                    status = "not_in_sampled_directories";
                }
            }
            log_line(log, "import module=" + utf8(owner.filename().wstring()) + " dependency=" + dep.name
                     + " kind=" + (dep.delayed ? "delay" : "normal") + " iat=" + hex(dep.iat) + " " + status);
        }
    };
    scan(image, dll, entries);
    for (unsigned i = 0; !pending.empty() && i < 64; ++i) {
        const auto dependency = pending.front();
        pending.pop_front();
        Image dep;
        reason.clear();
        if (!dep.open(dependency, reason))
            log_line(log, "dependency_PE_invalid path=" + utf8(dependency.wstring()) + " " + reason);
        else {
            log_line(log, "dependency_PE_ok path=" + utf8(dependency.wstring()) + " version=" + file_version(dependency));
            scan(dep, dependency, imports(dep));
        }
    }
    log_line(log, "stage=dependency_scan_complete normal_missing=" + std::to_string(missing)
             + " deferred_modules=" + std::to_string(pending.size()));
    const bool gdk = std::any_of(entries.begin(), entries.end(), [](const Import& item) {
        return _stricmp(item.name.c_str(), "PlayFabMultiplayerGDK.dll") == 0
            || _stricmp(item.name.c_str(), "libHttpClient.GDK.dll") == 0;
    });
    log_line(log, std::string("game_pass_import_signature=") + (gdk ? "yes" : "no"));
    return gdk && wait_rva && unity_rva;
}

static HANDLE exception_log = INVALID_HANDLE_VALUE;
static volatile LONG exceptions = 0;

static LONG CALLBACK observe(EXCEPTION_POINTERS* exception) {
    const auto record = exception->ExceptionRecord;
    const DWORD code = record->ExceptionCode;
    if (code != EXCEPTION_ACCESS_VIOLATION && code != EXCEPTION_ILLEGAL_INSTRUCTION && code != EXCEPTION_IN_PAGE_ERROR
        && code != EXCEPTION_STACK_OVERFLOW && code != 0xe06d7363) return EXCEPTION_CONTINUE_SEARCH;
    if (InterlockedIncrement(&exceptions) > 12) return EXCEPTION_CONTINUE_SEARCH;
    MEMORY_BASIC_INFORMATION memory{};
    VirtualQuery(record->ExceptionAddress, &memory, sizeof(memory));
    char line[240];
    const int size = sprintf_s(line, "first_chance_exception code=0x%08lX address=%p image_base=%p image_offset=0x%llX\r\n",
                              code, record->ExceptionAddress, memory.AllocationBase,
                              static_cast<unsigned long long>(uintptr_t(record->ExceptionAddress) - uintptr_t(memory.AllocationBase)));
    DWORD written = 0;
    if (size > 0) WriteFile(exception_log, line, DWORD(size), &written, nullptr);
    FlushFileBuffers(exception_log);
    return EXCEPTION_CONTINUE_SEARCH;
}

static void loaded_modules(HANDLE log) {
    const HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, GetCurrentProcessId());
    if (snapshot == INVALID_HANDLE_VALUE) { log_line(log, "module_list_failed " + win_error(GetLastError())); return; }
    MODULEENTRY32W module{};
    module.dwSize = sizeof(module);
    unsigned limit = 0;
    for (BOOL ok = Module32FirstW(snapshot, &module); ok && limit < 180; ok = Module32NextW(snapshot, &module), ++limit) {
        log_line(log, "loaded_module=" + utf8(module.szModule) + " base=" + hex(uintptr_t(module.modBaseAddr))
                 + " path=" + utf8(module.szExePath));
    }
    CloseHandle(snapshot);
}

static int probe(HANDLE log, const fs::path& dll, const fs::path& root) {
    exception_log = log;
    AddVectoredExceptionHandler(1, observe);
    SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX | SEM_NOOPENFILEERRORBOX);
    wchar_t desktop[120]{};
    DWORD size = 0;
    GetUserObjectInformationW(GetThreadDesktop(GetCurrentThreadId()), UOI_NAME, desktop, sizeof(desktop), &size);
    if (!std::wstring(desktop).starts_with(L"FM27XgpDiag_")) {
        log_line(log, "stage=probe_blocked expected_private_desktop");
        return 24;
    }
    UINT32 package_size = 0;
    const LONG package_status = GetCurrentPackageFullName(&package_size, nullptr);
    log_line(log, "stage=probe_started package_query=" + std::to_string(package_status)
             + " no_package=" + (package_status == APPMODEL_ERROR_NO_PACKAGE ? "yes" : "no"));
    if (!SetDefaultDllDirectories(LOAD_LIBRARY_SEARCH_SYSTEM32 | LOAD_LIBRARY_SEARCH_USER_DIRS)) {
        log_line(log, "stage=loader_policy_failed " + win_error(GetLastError()));
        return 24;
    }
    for (const auto& path : std::set<fs::path>{root, dll.parent_path()}) {
        if (!AddDllDirectory(path.c_str()))
            log_line(log, "loader_directory_failed path=" + utf8(path.wstring()) + " " + win_error(GetLastError()));
        else
            log_line(log, "loader_directory=" + utf8(path.wstring()));
    }
    log_line(log, "stage=LoadLibraryExW_begin");
    const ULONGLONG start = GetTickCount64();
    const auto module = LoadLibraryExW(dll.c_str(), nullptr, LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR
        | LOAD_LIBRARY_SEARCH_USER_DIRS | LOAD_LIBRARY_SEARCH_SYSTEM32);
    const DWORD error = module ? 0 : GetLastError();
    log_line(log, std::string("stage=LoadLibraryExW_end success=") + (module ? "yes" : "no")
             + " elapsed_ms=" + std::to_string(GetTickCount64() - start) + " " + win_error(error));
    loaded_modules(log);
    if (!module) return 21;
    Image image;
    std::string reason;
    if (!image.open(dll, reason)) return 23;
    const auto wait = reinterpret_cast<const unsigned char*>(GetProcAddress(module, "WaitForActivation"));
    const auto base = reinterpret_cast<const unsigned char*>(module);
    const auto wait_offset = uintptr_t(wait) - uintptr_t(base);
    const auto image_size = image.nt.OptionalHeader.SizeOfImage;
    const auto flag = wait && wait_offset + 30 <= image_size && readable(wait, 30)
                         ? activation_flag(wait, uint32_t(wait_offset), image_size) : std::nullopt;
    if (!flag || !readable(base + *flag, sizeof(uint32_t))) {
        log_line(log, "stage=activation_signature_unrecognized");
        return 23;
    }
    log_line(log, "stage=activation_poll_begin wait_rva=" + hex(wait_offset) + " flag_rva=" + hex(*flag));
    auto state = reinterpret_cast<const volatile uint32_t*>(base + *flag);
    uint32_t previous = UINT32_MAX;
    for (unsigned i = 0; i <= 120; ++i) {
        const auto value = *state;
        if (!i || value != previous || i % 20 == 0)
            log_line(log, "activation_word=" + std::to_string(value) + " elapsed_ms=" + std::to_string(i * 100));
        if (!value) { log_line(log, "stage=activation_ready"); return 0; }
        previous = value;
        if (i < 120) Sleep(100);
    }
    log_line(log, "stage=activation_pending");
    return 22;
}

static std::wstring quote(const fs::path& path) {
    // Windows paths cannot contain a double quote. Escape any trailing separators.
    const auto value = path.wstring();
    const auto last = value.find_last_not_of(L'\\');
    return L"\"" + value + std::wstring(value.size() - (last == std::wstring::npos ? 0 : last + 1), L'\\') + L"\"";
}

static DWORD run_probe(HANDLE log, const fs::path& exe, const fs::path& dll, const fs::path& root, const fs::path& output) {
    const auto name = L"FM27XgpDiag_" + std::to_wstring(GetCurrentProcessId());
    const auto desktop = CreateDesktopW(name.c_str(), nullptr, nullptr, 0, GENERIC_ALL, nullptr);
    if (!desktop) { log_line(log, "private_desktop_failed " + win_error(GetLastError())); return 24; }
    const auto job = CreateJobObjectW(nullptr, nullptr);
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits{};
    limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
    if (!job || !SetInformationJobObject(job, JobObjectExtendedLimitInformation, &limits, sizeof(limits))) {
        log_line(log, "probe_job_failed " + win_error(GetLastError()));
        if (job) CloseHandle(job);
        CloseDesktop(desktop);
        return 24;
    }
    STARTUPINFOW startup{};
    startup.cb = sizeof(startup);
    startup.lpDesktop = const_cast<wchar_t*>(name.c_str());
    PROCESS_INFORMATION process{};
    auto command = quote(exe) + L" --probe-child --dll " + quote(dll) + L" --game-root " + quote(root)
                   + L" --output " + quote(output);
    log_line(log, "stage=child_launch_begin timeout_ms=30000");
    DWORD result = 24;
    if (!CreateProcessW(exe.c_str(), command.data(), nullptr, nullptr, FALSE, CREATE_NO_WINDOW | CREATE_SUSPENDED,
                        nullptr, nullptr, &startup, &process)) {
        log_line(log, "child_launch_failed " + win_error(GetLastError()));
    } else {
        if (!AssignProcessToJobObject(job, process.hProcess) || ResumeThread(process.hThread) == DWORD(-1)) {
            log_line(log, "child_containment_failed " + win_error(GetLastError()));
            TerminateProcess(process.hProcess, 24);
        } else {
            const auto wait = WaitForSingleObject(process.hProcess, 30000);
            if (wait == WAIT_TIMEOUT) {
                log_line(log, "stage=child_timeout exit=25");
                TerminateJobObject(job, 25);
                WaitForSingleObject(process.hProcess, 2000);
                result = 25;
            } else if (wait == WAIT_OBJECT_0) {
                if (!GetExitCodeProcess(process.hProcess, &result)) log_line(log, "child_exit_unreadable " + win_error(GetLastError()));
            } else {
                log_line(log, "child_wait_failed " + win_error(GetLastError()));
            }
        }
        CloseHandle(process.hThread);
        CloseHandle(process.hProcess);
    }
    CloseHandle(job);
    CloseDesktop(desktop);
    log_line(log, "stage=child_finished exit=" + std::to_string(result) + " exit_hex=" + hex(result));
    return result;
}

static fs::path default_log(const fs::path& directory) {
    SYSTEMTIME time{};
    GetLocalTime(&time);
    wchar_t filename[120];
    swprintf_s(filename, L"FM27-XGP-Diagnostic-%04u%02u%02u-%02u%02u%02u-%lu.txt", time.wYear, time.wMonth,
               time.wDay, time.wHour, time.wMinute, time.wSecond, GetCurrentProcessId());
    return directory / filename;
}

static void console(const wchar_t* message) {
    DWORD written = 0;
    WriteConsoleW(GetStdHandle(STD_OUTPUT_HANDLE), message, DWORD(wcslen(message)), &written, nullptr);
}

int wmain(int argc, wchar_t** argv) {
    bool child = false, quiet = false, static_only = false;
    fs::path dll, root, output;
    for (int i = 1; i < argc; ++i) {
        const std::wstring arg = argv[i];
        if (arg == L"--probe-child") child = true;
        else if (arg == L"--quiet") quiet = true;
        else if (arg == L"--static-only") static_only = true;
        else if (i + 1 < argc && arg == L"--dll") dll = fs::absolute(argv[++i]);
        else if (i + 1 < argc && arg == L"--game-root") root = fs::absolute(argv[++i]);
        else if (i + 1 < argc && arg == L"--output") output = fs::absolute(argv[++i]);
        else {
            if (!quiet) MessageBoxW(nullptr, L"不支持的诊断参数。请直接双击运行。", L"FM27 XGP 诊断", MB_OK | MB_ICONERROR);
            return 20;
        }
    }
    wchar_t exe_path[32768]{};
    GetModuleFileNameW(nullptr, exe_path, ARRAYSIZE(exe_path));
    const fs::path exe = exe_path;
    const bool default_output = output.empty();
    if (default_output) output = default_log(exe.parent_path());
    const auto open_log = [&] {
        return CreateFileW(output.c_str(), FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                           nullptr, child ? OPEN_EXISTING : CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr);
    };
    auto log = open_log();
    if (log == INVALID_HANDLE_VALUE && default_output && !child) {
        wchar_t temporary[32768]{};
        if (GetTempPathW(ARRAYSIZE(temporary), temporary)) {
            output = default_log(temporary);
            log = open_log();
        }
    }
    if (log == INVALID_HANDLE_VALUE) {
        if (!child && !quiet) MessageBoxW(nullptr, L"无法创建诊断日志。请把 EXE 放在可写的文件夹中再运行。", L"FM27 XGP 诊断", MB_OK | MB_ICONERROR);
        return 20;
    }
    if (child) {
        // The parent records a crash or a stuck DLL detach through the job and deadline.
        const auto result = !dll.empty() && !root.empty() ? probe(log, dll, root) : 24;
        log_line(log, "stage=probe_return code=" + std::to_string(result));
        return result;
    }

    if (!quiet) console(L"FM27 XGP 诊断正在查找游戏安装并收集日志。\r\n");
    log_line(log, std::string("FM27_XGP_DIAGNOSTIC version=") + version + " clock=monotonic_ms");
    OSVERSIONINFOW os{sizeof(os)};
    const auto version_info = reinterpret_cast<LONG (WINAPI*)(OSVERSIONINFOW*)>(GetProcAddress(GetModuleHandleW(L"ntdll.dll"), "RtlGetVersion"));
    if (version_info && version_info(&os) == 0)
        log_line(log, "windows=" + std::to_string(os.dwMajorVersion) + "." + std::to_string(os.dwMinorVersion)
                 + "." + std::to_string(os.dwBuildNumber) + " process=x64");
    services(log);
    if (dll.empty()) {
        if (!root.empty()) {
            log_line(log, "selected_game_folder=" + utf8(root.wstring()));
            root = resolve_root(root, log);
        } else if (!quiet) {
            const auto found = discover(log);
            if (found.size() == 1) root = *found.begin();
            while (root.empty()) {
                const auto folder = choose_folder();
                if (folder.empty()) break;
                log_line(log, "selected_game_folder=" + utf8(folder));
                root = resolve_root(folder, log);
                if (root.empty()) MessageBoxW(nullptr, L"没在这个文件夹找到 FM27 的 game_plugin.dll。请在 Xbox 应用的「管理 → 文件」中找到游戏目录。", L"FM27 XGP 诊断", MB_OK | MB_ICONINFORMATION);
            }
        }
        if (!root.empty()) dll = root / plugin_relative;
    } else if (root.empty()) {
        root = dll.parent_path();
    }

    DWORD result = 20;
    if (dll.empty()) {
        log_line(log, "stage=game_root_not_found_or_selection_cancelled");
    } else {
        if (!quiet) console(L"正在检查原版 DLL 和依赖。在隔离进程中试加载，最长等待约 30 秒。\r\n");
        log_line(log, "game_root=" + utf8(root.wstring()));
        const auto is_game_pass = inspect(log, dll, root);
        if (static_only) {
            log_line(log, "stage=static_only");
            result = is_game_pass ? 0 : 26;
        } else if (is_game_pass) {
            result = run_probe(log, exe, dll, root, output);
        } else {
            log_line(log, "stage=probe_skipped_wrong_platform_or_unusable_PE");
            result = 26;
        }
    }
    log_line(log, "stage=diagnostic_finished result=" + std::to_string(result) + " match_simulation=not_attempted");
    CloseHandle(log);
    if (!quiet) {
        const auto message = std::wstring(result == 0 ? L"诊断完成。" : L"诊断完成，日志已记录失败阶段。")
                           + L"\n请把这一个 TXT 文件发回给开发者。\n\n" + output.wstring();
        if (MessageBoxW(nullptr, (message + L"\n\n打开日志？").c_str(), L"FM27 XGP 诊断", MB_YESNO | MB_ICONINFORMATION) == IDYES)
            ShellExecuteW(nullptr, L"open", output.c_str(), nullptr, nullptr, SW_SHOWNORMAL);
    }
    return int(result);
}
