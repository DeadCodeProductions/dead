#include "test_tool.hpp"
#include <catch2/catch.hpp>

TEST_CASE("DCEInstrumentTool if-else compound", "[dcei][if]") {
    auto Code = R"code(
    int foo(int a){
        if (a > 0){
        a = 1;
        } else{
        a = 0;
        }
        return a;
    }
    )code";
    auto ExpectedCode = R"code(void DCEMarker0_(void);
    void DCEMarker1_(void);

    int foo(int a){
        if (a > 0){
        DCEMarker0_();
        a = 1;
        } else{
        DCEMarker1_();
        a = 0;
        }
        return a;
    }
    )code";

    REQUIRE(formatCode(ExpectedCode) == runDCEInstrumentOnCode(Code));
}

TEST_CASE("DCEInstrumentTool if-else non-compound", "[dcei][if]") {
    auto Code = R"code(
    int foo(int a){
        if (a > 0)
            a=1;
        else
            a=0;
        return a;
    }
    )code";
    auto ExpectedCode = R"code(void DCEMarker0_(void);
    void DCEMarker1_(void);

    int foo(int a){
        if (a > 0){
        DCEMarker0_();
            a=1;
        } else{
        DCEMarker1_();
            a=0;
        }
        return a;
    }
    )code";

    REQUIRE(formatCode(ExpectedCode) == runDCEInstrumentOnCode(Code));
}

TEST_CASE("DCEInstrumentTool nested if", "[dcei][if][nested]") {
    auto Code = R"code(
    int foo(int a){
        if (a > 0){
            if (a==1) {
                a = 1;
            }
            else 
                a = 2;
            
        }
        return 0;
    }
    )code";
    auto ExpectedCode = R"code(void DCEMarker0_(void);
    void DCEMarker1_(void);
    void DCEMarker2_(void);

    int foo(int a){
        if (a > 0){
            DCEMarker0_();
            if (a==1) {
                DCEMarker1_();
                a = 1;
            }
            else {
                DCEMarker2_();
                a = 2;
            }
        }
        return 0;
    }
    )code";

    REQUIRE(formatCode(ExpectedCode) == runDCEInstrumentOnCode(Code));
}

TEST_CASE("DCEInstrumentTool if with return", "[dcei][if][return]") {
    auto Code = R"code(
    int foo(int a){
        if (a > 0)
            return 1;
        return 0;
    }
    )code";
    auto ExpectedCode = R"code(void DCEMarker0_(void);
    void DCEMarker1_(void);

    int foo(int a){
        if (a > 0){
            DCEMarker0_();
            return 1;
        }
        DCEMarker1_();
        return 0;
    }
    )code";

    REQUIRE(formatCode(ExpectedCode) == runDCEInstrumentOnCode(Code));
}

TEST_CASE("DCEInstrumentTool nested if with return",
          "[dcei][if][return][nested]") {
    auto Code = R"code(
    int foo(int a){
        if (a >= 0) {
            if (a >= 0) {
                return 1;
            }
        }
        return 0;
    }
    )code";
    auto ExpectedCode = R"code(void DCEMarker0_(void);
    void DCEMarker1_(void);
    void DCEMarker2_(void);
    void DCEMarker3_(void);

    int foo(int a){
        if (a >= 0) {
            DCEMarker0_();
            if (a >= 0) {
                DCEMarker2_();
                return 1;
            }
            DCEMarker3_();
        }
        DCEMarker1_();
        return 0;
    }
    )code";

    REQUIRE(formatCode(ExpectedCode) == runDCEInstrumentOnCode(Code));
}

TEST_CASE("DCEInstrumentTool for stmt nested if with return",
          "[dcei][for][if][nested][return]") {

    auto Code = R"code(
    int foo(int a){
        int b = 0;
        for (int i = 0; i < a; ++i)
            if (i == 3)
                return b;
            else 
                ++b;
        return b;
    }
    )code";

    auto ExpectedCode = R"code(void DCEMarker0_(void);
    void DCEMarker1_(void);
    void DCEMarker2_(void);
    void DCEMarker3_(void);
    void DCEMarker4_(void);

    int foo(int a){
        int b = 0;
        for (int i = 0; i < a; ++i){
            DCEMarker0_();
            if (i == 3){
                DCEMarker2_();
                return b;
            } else {
                DCEMarker3_();
                ++b;
            }
            DCEMarker4_();
        }
        DCEMarker1_();
        return b;
    }
    )code";

    REQUIRE(formatCode(ExpectedCode) == runDCEInstrumentOnCode(Code));
}

