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

Metrics below combine runs 1 and 2. Values are medians; time columns are milliseconds. Decode/s only includes samples where the model returned the full decode passage.

#### openai/gpt-oss-120b

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| cerebras/fp16 | 271.4 | 295.6 | 3.626 | 7.347 |
| groq | 366.4 | 295.5 | 1.297 | 3.976 |
| sambanova | 366.9 | 305.8 | 1.188 | 4.276 |
| amazon-bedrock | 426.6 | 354.8 | 2.243 | 3.036 |
| baseten/fp4 | 480.1 | 420.4 | 5.979 | 1.018 |
| parasail/fp4 | 487.9 | 419.9 | 2.004 | 0.281 |
| deepinfra/turbo | 508.3 | 588.4 | 1.768 | 0.731 |
| google-vertex/global | 700.4 | 48270.1 | 2.690 | 0.589 |
| together | 806.9 | 878.8 | 2.358 | 0.229 |
| amazon-bedrock/eu-west-1 | 825.6 | 458.6 | 1.353 | 0.776 |
| novita/fp4 | 956.9 | - | 3.446 | - |
| coreweave/fp4 | 1130.0 | 812.3 | 2.471 | 0.084 |
| digitalocean | 1191.0 | 977.3 | 2.595 | 0.107 |
| akashml/bf16 | 1371.7 | 1539.4 | 0.666 | 0.305 |
| mancer/fp8 | 1609.5 | 1186.0 | 0.561 | 0.078 |
| deepinfra/bf16 | 2249.9 | 1183.9 | 2.668 | 0.123 |
| siliconflow/fp8 | 6771.3 | 5961.3 | 0.277 | 0.076 |
| mara | 7386.9 | 11124.2 | 0.432 | 0.413 |
| phala | 7798.9 | - | - | - |
| nebius/fp4 | 12192.4 | 1380.8 | 0.727 | 0.400 |

#### deepseek/deepseek-v4-flash-0731

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| coreweave/fp8 | 408.2 | 369.6 | 0.523 | 0.625 |
| deepinfra/fp8 | 731.8 | 528.7 | 0.953 | 0.325 |
| io-net/fp8 | 735.2 | 758.0 | 0.620 | 0.041 |
| makora | 836.5 | 449.0 | 1.788 | 1.014 |
| together | 919.1 | 1498.2 | 1.562 | 0.668 |
| fireworks | 938.7 | 2200.9 | - | - |
| venice | 960.7 | 919.7 | 0.942 | 0.158 |
| akashml/fp8 | 960.8 | 6707.0 | 0.614 | 0.073 |
| atlas-cloud/fp4 | 1235.8 | 1648.1 | 0.731 | 1.141 |
| reka/fp4 | 1279.4 | 1119.6 | 1.511 | 2.891 |
| alibaba | 1399.4 | 1131.8 | 1.536 | 0.216 |
| relace/fp4 | 1464.2 | 2530.2 | - | 0.873 |
| cloudflare | 1503.8 | 2878.9 | 0.873 | - |
| digitalocean | 1556.7 | 3298.0 | 2.736 | 0.063 |
| streamlake/fp8 | 1595.0 | 1490.7 | 1.875 | 0.363 |
| wafer/fast | 1719.0 | 1699.9 | 2.328 | 11.042 |
| inceptron/fp4 | 1859.9 | 1053.4 | 0.409 | 0.307 |
| siliconflow/fp8 | 2042.8 | 3191.2 | 2.267 | 0.255 |
| novita/fp8 | 2047.5 | 4134.2 | 17.012 | 0.873 |
| baseten/fp8 | 2927.9 | 720.1 | 1.773 | - |
| open-inference/fp4 | 3012.0 | 5198.6 | 0.048 | 0.017 |
| gmicloud/fp8 | 3277.1 | 1982.7 | 0.969 | 0.654 |
| phala | 3292.6 | 2162.2 | 0.128 | 0.705 |
| morph/bf16 | 9378.9 | 3658.9 | 0.062 | 0.033 |
| ambient/fp4 | 9565.5 | 11622.5 | 0.007 | - |
| baidu/fp8 | - | - | - | 1.015 |
| deepseek | - | - | - | - |
| mancer/fp8 | - | 983.9 | 0.316 | - |
| parasail/fp8 | - | - | - | - |

#### google/gemini-3.7-flash

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| google-ai-studio/flex | 1920.3 | 1732.9 | 3.791 | 1.915 |
| google-ai-studio/priority | 2133.8 | 1072.3 | 3.932 | - |
| google-vertex/global | 2200.3 | 1685.0 | 1.716 | 1.019 |
| google-vertex/global/priority | 2323.7 | 1584.7 | 2.899 | 0.840 |
| google-ai-studio | 2369.2 | 1275.6 | 6.567 | 1.635 |
| google-vertex/global/flex | 12230.5 | 13157.1 | 0.314 | 0.794 |

