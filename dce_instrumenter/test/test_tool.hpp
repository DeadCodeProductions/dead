#pragma once 

#include <llvm/ADT/StringRef.h>

std::string formatCode(llvm::StringRef Code);
std::string runDCEInstrumentOnCode(llvm::StringRef Code);
std::string runDCECanicalizeOnCode(llvm::StringRef Code);
std::string runStaticGlobalsOnCode(llvm::StringRef Code);
