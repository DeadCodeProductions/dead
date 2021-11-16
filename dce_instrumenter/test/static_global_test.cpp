#include "test_tool.hpp"
#include <catch2/catch.hpp>

TEST_CASE("GlobalStaticInstrumenterTool single global"){
    auto Code = R"code(
    int a;
    )code";

    auto ExpectedCode = R"code(
    static int a;
    )code";

    CAPTURE(Code);
    REQUIRE(formatCode(ExpectedCode) == runStaticGlobalsOnCode(Code));

}

TEST_CASE("GlobalStaticInstrumenterTool two globals"){
    auto Code = R"code(
    int a;
    int b;
    )code";

    auto ExpectedCode = R"code(
    static int a;
    static int b;
    )code";

    CAPTURE(Code);
    REQUIRE(formatCode(ExpectedCode) == runStaticGlobalsOnCode(Code));
}

TEST_CASE("GlobalStaticInstrumenterTool two globals already static"){
    auto Code = R"code(
    static int a;
    static int b;
    )code";

    auto ExpectedCode = R"code(
    static int a;
    static int b;
    )code";

    CAPTURE(Code);
    REQUIRE(formatCode(ExpectedCode) == runStaticGlobalsOnCode(Code));
}

TEST_CASE("GlobalStaticInstrumenterTool two globals one already static"){
    auto Code = R"code(
    int a;
    static int b;
    )code";

    auto ExpectedCode = R"code(
    static int a;
    static int b;
    )code";

    CAPTURE(Code);
    REQUIRE(formatCode(ExpectedCode) == runStaticGlobalsOnCode(Code));
}

TEST_CASE("GlobalStaticInstrumenterTool functions"){
    auto Code = R"code(
    int main() { return 0;}
    int foo(){ return 42;}
    static int bar(){ return 42;}
    )code";

    auto ExpectedCode = R"code(
    int main() { return 0;}
    static int foo(){ return 42;}
    static int bar(){ return 42;}
    )code";

    CAPTURE(Code);
    REQUIRE(formatCode(ExpectedCode) == runStaticGlobalsOnCode(Code));
}
