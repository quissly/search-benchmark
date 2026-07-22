# Pooled-IDCG nDCG — corrected computation

## Sanity checks

1. **Returned hits ⊆ judged pool:** PASS — no exceptions
   - duplicate ids within one engine's hit list: 3 [('pharmacy', 'q_1149', 'quissly', ['omezdsrcapsule15s']), ('pharmacy', 'q_1250', 'quissly', ['collashotc2capsule10s']), ('pharmacy', 'q_1192', 'doofinder', ['collashotc2capsule10s'])]
   - same product judged with different gains on one query: 0 
2. **No nDCG > 1.0 anywhere:** PASS — max per-query pooled nDCG is 1.000000

3. **Worked examples** (eyeball the math):

### mixed-gain pool: auto / q_1505 — “aftermarket exhaust manifold to complement a stage 1 ECU tune”

- pool (44 products, id:gain, desc): b0714nnm6l:1.0, b003hii32e:1.0, b0878wvn3t:1.0, b087d275gv:1.0, b07jwblt7v:1.0, b000fq7tje:0.1, b07x8wx8v1:0.01, b0083h5nq8:0.01, b009x1qtei:0.01, b000c2ecl4:0.01, b0bqxgv6fq:0.01, b000bw8w02:0.01 …
- pool gains@10 desc: [1.0, 1.0, 1.0, 1.0, 1.0, 0.1, 0.01, 0.01, 0.01, 0.01]
- IDCG@10 = 2.996469, IDCG@20 = 3.016845
  - quissly: top-10 gains [1.0, 0.0, 1.0, 0.01, 0.0, 0.0, 0.0, 0.0, 1.0, 0.1] → DCG@10 = 1.834243, pooled nDCG@10 = 0.612135 (shipped self-norm: 0.842220)
  - doofinder: top-10 gains [1.0, 0.0, 1.0, 0.0, 0.01, 1.0, 0.01, 0.0, 1.0, 0.01] → DCG@10 = 2.167330, pooled nDCG@10 = 0.723295 (shipped self-norm: 0.842542)
  - luigisbox: top-10 gains [] → DCG@10 = 0.000000, pooled nDCG@10 = 0.000000 (shipped self-norm: 0.000000)
  - clerk: top-10 gains [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.01, 0.01] → DCG@10 = 0.005901, pooled nDCG@10 = 0.001969 (shipped self-norm: 0.361815)
  - algolia: top-10 gains [] → DCG@10 = 0.000000, pooled nDCG@10 = 0.000000 (shipped self-norm: 0.000000)

### substitute-only pool (recall excludes, pooled nDCG includes): auto / q_1475 — “DOT 5 silicone fluid”

- pool (28 products, id:gain, desc): b000wkniuw:0.1, b08lbh6297:0.1, b07dlyb4rl:0.1, b07v5k5f1l:0.1, b06wvwscfk:0.1, b00ew3grcq:0.01, b081gvkxln:0.01, b00cq7yofc:0.0, b009pydyku:0.0, b0bw4hddtp:0.0, b000k7yrfc:0.0, b082m3hzx6:0.0 …
- pool gains@10 desc: [0.1, 0.1, 0.1, 0.1, 0.1, 0.01, 0.01, 0.0, 0.0, 0.0]
- IDCG@10 = 0.301741, IDCG@20 = 0.301741
  - quissly: top-10 gains [0.0, 0.1, 0.1, 0.01, 0.0, 0.1, 0.0, 0.0, 0.0, 0.0] → DCG@10 = 0.153020, pooled nDCG@10 = 0.507125 (shipped self-norm: 0.703867)
  - doofinder: top-10 gains [0.0] → DCG@10 = 0.000000, pooled nDCG@10 = 0.000000 (shipped self-norm: 0.000000)
  - luigisbox: top-10 gains [0.0, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0] → DCG@10 = 0.063093, pooled nDCG@10 = 0.209096 (shipped self-norm: 0.630930)
  - clerk: top-10 gains [0.0, 0.01, 0.0, 0.0, 0.0] → DCG@10 = 0.006309, pooled nDCG@10 = 0.020910 (shipped self-norm: 0.630930)
  - algolia: top-10 gains [0.0] → DCG@10 = 0.000000, pooled nDCG@10 = 0.000000 (shipped self-norm: 0.000000)

