#include "test_tool.hpp"

#include <DCEInstrumenter.hpp>

#include <clang/Format/Format.h>
#include <clang/Tooling/Core/Replacement.h>
#include <clang/Tooling/Refactoring.h>
#include <clang/Tooling/Tooling.h>

#include <RewriterTestContext.h>

#include <catch2/catch.hpp>
#include <memory>

using namespace clang;

std::string formatCode(llvm::StringRef Code) {
    tooling::Replacements Replaces = format::reformat(
        format::getLLVMStyle(), Code, {tooling::Range(0, Code.size())});
    auto ChangedCode = tooling::applyAllReplacements(Code, Replaces);
    REQUIRE(static_cast<bool>(ChangedCode));
    return *ChangedCode;
}

std::string runDCEInstrumentOnCode(llvm::StringRef Code) {
    auto CanonicalizedCode = runDCECanicalizeOnCode(Code);
    clang::RewriterTestContext Context;
    clang::FileID ID =
        Context.createInMemoryFile("input.cc", CanonicalizedCode);

    std::map<std::string, tooling::Replacements> FileToReplacements;
    dcei::DCEInstrumenterTool DCETool{FileToReplacements};
    ast_matchers::MatchFinder Finder;
    DCETool.registerMatchers(Finder);
    std::unique_ptr<tooling::FrontendActionFactory> Factory =
        tooling::newFrontendActionFactory(&Finder);
    REQUIRE(tooling::runToolOnCode(Factory->create(), CanonicalizedCode,
                                   "input.cc"));
    formatAndApplyAllReplacements(FileToReplacements, Context.Rewrite);
    return formatCode(Context.getRewrittenText(ID));
}

std::string runDCECanicalizeOnCode(llvm::StringRef Code) {
    clang::RewriterTestContext Context;
    clang::FileID ID = Context.createInMemoryFile("input.cc", Code);

    std::map<std::string, tooling::Replacements> FileToReplacements;
    dcei::DCECanonicalizerTool DCECanTool{FileToReplacements};
    ast_matchers::MatchFinder Finder;
    DCECanTool.registerMatchers(Finder);
    std::unique_ptr<tooling::FrontendActionFactory> Factory =
        tooling::newFrontendActionFactory(&Finder);
    REQUIRE(tooling::runToolOnCodeWithArgs(Factory->create(), Code,
                                           {"-Wno-empty-body"}, "input.cc"));
    formatAndApplyAllReplacements(FileToReplacements, Context.Rewrite);
    return formatCode(Context.getRewrittenText(ID));
}

std::string runStaticGlobalsOnCode(llvm::StringRef Code){
    clang::RewriterTestContext Context;
    clang::FileID ID = Context.createInMemoryFile("input.cc", Code);

    std::map<std::string, tooling::Replacements> FileToReplacements;
    dcei::GlobalStaticInstrumenterTool StaticGlobalsTool{FileToReplacements};
    ast_matchers::MatchFinder Finder;
    StaticGlobalsTool.registerMatchers(Finder);
    std::unique_ptr<tooling::FrontendActionFactory> Factory =
        tooling::newFrontendActionFactory(&Finder);
    REQUIRE(tooling::runToolOnCodeWithArgs(Factory->create(), Code,
                                           {"-Wno-empty-body"}, "input.cc"));
    formatAndApplyAllReplacements(FileToReplacements, Context.Rewrite);
    return formatCode(Context.getRewrittenText(ID));
}
