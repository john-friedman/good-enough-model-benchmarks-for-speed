# Good Enough Model Benchmarks for Speed

I like [OpenRouter's fastest models chart](https://openrouter.ai/rankings#performance). But it is bad at comparing effective model speed. For instance:

- Output tokens per second are misleading, as GPT 5.6 Luna's tokenizer is twice as efficient as Claude 5's tokenizer.
- Does not show prefill (how much input text can be processed)
- Latency is median time to first token. So if a model on an endpoint is used primarily for large amounts of text input, it will appear slower than a model used primarily for small amounts of text input.
- Does not measure prompt caching latency reduction.

Here is a rough benchmark for how long things take.


## Benchmark 

1. Time before prefill
2. Standard prefill per second
3. Standard decode per second
4. Time before prefill (prompt cached)

Prefill text is 14k tokens using the GPT 5.x tokenizer. Decode is 150 tokens.

Run output is grouped by numbered app run:

```
runs/{count}/time_before_prefill/
runs/{count}/standard_prefill/
runs/{count}/standard_decode/
runs/{count}/time_before_prefill_prompt_cached/
```

### Mechanics

- Time before prefill: test each endpoint ten times with "Print 'On Belay' and nothing else."
- Standard prefill per second: Send 100 paragraphs of lorem ipsum. Calculate standard prefill per second as 1/(end time - time before prefill)
- Standard decode per second: Ask model to repeat 1:1 the prompt. Calculate standard decode as 1/(end time - standard prefill time - time before prefill)
- Time before prefill (prompt cached): Do time before prefill, cache it, follow up with "Print 'On Belay' and nothing else."

Note: this is not a rigorous estimation. It's a dumb and simple, good enough approach. Also, I currently run it off my laptop in California which incurs latency costs.

## Model Router

### Open Router

Metrics below are split into benchmark sets: Benchmark one combines runs 1 and 2; Benchmark two combines runs 3 and 4; Benchmark three is run 5. Values are medians; time columns are milliseconds. Each metric cell includes its sample count in parentheses. Decode/s only includes samples where the model returned the full decode passage.

#### openai/gpt-oss-120b

##### Benchmark one

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| cerebras/fp16 | 271.4 (10) | 295.6 (10) | 3.704 (10) | 6.857 (6) |
| groq | 366.4 (10) | 295.5 (10) | 1.297 (10) | 3.976 (3) |
| sambanova | 366.9 (10) | 305.8 (10) | 1.232 (10) | 4.276 (9) |
| amazon-bedrock | 426.6 (10) | 354.8 (10) | 1.991 (10) | 3.601 (8) |
| parasail/fp4 | 487.9 (10) | 408.2 (10) | 1.997 (10) | 0.281 (10) |
| baseten/fp4 | 492.6 (10) | 427.8 (10) | 4.965 (10) | 1.016 (10) |
| deepinfra/turbo | 508.3 (10) | 609.3 (10) | 2.839 (7) | 0.612 (9) |
| google-vertex/global | 700.4 (10) | 6336.3 (10) | 2.367 (10) | 0.715 (4) |
| together | 806.9 (10) | 837.9 (10) | 2.567 (10) | 0.229 (10) |
| amazon-bedrock/eu-west-1 | 825.6 (10) | 458.6 (10) | 1.353 (10) | 0.776 (10) |
| novita/fp4 | 956.9 (10) | - (0) | 3.446 (9) | 0.427 (10) |
| coreweave/fp4 | 1130.0 (10) | 848.2 (10) | 2.471 (8) | 0.084 (10) |
| digitalocean | 1191.0 (10) | 977.3 (10) | 2.675 (10) | 0.107 (10) |
| akashml/bf16 | 1371.7 (10) | 1497.8 (10) | 0.782 (9) | 0.170 (10) |
| mancer/fp8 | 1609.5 (10) | 1186.0 (10) | 0.561 (10) | 0.078 (10) |
| phala | 1633.5 (3) | 3001.0 (3) | 0.182 (1) | - (0) |
| deepinfra/bf16 | 2249.9 (10) | 1183.9 (10) | 2.668 (7) | 0.123 (10) |
| mara | 6725.9 (6) | 7423.3 (10) | 0.432 (4) | 0.374 (3) |
| siliconflow/fp8 | 6771.3 (10) | 5961.3 (10) | 0.277 (10) | 0.076 (10) |
| nebius/fp4 | 12192.4 (10) | 1380.8 (10) | 1.098 (9) | 1.296 (10) |

##### Benchmark two

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| groq | 258.2 (10) | 454.2 (10) | 0.863 (10) | 3.603 (7) |
| cerebras/fp16 | 423.7 (10) | 342.5 (10) | 2.161 (10) | 8.959 (4) |
| parasail/fp4 | 428.3 (10) | 551.6 (10) | 1.294 (10) | 0.251 (10) |
| baseten/fp4 | 498.1 (10) | 541.2 (10) | 3.308 (10) | 0.893 (10) |
| amazon-bedrock | 545.2 (10) | 602.6 (10) | 2.990 (10) | 1.355 (10) |
| sambanova | 566.8 (10) | 426.0 (10) | 1.012 (10) | 2.912 (10) |
| nebius/fp4 | 576.2 (10) | 547.1 (10) | 1.128 (10) | 1.025 (9) |
| google-vertex/global | 598.3 (10) | 2630.4 (10) | 1.547 (10) | 0.017 (6) |
| phala | 627.2 (9) | 497.2 (3) | 2.047 (2) | - (0) |
| deepinfra/turbo | 669.5 (10) | 697.8 (10) | 1.071 (10) | 1.132 (8) |
| together | 720.6 (10) | 723.3 (10) | 3.979 (10) | 0.457 (10) |
| novita/fp4 | 745.0 (10) | 1585.8 (10) | 7.601 (7) | 0.324 (9) |
| coreweave/fp4 | 827.1 (10) | 886.6 (10) | 1.843 (9) | 0.074 (10) |
| amazon-bedrock/eu-west-1 | 896.4 (10) | 850.7 (10) | 1.485 (10) | 0.757 (10) |
| mancer/fp8 | 929.3 (10) | 728.8 (10) | 0.833 (10) | 0.282 (10) |
| akashml/bf16 | 1068.5 (10) | 1534.2 (10) | 1.449 (10) | 0.206 (10) |
| digitalocean | 1631.3 (10) | 1599.6 (10) | 2.507 (9) | 0.093 (10) |
| deepinfra/bf16 | 2103.1 (10) | 1080.2 (10) | 4.241 (5) | 0.075 (10) |
| mara | 2976.7 (7) | 2367.2 (10) | 0.076 (6) | 0.124 (3) |
| siliconflow/fp8 | 3079.1 (10) | 2397.4 (10) | 0.113 (10) | 0.050 (8) |

#### deepseek/deepseek-v4-flash-0731

##### Benchmark one

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| coreweave/fp8 | 408.2 (10) | 369.6 (10) | 0.549 (10) | 0.625 (10) |
| deepinfra/fp8 | 731.8 (10) | 528.7 (10) | 0.953 (9) | 0.325 (10) |
| io-net/fp8 | 735.2 (10) | 758.0 (10) | 0.620 (10) | 0.041 (10) |
| makora | 836.5 (10) | 449.0 (10) | 1.788 (10) | 1.014 (10) |
| together | 919.1 (10) | 1498.2 (10) | 1.562 (9) | 0.565 (10) |
| fireworks | 931.9 (10) | 954.7 (10) | 1.603 (7) | 0.658 (10) |
| venice | 960.7 (10) | 919.7 (10) | 0.977 (10) | 0.158 (10) |
| akashml/fp8 | 960.8 (10) | 6707.0 (10) | 0.480 (10) | 0.073 (10) |
| mancer/fp8 | 1200.4 (5) | 952.2 (5) | 0.316 (1) | 0.115 (2) |
| baseten/fp8 | 1259.9 (10) | 728.3 (10) | 1.146 (10) | 1.034 (10) |
| reka/fp4 | 1279.4 (10) | 1119.6 (10) | 1.511 (10) | 3.186 (8) |
| alibaba | 1399.4 (10) | 1131.8 (10) | 1.166 (10) | 0.213 (10) |
| relace/fp4 | 1464.2 (10) | 2530.2 (10) | 1.538 (1) | 0.580 (7) |
| atlas-cloud/fp4 | 1465.7 (10) | 1648.1 (10) | 0.424 (10) | 1.105 (10) |
| cloudflare | 1503.8 (10) | 2878.9 (1) | 0.873 (1) | - (0) |
| streamlake/fp8 | 1595.0 (10) | 1490.7 (10) | 1.875 (9) | 0.335 (10) |
| digitalocean | 1604.5 (10) | 3298.0 (10) | 3.022 (10) | 0.063 (10) |
| wafer/fast | 1719.0 (10) | 1699.9 (10) | 0.951 (10) | 3.440 (4) |
| baidu/fp8 | 1745.7 (1) | - (0) | - (0) | 1.015 (6) |
| parasail/fp8 | 1770.8 (10) | 1266.0 (10) | 0.921 (9) | 0.738 (6) |
| inceptron/fp4 | 1859.9 (10) | 1053.4 (10) | 2.112 (7) | 0.313 (10) |
| siliconflow/fp8 | 2042.8 (10) | 3191.2 (10) | 1.889 (10) | 0.255 (10) |
| novita/fp8 | 2047.5 (10) | 4134.2 (10) | 2.178 (7) | 0.758 (10) |
| open-inference/fp4 | 3012.0 (10) | 5198.6 (10) | 0.048 (10) | 0.017 (8) |
| gmicloud/fp8 | 3277.1 (10) | 1982.7 (10) | 1.258 (9) | 0.554 (10) |
| phala | 3292.6 (10) | 2162.2 (10) | 0.128 (10) | 0.494 (2) |
| morph/bf16 | 9378.9 (10) | 3658.9 (10) | 0.072 (9) | 0.033 (10) |
| ambient/fp4 | 9565.5 (10) | 10928.4 (10) | 0.083 (8) | 0.011 (10) |
| deepseek | - (0) | - (0) | - (0) | - (0) |

##### Benchmark two

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| wafer/fast | 743.5 (10) | 820.0 (10) | 0.861 (8) | 1.044 (4) |
| makora | 868.9 (10) | 464.6 (10) | 1.851 (8) | 0.311 (10) |
| deepinfra/fp8 | 895.1 (10) | 664.5 (10) | 2.238 (10) | 0.104 (10) |
| fireworks | 903.2 (10) | 991.7 (8) | - (0) | - (0) |
| alibaba | 1214.5 (10) | 1571.0 (10) | 1.728 (10) | 0.212 (10) |
| venice | 1328.0 (10) | 5977.6 (10) | 1.388 (9) | 0.086 (10) |
| atlas-cloud/fp4 | 1331.7 (10) | 1259.2 (10) | 0.959 (10) | 1.175 (10) |
| streamlake/fp8 | 1396.4 (10) | 1313.5 (10) | 1.355 (10) | 0.419 (4) |
| novita/fp8 | 1411.6 (10) | 1232.6 (10) | 1.413 (10) | 0.061 (8) |
| parasail/fp8 | 1414.6 (10) | 10529.7 (1) | 0.072 (1) | 0.110 (3) |
| mancer/fp8 | 1475.8 (10) | 881.9 (6) | 1.228 (8) | 0.163 (7) |
| relace/fp4 | 1597.0 (10) | 1156.0 (10) | 1.926 (10) | 0.201 (6) |
| phala | 1637.5 (10) | 2139.8 (10) | 0.967 (9) | 0.571 (6) |
| together | 1830.6 (10) | 935.2 (10) | 1.624 (10) | 0.552 (10) |
| akashml/fp8 | 1858.7 (10) | 4226.7 (10) | 0.472 (10) | 0.044 (10) |
| digitalocean | 1912.3 (10) | 1567.8 (10) | 0.478 (10) | 0.072 (9) |
| gmicloud/fp8 | 1944.6 (10) | 2361.6 (10) | 0.831 (9) | 0.683 (8) |
| siliconflow/fp8 | 2068.6 (10) | 2068.2 (10) | 1.072 (10) | 0.395 (9) |
| morph/bf16 | 2379.2 (10) | 3966.8 (10) | 0.530 (9) | 0.075 (10) |
| reka/fp4 | 2688.0 (10) | 3349.6 (10) | 1.071 (10) | 0.274 (6) |
| open-inference/fp4 | 3661.6 (10) | 4093.6 (10) | 0.028 (10) | 0.026 (10) |
| cloudflare | 4818.4 (10) | 1429.3 (10) | - (0) | 0.106 (10) |
| ambient/fp4 | 5108.0 (10) | 4029.4 (10) | 0.693 (10) | 0.009 (10) |
| inceptron/fp4 | 6209.5 (10) | 3702.2 (10) | 0.798 (4) | 0.022 (8) |
| baseten/fp8 | 6723.6 (10) | 2842.1 (2) | 0.577 (5) | 0.290 (6) |
| baidu/fp8 | 7718.1 (10) | 26739.0 (10) | 0.497 (10) | 2.389 (1) |
| coreweave/fp8 | 9113.1 (10) | 3658.8 (10) | 0.174 (9) | 0.013 (10) |
| deepseek | - (0) | - (0) | - (0) | - (0) |

#### google/gemini-3.7-flash

##### Benchmark one

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| google-ai-studio/flex | 1920.3 (10) | 1732.9 (10) | 3.791 (7) | 1.915 (4) |
| google-ai-studio/priority | 2133.8 (10) | 1072.3 (10) | 0.965 (7) | 5.880 (3) |
| google-vertex/global | 2200.3 (10) | 1656.4 (10) | 1.687 (10) | 0.851 (10) |
| google-vertex/global/priority | 2323.7 (10) | 1584.7 (10) | 2.899 (10) | 0.890 (10) |
| google-ai-studio | 2369.2 (10) | 1275.6 (10) | 1.600 (8) | 2.073 (7) |
| google-vertex/global/flex | 12230.5 (10) | 13157.1 (10) | 0.575 (10) | 0.672 (5) |

##### Benchmark two

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| google-vertex/global | 2178.6 (10) | 1257.9 (10) | 1.861 (10) | 0.629 (7) |
| google-ai-studio/priority | 2234.8 (10) | 1784.5 (10) | 0.685 (4) | 2.649 (6) |
| google-vertex/global/priority | 2573.4 (10) | 1602.6 (10) | 1.383 (9) | 1.177 (4) |
| google-ai-studio | 4087.1 (10) | 1552.2 (10) | 0.381 (5) | 1.655 (4) |
| google-ai-studio/flex | 7570.3 (10) | 2148.8 (10) | 1.082 (5) | 4.112 (2) |
| google-vertex/global/flex | 12782.2 (10) | 11912.2 (10) | 0.056 (9) | 0.085 (1) |

#### google/gemini-3.5-flash-lite

##### Benchmark one

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| google-ai-studio | 668.3 (10) | 469.6 (10) | 4.234 (10) | 10.462 (8) |
| google-ai-studio/flex | 700.1 (10) | 445.7 (10) | 2.230 (10) | 9.150 (2) |
| google-ai-studio/priority | 710.6 (10) | 486.8 (10) | 1.275 (10) | 24.311 (5) |
| google-vertex/global/priority | 849.6 (10) | 668.3 (10) | 1.572 (10) | 14.745 (6) |
| google-vertex/global | 854.3 (10) | 640.8 (10) | 2.293 (10) | 6.630 (7) |
| google-vertex/us | 962.7 (10) | 656.6 (10) | 1.540 (10) | 11.911 (5) |
| google-vertex/global/flex | 6866.8 (10) | 6758.1 (10) | 1.796 (10) | 9.792 (8) |

##### Benchmark two

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| google-ai-studio/priority | 711.3 (10) | 503.2 (10) | 1.291 (10) | 7.605 (8) |
| google-ai-studio/flex | 794.4 (10) | 533.1 (10) | 1.473 (10) | 7.561 (7) |
| google-ai-studio | 804.2 (10) | 483.9 (10) | 6.747 (10) | 5.990 (10) |
| google-vertex/global | 926.3 (10) | 670.8 (10) | 1.836 (10) | 4.388 (8) |
| google-vertex/global/priority | 946.1 (10) | 706.0 (10) | 1.938 (10) | 10.175 (10) |
| google-vertex/us | 1121.5 (10) | 710.8 (10) | 1.908 (10) | 6.979 (8) |
| google-vertex/global/flex | 6904.6 (10) | 6761.8 (10) | 1.928 (10) | 13.919 (8) |

#### openai/gpt-5.6-luna

##### Benchmark one

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| openai/priority | 935.4 (10) | 981.4 (10) | 1.634 (8) | 1.369 (10) |
| openai | 990.6 (10) | 1183.4 (10) | 2.174 (10) | 0.865 (10) |
| amazon-bedrock/us-east-1 | 1014.2 (10) | 586.7 (10) | 1.273 (10) | 2.035 (10) |
| openai/flex | 1386.5 (10) | 1328.8 (10) | 1.619 (9) | 1.158 (10) |
| azure/us | 1816.1 (10) | 1751.4 (10) | 2.907 (8) | 0.690 (9) |
| azure/eu | 1946.6 (10) | 1384.9 (10) | 4.760 (8) | 0.663 (9) |
| azure | 2259.0 (10) | 1866.2 (10) | 2.209 (8) | 0.523 (10) |

##### Benchmark two

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| amazon-bedrock/us-east-1 | 1014.8 (10) | 676.4 (10) | 2.491 (10) | 0.851 (10) |
| openai/priority | 1019.3 (10) | 1159.5 (10) | 2.191 (10) | 1.264 (10) |
| openai/flex | 1353.4 (10) | 1497.1 (10) | 2.848 (8) | 0.513 (10) |
| openai | 1445.8 (10) | 1254.0 (10) | 1.572 (4) | 0.723 (10) |
| azure/us | 1445.9 (10) | 1901.0 (10) | 2.482 (10) | 0.595 (10) |
| azure | 1473.4 (10) | 1839.2 (10) | 9.612 (7) | 0.811 (10) |
| azure/eu | 1891.6 (10) | 1751.2 (10) | 4.270 (9) | 0.722 (9) |

#### qwen/qwen3.8-27b

##### Benchmark one

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| io-net/fp8 | 648.3 (10) | 621.8 (10) | 0.365 (10) | 0.258 (10) |
| parasail/fp8 | 772.7 (10) | 709.8 (10) | 1.134 (8) | 0.123 (10) |
| coreweave/fp8 | 892.2 (10) | 631.1 (10) | 0.525 (10) | 0.120 (10) |
| akashml/bf16 | 1060.4 (10) | 884.6 (10) | 0.680 (10) | 0.141 (10) |
| cloudflare | 1227.1 (10) | 829.2 (10) | 0.282 (10) | 0.086 (10) |
| alibaba | 1463.1 (10) | 1394.4 (10) | 0.203 (10) | 0.200 (10) |
| venice/fp8 | 1545.7 (10) | 797.5 (1) | 0.532 (9) | 0.486 (5) |
| reka/fp8 | 1567.0 (10) | 1305.8 (10) | 0.670 (10) | 0.123 (10) |
| chutes/fp8 | 1941.1 (10) | 1697.7 (10) | 0.318 (10) | 0.082 (10) |
| phala | 17146.8 (10) | 121973.0 (10) | 0.007 (10) | 0.032 (4) |

##### Benchmark two

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| io-net/fp8 | 682.8 (10) | 3327.3 (10) | 0.423 (9) | 0.593 (8) |
| parasail/fp8 | 948.3 (10) | 733.7 (10) | 0.835 (10) | 0.152 (10) |
| akashml/bf16 | 1028.1 (10) | 1339.6 (10) | 0.773 (10) | 0.062 (10) |
| venice/fp8 | 1226.2 (10) | 825.7 (8) | 0.484 (10) | 0.111 (5) |
| cloudflare | 1231.2 (10) | 760.5 (10) | 0.378 (9) | 0.110 (10) |
| reka/fp8 | 1525.1 (10) | 1559.4 (10) | 0.643 (10) | 0.196 (10) |
| alibaba | 1671.4 (10) | 1436.6 (10) | 0.151 (10) | 0.172 (10) |
| chutes/fp8 | 2041.2 (10) | 1808.4 (10) | 0.466 (10) | 0.193 (10) |
| coreweave/fp8 | 3348.0 (10) | 3616.8 (10) | 0.423 (7) | 0.066 (10) |
| phala | 3568.0 (10) | 5583.7 (10) | 0.374 (7) | 0.103 (10) |

#### xiaomi/mimo-v2.5

##### Benchmark one

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| deepinfra/bf16 | 709.7 (10) | 774.2 (10) | 1.909 (10) | 0.487 (10) |
| parasail/fp8 | 877.3 (10) | 649.1 (10) | 2.611 (7) | 0.441 (7) |
| gmicloud/fp8 | 4252.8 (10) | 6396.7 (10) | 0.545 (8) | 0.240 (10) |
| novita/fp8 | 5873.5 (10) | 3111.2 (10) | 0.184 (7) | 0.200 (10) |
| xiaomi/fp8 | 6845.4 (10) | 12948.3 (10) | 0.049 (7) | 0.136 (8) |

##### Benchmark two

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| xiaomi/fp8 | 1360.6 (10) | 1156.2 (10) | 1.008 (7) | 0.245 (10) |
| deepinfra/bf16 | 1370.5 (10) | 904.4 (10) | 6.600 (9) | 0.128 (10) |
| parasail/fp8 | 1446.6 (10) | 1382.6 (10) | 0.769 (9) | 0.280 (7) |
| gmicloud/fp8 | 6467.2 (10) | 7019.0 (10) | 0.268 (8) | 0.240 (9) |
| novita/fp8 | 6586.5 (10) | 4727.4 (10) | 0.296 (8) | 0.233 (9) |

#### mistralai/mistral-nemo

##### Benchmark one

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| mistral/eu | 1086.5 (10) | 549.9 (10) | 1.890 (10) | 1.011 (10) |
| parasail/fp8 | 1167.3 (4) | 408.9 (10) | 3.357 (1) | 0.729 (1) |
| io-net/fp16 | 4733.6 (10) | 480.0 (10) | 2.761 (9) | 0.803 (2) |
| deepinfra/fp8 | 9554.3 (10) | 6034.3 (10) | - (0) | - (0) |
| novita/fp8 | 13146.9 (10) | 1154.5 (10) | 0.044 (8) | 0.156 (9) |

##### Benchmark two

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| io-net/fp16 | 482.5 (10) | 452.4 (10) | 2.446 (9) | 0.324 (10) |
| parasail/fp8 | 596.3 (5) | 648.8 (5) | 0.715 (1) | - (0) |
| mistral/eu | 1101.3 (10) | 507.5 (10) | 1.302 (10) | 1.328 (10) |
| deepinfra/fp8 | 7762.8 (10) | 8172.7 (10) | - (0) | - (0) |
| novita/fp8 | 26607.6 (7) | 7780.3 (4) | 0.145 (2) | 0.112 (4) |

#### moonshotai/kimi-k3

##### Benchmark one

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| fireworks/fast | 655.5 (10) | 934.7 (10) | 1.370 (10) | 0.668 (6) |
| fireworks/us | 1169.8 (10) | 907.4 (10) | 0.916 (10) | 0.321 (8) |
| baseten/fp8 | 1200.4 (8) | - (0) | 0.628 (6) | 0.343 (1) |
| fireworks | 1259.7 (10) | 1676.0 (10) | 1.145 (10) | 0.174 (10) |
| makora | 1315.0 (10) | 1185.9 (10) | 1.690 (10) | 0.823 (10) |
| digitalocean | 1389.3 (10) | 1242.8 (10) | 1.272 (10) | 0.145 (10) |
| modal/mxfp4 | 1932.1 (10) | 1119.5 (10) | 1.263 (10) | 0.764 (10) |
| alibaba | 1944.9 (10) | 3763.6 (10) | 0.359 (10) | 0.069 (10) |
| chutes/mxfp4 | 2573.9 (10) | 2774.1 (10) | 0.763 (10) | 0.135 (10) |
| together | 3503.1 (10) | 2320.2 (10) | 0.498 (8) | 0.360 (6) |
| deepinfra/bf16 | 4777.8 (10) | 921.7 (10) | 0.813 (10) | 0.058 (10) |
| phala | 5427.2 (10) | 33321.6 (10) | 0.158 (10) | 0.160 (6) |
| moonshotai/mxfp4 | 6321.9 (10) | 5414.8 (10) | 0.926 (8) | 0.183 (10) |
| sail-research/fp4 | 24778.1 (10) | 1093.3 (10) | 0.194 (9) | 0.110 (10) |
| morph/fast | - (0) | - (0) | - (0) | - (0) |
| morph/fp4 | - (0) | - (0) | - (0) | - (0) |

##### Benchmark two

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| fireworks/fast | 783.3 (10) | 867.5 (10) | 0.898 (10) | 0.612 (10) |
| baseten/fp8 | 907.3 (6) | 1026.9 (9) | 1.328 (3) | 0.322 (1) |
| modal/mxfp4 | 1004.2 (10) | 1063.2 (10) | 0.882 (10) | 1.161 (10) |
| digitalocean | 1397.9 (10) | 1483.7 (10) | 0.584 (10) | 0.128 (10) |
| together | 1434.8 (10) | 1785.0 (10) | 0.988 (10) | 0.371 (10) |
| deepinfra/bf16 | 2024.1 (10) | 1133.8 (10) | 0.506 (10) | 0.140 (10) |
| alibaba | 2277.8 (10) | 1342.0 (10) | 0.974 (10) | 0.215 (10) |
| sail-research/fp4 | 2362.1 (10) | 1513.6 (10) | 0.506 (10) | 0.080 (4) |
| chutes/mxfp4 | 2680.9 (10) | 2176.7 (10) | 0.917 (8) | 0.132 (10) |
| phala | 2826.6 (10) | 3188.3 (10) | 0.864 (8) | 0.177 (10) |
| fireworks | 3882.4 (10) | 1440.2 (10) | 0.153 (10) | 0.446 (9) |
| moonshotai/mxfp4 | 3979.4 (10) | 3849.5 (8) | 0.104 (10) | 0.045 (10) |
| parasail/fp4 | 10487.5 (10) | 962.3 (10) | 0.335 (10) | 0.183 (10) |
| fireworks/us | 12566.9 (10) | 1127.4 (8) | 0.425 (6) | 0.171 (8) |
| makora | - (0) | 2147.7 (5) | - (0) | - (0) |
| morph/fast | - (0) | - (0) | - (0) | - (0) |
| morph/fp4 | - (0) | - (0) | - (0) | - (0) |

#### anthropic/claude-sonnet-5

##### Benchmark one

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| anthropic | 1400.3 (10) | 1149.3 (10) | 0.902 (10) | 0.510 (10) |
| azure/us | 1424.1 (10) | 1273.9 (10) | 4.364 (10) | 0.571 (10) |
| google-vertex/global | 1575.2 (10) | 1210.4 (10) | 2.138 (10) | 0.555 (10) |
| google-vertex/europe | 1582.3 (10) | 1314.5 (10) | 1.392 (10) | 0.513 (10) |
| google-vertex/us | 1636.2 (10) | 1002.7 (10) | 2.186 (10) | 0.449 (10) |
| amazon-bedrock/us-east-1 | 2144.7 (10) | 1804.4 (10) | 1.664 (10) | 0.234 (10) |
| amazon-bedrock/global | 2360.2 (10) | 1855.6 (10) | 2.235 (10) | 0.239 (10) |
| azure/global | 2395.4 (10) | 2035.9 (10) | 1.128 (10) | 0.645 (10) |
| claude-on-aws | 2505.4 (10) | 2224.1 (10) | 2.005 (10) | 0.213 (10) |

##### Benchmark two

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| google-vertex/global | 1310.7 (10) | 1182.7 (10) | 2.160 (10) | 0.388 (10) |
| google-vertex/us | 1589.7 (10) | 1106.7 (10) | 2.531 (10) | 0.488 (10) |
| anthropic | 1650.5 (10) | 1331.1 (10) | 1.005 (10) | 0.395 (10) |
| google-vertex/europe | 1668.2 (10) | 1221.1 (10) | 1.166 (10) | 0.405 (10) |
| azure/us | 1702.9 (10) | 1195.4 (10) | 11.887 (10) | 0.587 (10) |
| amazon-bedrock/us-east-1 | 2109.2 (10) | 1814.1 (10) | 0.574 (10) | 0.215 (10) |
| amazon-bedrock/global | 2166.5 (10) | 1679.3 (10) | 0.957 (10) | 0.211 (10) |
| claude-on-aws | 2574.0 (10) | 2370.7 (10) | 1.929 (10) | 0.223 (10) |
| azure/global | 2629.1 (10) | 1972.0 (10) | 1.166 (10) | 0.506 (10) |

#### z-ai/glm-5.2

##### Benchmark two

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| together | 405.8 (10) | 361.4 (10) | 1.153 (9) | 0.437 (10) |
| coreweave/fp4 | 436.9 (3) | 698.3 (5) | 1.153 (1) | - (0) |
| friendli | 444.5 (10) | 335.4 (10) | 0.535 (10) | 0.765 (10) |
| makora/fp8 | 574.7 (10) | 448.4 (10) | 1.044 (9) | 0.500 (10) |
| makora/fp4 | 598.1 (10) | 391.9 (10) | 2.781 (8) | 0.749 (9) |
| fireworks/fast | 611.8 (10) | 859.8 (10) | 0.985 (8) | 0.948 (9) |
| alibaba/fast | 650.7 (10) | 644.5 (10) | 1.049 (10) | 0.284 (10) |
| io-net/fp4 | 735.6 (2) | 1380.5 (10) | 3.249 (2) | 0.382 (4) |
| inceptron/fp4 | 761.0 (10) | 779.6 (10) | 2.095 (10) | 0.147 (10) |
| fireworks | 835.8 (10) | 893.8 (10) | 0.553 (10) | 0.182 (10) |
| fireworks/fast-us | 871.6 (10) | 1156.9 (10) | 0.261 (10) | 0.484 (9) |
| alibaba/fp8 | 929.9 (10) | 968.1 (10) | 0.835 (10) | 0.134 (9) |
| cloudflare/fast | 992.0 (10) | 1461.4 (10) | 2.896 (3) | 1.137 (8) |
| mistral/zdr | 1035.5 (10) | 2351.6 (10) | 1.069 (8) | 0.261 (10) |
| parasail/fp4 | 1038.2 (10) | 365.1 (10) | 2.241 (10) | 0.445 (10) |
| atlas-cloud/fp8 | 1104.2 (10) | 1104.9 (10) | 0.985 (10) | 0.187 (10) |
| z-ai/fp8 | 1123.7 (10) | 1092.1 (10) | 0.716 (10) | 0.142 (8) |
| novita/fp8 | 1169.6 (10) | 4839.1 (10) | 0.443 (9) | 0.290 (5) |
| deepinfra/fp4 | 1169.7 (10) | 757.1 (10) | 0.745 (7) | 0.114 (9) |
| digitalocean | 1273.3 (10) | 857.9 (10) | 2.101 (10) | 0.063 (4) |
| reka/fp8 | 1353.6 (10) | 1075.2 (10) | 0.488 (10) | 0.101 (10) |
| venice/fp8 | 1390.1 (10) | 1486.0 (10) | 0.587 (10) | 0.132 (10) |
| baidu/fp8 | 1442.4 (10) | 1148.6 (10) | 1.477 (10) | 0.261 (10) |
| gmicloud/fp8 | 1651.7 (10) | 1477.3 (10) | 0.991 (5) | 0.179 (10) |
| sail-research/fp8 | 1806.3 (10) | 1551.9 (10) | 0.504 (10) | 0.064 (10) |
| crusoe/fp8 | 1838.3 (10) | 1500.8 (10) | 1.205 (10) | 0.152 (10) |
| siliconflow/fp8 | 1919.1 (10) | 4353.6 (10) | 1.163 (10) | 0.113 (7) |
| streamlake/fp8 | 1987.3 (10) | 1282.6 (10) | 0.646 (10) | 0.195 (9) |
| phala/fp8 | 2027.7 (10) | 1550.2 (10) | 1.188 (10) | 0.151 (10) |
| baseten/fast | 2075.0 (10) | 1316.4 (10) | 0.781 (9) | 0.607 (6) |
| cloudflare | 2264.5 (10) | 2572.3 (10) | 0.416 (10) | 0.255 (9) |
| baseten/fp8 | 2366.0 (10) | 855.6 (10) | 0.536 (10) | 0.121 (10) |
| mistral/eu | 2647.5 (10) | 3055.2 (10) | 2.496 (9) | 0.173 (10) |
| mistral | 4521.4 (10) | 2593.7 (10) | 0.276 (10) | 0.090 (9) |
| wafer | 5378.2 (10) | 3833.7 (10) | 0.224 (9) | 0.093 (10) |
| decart/fp4 | 5560.6 (10) | 1399.0 (10) | 0.247 (5) | 0.116 (10) |
| ambient/fp8 | 17707.6 (10) | 1043.7 (10) | 0.068 (10) | 0.031 (9) |
| morph/fp4 | 22713.4 (10) | 1858.8 (10) | 0.134 (10) | 0.011 (9) |

#### z-ai/glm-5.3-flash

##### Benchmark two

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| z-ai/fp8 | 1518.8 (10) | 1343.9 (10) | 0.436 (10) | 2.248 (10) |

##### Benchmark three

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| baseten/fp8 | 619.9 (1) | 401.2 (7) | 0.813 (3) | - (0) |
| makora | 853.5 (10) | 547.9 (10) | 2.548 (7) | 0.799 (10) |
| together | 1076.9 (10) | 476.1 (10) | 1.851 (10) | 0.389 (8) |
| io-net/fp8 | 1088.4 (10) | 1743.3 (10) | 0.784 (10) | 2.266 (4) |
| digitalocean | 1093.8 (10) | 1146.7 (10) | 1.718 (8) | 0.086 (10) |
| morph/fp8 | 1242.4 (10) | 903.2 (10) | 0.306 (10) | 0.319 (10) |
| parasail/fp8 | 1287.2 (10) | 891.4 (10) | 1.580 (10) | 0.167 (10) |
| wafer | 1663.1 (9) | 1291.6 (10) | 2.390 (6) | 0.675 (9) |
| z-ai/fp8 | 1827.5 (10) | 1250.9 (10) | 0.766 (10) | 0.395 (10) |
| novita/fp8 | 1858.6 (10) | 1356.4 (10) | 1.450 (10) | 0.498 (9) |
| cloudflare | 1880.6 (10) | 1890.7 (10) | 1.545 (5) | 0.661 (1) |
| reka/fp8 | 2499.7 (10) | 2391.0 (10) | 0.634 (8) | 0.269 (10) |
| gmicloud/fp8 | 2643.1 (10) | 1943.2 (10) | 1.089 (7) | 0.459 (6) |
| phala/fp8 | 4053.7 (10) | 1562.1 (10) | 1.140 (5) | 0.140 (5) |
| friendli | 4541.6 (10) | 5453.3 (10) | 0.531 (6) | 0.949 (6) |
| venice | 6839.4 (10) | 6739.5 (10) | 2.963 (3) | 0.087 (10) |
| modal/fp8 | 8080.1 (10) | 516.7 (10) | 1.809 (8) | 1.307 (8) |
| deepinfra/fp8 | - (0) | - (0) | - (0) | - (0) |

## App Layout

- Python app and benchmark code: `app/`
- HTML templates: `ui/templates/`
- Browser CSS/JS: `ui/static/`