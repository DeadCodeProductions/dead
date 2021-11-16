#include "test_tool.hpp"
#include <catch2/catch.hpp>

TEST_CASE("DCECanonicalizeTool if-else", "[dcec][if]") {
    auto Code = R"code(
    int foo(int a){
        if (a > 0)a = 1;
        else
            a = 0;return a;
    }
    )code";

    auto ExpectedCode = R"code(
    int foo(int a){
        if (a > 0){
            a = 1;
        } else{
            a = 0;
        }
        return a;
    }
    )code";

    CAPTURE(Code);
    REQUIRE(formatCode(ExpectedCode) == runDCECanicalizeOnCode(Code));

    Code = R"code(
        int foo(int a){
            if (a > 0){
                a = 1;
            }
            else
                a = 0 ;
            return a;
        }
        )code";

    CAPTURE(Code);
    REQUIRE(formatCode(ExpectedCode) == runDCECanicalizeOnCode(Code));
}

TEST_CASE("DCECanonicalizeTool loops",
          "[dcec][loop][for][while][do][range-for]") {
    std::string Code = R"code(
    #include<initializer_list>
    int foo(int a){
        LOOP
            a = 0SPACE;END
        return a;
    }
    )code";
    std::string ExpectedCode = R"code(
    #include<initializer_list>
    int foo(int a){
        LOOP{
            a = 0;
        }END
        return a;
    }
    )code";

    auto check_loops = [&]() {
        SECTION("for") {
            Code.replace(Code.find("LOOP"), 4, "for(;;)");
            ExpectedCode.replace(ExpectedCode.find("LOOP"), 4, "for(;;)");
        }
        SECTION("while") {
            Code.replace(Code.find("LOOP"), 4, "while(1)");
            ExpectedCode.replace(ExpectedCode.find("LOOP"), 4, "while(1)");
        }
        SECTION("range-for") {
            Code.replace(Code.find("LOOP"), 4, "for(auto b: {1,2,3})");
            ExpectedCode.replace(ExpectedCode.find("LOOP"), 4,
                                 "for(auto b: {1,2,3})");
        }
        SECTION("do") {
            Code.replace(Code.find("LOOP"), 4, "do");
            Code.replace(Code.find("END"), 3, "END while(1);");
            ExpectedCode.replace(ExpectedCode.find("LOOP"), 4, "do");
            ExpectedCode.replace(ExpectedCode.find("END"), 3, "ENDwhile(1);");
        }
    };

    SECTION("no compound body") {
        SECTION("Without space after semicolon") {
            Code.replace(Code.find("SPACE"), 5, "");
            check_loops();
        }
        SECTION("With space after semicolon") {
            Code.replace(Code.find("SPACE"), 5, " ");
            check_loops();
        }

        Code.replace(Code.find("END"), 3, "");
        ExpectedCode.replace(ExpectedCode.find("END"), 3, "");
    }

    SECTION("compound body") {
        Code.replace(Code.find("LOOP"), 4, "LOOP{");
        SECTION("Without space after semicolon") {
            Code.replace(Code.find("SPACE"), 5, "");
            check_loops();
        }
        SECTION("With space after semicolon") {
            Code.replace(Code.find("SPACE"), 5, " ");
            check_loops();
        }

        Code.replace(Code.find("END"), 3, "}");
        ExpectedCode.replace(ExpectedCode.find("END"), 3, "");
    }

    CAPTURE(Code);
    REQUIRE(formatCode(ExpectedCode) == runDCECanicalizeOnCode(Code));
}

TEST_CASE("DCECanonicalizeTool switch", "[dcec][switch]") {
    std::string Code = R"code(
    int foo(int a){
        switch(a){
            case 1:
                break;
            case 2:{
                a = 3;
                break;
            }
            case -1:
            case 3:
                a = 4;
                break;
            case 4:
            default:
                return 2;

        }
        return a;
    }
    )code";
    std::string ExpectedCode = R"code(
    int foo(int a){
        switch(a){
            case 1:{
                break;
            }
            case 2:{
                a = 3;
                break;
            }
            case -1:
            case 3:{
                a = 4;
                }
                break;
            case 4:
            default:{
                return 2;
                }
        }
        return a;
    }
    )code";

    REQUIRE(formatCode(ExpectedCode) == runDCECanicalizeOnCode(Code));
}

TEST_CASE("DCECanonicalizeTool empty body", "[dcec][if][for][do]") {
    std::string Code = R"code(
    int foo(int a){
        if (a > 0);
        for(;;);
        do;while(1);
        return a;
    }
    )code";
    std::string ExpectedCode = R"code(
    int foo(int a){
        if (a > 0){}
        for(;;){}
        do{}while(1);
        return a;
    }
    )code";

    REQUIRE(formatCode(ExpectedCode) == runDCECanicalizeOnCode(Code));
}

TEST_CASE("DCECanonicalizeTool nested if", "[dcec][if][nested]") {
    std::string Code = R"code(
    int foo(int a){
        if (a > 0)
            if (a == 10)
                return 10;
        return a;
    }
    )code";
    std::string ExpectedCode = R"code(
    int foo(int a){
        if (a > 0){
            if (a == 10){
                return 10;
            }
        }
        return a;
    }
    )code";

    REQUIRE(formatCode(ExpectedCode) == runDCECanicalizeOnCode(Code));
}

TEST_CASE("DCECanonicalizeTool nested complex",
          "[dcec][if][for][switch][while][do][nested]") {
    std::string Code = R"code(
    int foo(int a){
        if (a > 0)
            for (int b=a; b > 0; --b)
                switch(b){
                    case 1:
                        break;
                    default:
                        while(b > 10) --b;
                        return b;
                }
        else
            do
                ++a;while(a<0);
        return a;
    }
    )code";
    std::string ExpectedCode = R"code(
    int foo(int a){
        if (a > 0){
            for (int b=a; b > 0; --b){
                switch(b){
                    case 1:{
                        break;
                    }
                    default:{
                        while(b > 10){ --b;}
                        }
                        return b;
                }
            }
        }
        else {
            do{ ++a;}
            while(a<0);
        }
        return a;
    }
    )code";

    REQUIRE(formatCode(ExpectedCode) == runDCECanicalizeOnCode(Code));
}
