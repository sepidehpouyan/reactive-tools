#ifndef TA_H
#define TA_H


#define TA_ONE_UUID \
	{ 0xd3bc8433, 0x2eb5, 0x4c00, { 0xa0, 0x05, 0x3f, 0x87, 0xc1, 0xd3, 0xb4, 0x05} }
	
	
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


#endif /*TA_HELLO_WORLD_H*/