### all-zero pool (excluded: IDCG=0): cosmetics / q_0912 — “dental floss”

- pool (22 products, id:gain, desc): b07gd5qtxg:0.0, b093t3kn3q:0.0, b093plkltx:0.0, b00a81xvx4:0.0, b01lytldei:0.0, b00ha0aana:0.0, b01148s5gm:0.0, b00mw8e1mq:0.0, b0c675n5v2:0.0, b00o1fx6uq:0.0, b09fxjsgxy:0.0, b01lwxjanq:0.0 …
- pool gains@10 desc: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
- IDCG@10 = 0.000000, IDCG@20 = 0.000000
- **excluded** (pooled IDCG = 0; nothing judged better than Irrelevant anywhere)
  - quissly: top-10 gains [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] → DCG@10 = 0.000000, pooled nDCG@10 = excluded (shipped self-norm: 0.000000)
  - doofinder: top-10 gains [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] → DCG@10 = 0.000000, pooled nDCG@10 = excluded (shipped self-norm: 0.000000)
  - luigisbox: top-10 gains [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] → DCG@10 = 0.000000, pooled nDCG@10 = excluded (shipped self-norm: 0.000000)
  - clerk: top-10 gains [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] → DCG@10 = 0.000000, pooled nDCG@10 = excluded (shipped self-norm: 0.000000)
  - algolia: top-10 gains [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] → DCG@10 = 0.000000, pooled nDCG@10 = excluded (shipped self-norm: 0.000000)

## Excluded queries (pooled IDCG@k = 0 — identical set for @10 and @20)

- overall: **47** of 1259 excluded → nDCG population n = 1212
- recall's Exact-only pool excludes 200; pooled IDCG (any gain > 0) excludes 47. The **153** queries in between have no Exact anywhere but at least one Substitute/Complementary — they enter corrected nDCG but not recall. (Pooled exclusion is a strict subset of recall's: verified.)

| slice | queries | excluded | included n |
|---|---:|---:|---:|
| auto | 180 | 0 | 180 |
| cosmetics | 180 | 3 | 177 |
| electronics | 180 | 2 | 178 |
| fast_fashion | 180 | 6 | 174 |
| furniture | 179 | 2 | 177 |
| marketplace | 180 | 26 | 154 |
| pharmacy | 180 | 8 | 172 |
| tier: simple | 475 | 9 | 466 |
| tier: medium | 469 | 21 | 448 |
| tier: complex | 315 | 17 | 298 |
| **all** | **1259** | **47** | **1212** |

## Corrected (pooled-IDCG) vs shipped (self-normalized) nDCG

Deltas ≥ 10pp in **bold**; negative delta = corrected number is lower than shipped.

### overall

| engine | k | shipped | corrected | delta | n (shipped → corrected) |
|---|---:|---:|---:|---:|---:|
| quissly | 10 | 82.91 | 73.78 | -9.12 | 1259 → 1212 |
| quissly | 20 | 82.08 | 77.28 | -4.81 | 1259 → 1212 |
| doofinder | 10 | 73.28 | 54.24 | **-19.04** | 1259 → 1212 |
| doofinder | 20 | 73.00 | 54.50 | **-18.50** | 1259 → 1212 |
| luigisbox | 10 | 67.35 | 50.81 | **-16.53** | 1259 → 1212 |
| luigisbox | 20 | 66.86 | 50.41 | **-16.45** | 1259 → 1212 |
| clerk | 10 | 67.35 | 49.24 | **-18.11** | 1259 → 1212 |
| clerk | 20 | 67.14 | 49.21 | **-17.93** | 1259 → 1212 |
| algolia | 10 | 54.80 | 44.06 | **-10.75** | 1259 → 1212 |
| algolia | 20 | 54.44 | 43.77 | **-10.68** | 1259 → 1212 |

### sector:auto

