/* ISR-обработчики (Cortex-M4 system + периферия). */

void NMI_Handler(void)        { while (1) {} }
void HardFault_Handler(void)  { while (1) {} }
void MemManage_Handler(void)  { while (1) {} }
void BusFault_Handler(void)   { while (1) {} }
void UsageFault_Handler(void) { while (1) {} }
void DebugMon_Handler(void)   {}
/* SVC/PendSV/SysTick — отдают FreeRTOS-порту. */