TEST_CASE("DCEInstrumentTool for stmt nested if with return and extra stmt",
          "[dcei][for][if][nested][return]") {

    auto Code = R"code(
    int foo(int a){
        int b = 0;
        for (int i = 0; i < a; ++i){
            if (i == 3)
                return b;
            else 
                ++b;
            ++b;
        }
        return b;
    }
    )code";

    auto ExpectedCode = R"code(void DCEMarker0_(void);
    void DCEMarker1_(void);
    void DCEMarker2_(void);
    void DCEMarker3_(void);
    void DCEMarker4_(void);

    int foo(int a){
        int b = 0;
        for (int i = 0; i < a; ++i){
            DCEMarker0_();
            if (i == 3){
                DCEMarker2_();
                return b;
            } else {
                DCEMarker3_();
                ++b;
            }
            DCEMarker4_();
            ++b;
        }
        DCEMarker1_();
        return b;
    }
    )code";

    REQUIRE(formatCode(ExpectedCode) == runDCEInstrumentOnCode(Code));
}

TEST_CASE("DCEInstrumentTool for stmt with return", "[dcei][for][return]") {

    auto Code = R"code(
    int foo(int a){
        int b = 0;
        for (int i = 0; i < a; ++i)
            return i;
        return b;
    }
    )code";

    auto ExpectedCode = R"code(void DCEMarker0_(void);
    void DCEMarker1_(void);

    int foo(int a){
        int b = 0;
        for (int i = 0; i < a; ++i){
            DCEMarker0_();
            return i;
        }
        DCEMarker1_();
        return b;
    }
    )code";

    REQUIRE(formatCode(ExpectedCode) == runDCEInstrumentOnCode(Code));
}

TEST_CASE("DCEInstrumentTool while stmt with return", "[dcei][while][return]") {

    auto Code = R"code(
    int foo(int a){
        int b = 0;
        while(true)
            return 0;
        return b;
    }
    )code";

    auto ExpectedCode = R"code(void DCEMarker0_(void);
    void DCEMarker1_(void);

    int foo(int a){
        int b = 0;
        while(true) {
            DCEMarker0_();
            return 0;
        }
        DCEMarker1_();
        return b;
    }
    )code";

    REQUIRE(formatCode(ExpectedCode) == runDCEInstrumentOnCode(Code));
}

TEST_CASE("DCEInstrumentTool do while stmt with return", "[dcei][do][return]") {

    auto Code = R"code(
    int foo(int a){
        int b = 0;
        do 
          return b;
        while(b<10);
        return b;
    }
    )code";

    auto ExpectedCode = R"code(void DCEMarker0_(void);
    void DCEMarker1_(void);

    int foo(int a){
        int b = 0;
        do {
          DCEMarker0_();
          return b;
        } while(b<10);
        DCEMarker1_();
        return b;
    }
    )code";

    REQUIRE(formatCode(ExpectedCode) == runDCEInstrumentOnCode(Code));
}

TEST_CASE("DCEInstrumentTool switch", "[dcei][switch][return]") {
    auto Code = R"code(
    int foo(int a){
        switch(a){
        case 1:
            a = 2;
            break;
        case 2:
        case 3:
            break;
        case 4:
            return 3;
        case 5:{
            a = 5;
        }
        default:
            a = 42;
        }
        return a;
    }
    )code";
    auto ExpectedCode = R"code(void DCEMarker0_(void);
    void DCEMarker1_(void);
    void DCEMarker2_(void);
    void DCEMarker3_(void);
    void DCEMarker4_(void);
    void DCEMarker5_(void);

    int foo(int a){
        switch(a){
        case 1: {
          DCEMarker1_();
            a = 2;
          } break;
        case 2:
        case 3:{
          DCEMarker5_();
           break;
           }
        case 4:{
          DCEMarker2_();
          return 3;
          }
        case 5:{
          DCEMarker3_();
          a = 5;
        }
        default:{
          DCEMarker4_();
          a = 42;
          }
        }
        DCEMarker0_();
        return a;
    }
    )code";

    REQUIRE(formatCode(ExpectedCode) == runDCEInstrumentOnCode(Code));
}

