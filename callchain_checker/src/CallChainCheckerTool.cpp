#include <clang/ASTMatchers/ASTMatchFinder.h>
#include <clang/Tooling/CommonOptionsParser.h>
#include <clang/Tooling/Tooling.h>
#include <llvm/Support/CommandLine.h>
#include <llvm/Support/Signals.h>

#include "CallChainChecker.hpp"

using namespace llvm;
using namespace clang;
using namespace clang::tooling;

using namespace ccc;

namespace {
cl::OptionCategory CCCOptions("call-chain-checker options");
cl::opt<std::string> From("from", cl::desc("Beginning of call chain."),
                          cl::value_desc("function name"), cl::cat(CCCOptions));
cl::opt<std::string> To("to", cl::desc("End of call chain."),
                        cl::value_desc("function name"), cl::cat(CCCOptions));

} // namespace

int main(int argc, const char **argv) {
    auto ExpectedParser =
        CommonOptionsParser::create(argc, argv, CCCOptions);
    if (!ExpectedParser) {
        llvm::errs() << ExpectedParser.takeError();
        return 1;
    }
    CommonOptionsParser &OptionsParser = ExpectedParser.get();

    ClangTool Tool(OptionsParser.getCompilations(),
                   OptionsParser.getSourcePathList());

    std::vector<CallPair> Calls;
    CallChainCollector CCC{Calls};
    ast_matchers::MatchFinder Finder;
    CCC.registerMatchers(Finder);
    auto ret = Tool.run(newFrontendActionFactory(&Finder).get());
    if (ret != 0)
        return ret;
    if (callChainExists(Calls, From, To))
        outs() << "call chain exists between " << From << " -> " << To << '\n';
    else
        outs() << "no call chain between " << From << " -> " << To << '\n';
    return 0;
}
