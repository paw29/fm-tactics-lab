// Match preparation consumes this result immediately to adjust player form.
// Only that call site gets the override. Other competition queries stay native.
static constexpr unsigned char importance_caller_prefix[]={
    0x48,0x89,0xc1,0x31,0xd2,0x49,0x89,0xf0,0xe8
};
static constexpr unsigned importance_result = native_layout::player_runtime(0x1c64);
static constexpr unsigned importance_condition = native_layout::player_input(0xc78);
static constexpr unsigned char importance_caller_suffix[]={
    0x41,0x89,0xc0,0x89,0x86,(unsigned char)importance_result,(unsigned char)(importance_result>>8),0,0,
    0x0f,0xbf,0x86,(unsigned char)importance_condition,(unsigned char)(importance_condition>>8),0,0
};
static constexpr unsigned char importance_prologue[]={
    0x56,0x57,0x53,0x4c,0x8b,0x89,0x18,0x06,0,0,0x49,0x83,0xb9,0x78,0x06,0,0,0
};
static constexpr size_t importance_return_offset=sizeof(importance_caller_prefix)+sizeof(int32_t);
struct ImportanceLocation {uint32_t entry=0, return_address=0;};
static ImportanceLocation importance_location;
static unsigned match_importance=0;
static unsigned char* importance_return_address=nullptr;
static int (*original_importance)(void*,void*,void*)=nullptr;

static bool locate_match_importance(const fs::path& path){
    CompatImage image;
    if(!image.open(path))return false;
    ImportanceLocation found;
    if constexpr(native_layout::steam_27_1){
        constexpr unsigned entry=0xf2710, return_address=0xf01aa;
        unsigned char prologue[sizeof(importance_prologue)]={}, suffix[sizeof(importance_caller_suffix)]={};
        unsigned char prefix[sizeof(importance_caller_prefix)]={};
        int32_t displacement=0;
        const bool verified=image.read(entry,prologue,sizeof(prologue))&&
            image.read(return_address,suffix,sizeof(suffix))&&
            image.read(return_address-importance_return_offset,prefix,sizeof(prefix))&&
            image.read(return_address-sizeof(displacement),&displacement,sizeof(displacement))&&
            (int64_t)return_address+displacement==entry&&
            !memcmp(prologue,importance_prologue,sizeof(prologue))&&
            !memcmp(suffix,importance_caller_suffix,sizeof(suffix))&&
            !memcmp(prefix,importance_caller_prefix,sizeof(prefix));
        importance_location=verified?ImportanceLocation{entry,return_address}:ImportanceLocation{};
        return verified;
    }
    for(const auto& section:image.sections){
        if(!(section.Characteristics&IMAGE_SCN_MEM_EXECUTE))continue;
        std::vector<unsigned char> code(section.SizeOfRawData);
        if(!image.raw(section.PointerToRawData,code.data(),code.size()))return false;
        auto cursor=code.begin();
        while((cursor=std::search(cursor,code.end(),std::begin(importance_caller_prefix),
                                 std::end(importance_caller_prefix)))!=code.end()){
            const auto caller_offset=cursor++-code.begin();
            const auto return_offset=caller_offset+importance_return_offset;
            if(return_offset+sizeof(importance_caller_suffix)>code.size()||
               memcmp(code.data()+return_offset,importance_caller_suffix,sizeof(importance_caller_suffix)))continue;
            int32_t displacement=0;
            memcpy(&displacement,code.data()+return_offset-sizeof(displacement),sizeof(displacement));
            const auto entry_offset=(int64_t)return_offset+displacement;
            if(entry_offset<0||entry_offset+sizeof(importance_prologue)>code.size()||
               memcmp(code.data()+entry_offset,importance_prologue,sizeof(importance_prologue)))continue;
            if(found.entry)return false;
            found={(uint32_t)(section.VirtualAddress+entry_offset),(uint32_t)(section.VirtualAddress+return_offset)};
        }
    }
    importance_location=found;
    return found.entry!=0;
}

__declspec(noinline) static int override_match_importance(void* team,void* flag,void* player){
    if(match_importance&&_ReturnAddress()==importance_return_address)return match_importance;
    return original_importance(team,flag,player);
}

static bool install_match_importance(){
    if(!match_importance)return true;
    if(original_importance)return true;
    if(!importance_location.entry)return false;
    auto entry=native_base+importance_location.entry;
    auto return_address=native_base+importance_location.return_address;
    if(memcmp(entry,importance_prologue,sizeof(importance_prologue))||
       memcmp(return_address,importance_caller_suffix,sizeof(importance_caller_suffix)))return false;
    // The displaced pushes, load and compare are position independent.
    auto trampoline=(unsigned char*)VirtualAlloc(nullptr,64,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);
    if(!trampoline)return false;
    unsigned char jump[14]={0xff,0x25};
    auto continuation=entry+sizeof(importance_prologue);
    memcpy(trampoline,entry,sizeof(importance_prologue));
    memcpy(jump+6,&continuation,sizeof(continuation));
    memcpy(trampoline+sizeof(importance_prologue),jump,sizeof(jump));
    DWORD old=0;
    if(!VirtualProtect(trampoline,64,PAGE_EXECUTE_READ,&old)){
        VirtualFree(trampoline,0,MEM_RELEASE);
        return false;
    }
    FlushInstructionCache(GetCurrentProcess(),trampoline,64);
    if(!VirtualProtect(entry,sizeof(importance_prologue),PAGE_EXECUTE_READWRITE,&old)){
        VirtualFree(trampoline,0,MEM_RELEASE);
        return false;
    }
    original_importance=(decltype(original_importance))trampoline;
    importance_return_address=return_address;
    auto replacement=&override_match_importance;
    memcpy(jump+6,&replacement,sizeof(replacement));
    memcpy(entry,jump,sizeof(jump));
    memset(entry+sizeof(jump),0x90,sizeof(importance_prologue)-sizeof(jump));
    DWORD unused=0;
    const bool restored=VirtualProtect(entry,sizeof(importance_prologue),old,&unused)!=0;
    FlushInstructionCache(GetCurrentProcess(),entry,sizeof(importance_prologue));
    return restored;
}

static bool verify_match_importance(unsigned char* match){
    if(!match_importance)return true;
    bool verified=true;
    fprintf(log_file,"{\"event\":\"native_match_importance_readback\",\"requested\":%u,\"starters\":[",match_importance);
    for(unsigned side=0;side<2;side++){
        const auto team=*(unsigned char**)(match+0x15380+side*8);
        fputs(side?",[":"[",log_file);
        for(unsigned slot=0;slot<11;slot++){
            const auto player=*(unsigned char**)(team+0x138+slot*8);
            const auto value=player?*(uint32_t*)(player+importance_result):0;
            fprintf(log_file,"%s%u",slot?",":"",value);
            verified=verified&&value==match_importance;
        }
        fputs("]",log_file);
    }
    fprintf(log_file,"],\"verified\":%s}\n",verified?"true":"false");fflush(log_file);
    return verified;
}
