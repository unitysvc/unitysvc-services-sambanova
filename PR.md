# PR Summary: BYOP Service Populator Implementation

## Overview

This PR implements a service populator system for SambaNova and other providers that generates BYOP (Bring Your Own Provider) service data from provider APIs using the `unitysvc_services` data builders.

## Changes

### 1. Update Services Script (`data/sambanova/scripts/update_services.py`)

Added/updated the following features:

- **`_current_pricing` tracking**: Stores pricing data during offering build to share with listing builder
- **`format_price()` method**: Formats prices without trailing `.0` for whole numbers (e.g., `"3"` instead of `"3.0"`)
- **Function calling code example**: Added `code-example-fc.py.j2` to code examples for LLM models
- **Full API key placeholder**: Uses full API key length for UI placeholder (removed `min()` truncation)
- **Actual `list_price` values**: Sets `list_price` to actual pricing (instead of `null`)
- **LiteLLM integration**: Fetches model pricing and context window data from LiteLLM

### 2. Service Data Migration

- **Removed**: Original non-byop service folders (14 services)
- **Added**: New `-byop` service folders with standardized naming

### 3. Generated Services (17 models)

| Model | Service Type | Pricing Found |
|-------|--------------|---------------|
| ALLaM-7B-Instruct-preview | llm | Yes |
| DeepSeek-R1-0528 | llm | Yes |
| DeepSeek-R1-Distill-Llama-70B | llm | Yes |
| DeepSeek-V3-0324 | llm | Yes |
| DeepSeek-V3.1 | llm | Yes |
| DeepSeek-V3.1-Terminus | llm | Yes |
| DeepSeek-V3.1-cb | llm | No |
| DeepSeek-V3.2 | llm | Yes |
| E5-Mistral-7B-Instruct | embedding | Yes |
| Llama-3.3-Swallow-70B-Instruct-v0.4 | llm | No |
| Llama-4-Maverick-17B-128E-Instruct | llm | Yes |
| Meta-Llama-3.1-8B-Instruct | llm | Yes |
| Meta-Llama-3.3-70B-Instruct | llm | Yes |
| Qwen3-235B | llm | No |
| Qwen3-32B | llm | No |
| Whisper-Large-v3 | prerecorded_transcription | No |
| gpt-oss-120b | llm | Yes |

## Data Format Improvements

The generated data now matches the expected format:

### Offering (`offering.json`)
```json
{
  "payout_price": {
    "type": "one_million_tokens",
    "input": "0.2",          // No trailing .0
    "output": "0.4",
    "description": "Pricing Per 1M Tokens Input/Output",
    "reference": null
  }
}
```

### Listing (`listing.json`)
```json
{
  "list_price": {
    "type": "one_million_tokens",
    "input": "0.2",
    "output": "0.4",
    "description": "Pricing Per 1M Tokens Input/Output",
    "reference": null
  },
  "documents": {
    "Python function calling code example": {
      "category": "code_example",
      "file_path": "../../docs/code-example-fc.py.j2",
      "mime_type": "python"
    }
  }
}
```

## Validation

```
✓ usvc data validate - All data files are valid!
```

## Related Repositories

The same populator pattern was applied to all 7 provider repositories:

| Repository | Models | Status |
|------------|--------|--------|
| unitysvc-services-deepseek | 2 | ✓ |
| unitysvc-services-groq | 20 | ✓ |
| unitysvc-services-mistral | 66 | ✓ |
| unitysvc-services-nebius | 45 | ✓ |
| unitysvc-services-huggingface | 20 | ✓ |
| unitysvc-services-inception | 2 | ✓ |
| unitysvc-services-sambanova | 17 | ✓ |

**Total: 172 BYOP services**

## Test Plan

- [x] Run `usvc data populate` - generates service data successfully
- [x] Run `usvc data validate` - all data files valid
- [x] Verify pricing format matches original data (no trailing `.0`)
- [x] Verify `list_price` populated with actual values
- [x] Verify function calling code example included
- [x] Push to remote repository
