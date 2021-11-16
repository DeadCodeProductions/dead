#include "DCEInstrumenter.hpp"

#include <clang/AST/Decl.h>
#include <clang/AST/Stmt.h>
#include <clang/ASTMatchers/ASTMatchers.h>
#include <clang/Lex/Lexer.h>
#include <sstream>
#include <string>

using namespace clang;
using namespace clang::ast_matchers;

namespace dcei {

void addReplacementOrDie(
    SourceLocation Start, SourceLocation End, llvm::StringRef ReplacementText,
    const SourceManager &SM,
    std::map<std::string, tooling::Replacements> &FileToReplacements);

DCECanonicalizerTool::DCECanonicalizerTool(
    std::map<std::string, clang::tooling::Replacements> &FileToReplacements)
    : FileToReplacements{FileToReplacements} {}

void DCECanonicalizerTool::registerMatchers(
    clang::ast_matchers::MatchFinder &Finder) {

    Finder.addMatcher(
        ifStmt(isExpansionInMainFile(), hasThen(stmt().bind("stmt"))), this);
    Finder.addMatcher(
        ifStmt(isExpansionInMainFile(), hasElse(stmt().bind("stmt"))), this);
    Finder.addMatcher(
        mapAnyOf(forStmt, whileStmt, doStmt, cxxForRangeStmt)
            .with(isExpansionInMainFile(), hasBody(stmt().bind("stmt"))),
        this);

    Finder.addMatcher(caseStmt(isExpansionInMainFile(),
                               unless(anyOf(hasDescendant(defaultStmt()),
                                            hasDescendant(caseStmt()))))
                          .bind("switch_case"),
                      this);
    Finder.addMatcher(defaultStmt(isExpansionInMainFile(),
                                  unless(anyOf(hasDescendant(defaultStmt()),
                                               hasDescendant(caseStmt()))))
                          .bind("switch_case"),
                      this);
}

void DCECanonicalizerTool::handleStmt(const clang::Stmt &Statement) {
    auto StmtBegin = Statement.getBeginLoc();
    if (SM->getMainFileID() != SM->getFileID(SM->getSpellingLoc(StmtBegin)))
        return;

    if (isa<CompoundStmt>(Statement))
        return;

    if (isa<NullStmt>(Statement)) {
        addReplacementOrDie(StmtBegin, StmtBegin, std::string{"{}"}, *SM,
                            FileToReplacements);
        return;
    }

    auto StmtEnd = Statement.getEndLoc();
    const char *BeginSource = SM->getCharacterData(StmtBegin);
    if (not BeginSource)
        llvm_unreachable("Cannot read source code");
    auto BeginTokenLen = Lexer::MeasureTokenLength(StmtBegin, *SM, *LO);
    addReplacementOrDie(
        StmtBegin, StmtBegin,
        std::string{"{"} +
            std::string{BeginSource, BeginSource + BeginTokenLen},
        *SM, FileToReplacements);

    auto EndTokenLoc = [&]() {
        auto SemiToken = Lexer::findNextToken(StmtEnd, *SM, *LO);
        if (SemiToken and SemiToken->is(tok::semi))
            return SemiToken->getLocation();
        else
            return Lexer::GetBeginningOfToken(StmtEnd, *SM, *LO);
    }();
    ++CurlyBracesInsertedAtLocation[EndTokenLoc];
}

void DCECanonicalizerTool::run(
    const clang::ast_matchers::MatchFinder::MatchResult &Result) {
    if (not SM)
        SM = Result.SourceManager;
    if (not LO)
        LO = &Result.Context->getLangOpts();

    if (const auto *Statement = Result.Nodes.getNodeAs<Stmt>("stmt"))
        handleStmt(*Statement);
    else if (const auto *SwitchCase_ =
                 Result.Nodes.getNodeAs<SwitchCase>("switch_case"))
        handleStmt(*SwitchCase_->getSubStmt());
}

void DCECanonicalizerTool::onEndOfTranslationUnit() {
    for (const auto &[Loc, NBraces] : CurlyBracesInsertedAtLocation) {
        auto TokenLen = Lexer::MeasureTokenLength(Loc, *SM, *LO);
        const char *Source = SM->getCharacterData(Loc);
        if (not Source)
            llvm_unreachable("Cannot read source code");
        addReplacementOrDie(Loc, Loc,
                            std::string{Source, Source + TokenLen} +
                                std::string(NBraces, '}'),
                            *SM, FileToReplacements);
    }
}

DCEInstrumenterTool::DCEInstrumenterTool(
    std::map<std::string, clang::tooling::Replacements> &FileToReplacements)
    : FileToReplacements{FileToReplacements} {}

void DCEInstrumenterTool::registerMatchers(
    clang::ast_matchers::MatchFinder &Finder) {
    Finder.addMatcher(
        ifStmt(isExpansionInMainFile(), hasThen(compoundStmt().bind("cstmt"))),
        this);
    Finder.addMatcher(
        ifStmt(isExpansionInMainFile(), hasElse(compoundStmt().bind("cstmt"))),
        this);
    Finder.addMatcher(mapAnyOf(forStmt, whileStmt, doStmt, cxxForRangeStmt)
                          .with(isExpansionInMainFile(),
                                hasBody(compoundStmt().bind("cstmt"))),
                      this);
    Finder.addMatcher(caseStmt(isExpansionInMainFile(),
                               unless(anyOf(hasDescendant(defaultStmt()),
                                            hasDescendant(caseStmt()))))
                          .bind("switch_case"),
                      this);
    Finder.addMatcher(defaultStmt(isExpansionInMainFile(),
                                  unless(anyOf(hasDescendant(defaultStmt()),
                                               hasDescendant(caseStmt()))))
                          .bind("switch_case"),
                      this);

    // XXX: A more precise check is to figure out if there are returns on all
    // paths
    auto HasReturnDesc =
        allOf(isExpansionInMainFile(), hasDescendant(returnStmt()));
    Finder.addMatcher(mapAnyOf(ifStmt, forStmt, whileStmt, doStmt,
                               cxxForRangeStmt, switchStmt)
                          .with(HasReturnDesc)
                          .bind("stmt_with_return_descendant"),
                      this);
}

void DCEInstrumenterTool::run(
    const clang::ast_matchers::MatchFinder::MatchResult &Result) {
    if (not SM)
        SM = Result.SourceManager;
    if (not LO)
        LO = &Result.Context->getLangOpts();

    if (const auto *CStatement = Result.Nodes.getNodeAs<CompoundStmt>("cstmt"))
        handleCompoundStmt(*CStatement);
    else if (const auto *Statement =
                 Result.Nodes.getNodeAs<Stmt>("stmt_with_return_descendant"))
        handleStmtWithReturnDescendant(*Statement);
    else if (const auto *SwitchCase_ =
                 Result.Nodes.getNodeAs<SwitchCase>("switch_case"))
        if (const auto *CStatement =
                dyn_cast<CompoundStmt>(SwitchCase_->getSubStmt()))
            handleCompoundStmt(*CStatement);
}

void DCEInstrumenterTool::handleCompoundStmt(
    const clang::CompoundStmt &CStatement) {

    auto LBracLoc = CStatement.getLBracLoc();
    addReplacementOrDie(LBracLoc, LBracLoc, "{\n" + getNewDCECallStr(), *SM,
                        FileToReplacements);
}

void DCEInstrumenterTool::handleStmtWithReturnDescendant(
    const clang::Stmt &Statement) {

    auto StmtEnd = Statement.getEndLoc();

    if (SM->getMainFileID() != SM->getFileID(SM->getSpellingLoc(StmtEnd)))
        return;

    auto EndTokenLoc = [&]() {
        auto SemiToken = Lexer::findNextToken(StmtEnd, *SM, *LO);
        if (SemiToken and SemiToken->is(tok::semi))
            return SemiToken->getLocation();
        else
            return Lexer::GetBeginningOfToken(StmtEnd, *SM, *LO);
    }();

    auto TokenLen = Lexer::MeasureTokenLength(EndTokenLoc, *SM, *LO);
    const char *Source = SM->getCharacterData(EndTokenLoc);
    if (not Source)
        llvm_unreachable("Cannot read source code");

    addReplacementOrDie(EndTokenLoc, EndTokenLoc,
                        std::string{Source, Source + TokenLen} + "\n" +
                            getNewDCECallStr(),
                        *SM, FileToReplacements);
}

void DCEInstrumenterTool::onEndOfTranslationUnit() {
    if (not NFunctionsInserted)
        return;
    std::stringstream SS;
    for (size_t I = 0; I < NFunctionsInserted; ++I)
        SS << "void "
              "DCEMarker"
           << std::to_string(I) << "_(void);\n";

    auto FBeginLoc = SM->getLocForStartOfFile(SM->getMainFileID());
    auto TokenLen = Lexer::MeasureTokenLength(FBeginLoc, *SM, *LO);
    const char *Source = SM->getCharacterData(FBeginLoc);
    if (not Source)
        llvm_unreachable("Cannot read source code");

    addReplacementOrDie(FBeginLoc, FBeginLoc,
                        SS.str() + std::string{Source, Source + TokenLen}, *SM,
                        FileToReplacements);
}

std::string DCEInstrumenterTool::getNewDCECallStr() {
    return "DCEMarker" + std::to_string(NFunctionsInserted++) + "_();";
}

GlobalStaticInstrumenterTool::GlobalStaticInstrumenterTool(
    std::map<std::string, clang::tooling::Replacements> &FileToReplacements)
    : FileToReplacements{FileToReplacements} {}

void GlobalStaticInstrumenterTool::registerMatchers(
    clang::ast_matchers::MatchFinder &Finder) {
    Finder.addMatcher(varDecl(isExpansionInMainFile(), isDefinition(),
                              hasGlobalStorage(),
                              unless(isStaticStorageClass()))
                          .bind("global"),
                      this);
    Finder.addMatcher(functionDecl(isExpansionInMainFile(), isDefinition(),
                                   unless(isStaticStorageClass()),
                                   unless(isMain()))
                          .bind("global"),
                      this);
}

void GlobalStaticInstrumenterTool::run(
    const clang::ast_matchers::MatchFinder::MatchResult &Result) {
    if (not SM)
        SM = Result.SourceManager;
    if (not LO)
        LO = &Result.Context->getLangOpts();

    if (const auto *GlobalDecl = Result.Nodes.getNodeAs<Decl>("global")) {
        auto Begin = GlobalDecl->getBeginLoc();
        auto TokenLen = Lexer::MeasureTokenLength(Begin, *SM, *LO);
        const char *Source = SM->getCharacterData(Begin);

        addReplacementOrDie(Begin, Begin,
                            "static " + std::string{Source, Source + TokenLen},
                            *SM, FileToReplacements);
    }
}

tooling::Replacement createReplacement(SourceLocation Start, SourceLocation End,
                                       llvm::StringRef ReplacementText,
                                       const SourceManager &SM) {
    if (!Start.isValid() || !End.isValid()) {
        llvm::errs() << "start or end location were invalid\n";
        return tooling::Replacement();
    }
    if (SM.getDecomposedLoc(Start).first != SM.getDecomposedLoc(End).first) {
        llvm::errs()
            << "start or end location were in different macro expansions\n";
        return tooling::Replacement();
    }
    Start = SM.getSpellingLoc(Start);
    End = SM.getSpellingLoc(End);
    if (SM.getFileID(Start) != SM.getFileID(End)) {
        llvm::errs() << "start or end location were in different files\n";
        return tooling::Replacement();
    }
    return tooling::Replacement(
        SM,
        CharSourceRange::getTokenRange(SM.getSpellingLoc(Start),
                                       SM.getSpellingLoc(End)),
        ReplacementText);
}

void addReplacementOrDie(
    SourceLocation Start, SourceLocation End, llvm::StringRef ReplacementText,
    const SourceManager &SM,
    std::map<std::string, tooling::Replacements> &FileToReplacements) {
    const auto R = createReplacement(Start, End, ReplacementText, SM);
    auto Err = FileToReplacements[std::string(R.getFilePath())].add(R);
    if (Err)
        llvm_unreachable(llvm::toString(std::move(Err)).c_str());
}

} // namespace dcei
