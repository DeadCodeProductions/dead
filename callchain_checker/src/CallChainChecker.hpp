#include <vector>

#include <clang/AST/Decl.h>
#include <clang/ASTMatchers/ASTMatchFinder.h>

namespace ccc {

struct CallPair {
    const struct clang::FunctionDecl *Caller;
    const struct clang::FunctionDecl *Callee;

    CallPair(const clang::FunctionDecl *Caller,
             const clang::FunctionDecl *Callee)
        : Caller{Caller}, Callee{Callee} {}
};

bool callChainExists(const std::vector<CallPair> &Calls, std::string From,
                     std::string To);

class CallChainCollector
    : public clang::ast_matchers::MatchFinder::MatchCallback {
  public:
    CallChainCollector(std::vector<CallPair> &Calls) : Calls{Calls} {}
    void registerMatchers(clang::ast_matchers::MatchFinder &Finder);
    void
    run(const clang::ast_matchers::MatchFinder::MatchResult &Result) override;

  private:
    std::vector<CallPair> &Calls;
};

} // namespace ccc
