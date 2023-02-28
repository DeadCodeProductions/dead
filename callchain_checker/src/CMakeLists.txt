add_library(ccc-lib CallChainChecker.cpp)
target_include_directories(ccc-lib PUBLIC ${LLVM_INCLUDE_DIRS} ${CLANG_INCLUDE_DIRS})
target_link_libraries(ccc-lib PUBLIC clang-cpp Boost::headers)

add_executable(ccc CallChainCheckerTool.cpp)
target_include_directories(ccc PRIVATE ${LLVM_INCLUDE_DIRS} ${CLANG_INCLUDE_DIRS})
target_link_libraries(ccc PUBLIC ccc-lib LLVM)
