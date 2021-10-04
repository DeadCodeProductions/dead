add_library(ccc-lib CallChainChecker.cpp)
target_link_libraries(ccc-lib PUBLIC clang-cpp Boost::headers)

add_executable(ccc CallChainCheckerTool.cpp)
target_link_libraries(ccc PUBLIC ccc-lib LLVM)
