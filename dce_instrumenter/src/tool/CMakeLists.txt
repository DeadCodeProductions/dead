add_executable(dcei DCEInstrument.cpp)
target_link_libraries(dcei PUBLIC DCEIlib)

add_executable(static-annotator StaticAnnotator.cpp)
target_link_libraries(static-annotator PUBLIC DCEIlib)
