Stochastic BPE (Stochastic Byte pair encoding), a file compressor with stochastic capability.

# Benchmark
| Name & Command | Uncompressed Size | Compressed Size | Compress Time | Decompress Time
|-:|-|-|-|-
| [enwik8](http://mattmahoney.net/dc/enwik8.zip) (c enwik8 enwik8_sbpe.bin .be1 .a110 .a21) | 100,000,000 bytes | 91,153,707 bytes | 9m 7.234s | -
| file_sbpe.bin (c file_str.txt file_sbpe.bin .be1 .a2500) | 2109 bytes | 1476 bytes | 1.050s | 0.031s

**Footnotes:**  
`file_sbpe.bin` is generated from `enc_sbpe.py`.  
Tested on `i5-9300H Void x86_64 24 GB RAM`.  