| engine | k | shipped | corrected | delta | n (shipped → corrected) |
|---|---:|---:|---:|---:|---:|
| quissly | 10 | 93.45 | 80.06 | **-13.38** | 180 → 180 |
| quissly | 20 | 91.60 | 82.74 | -8.86 | 180 → 180 |
| doofinder | 10 | 81.88 | 59.54 | **-22.33** | 180 → 180 |
| doofinder | 20 | 81.50 | 60.91 | **-20.58** | 180 → 180 |
| luigisbox | 10 | 78.64 | 57.30 | **-21.33** | 180 → 180 |
| luigisbox | 20 | 78.34 | 56.75 | **-21.60** | 180 → 180 |
| clerk | 10 | 77.98 | 58.11 | **-19.88** | 180 → 180 |
| clerk | 20 | 77.57 | 59.08 | **-18.49** | 180 → 180 |
| algolia | 10 | 64.85 | 51.06 | **-13.79** | 180 → 180 |
| algolia | 20 | 64.78 | 51.36 | **-13.42** | 180 → 180 |

### sector:cosmetics

| engine | k | shipped | corrected | delta | n (shipped → corrected) |
|---|---:|---:|---:|---:|---:|
| quissly | 10 | 90.57 | 79.07 | **-11.50** | 180 → 177 |
| quissly | 20 | 89.39 | 81.38 | -8.01 | 180 → 177 |
| doofinder | 10 | 86.58 | 66.24 | **-20.33** | 180 → 177 |
| doofinder | 20 | 85.27 | 64.74 | **-20.52** | 180 → 177 |
| luigisbox | 10 | 79.82 | 62.74 | **-17.08** | 180 → 177 |
| luigisbox | 20 | 79.08 | 61.75 | **-17.32** | 180 → 177 |
| clerk | 10 | 81.46 | 58.26 | **-23.20** | 180 → 177 |
| clerk | 20 | 80.31 | 57.54 | **-22.77** | 180 → 177 |
| algolia | 10 | 62.45 | 53.12 | -9.33 | 180 → 177 |
| algolia | 20 | 62.35 | 51.96 | **-10.39** | 180 → 177 |

### sector:electronics

| engine | k | shipped | corrected | delta | n (shipped → corrected) |
|---|---:|---:|---:|---:|---:|
| quissly | 10 | 87.56 | 76.00 | **-11.56** | 180 → 178 |
| quissly | 20 | 86.15 | 79.49 | -6.66 | 180 → 178 |
| doofinder | 10 | 77.65 | 51.37 | **-26.27** | 180 → 178 |
| doofinder | 20 | 77.51 | 52.37 | **-25.14** | 180 → 178 |
| luigisbox | 10 | 70.97 | 50.11 | **-20.86** | 180 → 178 |
| luigisbox | 20 | 69.46 | 50.23 | **-19.23** | 180 → 178 |
| clerk | 10 | 72.42 | 49.17 | **-23.25** | 180 → 178 |
| clerk | 20 | 71.62 | 49.24 | **-22.38** | 180 → 178 |
| algolia | 10 | 63.80 | 46.45 | **-17.35** | 180 → 178 |
| algolia | 20 | 62.46 | 46.00 | **-16.46** | 180 → 178 |

### sector:fast_fashion

| engine | k | shipped | corrected | delta | n (shipped → corrected) |
|---|---:|---:|---:|---:|---:|
| quissly | 10 | 80.31 | 69.35 | **-10.96** | 180 → 174 |
| quissly | 20 | 80.11 | 74.17 | -5.93 | 180 → 174 |
| doofinder | 10 | 69.57 | 49.20 | **-20.37** | 180 → 174 |
| doofinder | 20 | 69.74 | 49.56 | **-20.18** | 180 → 174 |
| luigisbox | 10 | 55.43 | 44.40 | **-11.03** | 180 → 174 |
| luigisbox | 20 | 55.52 | 43.44 | **-12.09** | 180 → 174 |
| clerk | 10 | 62.03 | 43.66 | **-18.37** | 180 → 174 |
| clerk | 20 | 63.04 | 43.00 | **-20.04** | 180 → 174 |
| algolia | 10 | 47.31 | 39.87 | -7.44 | 180 → 174 |
| algolia | 20 | 47.85 | 39.02 | -8.83 | 180 → 174 |

### sector:furniture

