#!/usr/bin/env python3
"""
Simplified update_services.py for SambaNova using unitysvc_services data builders.

Usage: scripts/update_services.py [--force]
"""

import json
import os
import sys
from pathlib import Path

import any_llm
import requests

from unitysvc_services import ListingDataBuilder, OfferingDataBuilder

# Configuration
PROVIDER_NAME = "sambanova"
DISPLAY_NAME = "SambaNova Systems"
API_BASE_URL = "https://api.sambanova.ai/v1"
ENV_API_KEY_NAME = "SAMBANOVA_API_KEY"

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR.parent / "services"


class LiteLLMDataFetcher:
    """Fetches model pricing data from LiteLLM."""

    def __init__(self):
        self.session = requests.Session()
        self._data = None

    def fetch(self) -> dict:
        if self._data is not None:
            return self._data
        url = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
        try:
            print("Fetching LiteLLM model data...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            self._data = response.json()
            print(f"  Found {len(self._data)} models in LiteLLM data")
            return self._data
        except (requests.RequestException, json.JSONDecodeError) as e:
            print(f"Warning: Failed to fetch LiteLLM model data: {e}")
            self._data = {}
            return self._data

    def lookup(self, model_id: str) -> dict | None:
        data = self.fetch()
        if not data:
            return None
        provider_key = f"{PROVIDER_NAME}/{model_id}"
        if provider_key in data:
            return data[provider_key]
        if model_id in data:
            return data[model_id]
        for key in data:
            if model_id in key or key.endswith(f"/{model_id}"):
                return data[key]
        return None


class ModelExtractor:
    """Extract model data and create service files."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.litellm = LiteLLMDataFetcher()
        self.stats = {"total": 0, "processed": 0, "skipped": 0, "failed": 0, "pricing_found": 0}

    def get_all_models(self) -> list:
        print(f"Fetching models from {DISPLAY_NAME} API...")
        try:
            models = any_llm.list_models(PROVIDER_NAME, api_key=self.api_key)
            print(f"Found {len(models)} models")
            return models
        except Exception as e:
            print(f"Error listing models: {e}")
            return []

    def determine_service_type(self, model_id: str) -> str:
        model_lower = model_id.lower()
        if any(kw in model_lower for kw in ["embed", "embedding"]):
            return "embedding"
        if any(kw in model_lower for kw in ["rerank"]):
            return "rerank"
        if any(kw in model_lower for kw in ["vision"]):
            return "vision_language_model"
        if any(kw in model_lower for kw in ["whisper"]):
            return "prerecorded_transcription"
        return "llm"

    def get_code_examples(self, model_id: str) -> list[tuple[str, str, str]]:
        model_lower = model_id.lower()
        if any(kw in model_lower for kw in ["whisper"]):
            return [
                ("Python code example", "../../docs/code-example-prerecordedtranscription.py.j2", "python"),
                ("JavaScript code example", "../../docs/code-example-prerecordedtranscription.js.j2", "javascript"),
                ("cURL code example", "../../docs/code-example-prerecordedtranscription.sh.j2", "bash"),
            ]
        return [
            ("Python code example", "../../docs/code-example.py.j2", "python"),
            ("JavaScript code example", "../../docs/code-example.js.j2", "javascript"),
            ("cURL code example", "../../docs/code-example.sh.j2", "bash"),
        ]

    def build_offering(self, model_id: str, model_info: dict) -> OfferingDataBuilder:
        service_type = self.determine_service_type(model_id)
        display_name = model_id.replace("-", " ").replace("_", " ").title()

        builder = (
            OfferingDataBuilder(model_id)
            .set_description(f"{display_name} language model")
            .set_display_name(display_name)
            .set_service_type(service_type)
            .set_status("ready")
            .add_tag("byop")
        )

        litellm_details = self.litellm.lookup(model_id)
        if litellm_details:
            for field in ["max_tokens", "max_input_tokens", "max_output_tokens", "mode"]:
                if field in litellm_details:
                    builder.add_detail(field, litellm_details[field])
            if "max_input_tokens" in litellm_details:
                builder.add_detail("contextLength", litellm_details["max_input_tokens"])
            if "litellm_provider" in litellm_details:
                builder.add_detail("litellm_provider", litellm_details["litellm_provider"])
            if "input_cost_per_token" in litellm_details and "output_cost_per_token" in litellm_details:
                input_price = float(litellm_details["input_cost_per_token"]) * 1_000_000
                output_price = float(litellm_details["output_cost_per_token"]) * 1_000_000
                builder.set_payout_price({
                    "type": "one_million_tokens",
                    "input": str(input_price),
                    "output": str(output_price),
                    "description": "Pricing Per 1M Tokens Input/Output",
                    "reference": None,
                })
                self.stats["pricing_found"] += 1

        if "owned_by" in model_info:
            builder.add_detail("owned_by", model_info["owned_by"])
        if "object" in model_info:
            builder.add_detail("object", model_info["object"])

        builder.add_upstream_interface(f"{DISPLAY_NAME} API", base_url=API_BASE_URL, rate_limits=[])
        return builder

    def build_listing(self, model_id: str) -> ListingDataBuilder:
        placeholder = "x" * min(len(self.api_key), 40) if self.api_key else "x" * 40

        builder = (
            ListingDataBuilder()
            .set_status("ready")
            .add_user_interface("Provider API", base_url=f"${{GATEWAY_BASE_URL}}/p/{PROVIDER_NAME}")
        )

        for title, path, mime_type in self.get_code_examples(model_id):
            builder.add_code_example(title, path, mime_type=mime_type, description="Example code to use the model")

        builder.set_raw("user_parameters_schema", {
            "title": "Be Your Own Provider",
            "description": "Access service with your own api-key",
            "type": "object",
            "required": ["apikey"],
            "properties": {"apikey": {"type": "string", "title": "API Key", "default": ""}},
        })
        builder.set_raw("user_parameters_ui_schema", {
            "apikey": {
                "ui:autofocus": True,
                "ui:emptyValue": "",
                "ui:placeholder": placeholder,
                "ui:autocomplete": "family-name",
                "ui:enableMarkdownInDescription": False,
                "ui:description": f"API Key known as {ENV_API_KEY_NAME}",
            }
        })
        builder.set_raw("service_options", {"default_parameters": {"apikey": self.api_key}})
        builder.set_raw("list_price", None)
        return builder

    def process_model(self, model, output_dir: Path, force: bool) -> bool:
        model_info = json.loads(model.to_json())
        model_id = model_info.get("id", str(model))
        dir_name = model_id.replace(":", "_").replace("/", "_") + "-byop"
        data_dir = output_dir / dir_name

        offering = self.build_offering(model_id, model_info)
        listing = self.build_listing(model_id)

        offering_written = offering.write(data_dir / "offering.json", force=force)
        listing_written = listing.write(data_dir / "listing.json", force=force)

        status = []
        if offering_written:
            status.append("offering")
        if listing_written:
            status.append("listing")
        print(f"  {'Written: ' + ', '.join(status) if status else 'Unchanged'}")
        return True

    def run(self, force: bool = False):
        print(f"Starting {DISPLAY_NAME} model extraction...\n")
        models = self.get_all_models()
        if not models:
            print("No models to process.")
            return

        self.stats["total"] = len(models)
        for i, model in enumerate(models, 1):
            model_info = json.loads(model.to_json())
            model_id = model_info.get("id", str(model))
            print(f"\n[{i}/{len(models)}] {model_id}")

            dir_name = model_id.replace(":", "_").replace("/", "_") + "-byop"
            if not force and (OUTPUT_DIR / dir_name / "offering.json").exists():
                print("  Skipped - exists (use --force)")
                self.stats["skipped"] += 1
                continue

            if self.process_model(model, OUTPUT_DIR, force):
                self.stats["processed"] += 1
            else:
                self.stats["failed"] += 1

        print(f"\nDone! Total: {self.stats['total']}, Processed: {self.stats['processed']}, "
              f"Skipped: {self.stats['skipped']}, Failed: {self.stats['failed']}, "
              f"Pricing found: {self.stats['pricing_found']}")


def main():
    force = "--force" in sys.argv
    api_key = os.environ.get(ENV_API_KEY_NAME)
    if not api_key:
        print(f"Error: {ENV_API_KEY_NAME} not set")
        sys.exit(1)
    ModelExtractor(api_key).run(force=force)


if __name__ == "__main__":
    main()
