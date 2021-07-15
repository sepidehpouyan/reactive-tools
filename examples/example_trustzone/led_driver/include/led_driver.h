#ifndef LED_DRIVER_H
#define LED_DRIVER_H


#define LED_DRIVER_UUID \
	{ 0xb210f0df, 0x8a68, 0x4b24, { 0x88, 0x0a, 0x87, 0x13, 0x58, 0x6c, 0x4d, 0x10 } }
	
	

#define TA_AES_ALGO_ECB			0
#define TA_AES_ALGO_CBC			1
#define TA_AES_ALGO_GCM			2

#define TA_AES_SIZE_128BIT		(128 / 8)
#define TA_AES_SIZE_256BIT		(256 / 8)

#define TA_AES_MODE_ENCODE		        1
#define TA_AES_MODE_DECODE		        0

#define AES                     0 // aes-gcm-128
#define SPONGENT                1 // spongent-128


/* The function IDs implemented in this TA */
#define SET_KEY                               0
#define ATTEST                                1
#define HANDLE_INPUT                          2
#define ENTRY                                 3

#endif
