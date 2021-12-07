#include "clang/Rewrite/Core/Rewriter.h"
#include <clang/Frontend/TextDiagnosticPrinter.h>
#include <clang/Tooling/CommonOptionsParser.h>
#include <clang/Tooling/CompilationDatabase.h>
#include <clang/Tooling/Refactoring.h>
#include <clang/Tooling/Tooling.h>
#include <llvm/Support/Signals.h>

#include <DCEInstrumenter.hpp>
#include <llvm/Support/raw_ostream.h>

using namespace llvm;
using namespace clang;
using namespace clang::tooling;

static cl::OptionCategory DCEInstrOptions("static-annotator options");

template <typename ToolType>
int applyTool(const CompilationDatabase &Compilations,
              const std::vector<std::string> &Files) {
    RefactoringTool Tool(Compilations, Files);

    LangOptions DefaultLangOptions;
    IntrusiveRefCntPtr<DiagnosticOptions> DiagOpts = new DiagnosticOptions();
    clang::TextDiagnosticPrinter DiagnosticPrinter(errs(), &*DiagOpts);
    DiagnosticsEngine Diagnostics(
        IntrusiveRefCntPtr<DiagnosticIDs>(new DiagnosticIDs()), &*DiagOpts,
        &DiagnosticPrinter, false);
    auto &FileMgr = Tool.getFiles();
    SourceManager Sources(Diagnostics, FileMgr);
    Rewriter Rewrite(Sources, DefaultLangOptions);

    ToolType TemplateTool(Tool.getReplacements());
    ast_matchers::MatchFinder Finder;
    TemplateTool.registerMatchers(Finder);
    std::unique_ptr<tooling::FrontendActionFactory> Factory =
        tooling::newFrontendActionFactory(&Finder);

    if (int Result = Tool.run(Factory.get()))
        return Result;

    if (!formatAndApplyAllReplacements(Tool.getReplacements(), Rewrite)) {
        llvm::errs() << "Failed applying all replacements.\n";
        return 1;
    }

    return Rewrite.overwriteChangedFiles();
}

int makeGlobalsStatic(const CompilationDatabase &Compilations,
                      const std::vector<std::string> &Files) {
    return applyTool<dcei::GlobalStaticInstrumenterTool>(Compilations, Files);
}

int main(int argc, const char **argv) {
    auto ExpectedParser =
        CommonOptionsParser::create(argc, argv, DCEInstrOptions);
    if (!ExpectedParser) {
        llvm::errs() << ExpectedParser.takeError();
        return 1;
    }
    CommonOptionsParser &OptionsParser = ExpectedParser.get();

    const auto &Compilations = OptionsParser.getCompilations();
    const auto &Files = OptionsParser.getSourcePathList();

    return makeGlobalsStatic(Compilations, Files);
}
