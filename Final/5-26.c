/*-------------------------------------------------------------------------*/
/* CYTM_V4 "Commercial OS" - IAR EDITION (H&D Branded Victory Code)        */
/* UI UPDATE: Dynamic Auto-Formatting for 2-Digit Manufacturing Months     */
/*-------------------------------------------------------------------------*/
#include "numicro_8051.h"

/* =========================================zzz============================== */
/* ??? FACTORY CONFIGURATION - CHANGE MANUFACTURING DATE HERE ???           */
/* ======================================================================= */
#define MFG_MONTH       5   // Month (e.g. 5 for May, 12 for Dec)
#define MFG_YEAR_TENS   2    // Year first digit (e.g. 2 for 2027)
#define MFG_YEAR_ONES   6    // Year second digit (e.g. 7 for 2027)

#define FLASH_KB        16   // Chip flash size: MG51xB9AE = 16, MG51xC9AE = 32
#define CAL_MS          1000 // 1ms ticks per timer second. Clock calibration:
                             // run 999 s, time it with a stopwatch, then
                             // CAL_MS = 1000 * 999 / stopwatch_seconds
#define SET_TIMEOUT     3000 // x10ms: 30 s with no key in settings = cancel, nothing saved
/* ======================================================================= */

#define RELAY P07  
#define B_SET P17  
#define B_STP P30  
#define B_STA P20  

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

// --- FACTORY DEFAULTS ---
// ON: 2 (Minutes Mode = 1), OFF: 30 (Seconds Mode = 0)
volatile unsigned int on_v=2, off_v=30, t_val=2, val=1, ms=0;
volatile unsigned char on_m=1, off_m=0;
// ----------------------------

volatile unsigned char mode=0, sec_cnt=0, u_st=0, d_mux=0;
volatile unsigned char is_run=0, phase=1, t_min=0; 

volatile unsigned int set_time=0, up_time=0, dn_time=0, combo_time=0;
volatile unsigned char tick_10ms=0;

volatile unsigned int brand_ms=2000; 
volatile unsigned int date_ms=0;

unsigned int new_on_v, idle=0;  // ON value held until settings are confirmed
unsigned char new_on_m, mem_ah=0x3F, mem_err=0;

volatile unsigned char d_buf[3] = {0}; 
const unsigned char seg[10] = {0x3F,0x06,0x5B,0x4F,0x66,0x6D,0x7D,0x07,0x7F,0x6F};

void OUT_SEG(unsigned char v) { 
    v = ~v; 
    SA = (v & 0x01) ? 1 : 0;
    SB = (v & 0x02) ? 1 : 0;
    SC = (v & 0x04) ? 1 : 0;
    SD = (v & 0x08) ? 1 : 0;
    SE = (v & 0x10) ? 1 : 0;
    SF = (v & 0x20) ? 1 : 0;
    SG = (v & 0x40) ? 1 : 0;
    SDP= (v & 0x80) ? 1 : 0; 
}

void fmt(unsigned int v, unsigned char dot) {
    unsigned char h=0, t=0, u;
    while(v>=100) { h++; v-=100; }
    u = v; 
    while(u>=10)  { t++; u-=10; }
    d_buf[0] = h ? seg[h] : 0; 
    d_buf[1] = (h||t) ? seg[t] : 0; 
    d_buf[2] = seg[u] | (dot ? 0x80 : 0);
}

void txt(unsigned char a, unsigned char b, unsigned char c) {
    d_buf[0]=a; d_buf[1]=b; d_buf[2]=c;
}

void iap_w(unsigned char a, unsigned char d) { 
    unsigned char ea_bak = EA; EA = 0;
    IAPAL=a; IAPFD=d; TA=0xAA; TA=0x55; IAPTRG |= 0x01; 
    EA = ea_bak;
}

unsigned char iap_r(unsigned char a) { 
    unsigned char ea_bak = EA; EA = 0;
    IAPAL=a; TA=0xAA; TA=0x55; IAPTRG |= 0x01; 
    EA = ea_bak;
    return IAPFD; 
}

// High byte of the last 256 bytes of APROM (0x3F on 16K, no LDROM). LDROM sits at the
// top of flash, so its size (CONFIG1.LDSIZE) moves the APROM end down.
// LDSIZE: 111=0K, 110=1K, 101=2K, 100=3K, 0xx=4K. IAP must be enabled.
unsigned char mem_page(void) {
    unsigned char ld;
    IAPCN=0xC0; IAPAH=0; ld = iap_r(1) & 7;
    ld = (ld & 4) ? 7 - ld : 4;
    return FLASH_KB*4 - ld*4 - 1;
}

