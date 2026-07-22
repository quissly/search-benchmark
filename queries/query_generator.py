import os
import json
import re
import sys
import time
import math
import random
from pathlib import Path
from dotenv import load_dotenv
from google import genai

load_dotenv(Path(__file__).parent.parent / ".env")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
if not GEMINI_API_KEY:
    sys.exit("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=GEMINI_API_KEY)

OUTPUT_DIR = Path(__file__).parent / "query_outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

CATEGORIES = [
    "fashion",
    "furniture",
    "electronics",
    "marketplace",
    "personal_care",
    "pharmaceuticals",
    "auto_parts",
    "grocery",
]

TARGET_TOTAL = 225  # midpoint of 200-250 per category
COMPLEXITY_DIST = {
    "simple": 0.30,
    "medium": 0.30,
    "complex": 0.20,
    "visual": 0.20,
}

SEED_EXAMPLES = {
    "fashion": {
        "simple":  ["jeans", "red dress", "sneakers", "t-shirt"],
        "medium":  ["men's graphic tees", "waterproof winter boots", "women's linen blazer", "slim fit chinos"],
        "complex": ["outfit for SF weather", "shoes to wear with a red dress", "business casual look for a summer wedding", "comfortable shoes for standing all day at work"],
    },
    "furniture": {
        "simple":  ["sofa", "dining table", "bookshelf", "bed frame"],
        "medium":  ["built-in wine fridge", "velvet armchair", "mid-century coffee table", "L-shaped desk"],
        "complex": ["space saving desk for a small apartment", "pet-friendly living room couch", "storage bed for a studio flat", "outdoor furniture that withstands rain"],
    },
    "electronics": {
        "simple":  ["monitor", "mechanical keyboard", "webcam", "SSD"],
        "medium":  ["noise-cancelling over ear headphones", "4K gaming monitor", "wireless ergonomic mouse", "USB-C hub for MacBook"],
        "complex": ["best laptop for graphic design", "streaming camera under $500", "home office setup for video calls", "cheap tablet for college note-taking"],
    },
    "marketplace": {
        "simple":  ["backpack", "coffee mug", "candles", "notebook"],
        "medium":  ["stainless steel water bottle", "cast iron skillet", "leather card wallet", "bamboo cutting board"],
        "complex": ["books about domestic animals for $50", "gift for a 10 year old boy", "eco-friendly kitchen starter kit under $100", "white elephant gift under $25"],
    },
    "personal_care": {
        "simple":  ["sunscreen", "shampoo", "moisturizer", "deodorant"],
        "medium":  ["skincare for acne", "sulfate-free curl cream", "vitamin C serum for dark spots", "reef-safe SPF 50 sunscreen"],
        "complex": ["routine for severe dry winter skin", "fragrance-free sensitive face wash", "simple morning skincare for oily skin", "hair care for color-treated curly hair"],
    },
    "pharmaceuticals": {
        "simple":  ["ibuprofen", "allergy pills", "antacid", "melatonin"],
        "medium":  ["children's cough syrup", "non-drowsy antihistamine", "probiotic for digestive health", "vitamin D3 2000 IU"],
        "complex": ["medicine for a migraine that won't cause sleepiness", "relief for sore throat and fever", "safe antacid for pregnancy heartburn", "allergy medicine that doesn't make you groggy"],
    },
    "auto_parts": {
        "simple":  ["spark plugs", "wiper blades", "oil filter", "brake pads"],
        "medium":  ["ceramic brake pads", "12v car battery", "synthetic 5W-30 motor oil", "cabin air filter for Toyota Camry"],
        "complex": ["best windshield wipers for heavy snow", "how to fix a squeaking alternator belt", "affordable tires for highway driving", "battery for cold weather starts"],
    },
    "grocery": {
        "simple":  ["milk", "apples", "eggs", "bread"],
        "medium":  ["organic whole milk", "gluten-free pasta", "free-range chicken breast", "dark roast ground coffee"],
        "complex": ["ingredients for a vegan lasagna", "school snacks for a peanut allergy", "quick weeknight dinner ingredients under $20", "healthy meal prep items for one person"],
    },
}

COMPLEXITY_PROMPTS = {
    "simple": (
        "Generate {n} SIMPLE search queries for the '{category}' category.\n"
        "Rules: 1-2 words only. Must be exact product names or very broad categories.\n"
        "Examples: {examples}\n"
        "Return ONLY a JSON array of strings. No explanations."
    ),
    "medium": (
        "Generate {n} MEDIUM search queries for the '{category}' category.\n"
        "Rules: 3-4 words. Must include at least one specific attribute such as gender, material, condition, size, or feature.\n"
        "Examples: {examples}\n"
        "Return ONLY a JSON array of strings. No explanations."
    ),
    "complex": (
        "Generate {n} COMPLEX natural-language search queries for the '{category}' category.\n"
        "Rules: Full intent phrases. Must be one of: problem-solution, relational ('X to go with Y'), budget-constrained ('under $N'), or situational ('for [occasion/environment]').\n"
        "Examples: {examples}\n"
        "Return ONLY a JSON array of strings. No explanations."
    ),
}


def compute_counts(total: int) -> dict[str, int]:
    counts = {c: math.floor(total * pct) for c, pct in COMPLEXITY_DIST.items()}
    remainder = total - sum(counts.values())
    for c in list(COMPLEXITY_DIST.keys())[:remainder]:
        counts[c] += 1
    return counts


def extract_json_array(text: str) -> list:
    match = re.search(r"\[.*?\]", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(text.strip())


def generate_text_queries(category: str, complexity: str, n: int) -> list[str]:
    examples = ", ".join(f'"{e}"' for e in SEED_EXAMPLES[category][complexity])
    prompt = COMPLEXITY_PROMPTS[complexity].format(
        n=n, category=category.replace("_", " "), examples=examples
    )
    for attempt in range(4):
        try:
            response = client.models.generate_content(model="gemini-2.5-pro", contents=prompt)
            queries = extract_json_array(response.text or "")
            if isinstance(queries, list) and len(queries) >= n * 0.8:
                return [str(q).strip() for q in queries[:n]]
        except Exception as e:
            print(f"  Attempt {attempt + 1} failed: {e}")
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"Failed to generate {complexity} queries for {category}")


def build_query_objects(category: str, counts: dict[str, int], start_id: int) -> list[dict]:
    records = []
    qid = start_id

    for complexity, n in counts.items():
        if complexity == "visual":
            for _ in range(n):
                records.append({
                    "query_id": f"q_{qid:04d}",
                    "category": category,
                    "complexity": "visual",
                    "text_query": None,
                    "image_url": "PLACEHOLDER",
                })
                qid += 1
            continue

        print(f"  Generating {n} {complexity} queries …")
        texts = generate_text_queries(category, complexity, n)
        for text in texts:
            records.append({
                "query_id": f"q_{qid:04d}",
                "category": category,
                "complexity": complexity,
                "text_query": text,
                "image_url": None,
            })
            qid += 1
        time.sleep(2)

    random.shuffle(records)
    return records


def main():
    all_queries = []
    global_id = 1

    for category in CATEGORIES:
        print(f"\n[{category}]")
        counts = compute_counts(TARGET_TOTAL)
        print(f"  Distribution: {counts}")
        queries = build_query_objects(category, counts, global_id)
        global_id += len(queries)
        all_queries.extend(queries)

        out_path = OUTPUT_DIR / f"{category}_queries.json"
        out_path.write_text(json.dumps(queries, indent=2, ensure_ascii=False))
        print(f"  Saved {len(queries)} queries → {out_path.name}")

    combined_path = OUTPUT_DIR / "queries.json"
    combined_path.write_text(json.dumps(all_queries, indent=2, ensure_ascii=False))
    print(f"\nDone. {len(all_queries)} total queries saved to {combined_path}")


if __name__ == "__main__":
    main()
