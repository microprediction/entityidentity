# LLM Classification Cost Estimates

## Pricing (as of September 2024)

### OpenAI GPT-4o
- **Input**: $2.50 per 1M tokens
- **Output**: $10.00 per 1M tokens

### OpenAI GPT-4o-mini
- **Input**: $0.15 per 1M tokens
- **Output**: $0.60 per 1M tokens

### Anthropic Claude 3 Haiku
- **Input**: $0.25 per 1M tokens
- **Output**: $1.25 per 1M tokens

## Token Usage Per Company

### Prompt Size (Input)
- System prompt: ~300 tokens
- Sector definitions: ~600 tokens
- Company info: ~50 tokens
- **Total input per company**: ~950 tokens

### Response Size (Output)
- JSON response: ~150 tokens
- **Total output per company**: ~150 tokens

### Total per Company
- **Input**: 950 tokens
- **Output**: 150 tokens
- **Total**: 1,100 tokens per company

## Cost Estimates by Dataset Size

### Small Dataset (1,000 companies)
| Model | Input Cost | Output Cost | Total Cost | Time (est) |
|-------|-----------|-------------|------------|------------|
| GPT-4o | $2.38 | $1.50 | **$3.88** | 10-15 min |
| GPT-4o-mini | $0.14 | $0.09 | **$0.23** | 10-15 min |
| Claude Haiku | $0.24 | $0.19 | **$0.43** | 10-15 min |

### Medium Dataset (10,000 companies)
| Model | Input Cost | Output Cost | Total Cost | Time (est) |
|-------|-----------|-------------|------------|------------|
| GPT-4o | $23.75 | $15.00 | **$38.75** | 2-3 hours |
| GPT-4o-mini | $1.43 | $0.90 | **$2.33** | 2-3 hours |
| Claude Haiku | $2.38 | $1.88 | **$4.26** | 2-3 hours |

### Large Dataset (100,000 companies)
| Model | Input Cost | Output Cost | Total Cost | Time (est) |
|-------|-----------|-------------|------------|------------|
| GPT-4o | $237.50 | $150.00 | **$387.50** | 20-30 hours |
| GPT-4o-mini | $14.25 | $9.00 | **$23.25** | 20-30 hours |
| Claude Haiku | $23.75 | $18.75 | **$42.50** | 20-30 hours |

### GLEIF Full Dataset (~2.5M companies)
| Model | Input Cost | Output Cost | Total Cost | Time (est) |
|-------|-----------|-------------|------------|------------|
| GPT-4o | $5,937.50 | $3,750.00 | **$9,687.50** | 20-25 days |
| GPT-4o-mini | $356.25 | $225.00 | **$581.25** | 20-25 days |
| Claude Haiku | $593.75 | $468.75 | **$1,062.50** | 20-25 days |

## Cost Reduction Strategies

### 1. Use GPT-4o-mini (Recommended)
- **95% cheaper** than GPT-4o
- Still very accurate for classification tasks
- **Best value**: $0.23 per 1,000 companies

### 2. Caching (Built-in)
- Classifications are cached to `.cache/companies/classifications.json`
- Re-running on same data: **$0** (uses cache)
- Only new/changed companies are processed

### 3. Batch Processing
- Process in chunks (default: 100 companies per batch)
- Resume from cache if interrupted
- No duplicate work

### 4. Pre-filtering
- Use keyword-based filter first (free, instant)
- Only classify ambiguous cases with LLM
- Can reduce dataset by 50-70%

### 5. Hybrid Approach (Recommended)
```bash
# Step 1: Quick keyword filter (free, instant)
python -m entityidentity.companies.companyfilter \
  --input full_data.parquet \
  --output potential_matches.parquet \
  --strategy keyword

# Step 2: LLM classification on smaller set
python -m entityidentity.companies.companyfilter \
  --input potential_matches.parquet \
  --output final_matches.parquet \
  --provider openai
```

**Hybrid cost for 2.5M companies**:
- Keyword filter: ~500K potential matches (free)
- LLM classify 500K: ~$116 (GPT-4o-mini)
- **Total: $116** vs $581 (83% savings)

## Real-World Example: Mining Companies Only

### Expected Reduction
- Total companies in GLEIF: 2.5M
- Mining/energy/manufacturing: ~5-10% = 125K-250K
- **Estimated cost**: $29-58 (GPT-4o-mini)

### With Caching
- First run: $29-58
- Subsequent updates: Only new companies
- Monthly updates: ~$2-5 (only new registrations)

## Recommendations

1. **Start small**: Test on 1,000 companies first ($0.23)
2. **Use GPT-4o-mini**: Best cost/performance ratio
3. **Enable caching**: Saves $$$ on reruns
4. **Hybrid approach**: Pre-filter with keywords
5. **Batch processing**: Process overnight/weekend for large datasets

## Rate Limits

### OpenAI (Tier 1)
- 500 requests/min
- ~30K companies/hour
- Full GLEIF: ~85 hours

### Anthropic (Free Tier)
- 50 requests/min  
- ~3K companies/hour
- Upgrade for faster processing

## Summary

For your use case (metals value chain):
- **Dataset size**: ~250K companies (after filtering)
- **Recommended model**: GPT-4o-mini
- **Estimated cost**: ~$58 one-time
- **Monthly updates**: ~$2-5
- **Processing time**: 8-10 hours

**ROI**: Manual classification of 250K companies would take months and cost tens of thousands in labor. LLM classification: $58 and done overnight.