void MemSave(void) {
    EA=0; TA=0xAA; TA=0x55; CHPCON|=1; TA=0xAA; TA=0x55; IAPUEN|=1; IAPAH=mem_ah;
    IAPCN=0x22; iap_w(0, 0xFF);
    IAPCN=0x21;
    iap_w(1, on_v>>8); iap_w(2, on_v);
    iap_w(3, off_v>>8); iap_w(4, off_v);
    iap_w(5, on_m); iap_w(6, off_m);
    iap_w(0, 0xA8); // Marker last: power loss mid-save leaves page unmarked, MemLoad keeps defaults
    TA=0xAA; TA=0x55; IAPUEN&=~1;
    IAPCN=0;        // Read back to catch a failed erase/program
    mem_err = iap_r(0) != 0xA8
           || iap_r(1) != (unsigned char)(on_v>>8)  || iap_r(2) != (unsigned char)on_v
           || iap_r(3) != (unsigned char)(off_v>>8) || iap_r(4) != (unsigned char)off_v
           || iap_r(5) != on_m || iap_r(6) != off_m;
    TA=0xAA; TA=0x55; CHPCON&=~1; EA=1;
}

void MemLoad(void) {
    unsigned int a, b;
    unsigned char am, bm;
    EA=0; TA=0xAA; TA=0x55; CHPCON|=1;
    mem_ah = mem_page();
    IAPAH=mem_ah; IAPCN=0;
    if(iap_r(0) == 0xA8) {
        a = (iap_r(1)<<8) | iap_r(2);
        b = (iap_r(3)<<8) | iap_r(4);
        am = iap_r(5);
        bm = iap_r(6);
        // Corrupt data keeps factory defaults. Old firmware allowed 0: treat as 1.
        if(a <= 999 && b <= 999 && am <= 1 && bm <= 1) {
            on_v = a ? a : 1;
            off_v = b ? b : 1;
            on_m = am;
            off_m = bm;
        }
    }
    TA=0xAA; TA=0x55; CHPCON&=~1; EA=1;
}

#pragma vector = 0x0B
__interrupt void Timer0_ISR(void) {
    static unsigned char t10 = 0;
    unsigned int current_target; 
    
    clr_CKCON_T0M; clr_TCON_TF0; TH0=0xF8; TL0=0x30;
    D1=0; D2=0; D3=0; DL=0;
    
    if(d_mux==0) { OUT_SEG(d_buf[0]); D1=1; }
    else if(d_mux==1) { OUT_SEG(d_buf[1]); D2=1; }
    else if(d_mux==2) { OUT_SEG(d_buf[2]); D3=1; }
    else { OUT_SEG(0); if(is_run && phase) SB=0; if(mode) SF=0; DL=1; }
    d_mux = (d_mux+1)&3; 
    
    if (brand_ms > 0) brand_ms--;
    if (date_ms > 0) date_ms--;

    if (++t10 >= 10) {
        t10 = 0;
        tick_10ms = 1;
    }
    
    if(is_run && ++ms>=CAL_MS) {
        ms=0; 
        if(phase) {
            if (on_m) { if(++sec_cnt < 60) return; sec_cnt=0; }
            current_target = on_v;
        } else {
            if (off_m) { if(++sec_cnt < 60) return; sec_cnt=0; }
            current_target = off_v;
        }

        val++;
        if(val > current_target) { 
            phase = !phase; 
            val=1; 
            sec_cnt=0; 
        }
    }
}

void do_up(void) {
    if(!mode) is_run=1;
    else if(mode==1||mode==3) { u_st=2; t_min=1; }
    else {
        t_val++;
        if(t_val > 999) t_val=1;
    }
}

void do_dn(void) {
    if(!mode) is_run=0;
    else if(mode==1||mode==3) { u_st=1; t_min=0; }
    else {
        if (t_val > 1) t_val--;
        else t_val = 999;
    }
}

