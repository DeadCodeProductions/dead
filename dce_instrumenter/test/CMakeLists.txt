add_executable(dce_test test_driver.cpp test_tool.cpp dcei_test.cpp dcec_test.cpp static_global_test.cpp)

target_link_libraries(dce_test PRIVATE Catch2::Catch2 DCEIlib)
target_include_directories(dce_test SYSTEM PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/extern)

catch_discover_tests(dce_test)
