#include "CallChainChecker.hpp"

#include <llvm/Support/raw_ostream.h>
#include <unordered_map>

#include <clang/AST/Decl.h>
#include <clang/ASTMatchers/ASTMatchers.h>

#include <boost/graph/adjacency_list.hpp>
#include <boost/graph/breadth_first_search.hpp>
#include <boost/property_map/property_map.hpp>

using namespace clang;
using namespace clang::ast_matchers;

using namespace boost;

using StaticCallGraph = adjacency_list<vecS, vecS, directedS>;

namespace ccc {

bool callChainExists(const std::vector<CallPair> &Calls, std::string From,
                     std::string To) {
    std::unordered_map<std::string, size_t> FunctionToIdx;
    size_t idx = 0;
    StaticCallGraph SCG;
    for (const auto &[Caller, Callee] : Calls) {
        if (not FunctionToIdx.count(Caller)) {
            SCG.added_vertex(idx);
            FunctionToIdx[Caller] = idx++;
        }
        if (not FunctionToIdx.count(Callee)) {
            SCG.added_vertex(idx);
            FunctionToIdx[Callee] = idx++;
        }
        boost::add_edge(FunctionToIdx[Caller], FunctionToIdx[Callee], SCG);
    }
    if (not FunctionToIdx.count(From)) {
        llvm::errs() << From << " is not part of the call graph\n";
        return false;
    }
    if (not FunctionToIdx.count(To)) {
        llvm::errs() << To << " is not part of the call graph\n";
        return false;
    }

    std::vector<default_color_type> Colors(num_vertices(SCG));
    iterator_property_map ColorMap(Colors.begin(),
                                   boost::get(boost::vertex_index, SCG));
    breadth_first_search(SCG, FunctionToIdx.at(From), color_map(ColorMap));
    return Colors[FunctionToIdx.at(To)] == default_color_type::black_color;
}

void CallChainCollector::registerMatchers(
    clang::ast_matchers::MatchFinder &Finder) {
    Finder.addMatcher(callExpr(clang::ast_matchers::isExpansionInMainFile(),
                               callee(functionDecl().bind("callee")),
                               hasAncestor(functionDecl().bind("caller"))),
                      this);
}

void CallChainCollector::run(
    const clang::ast_matchers::MatchFinder::MatchResult &Result) {
    if (const auto *Callee = Result.Nodes.getNodeAs<FunctionDecl>("callee"))
        if (const auto *Caller = Result.Nodes.getNodeAs<FunctionDecl>("caller"))
            Calls.emplace_back(Caller->getNameAsString(),
                               Callee->getNameAsString());
}

} // namespace ccc
