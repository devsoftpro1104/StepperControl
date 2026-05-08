cmake_minimum_required(VERSION 3.22)

set(CMAKE_TOOLCHAIN_FILE "${CMAKE_CURRENT_LIST_DIR}/toolchain/arm-none-eabi.cmake"
    CACHE FILEPATH "")

project(stepper_control_fw C ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# ----- MCU flags (общие для C/ASM/линкера) -----
set(MCU_OPTS
    -mcpu=cortex-m4
    -mthumb
    -mfpu=fpv4-sp-d16
    -mfloat-abi=hard
)

add_compile_options(
    ${MCU_OPTS}
    -ffunction-sections
    -fdata-sections
    -Wall -Wextra -Wundef
    $<$<COMPILE_LANGUAGE:C>:-Wno-unused-parameter>
)

add_link_options(
    ${MCU_OPTS}
    -T${CMAKE_CURRENT_LIST_DIR}/linker/stm32f407xx_flash.ld
    -Wl,--gc-sections
    -Wl,-Map=${PROJECT_NAME}.map
    -Wl,--print-memory-usage
    -specs=nano.specs
    -specs=nosys.specs
)

# ----- Paths -----
set(TP   "${CMAKE_CURRENT_LIST_DIR}/third_party")
set(CMSIS_INC   "${TP}/CMSIS/Include")
set(CUBE_INC    "${TP}/STM32CubeF4/Drivers/CMSIS/Device/ST/STM32F4xx/Include")
set(LL_INC      "${TP}/STM32CubeF4/Drivers/STM32F4xx_HAL_Driver/Inc")
set(LL_SRC_DIR  "${TP}/STM32CubeF4/Drivers/STM32F4xx_HAL_Driver/Src")
set(FRT         "${TP}/FreeRTOS-Kernel")
set(USBD        "${TP}/STM32_USB_Device_Library")

file(GLOB LL_SOURCES CONFIGURE_DEPENDS "${LL_SRC_DIR}/stm32f4xx_ll_*.c")
# Эти LL-файлы подтягивают stm32f4xx_hal.h и для F407 не нужны (FMC/FSMC отсутствуют, USB через USBD).
list(FILTER LL_SOURCES EXCLUDE REGEX "stm32f4xx_ll_(fmc|fsmc|usb|sdmmc)\\.c$")

set(FRT_SOURCES
    ${FRT}/croutine.c
    ${FRT}/event_groups.c
    ${FRT}/list.c
    ${FRT}/queue.c
    ${FRT}/stream_buffer.c
    ${FRT}/tasks.c
    ${FRT}/timers.c
    ${FRT}/portable/GCC/ARM_CM4F/port.c
    ${FRT}/portable/MemMang/heap_4.c
    ${FRT}/CMSIS_RTOS_V2/cmsis_os2.c
)

# ----- Project sources -----
file(GLOB_RECURSE APP_SOURCES        CONFIGURE_DEPENDS "src/app/src/*.c")
file(GLOB_RECURSE BSP_SOURCES        CONFIGURE_DEPENDS "src/bsp/src/*.c")
file(GLOB_RECURSE DRIVER_SOURCES     CONFIGURE_DEPENDS "src/drivers/*/*.c" "src/drivers/*/src/*.c")
file(GLOB_RECURSE DEVICE_SOURCES     CONFIGURE_DEPENDS "src/devices/*/*.c")
file(GLOB_RECURSE MIDDLEWARE_SOURCES CONFIGURE_DEPENDS "src/middleware/*/*.c" "src/middleware/*/src/*.c")

set(STARTUP_SOURCES
    src/startup/startup_stm32f407xx.s
    src/startup/system_stm32f4xx.c
    src/startup/syscalls.c
)

add_executable(${PROJECT_NAME}
    ${STARTUP_SOURCES}
    ${APP_SOURCES}
    ${BSP_SOURCES}
    ${DRIVER_SOURCES}
    ${DEVICE_SOURCES}
    ${MIDDLEWARE_SOURCES}
    ${LL_SOURCES}
    ${FRT_SOURCES}
)

target_compile_definitions(${PROJECT_NAME} PRIVATE
    STM32F407xx
    USE_FULL_LL_DRIVER
    HSE_VALUE=8000000U
    "CMSIS_device_header=\"stm32f4xx.h\""
    USE_CUSTOM_SYSTICK_HANDLER_IMPLEMENTATION=1
)

target_include_directories(${PROJECT_NAME} PRIVATE
    src/app/inc
    src/bsp/inc
    src/hal_port/inc
    src/drivers/uart/inc
    src/middleware/protocol/inc
    src/config
    ${CMSIS_INC}
    ${CUBE_INC}
    ${LL_INC}
    ${FRT}/include
    ${FRT}/portable/GCC/ARM_CM4F
    ${FRT}/CMSIS_RTOS_V2
    ${USBD}/Core/Inc
    ${USBD}/Class/CDC/Inc
)

set_target_properties(${PROJECT_NAME} PROPERTIES SUFFIX ".elf")

add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:${PROJECT_NAME}> ${PROJECT_NAME}.bin
    COMMAND ${CMAKE_OBJCOPY} -O ihex   $<TARGET_FILE:${PROJECT_NAME}> ${PROJECT_NAME}.hex
    COMMAND ${CMAKE_SIZE} $<TARGET_FILE:${PROJECT_NAME}>
)

# ----- Flash через OpenOCD -----
find_program(OPENOCD_EXECUTABLE openocd)
if(OPENOCD_EXECUTABLE)
    add_custom_target(flash
        COMMAND ${OPENOCD_EXECUTABLE}
                -f "${CMAKE_CURRENT_LIST_DIR}/openocd.cfg"
                -c "program $<TARGET_FILE:${PROJECT_NAME}> verify reset exit"
        DEPENDS ${PROJECT_NAME}
        USES_TERMINAL
        COMMENT "Flashing ${PROJECT_NAME}.elf via OpenOCD"
    )
    add_custom_target(reset
        COMMAND ${OPENOCD_EXECUTABLE}
                -f "${CMAKE_CURRENT_LIST_DIR}/openocd.cfg"
                -c "init; reset; exit"
        USES_TERMINAL
    )
endif()