| engine | k | shipped | corrected | delta | n (shipped → corrected) |
|---|---:|---:|---:|---:|---:|
| quissly | 10 | 88.75 | 76.86 | **-11.89** | 179 → 177 |
| quissly | 20 | 87.04 | 81.20 | -5.84 | 179 → 177 |
| doofinder | 10 | 82.11 | 57.93 | **-24.19** | 179 → 177 |
| doofinder | 20 | 80.66 | 58.22 | **-22.45** | 179 → 177 |
| luigisbox | 10 | 77.90 | 55.47 | **-22.43** | 179 → 177 |
| luigisbox | 20 | 77.47 | 55.26 | **-22.21** | 179 → 177 |
| clerk | 10 | 75.80 | 52.73 | **-23.07** | 179 → 177 |
| clerk | 20 | 75.00 | 52.95 | **-22.05** | 179 → 177 |
| algolia | 10 | 62.42 | 47.06 | **-15.36** | 179 → 177 |
| algolia | 20 | 62.00 | 47.43 | **-14.57** | 179 → 177 |

### sector:marketplace

| engine | k | shipped | corrected | delta | n (shipped → corrected) |
|---|---:|---:|---:|---:|---:|
| quissly | 10 | 66.06 | 67.13 | +1.08 | 180 → 154 |
| quissly | 20 | 65.61 | 70.04 | +4.43 | 180 → 154 |
| doofinder | 10 | 59.58 | 55.88 | -3.70 | 180 → 154 |
| doofinder | 20 | 60.28 | 56.70 | -3.58 | 180 → 154 |
| luigisbox | 10 | 45.51 | 41.70 | -3.81 | 180 → 154 |
| luigisbox | 20 | 44.89 | 41.88 | -3.01 | 180 → 154 |
| clerk | 10 | 42.85 | 37.90 | -4.94 | 180 → 154 |
| clerk | 20 | 43.09 | 39.10 | -4.00 | 180 → 154 |
| algolia | 10 | 34.68 | 32.16 | -2.52 | 180 → 154 |
| algolia | 20 | 34.65 | 33.42 | -1.23 | 180 → 154 |

### sector:pharmacy

| engine | k | shipped | corrected | delta | n (shipped → corrected) |
|---|---:|---:|---:|---:|---:|
| quissly | 10 | 73.68 | 66.75 | -6.93 | 180 → 172 |
| quissly | 20 | 74.72 | 70.62 | -4.09 | 180 → 172 |
| doofinder | 10 | 55.61 | 39.12 | **-16.48** | 180 → 172 |
| doofinder | 20 | 56.11 | 38.68 | **-17.43** | 180 → 172 |
| luigisbox | 10 | 63.23 | 42.34 | **-20.89** | 180 → 172 |
| luigisbox | 20 | 63.30 | 41.97 | **-21.33** | 180 → 172 |
| clerk | 10 | 58.94 | 42.92 | **-16.02** | 180 → 172 |
| clerk | 20 | 59.40 | 41.78 | **-17.62** | 180 → 172 |
| algolia | 10 | 48.18 | 36.74 | **-11.44** | 180 → 172 |
| algolia | 20 | 47.06 | 35.37 | **-11.70** | 180 → 172 |

### complexity:simple

| engine | k | shipped | corrected | delta | n (shipped → corrected) |
|---|---:|---:|---:|---:|---:|
| quissly | 10 | 94.48 | 91.02 | -3.46 | 475 → 466 |
| quissly | 20 | 94.23 | 91.64 | -2.59 | 475 → 466 |
| doofinder | 10 | 84.79 | 72.39 | **-12.40** | 475 → 466 |
| doofinder | 20 | 84.74 | 72.25 | **-12.49** | 475 → 466 |
| luigisbox | 10 | 84.34 | 70.64 | **-13.69** | 475 → 466 |
| luigisbox | 20 | 83.66 | 70.57 | **-13.09** | 475 → 466 |
| clerk | 10 | 81.62 | 66.57 | **-15.05** | 475 → 466 |
| clerk | 20 | 81.35 | 66.95 | **-14.40** | 475 → 466 |
| algolia | 10 | 82.22 | 67.54 | **-14.68** | 475 → 466 |
| algolia | 20 | 81.76 | 68.42 | **-13.34** | 475 → 466 |

### complexity:medium

