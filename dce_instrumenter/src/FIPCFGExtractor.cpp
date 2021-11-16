#include "FIPCFGExtractor.hpp"

#include <algorithm>
#include <iterator>
#include <llvm/ADT/SmallPtrSet.h>
#include <llvm/ADT/SmallSet.h>
#include <llvm/Analysis/CFG.h>
#include <llvm/IR/InstrTypes.h>
#include <llvm/IR/Instructions.h>
#include <llvm/Passes/PassBuilder.h>
#include <llvm/Passes/PassPlugin.h>

using namespace llvm;

namespace dce {

SmallSet<std::pair<const BasicBlock *, const BasicBlock *>, 32>
getBackEdges(const Function &F) {
    SmallSet<std::pair<const BasicBlock *, const BasicBlock *>, 32>
        BackEdgesSet;

    SmallVector<std::pair<const BasicBlock *, const BasicBlock *>> BackEdges;
    FindFunctionBackedges(F, BackEdges);
    for (auto &BackEdge : BackEdges)
        BackEdgesSet.insert(BackEdge);

    return BackEdgesSet;
}

FIPCFGExtractor::Result FIPCFGExtractor::run(llvm::Module &M,
                                             llvm::ModuleAnalysisManager &) {
    decltype(FIPCFGExtractor::Result::first) Edges;
    decltype(FIPCFGExtractor::Result::second) DCEBBs;

    for (const auto &F : M) {
        if (F.isDeclaration())
            continue;
        auto BackEdges = getBackEdges(F);
        for (const auto &BB : F) {
            for (const auto &I : BB) {
                if (const auto *CB = dyn_cast<CallBase>(&I)) {
                    const auto *Callee = CB->getCalledFunction();
                    if (Callee->isDeclaration()) {
                        const auto &Name = Callee->getName();
                        if (Name.contains("DCEMarker"))
                            DCEBBs.push_back(DCEBB{&BB, Name.str()});
                        continue;
                    }
                    Edges.push_back(FIPCFGEdge{&BB, &Callee->getEntryBlock()});
                } else if (const auto *Br = dyn_cast<BranchInst>(&I)) {
                    for (const auto *Succ : Br->successors()) {
                        if (BackEdges.contains({&BB, Succ}))
                            continue;
                        Edges.push_back(FIPCFGEdge{&BB, Succ});
                    }
                } else if (const auto *Sw = dyn_cast<SwitchInst>(&I)) {
                    for (size_t i = 0; i < Sw->getNumSuccessors(); ++i) {
                        const auto *Succ = Sw->getSuccessor(i);
                        if (BackEdges.contains({&BB, Succ}))
                            continue;
                        Edges.push_back(FIPCFGEdge{&BB, Succ});
                    }
                }
            }
        }
    }
    return {Edges, DCEBBs};
}

AnalysisKey FIPCFGExtractor::Key;

PreservedAnalyses FIPCFGExtractorPrinter::run(Module &M,
                                              ModuleAnalysisManager &MAM) {
    auto [Edges, DCEBBs] = MAM.getResult<FIPCFGExtractor>(M);
    for (const auto &[From, To] : Edges)
        OS << "edge: " << From << ' ' << To << '\n';
    for (const auto &[BB, DCEMarker] : DCEBBs)
        OS << "iblock: " << BB << ' ' << DCEMarker << '\n';

    return PreservedAnalyses::all();
}

} // namespace dce

PassPluginLibraryInfo getFIPCFGExtractorPluginInfo() {
    return {
        LLVM_PLUGIN_API_VERSION, "fipcfg-extractor", LLVM_VERSION_STRING,
        [](PassBuilder &PB) {
            PB.registerPipelineParsingCallback(
                [&](StringRef Name, ModulePassManager &MPM,
                    ArrayRef<PassBuilder::PipelineElement>) {
                    if (Name == "print<fipcfg-extractor>") {
                        MPM.addPass(dce::FIPCFGExtractorPrinter{llvm::errs()});
                        return true;
                    }
                    return false;
                });
            PB.registerAnalysisRegistrationCallback(
                [](ModuleAnalysisManager &MAM) {
                    MAM.registerPass([&] { return dce::FIPCFGExtractor{}; });
                });
        }

    };
}

extern "C" LLVM_ATTRIBUTE_WEAK ::llvm::PassPluginLibraryInfo
llvmGetPassPluginInfo() {
    return getFIPCFGExtractorPluginInfo();
}
