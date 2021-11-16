add_library(DCEIlib DCEInstrumenter.cpp)
target_include_directories(DCEIlib PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(DCEIlib PUBLIC clang-cpp LLVM)

add_subdirectory(tool)

add_library(FIPCFGExtractor MODULE FIPCFGExtractor.cpp)
target_include_directories(FIPCFGExtractor PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