#### google/gemini-3.5-flash-lite

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| google-ai-studio | 668.3 | 469.6 | 4.234 | - |
| google-ai-studio/flex | 700.1 | 445.7 | 2.230 | - |
| google-ai-studio/priority | 710.6 | 486.8 | 1.275 | 100.864 |
| google-vertex/global/priority | 849.6 | 668.3 | 1.572 | 12.907 |
| google-vertex/global | 854.3 | 640.8 | 2.293 | 4.267 |
| google-vertex/us | 962.7 | 656.6 | 1.540 | 28.050 |
| google-vertex/global/flex | 6866.8 | 6758.1 | 1.698 | 4.173 |

#### openai/gpt-5.6-luna

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| openai/priority | 935.4 | 981.4 | 1.457 | 1.369 |
| openai | 990.6 | 1183.4 | 2.174 | 0.865 |
| amazon-bedrock/us-east-1 | 1014.2 | 586.7 | 1.273 | 2.017 |
| openai/flex | 1386.5 | 1328.8 | 1.557 | 1.158 |
| azure/us | 1816.1 | 1751.4 | 2.716 | 0.690 |
| azure/eu | 1946.6 | 1384.9 | 4.760 | 0.663 |
| azure | 2259.0 | 1866.2 | 2.506 | 0.529 |

#### qwen/qwen3.8-27b

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| io-net/fp8 | 648.3 | 621.8 | 0.315 | 0.258 |
| parasail/fp8 | 772.7 | 709.8 | 0.905 | 0.123 |
| coreweave/fp8 | 892.2 | 631.1 | 0.548 | 0.120 |
| akashml/bf16 | 1060.4 | 884.6 | 0.680 | 0.141 |
| cloudflare | 1227.1 | 829.2 | 0.194 | 0.086 |
| alibaba | 1463.1 | 1394.4 | 0.203 | 0.161 |
| reka/fp8 | 1567.0 | 1305.8 | 0.693 | 0.118 |
| venice/fp8 | 1605.2 | - | - | 0.674 |
| chutes/fp8 | 1941.1 | 1697.7 | 0.318 | 0.082 |
| phala | 17146.8 | 121973.0 | 0.006 | 0.034 |

#### xiaomi/mimo-v2.5

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| deepinfra/bf16 | 709.7 | 774.2 | 1.909 | 0.487 |
| parasail/fp8 | 877.3 | 649.1 | 2.611 | 0.441 |
| gmicloud/fp8 | 4252.8 | 6535.9 | 0.578 | 0.255 |
| novita/fp8 | 5873.5 | 3111.2 | - | 0.200 |
| xiaomi/fp8 | 6845.4 | 12948.3 | 0.055 | 0.159 |

#### mistralai/mistral-nemo

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| mistral/eu | 1086.5 | 549.9 | 1.997 | 1.005 |
| io-net/fp16 | 4733.6 | - | 2.604 | - |
| deepinfra/fp8 | 9554.3 | 6034.3 | - | - |
| novita/fp8 | 13146.9 | 1154.5 | 0.181 | 0.156 |
| parasail/fp8 | - | 408.9 | - | - |

#### moonshotai/kimi-k3

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| fireworks/us | 1176.0 | - | - | - |
| baseten/fp8 | 1176.5 | - | - | - |
| fireworks | 1285.3 | 1526.3 | 1.161 | 0.186 |
| makora | 1315.0 | 1185.9 | 1.690 | 0.823 |
| digitalocean | 1389.3 | 1242.8 | 0.885 | 0.145 |
| modal/mxfp4 | 1932.1 | 1119.5 | 1.263 | 0.764 |
| alibaba | 1944.9 | 3763.6 | 0.359 | 0.069 |
| chutes/mxfp4 | 2573.9 | 2774.1 | 0.609 | 0.132 |
| together | 3503.1 | - | 0.254 | 0.496 |
| deepinfra/bf16 | 4777.8 | 1042.4 | 0.817 | 0.058 |
| phala | 5427.2 | 33321.6 | 0.375 | 0.167 |
| moonshotai/mxfp4 | 6092.7 | 5582.5 | 0.879 | 0.156 |
| sail-research/fp4 | 24778.1 | 1093.3 | 0.050 | 0.093 |
| fireworks/fast | - | - | - | - |
| morph/fast | - | - | - | - |
| morph/fp4 | - | - | - | - |

#### anthropic/claude-sonnet-5

| endpoint | time before prefill | time before prefill (prompt cached) | standard prefill/s | standard decode/s |
| - | -: | -: | -: | -: |
| anthropic | 1400.3 | 1149.3 | 0.902 | 0.510 |
| azure/us | 1424.1 | 1273.9 | 5.452 | 0.571 |
| google-vertex/global | 1575.2 | 1210.4 | 2.163 | 0.555 |
| google-vertex/europe | 1582.3 | 1314.5 | 1.594 | 0.513 |
| google-vertex/us | 1636.2 | 1002.7 | 2.186 | 0.449 |
| amazon-bedrock/us-east-1 | 2144.7 | 1804.4 | 1.754 | 0.234 |
| amazon-bedrock/global | 2360.2 | 1855.6 | 2.387 | 0.239 |
| azure/global | 2395.4 | 2035.9 | 1.128 | 0.645 |
| claude-on-aws | 2505.4 | 2224.1 | 2.089 | 0.213 |


## App Layout

- Python app and benchmark code: `app/`
- HTML templates: `ui/templates/`
- Browser CSS/JS: `ui/static/`