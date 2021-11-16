#pragma once

#include <llvm/IR/BasicBlock.h>
#include <llvm/IR/Module.h>
#include <optional>

#include <llvm/IR/PassManager.h>

namespace dce {

struct FIPCFGEdge {
    const llvm::BasicBlock *From;
    const llvm::BasicBlock *To;
};

struct DCEBB {
    const llvm::BasicBlock *BB;
    std::string DCEMarker;
};

class FIPCFGExtractor : public llvm::AnalysisInfoMixin<FIPCFGExtractor> {
  public:
    using Result = std::pair<std::vector<FIPCFGEdge>, std::vector<DCEBB>>;
    Result run(llvm::Module &M, llvm::ModuleAnalysisManager &AM);

  private:
    static llvm::AnalysisKey Key;
    friend struct llvm::AnalysisInfoMixin<FIPCFGExtractor>;
};

class FIPCFGExtractorPrinter
    : public llvm::PassInfoMixin<FIPCFGExtractorPrinter> {
  public:
    explicit FIPCFGExtractorPrinter(llvm::raw_ostream &OutS) : OS{OutS} {}
    llvm::PreservedAnalyses run(llvm::Module &M,
                                llvm::ModuleAnalysisManager &MAM);

  private:
    llvm::raw_ostream &OS;
};

} // namespace dce
