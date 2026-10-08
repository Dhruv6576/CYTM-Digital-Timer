/*-------------------------------------------------------------------------*/
/* SDCC DISPLAY DIAGNOSTIC TEST                                            */
/*-------------------------------------------------------------------------*/
#include "numicro_8051.h"

#define D1 P10  
#define D2 P03  
#define D3 P04  
#define DL P06  
#define SA P00  
#define SB P02  
#define SC P05  
#define SD P12  
#define SE P11  
#define SF P01  
#define SG P14  
#define SDP P13  

unsigned char d_buf[3] = {0}; 
unsigned char d_mux=0;
__code unsigned char seg[10] = {0x3F,0x06,0x5B,0x4F,0x66,0x6D,0x7D,0x07,0x7F,0x6F};

// --- DISPLAY INTERRUPT (The exact one from the OS) ---
void Timer0_ISR(void) __interrupt (1) {
    unsigned char v;
    
    clr_CKCON_T0M; clr_TCON_TF0; TH0=0xF8; TL0=0x30;
    
    if(d_mux==0) v = d_buf[0];
    else if(d_mux==1) v = d_buf[1];
    else if(d_mux==2) v = d_buf[2];
    else v = 0;
    
    v = ~v; 

    // Blanking
    D1=0; D2=0; D3=0; DL=0;
    
    // Segment Injection
    if(v & 0x01) SA=1; else SA=0;
    if(v & 0x02) SB=1; else SB=0;
    if(v & 0x04) SC=1; else SC=0;
    if(v & 0x08) SD=1; else SD=0;
    if(v & 0x10) SE=1; else SE=0;
    if(v & 0x20) SF=1; else SF=0;
    if(v & 0x40) SG=1; else SG=0;
    if(v & 0x80) SDP=1; else SDP=0;

    // Digit Activation
    if(d_mux==0) D1=1;
    else if(d_mux==1) D2=1;
    else if(d_mux==2) D3=1;
    
    d_mux = (d_mux+1)&3; 
}

// Simple brute-force delay for testing
void test_delay(void) { 
    unsigned int i, j; 
    for(i=0; i<300; i++) {
        for(j=0; j<1000; j++); 
    }
}

void main(void) {
    unsigned char test_num = 0;
    
    // Initialize Pins & Timer
    P0M1=0x00; P0M2=0xFF; P1M1=0x00; P1M2=0x7F; 
    TIMER0_MODE1_ENABLE; clr_CKCON_T0M; TH0=0xF8; TL0=0x30;
    ENABLE_TIMER0_INTERRUPT; ENABLE_GLOBAL_INTERRUPT; set_TCON_TR0;   
    
    while(1) {
        // Push the same number to all three digits
        d_buf[0] = seg[test_num];
        d_buf[1] = seg[test_num];
        d_buf[2] = seg[test_num];
        
        test_delay(); // Wait
        
        // Cycle to the next number (0 through 9)
        if(++test_num > 9) {
            test_num = 0;
        }
    }
}