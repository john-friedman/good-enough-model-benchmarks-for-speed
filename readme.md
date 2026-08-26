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

Metrics below combine runs 1 and 2. Values are medians; time columns are milliseconds. Each metric cell includes its sample count in parentheses. Decode/s only includes samples where the model returned the full decode passage.

#### openai/gpt-oss-120b

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

#### deepseek/deepseek-v4-flash-0731

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

#### google/gemini-3.7-flash

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| google-ai-studio/flex | 1920.3 (10) | 1732.9 (10) | 3.791 (7) | 1.915 (4) |
| google-ai-studio/priority | 2133.8 (10) | 1072.3 (10) | 0.965 (7) | 5.880 (3) |
| google-vertex/global | 2200.3 (10) | 1656.4 (10) | 1.687 (10) | 0.851 (10) |
| google-vertex/global/priority | 2323.7 (10) | 1584.7 (10) | 2.899 (10) | 0.890 (10) |
| google-ai-studio | 2369.2 (10) | 1275.6 (10) | 1.600 (8) | 2.073 (7) |
| google-vertex/global/flex | 12230.5 (10) | 13157.1 (10) | 0.575 (10) | 0.672 (5) |

#### google/gemini-3.5-flash-lite

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| google-ai-studio | 668.3 (10) | 469.6 (10) | 4.234 (10) | 10.462 (8) |
| google-ai-studio/flex | 700.1 (10) | 445.7 (10) | 2.230 (10) | 9.150 (2) |
| google-ai-studio/priority | 710.6 (10) | 486.8 (10) | 1.275 (10) | 24.311 (5) |
| google-vertex/global/priority | 849.6 (10) | 668.3 (10) | 1.572 (10) | 14.745 (6) |
| google-vertex/global | 854.3 (10) | 640.8 (10) | 2.293 (10) | 6.630 (7) |
| google-vertex/us | 962.7 (10) | 656.6 (10) | 1.540 (10) | 11.911 (5) |
| google-vertex/global/flex | 6866.8 (10) | 6758.1 (10) | 1.796 (10) | 9.792 (8) |

#### openai/gpt-5.6-luna

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| openai/priority | 935.4 (10) | 981.4 (10) | 1.634 (8) | 1.369 (10) |
| openai | 990.6 (10) | 1183.4 (10) | 2.174 (10) | 0.865 (10) |
| amazon-bedrock/us-east-1 | 1014.2 (10) | 586.7 (10) | 1.273 (10) | 2.035 (10) |
| openai/flex | 1386.5 (10) | 1328.8 (10) | 1.619 (9) | 1.158 (10) |
| azure/us | 1816.1 (10) | 1751.4 (10) | 2.907 (8) | 0.690 (9) |
| azure/eu | 1946.6 (10) | 1384.9 (10) | 4.760 (8) | 0.663 (9) |
| azure | 2259.0 (10) | 1866.2 (10) | 2.209 (8) | 0.523 (10) |

#### qwen/qwen3.8-27b

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

#### xiaomi/mimo-v2.5

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| deepinfra/bf16 | 709.7 (10) | 774.2 (10) | 1.909 (10) | 0.487 (10) |
| parasail/fp8 | 877.3 (10) | 649.1 (10) | 2.611 (7) | 0.441 (7) |
| gmicloud/fp8 | 4252.8 (10) | 6396.7 (10) | 0.545 (8) | 0.240 (10) |
| novita/fp8 | 5873.5 (10) | 3111.2 (10) | 0.184 (7) | 0.200 (10) |
| xiaomi/fp8 | 6845.4 (10) | 12948.3 (10) | 0.049 (7) | 0.136 (8) |

#### mistralai/mistral-nemo

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| mistral/eu | 1086.5 (10) | 549.9 (10) | 1.890 (10) | 1.011 (10) |
| parasail/fp8 | 1167.3 (4) | 408.9 (10) | 3.357 (1) | 0.729 (1) |
| io-net/fp16 | 4733.6 (10) | 480.0 (10) | 2.761 (9) | 0.803 (2) |
| deepinfra/fp8 | 9554.3 (10) | 6034.3 (10) | - (0) | - (0) |
| novita/fp8 | 13146.9 (10) | 1154.5 (10) | 0.044 (8) | 0.156 (9) |

#### moonshotai/kimi-k3

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

#### anthropic/claude-sonnet-5

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

## App Layout

- Python app and benchmark code: `app/`
- HTML templates: `ui/templates/`
- Browser CSS/JS: `ui/static/`