| engine | k | shipped | corrected | delta | n (shipped → corrected) |
|---|---:|---:|---:|---:|---:|
| quissly | 10 | 78.61 | 65.93 | **-12.69** | 469 → 448 |
| quissly | 20 | 77.19 | 70.75 | -6.44 | 469 → 448 |
| doofinder | 10 | 75.34 | 55.78 | **-19.56** | 469 → 448 |
| doofinder | 20 | 75.04 | 56.00 | **-19.04** | 469 → 448 |
| luigisbox | 10 | 73.67 | 55.90 | **-17.77** | 469 → 448 |
| luigisbox | 20 | 73.19 | 55.43 | **-17.76** | 469 → 448 |
| clerk | 10 | 69.06 | 51.01 | **-18.05** | 469 → 448 |
| clerk | 20 | 68.65 | 50.34 | **-18.31** | 469 → 448 |
| algolia | 10 | 61.54 | 48.17 | **-13.37** | 469 → 448 |
| algolia | 20 | 61.04 | 46.57 | **-14.48** | 469 → 448 |

### complexity:complex

| engine | k | shipped | corrected | delta | n (shipped → corrected) |
|---|---:|---:|---:|---:|---:|
| quissly | 10 | 71.85 | 58.65 | **-13.20** | 315 → 298 |
| quissly | 20 | 71.06 | 64.62 | -6.44 | 315 → 298 |
| doofinder | 10 | 52.84 | 23.53 | **-29.30** | 315 → 298 |
| doofinder | 20 | 52.27 | 24.51 | **-27.77** | 315 → 298 |
| luigisbox | 10 | 32.31 | 12.17 | **-20.15** | 315 → 298 |
| luigisbox | 20 | 32.10 | 11.33 | **-20.77** | 315 → 298 |
| clerk | 10 | 43.28 | 19.46 | **-23.82** | 315 → 298 |
| clerk | 20 | 43.47 | 19.78 | **-23.69** | 315 → 298 |
| algolia | 10 | 3.44 | 1.16 | -2.28 | 315 → 298 |
| algolia | 20 | 3.43 | 1.00 | -2.42 | 315 → 298 |

## Engine-ordering changes (corrected vs shipped)

**overall, nDCG@10:**
- shipped:   quissly > doofinder > clerk > luigisbox > algolia
- corrected: quissly > doofinder > luigisbox > clerk > algolia
  - quissly: shipped 82.91 → corrected 73.78
  - doofinder: shipped 73.28 → corrected 54.24
  - luigisbox: shipped 67.35 → corrected 50.81
  - clerk: shipped 67.35 → corrected 49.24
  - algolia: shipped 54.80 → corrected 44.06

**overall, nDCG@20:**
- shipped:   quissly > doofinder > clerk > luigisbox > algolia
- corrected: quissly > doofinder > luigisbox > clerk > algolia
  - quissly: shipped 82.08 → corrected 77.28
  - doofinder: shipped 73.00 → corrected 54.50
  - luigisbox: shipped 66.86 → corrected 50.41
  - clerk: shipped 67.14 → corrected 49.21
  - algolia: shipped 54.44 → corrected 43.77

**sector:auto, nDCG@10:**
- shipped:   quissly > doofinder > luigisbox > clerk > algolia
- corrected: quissly > doofinder > clerk > luigisbox > algolia
  - quissly: shipped 93.45 → corrected 80.06
  - doofinder: shipped 81.88 → corrected 59.54
  - luigisbox: shipped 78.64 → corrected 57.30
  - clerk: shipped 77.98 → corrected 58.11
  - algolia: shipped 64.85 → corrected 51.06

**sector:auto, nDCG@20:**
- shipped:   quissly > doofinder > luigisbox > clerk > algolia
- corrected: quissly > doofinder > clerk > luigisbox > algolia
  - quissly: shipped 91.60 → corrected 82.74
  - doofinder: shipped 81.50 → corrected 60.91
  - luigisbox: shipped 78.34 → corrected 56.75
  - clerk: shipped 77.57 → corrected 59.08
  - algolia: shipped 64.78 → corrected 51.36

