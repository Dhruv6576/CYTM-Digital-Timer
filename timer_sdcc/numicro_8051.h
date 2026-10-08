#ifndef NUMICRO_8051_H
#define NUMICRO_8051_H

// --- SDCC SFR Definitions for MS51 ---
__sfr __at (0x80) P0;
__sfr __at (0x90) P1;
__sfr __at (0xA0) P2;
__sfr __at (0xB0) P3;
__sfr __at (0xB1) P0M1;
__sfr __at (0xB2) P0M2;
__sfr __at (0xD1) P1M1;
__sfr __at (0xD2) P1M2;
__sfr __at (0x8E) CKCON;
__sfr __at (0x88) TCON;
__sfr __at (0x89) TMOD;
__sfr __at (0x8A) TL0;
__sfr __at (0x8C) TH0;
__sfr __at (0xA8) IE;
__sfr __at (0xC7) TA;
__sfr __at (0xA4) IAPTRG;
__sfr __at (0xA5) IAPUEN;
__sfr __at (0xA6) IAPAL;
__sfr __at (0xA7) IAPAH;
__sfr __at (0xAE) IAPFD;
__sfr __at (0xAF) IAPCN;
__sfr __at (0x9F) CHPCON;

// --- SDCC Pin Definitions (SBITs) ---
__sbit __at (0x87) P07;
__sbit __at (0x86) P06;
__sbit __at (0x85) P05;
__sbit __at (0x84) P04;
__sbit __at (0x83) P03;
__sbit __at (0x82) P02;
__sbit __at (0x81) P01;
__sbit __at (0x80) P00;

__sbit __at (0x97) P17;
__sbit __at (0x94) P14;
__sbit __at (0x93) P13;
__sbit __at (0x92) P12;
__sbit __at (0x91) P11;
__sbit __at (0x90) P10;

__sbit __at (0xA0) P20;
__sbit __at (0xB0) P30;

__sbit __at (0xAF) EA;
__sbit __at (0xA9) ET0;
__sbit __at (0x8C) TR0;
__sbit __at (0x8D) TF0;

// --- System OS Macros ---
#define MODIFY_HIRC(x)         // MS51 natively boots at 24MHz
#define TIMER0_MODE1_ENABLE    TMOD &= 0xF0; TMOD |= 0x01
#define clr_CKCON_T0M          CKCON &= ~0x08
#define ENABLE_TIMER0_INTERRUPT ET0 = 1
#define ENABLE_GLOBAL_INTERRUPT EA = 1
#define set_TCON_TR0           TR0 = 1
#define clr_TCON_TF0           TF0 = 0

#endif