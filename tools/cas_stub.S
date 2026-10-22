/* cas stub "kernel" v3: fill the ABL framebuffer blue, then halt.
 * Runs with the MMU off (the shim jumps that way), x0 = boot_args PA. */
	.text
	.global _start
_start:
	movz	x1, #0x9C00, lsl #16		/* framebuffer PA 0x9C000000 */
	movz	w2, #0x00FF			/* ARGB 0xFF0000FF (pure blue) */
	movk	w2, #0xFF00, lsl #16
	movz	x3, #0x90A0			/* 1080*2340 = 0x2690A0 pixels */
	movk	x3, #0x0026, lsl #16
1:
	str	w2, [x1], #4
	subs	x3, x3, #1
	b.ne	1b
2:
	b	2b