**sector:cosmetics, nDCG@10:**
- shipped:   quissly > doofinder > clerk > luigisbox > algolia
- corrected: quissly > doofinder > luigisbox > clerk > algolia
  - quissly: shipped 90.57 → corrected 79.07
  - doofinder: shipped 86.58 → corrected 66.24
  - luigisbox: shipped 79.82 → corrected 62.74
  - clerk: shipped 81.46 → corrected 58.26
  - algolia: shipped 62.45 → corrected 53.12

**sector:cosmetics, nDCG@20:**
- shipped:   quissly > doofinder > clerk > luigisbox > algolia
- corrected: quissly > doofinder > luigisbox > clerk > algolia
  - quissly: shipped 89.39 → corrected 81.38
  - doofinder: shipped 85.27 → corrected 64.74
  - luigisbox: shipped 79.08 → corrected 61.75
  - clerk: shipped 80.31 → corrected 57.54
  - algolia: shipped 62.35 → corrected 51.96

**sector:electronics, nDCG@10:**
- shipped:   quissly > doofinder > clerk > luigisbox > algolia
- corrected: quissly > doofinder > luigisbox > clerk > algolia
  - quissly: shipped 87.56 → corrected 76.00
  - doofinder: shipped 77.65 → corrected 51.37
  - luigisbox: shipped 70.97 → corrected 50.11
  - clerk: shipped 72.42 → corrected 49.17
  - algolia: shipped 63.80 → corrected 46.45

**sector:electronics, nDCG@20:**
- shipped:   quissly > doofinder > clerk > luigisbox > algolia
- corrected: quissly > doofinder > luigisbox > clerk > algolia
  - quissly: shipped 86.15 → corrected 79.49
  - doofinder: shipped 77.51 → corrected 52.37
  - luigisbox: shipped 69.46 → corrected 50.23
  - clerk: shipped 71.62 → corrected 49.24
  - algolia: shipped 62.46 → corrected 46.00

**sector:fast_fashion, nDCG@10:**
- shipped:   quissly > doofinder > clerk > luigisbox > algolia
- corrected: quissly > doofinder > luigisbox > clerk > algolia
  - quissly: shipped 80.31 → corrected 69.35
  - doofinder: shipped 69.57 → corrected 49.20
  - luigisbox: shipped 55.43 → corrected 44.40
  - clerk: shipped 62.03 → corrected 43.66
  - algolia: shipped 47.31 → corrected 39.87

**sector:fast_fashion, nDCG@20:**
- shipped:   quissly > doofinder > clerk > luigisbox > algolia
- corrected: quissly > doofinder > luigisbox > clerk > algolia
  - quissly: shipped 80.11 → corrected 74.17
  - doofinder: shipped 69.74 → corrected 49.56
  - luigisbox: shipped 55.52 → corrected 43.44
  - clerk: shipped 63.04 → corrected 43.00
  - algolia: shipped 47.85 → corrected 39.02

**sector:pharmacy, nDCG@10:**
- shipped:   quissly > luigisbox > clerk > doofinder > algolia
- corrected: quissly > clerk > luigisbox > doofinder > algolia
  - quissly: shipped 73.68 → corrected 66.75
  - doofinder: shipped 55.61 → corrected 39.12
  - luigisbox: shipped 63.23 → corrected 42.34
  - clerk: shipped 58.94 → corrected 42.92
  - algolia: shipped 48.18 → corrected 36.74

**complexity:medium, nDCG@10:**
- shipped:   quissly > doofinder > luigisbox > clerk > algolia
- corrected: quissly > luigisbox > doofinder > clerk > algolia
  - quissly: shipped 78.61 → corrected 65.93
  - doofinder: shipped 75.34 → corrected 55.78
  - luigisbox: shipped 73.67 → corrected 55.90
  - clerk: shipped 69.06 → corrected 51.01
  - algolia: shipped 61.54 → corrected 48.17

### The audit's medium-tier @20 Quissly/Doofinder flip

- corrected medium@20: quissly 70.75 vs doofinder 56.00 → **flip does NOT persist: quissly ahead** (margin 14.75pp)
- shipped medium@20 was: quissly 77.19 vs doofinder 75.04

Reconciliation: the shipped column reproduces the audited pipeline values in every cell exactly (worst |diff| = 0.00e+00 pp).