void main(void) {
    unsigned char m; 
    unsigned char current_phase;
    unsigned char is_min_mode;
    unsigned int current_target; 
    unsigned int m_left;         
    unsigned char s_left;        
    unsigned int total_sec_left;
    unsigned int cur_val, cur_ms;
    unsigned char cur_sec, brand_on, date_on;

    MODIFY_HIRC(HIRC_24);
    P0M1=0x00; P0M2=0xFF;
    P1M1=0x00; P1M2=0x7F;
    P30_QUASI_MODE;   // STOP key: weak pull-up
    set_P2S_P20UP;    // START key: P20 internal pull-up

    B_SET = 1; B_STA = 1; B_STP = 1;

    MemLoad();

    is_run = 1;
    phase = 1;
    val = 1;
    sec_cnt = 0;
    brand_ms = 2000;
    date_ms = 0;

    TIMER0_MODE1_ENABLE; clr_CKCON_T0M; TH0=0xF8; TL0=0x30;
    ENABLE_TIMER0_INTERRUPT; ENABLE_GLOBAL_INTERRUPT; set_TCON_TR0;

    while(1) {
        // ISR updates these mid-loop; 16-bit reads take 2 bytes, so copy with ISR off
        EA=0;
        current_phase = phase;
        cur_val = val;
        cur_sec = sec_cnt;
        cur_ms = ms;
        brand_on = (brand_ms != 0);
        date_on = (date_ms != 0);
        EA=1;

        RELAY = (is_run && current_phase);
        m = mode;
        is_min_mode = current_phase ? on_m : off_m;
        current_target = current_phase ? on_v : off_v;

        if(!m) {
            if (date_on) {
                // --- DYNAMIC MANUFACTURING DATE LOGIC ---
                if (MFG_MONTH > 9) {
                    // Two-digit month (10, 11, 12) -> Shows MM.Y
                    txt(seg[MFG_MONTH / 10], seg[MFG_MONTH % 10] | 0x80, seg[MFG_YEAR_ONES]);
                } else {
                    // One-digit month (1-9) -> Shows M.YY
                    txt(seg[MFG_MONTH] | 0x80, seg[MFG_YEAR_TENS], seg[MFG_YEAR_ONES]); 
                }
            } 
            else if (brand_ms > 0) {
                if (mem_err) txt(0x79, 0x50, 0x50);  // "Err": last save did not verify
                else txt(0x76, 0x40, 0x5E);
            }
            else {
                if (is_min_mode) {
                    if (cur_sec == 0) {
                        m_left = current_target - cur_val + 1;
                        s_left = 0;
                    } else {
                        m_left = current_target - cur_val;
                        s_left = 60 - cur_sec;
                    }
                    total_sec_left = m_left * 60 + s_left;
                } else {
                    total_sec_left = current_target - cur_val + 1;
                }

                if (is_run && (total_sec_left % 5 == 0) && total_sec_left != 0 && !(cur_val == 1 && cur_sec == 0)) {
                    txt(0x3F, current_phase ? 0x54 : 0x71, current_phase ? 0 : 0x71); 
                } 
                else {
                    if (is_min_mode) {
                        if (m_left < 10) {
                            d_buf[0] = seg[m_left] | 0x80; 
                            d_buf[1] = seg[s_left / 10];
                            d_buf[2] = seg[s_left % 10];
                        } 
                        else if (m_left < 100) {
                            d_buf[0] = seg[m_left / 10];
                            d_buf[1] = seg[m_left % 10] | 0x80; 
                            d_buf[2] = seg[s_left / 10];
                        } 
                        else {
                            d_buf[0] = seg[m_left / 100];
                            d_buf[1] = seg[(m_left % 100) / 10];
                            d_buf[2] = seg[m_left % 10] | 0x80;
                        }
                    } else {
                        fmt(total_sec_left, (is_run && cur_ms < CAL_MS/2));
                    }
                }
            }
        }
        else if(m==1||m==3) { 
            if(!u_st) txt(0x3F, (m==1)?0x54:0x71, (m==1)?0:0x71);
            else if(u_st==1) txt(0x6D, 0x79, 0x39); 
            else txt(0x54, 0x06, 0x54); 
        }
        else fmt(t_val, 0); 
        
        if (tick_10ms) {
            tick_10ms = 0;

            if (!B_SET || !B_STA || !B_STP) idle = 0;
            else if (mode && ++idle >= SET_TIMEOUT) mode = 0;  // Walked away: cancel, nothing saved

            if (!B_STA && !B_STP) {
                if (combo_time < 250) combo_time++;
                if (combo_time == 200) {
                    EA=0; date_ms = 3000; EA=1;
                }
                up_time = 0; 
                dn_time = 0;
            } else {
                combo_time = 0; 
                
                if (!B_STA) {
                    if (up_time < 10000) up_time++;
                    if (up_time == 3) { do_up(); } 
                    else if (up_time > 50) { if (up_time % 5 == 0) do_up(); }
                } else { up_time = 0; }
                
                if (!B_STP) {
                    if (dn_time < 10000) dn_time++;
                    if (dn_time == 3) { do_dn(); } 
                    else if (dn_time > 50) { if (dn_time % 5 == 0) do_dn(); }
                } else { dn_time = 0; }
            }

            if (!B_SET) {
                if (set_time < 150) set_time++; 
                if (set_time == 100) {  
                    if(!mode) { mode=1; u_st=0; t_val=on_v; t_min=on_m; }
                }
            } else {
                if (set_time >= 3 && set_time < 100) { 
                    if(mode==1) mode=2;
                    else if(mode==2) { new_on_v=t_val; new_on_m=t_min; mode=3; u_st=0; t_val=off_v; t_min=off_m; }
                    else if(mode==3) mode=4;
                    else if(mode==4) {
                        // Commit both phases and restart the cycle, same as power-up
                        EA=0;
                        on_v=new_on_v; on_m=new_on_m; off_v=t_val; off_m=t_min;
                        phase=1; val=1; sec_cnt=0; ms=0; is_run=1; mode=0;
                        brand_ms = 2000;
                        MemSave();
                    }
                }
                set_time = 0; 
            }
        }
    }
}