# Rung A of HTTP/3 on Flow: picoquic driven by Net2 over IUDPSocket. Off by default (option FLOWQUIC).
# TLS here is OpenSSL, which flow already links. RFD66606-2261 wants mbedTLS; that is a recorded deviation.
set(FLOWQUIC_PICOQUIC_DIR "" CACHE PATH "picoquic source tree; blank fetches FLOWQUIC_PICOQUIC_TAG")
set(FLOWQUIC_PICOQUIC_TAG "a6f85e8a73a6e8d9bc2143ebacb4f218ed4c0caf" CACHE STRING "picoquic commit to fetch")

set(picoquic_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(BUILD_PICO_SIM OFF CACHE BOOL "" FORCE)
set(BUILD_DEMO OFF CACHE BOOL "" FORCE)
set(BUILD_HTTP ON CACHE BOOL "" FORCE) # h3zero and WebTransport (rung B)
set(BUILD_PQBENCH OFF CACHE BOOL "" FORCE)
set(BUILD_LOGREADER OFF CACHE BOOL "" FORCE)
set(PICOQUIC_FETCH_PTLS ON CACHE BOOL "" FORCE)
set(WITH_OPENSSL ON CACHE BOOL "" FORCE)

if(FLOWQUIC_PICOQUIC_DIR)
  add_subdirectory(${FLOWQUIC_PICOQUIC_DIR} picoquic EXCLUDE_FROM_ALL)
else()
  include(FetchContent)
  FetchContent_Declare(picoquic_src GIT_REPOSITORY https://github.com/private-octopus/picoquic.git GIT_TAG ${FLOWQUIC_PICOQUIC_TAG})
  FetchContent_GetProperties(picoquic_src)
  if(NOT picoquic_src_POPULATED)
    FetchContent_Populate(picoquic_src)
    add_subdirectory(${picoquic_src_SOURCE_DIR} ${picoquic_src_BINARY_DIR} EXCLUDE_FROM_ALL)
  endif()
endif()

add_flow_target(EXECUTABLE NAME flow_quic_echo SRCS QuicEcho.actor.cpp QuicDriver.cpp)
target_include_directories(flow_quic_echo PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(flow_quic_echo PUBLIC flow picohttp-core picoquic-core)
