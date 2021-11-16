#pragma once

#include <clang/AST/Stmt.h>
#include <clang/ASTMatchers/ASTMatchFinder.h>
#include <clang/Basic/LangOptions.h>
#include <clang/Basic/LangStandard.h>
#include <clang/Basic/SourceLocation.h>
#include <clang/Basic/SourceManager.h>
#include <clang/Tooling/Core/Replacement.h>

namespace dcei {

class DCECanonicalizerTool

    : public clang::ast_matchers::MatchFinder::MatchCallback {
  public:
    DCECanonicalizerTool(std::map<std::string, clang::tooling::Replacements>
                             &FileToReplacements);
    void registerMatchers(clang::ast_matchers::MatchFinder &Finder);

    void
    run(const clang::ast_matchers::MatchFinder::MatchResult &Result) override;

    void onEndOfTranslationUnit() override;

  private:
    void handleStmt(const clang::Stmt &Statement);

    std::map<clang::SourceLocation, size_t> CurlyBracesInsertedAtLocation;
    std::map<std::string, clang::tooling::Replacements> &FileToReplacements;
    const clang::SourceManager *SM = nullptr;
    const clang::LangOptions *LO = nullptr;
};

class DCEInstrumenterTool
    : public clang::ast_matchers::MatchFinder::MatchCallback {
  public:
    DCEInstrumenterTool(std::map<std::string, clang::tooling::Replacements>
                            &FileToReplacements);

    void registerMatchers(clang::ast_matchers::MatchFinder &Finder);

    void
    run(const clang::ast_matchers::MatchFinder::MatchResult &Result) override;

    void onEndOfTranslationUnit() override;

  private:
    void handleCompoundStmt(const clang::CompoundStmt &CStatement);
    void handleStmtWithReturnDescendant(const clang::Stmt &Statement);
    std::string getNewDCECallStr();

    std::map<std::string, clang::tooling::Replacements> &FileToReplacements;
    size_t NFunctionsInserted = 0;
    const clang::SourceManager *SM = nullptr;
    const clang::LangOptions *LO = nullptr;
};

class GlobalStaticInstrumenterTool
    : public clang::ast_matchers::MatchFinder::MatchCallback {
  public:
    GlobalStaticInstrumenterTool(
        std::map<std::string, clang::tooling::Replacements>
            &FileToReplacements);
    void registerMatchers(clang::ast_matchers::MatchFinder &Finder);
    void
    run(const clang::ast_matchers::MatchFinder::MatchResult &Result) override;

  private:
    std::map<std::string, clang::tooling::Replacements> &FileToReplacements;
    const clang::SourceManager *SM = nullptr;
    const clang::LangOptions *LO = nullptr;
};

} // namespace dcei
