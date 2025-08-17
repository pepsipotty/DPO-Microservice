#!/usr/bin/env python3
"""
Toy Novalto Dataset Generator

This tool generates a small, valid Novalto dataset for testing purposes.
The generated dataset contains realistic prompts and responses that can be
used for validation, testing, and development.

Usage:
    python tools/make_toy_novalto.py --out <output_path>

Example:
    python tools/make_toy_novalto.py --out data/dataset.json
    python tools/make_toy_novalto.py --out test_data.json --size 5
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any


def generate_toy_dataset(size: int = 10) -> List[Dict[str, Any]]:
    """
    Generate a toy dataset with realistic prompts and responses.
    
    Args:
        size: Number of prompt-response entries to generate
        
    Returns:
        List of dataset entries in Novalto format
    """
    
    # Template prompts and responses for different scenarios
    templates = [
        {
            "prompt": "\n\nHuman: What is the capital of France?\n\nAssistant:",
            "responses": [
                " The capital of France is Paris. It's located in the north-central part of the country and is known for its iconic landmarks like the Eiffel Tower, Louvre Museum, and Notre-Dame Cathedral.",
                " Paris is the capital city of France.",
                " The capital is Paris, which is also the largest city in France with over 2 million residents in the city proper."
            ],
            "pairs": [[0, 1], [0, 2], [2, 1]],
            "sft_target": " The capital of France is Paris. It's located in the north-central part of the country and is known for its iconic landmarks like the Eiffel Tower, Louvre Museum, and Notre-Dame Cathedral."
        },
        {
            "prompt": "\n\nHuman: Can you explain what machine learning is?\n\nAssistant:",
            "responses": [
                " Machine learning is a subset of artificial intelligence that enables computers to learn and improve from data without being explicitly programmed for each task.",
                " ML is when computers learn stuff from data.",
                " Machine learning involves algorithms that can identify patterns in data and make predictions or decisions based on those patterns. It's widely used in applications like recommendation systems, image recognition, and natural language processing."
            ],
            "pairs": [[2, 0], [0, 1], [2, 1]],
            "sft_target": " Machine learning involves algorithms that can identify patterns in data and make predictions or decisions based on those patterns. It's widely used in applications like recommendation systems, image recognition, and natural language processing."
        },
        {
            "prompt": "\n\nHuman: How do I make a peanut butter sandwich?\n\nAssistant:",
            "responses": [
                " To make a peanut butter sandwich: 1) Take two slices of bread, 2) Spread peanut butter on one slice, 3) Optionally add jelly or jam to the other slice, 4) Put the slices together with spreads facing inward.",
                " Put peanut butter on bread and make sandwich.",
                " First, gather your ingredients: bread, peanut butter, and optionally jelly. Spread the peanut butter evenly on one slice of bread using a knife. If using jelly, spread it on the second slice. Press the slices together gently."
            ],
            "pairs": [[0, 1], [2, 1], [2, 0]],
            "sft_target": " First, gather your ingredients: bread, peanut butter, and optionally jelly. Spread the peanut butter evenly on one slice of bread using a knife. If using jelly, spread it on the second slice. Press the slices together gently."
        },
        {
            "prompt": "\n\nHuman: What are the benefits of exercise?\n\nAssistant:",
            "responses": [
                " Exercise has numerous benefits including improved cardiovascular health, stronger muscles and bones, better mental health, weight management, and increased energy levels.",
                " Exercise is good for you.",
                " Regular physical activity helps prevent chronic diseases like heart disease and diabetes, improves mood and cognitive function, enhances sleep quality, and boosts immune system function."
            ],
            "pairs": [[0, 1], [2, 1], [2, 0]],
            "sft_target": " Regular physical activity helps prevent chronic diseases like heart disease and diabetes, improves mood and cognitive function, enhances sleep quality, and boosts immune system function."
        },
        {
            "prompt": "\n\nHuman: How does photosynthesis work?\n\nAssistant:",
            "responses": [
                " Photosynthesis is the process by which plants convert sunlight, carbon dioxide, and water into glucose and oxygen. It occurs primarily in the chloroplasts of plant cells.",
                " Plants use sunlight to make food from CO2 and water.",
                " Photosynthesis involves two main stages: the light-dependent reactions that capture energy from sunlight, and the Calvin cycle that uses this energy to convert CO2 into sugar. The overall equation is: 6CO2 + 6H2O + light energy → C6H12O6 + 6O2."
            ],
            "pairs": [[2, 0], [0, 1], [2, 1]],
            "sft_target": " Photosynthesis involves two main stages: the light-dependent reactions that capture energy from sunlight, and the Calvin cycle that uses this energy to convert CO2 into sugar. The overall equation is: 6CO2 + 6H2O + light energy → C6H12O6 + 6O2."
        },
        {
            "prompt": "\n\nHuman: What is the difference between weather and climate?\n\nAssistant:",
            "responses": [
                " Weather refers to short-term atmospheric conditions in a specific location, while climate describes long-term patterns of weather over large areas and extended time periods.",
                " Weather is daily, climate is long-term patterns.",
                " Weather is what you experience day-to-day - temperature, precipitation, wind, etc. Climate is the average weather patterns for a region over many years, typically 30 years or more."
            ],
            "pairs": [[0, 1], [2, 1], [0, 2]],
            "sft_target": " Weather refers to short-term atmospheric conditions in a specific location, while climate describes long-term patterns of weather over large areas and extended time periods."
        },
        {
            "prompt": "\n\nHuman: Can you recommend a good book to read?\n\nAssistant:",
            "responses": [
                " I'd recommend 'The Alchemist' by Paulo Coelho - it's a philosophical novel about following your dreams and personal growth that many readers find inspiring.",
                " Read any book you like.",
                " For fiction, 'To Kill a Mockingbird' by Harper Lee is excellent for its powerful themes. For non-fiction, 'Sapiens' by Yuval Noah Harari offers fascinating insights into human history."
            ],
            "pairs": [[0, 1], [2, 1], [2, 0]],
            "sft_target": " For fiction, 'To Kill a Mockingbird' by Harper Lee is excellent for its powerful themes. For non-fiction, 'Sapiens' by Yuval Noah Harari offers fascinating insights into human history."
        },
        {
            "prompt": "\n\nHuman: How do I learn to play guitar?\n\nAssistant:",
            "responses": [
                " Start with basic chords like G, C, and D. Practice regularly, use online tutorials or get a teacher, and begin with simple songs before progressing to more complex pieces.",
                " Get a guitar and practice.",
                " Begin by learning proper hand positioning and basic open chords. Practice chord transitions daily, start with simple strumming patterns, and consider using apps like Yousician or taking lessons from a qualified instructor."
            ],
            "pairs": [[2, 0], [0, 1], [2, 1]],
            "sft_target": " Begin by learning proper hand positioning and basic open chords. Practice chord transitions daily, start with simple strumming patterns, and consider using apps like Yousician or taking lessons from a qualified instructor."
        },
        {
            "prompt": "\n\nHuman: What is Python programming used for?\n\nAssistant:",
            "responses": [
                " Python is used for web development, data science, artificial intelligence, automation, scientific computing, and many other applications due to its simplicity and extensive libraries.",
                " Python is for programming stuff.",
                " Python excels in data analysis with libraries like pandas and numpy, web development with frameworks like Django and Flask, machine learning with scikit-learn and TensorFlow, and automation scripting."
            ],
            "pairs": [[2, 0], [0, 1], [2, 1]],
            "sft_target": " Python excels in data analysis with libraries like pandas and numpy, web development with frameworks like Django and Flask, machine learning with scikit-learn and TensorFlow, and automation scripting."
        },
        {
            "prompt": "\n\nHuman: How can I improve my memory?\n\nAssistant:",
            "responses": [
                " To improve memory, try techniques like spaced repetition, creating associations, getting adequate sleep, exercising regularly, and practicing mindfulness meditation.",
                " Study more and sleep well.",
                " Memory improvement strategies include: breaking information into chunks, using mnemonic devices, maintaining a healthy diet rich in omega-3 fatty acids, staying mentally active with puzzles, and minimizing stress."
            ],
            "pairs": [[2, 0], [0, 1], [2, 1]],
            "sft_target": " Memory improvement strategies include: breaking information into chunks, using mnemonic devices, maintaining a healthy diet rich in omega-3 fatty acids, staying mentally active with puzzles, and minimizing stress."
        }
    ]
    
    # Generate dataset by cycling through templates
    dataset = []
    for i in range(size):
        template = templates[i % len(templates)]
        
        # Create variations by modifying the prompt slightly
        entry = template.copy()
        if i >= len(templates):
            # Add some variation to prompts for entries beyond the base templates
            variation_suffix = f" (Question {i+1})"
            entry["prompt"] = template["prompt"].replace("\n\nAssistant:", variation_suffix + "\n\nAssistant:")
        
        dataset.append(entry)
    
    return dataset


def main():
    """Main function for the toy dataset generator."""
    parser = argparse.ArgumentParser(
        description="Generate a toy Novalto dataset for testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/make_toy_novalto.py --out data/dataset.json
  python tools/make_toy_novalto.py --out test_data.json --size 5
  python tools/make_toy_novalto.py --out large_test.json --size 50 --indent 4
        """
    )
    
    parser.add_argument(
        "--out", "-o",
        required=True,
        help="Output path for the generated dataset JSON file"
    )
    
    parser.add_argument(
        "--size", "-s",
        type=int,
        default=10,
        help="Number of prompt-response entries to generate (default: 10)"
    )
    
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation level (default: 2)"
    )
    
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Overwrite output file if it exists"
    )
    
    args = parser.parse_args()
    
    # Check if output file exists
    output_path = Path(args.out)
    if output_path.exists() and not args.force:
        print(f"Error: Output file already exists: {args.out}", file=sys.stderr)
        print("Use --force to overwrite", file=sys.stderr)
        sys.exit(1)
    
    # Validate size
    if args.size <= 0:
        print("Error: Size must be a positive integer", file=sys.stderr)
        sys.exit(1)
    
    try:
        print(f"Generating toy dataset with {args.size} entries...")
        
        # Generate the dataset
        dataset = generate_toy_dataset(args.size)
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the dataset to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=args.indent, ensure_ascii=False)
        
        print(f"✓ Toy dataset generated successfully: {args.out}")
        print(f"  Entries: {len(dataset)}")
        print(f"  Total prompts: {len(dataset)}")
        
        total_responses = sum(len(entry["responses"]) for entry in dataset)
        total_pairs = sum(len(entry["pairs"]) for entry in dataset)
        print(f"  Total responses: {total_responses}")
        print(f"  Total preference pairs: {total_pairs}")
        
        # Validate the generated dataset
        print("\nValidating generated dataset...")
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from datasets import validate_dataset_file
        
        is_valid = validate_dataset_file(str(output_path), "novalto")
        if is_valid:
            print("✓ Generated dataset is valid")
        else:
            print("✗ Generated dataset failed validation", file=sys.stderr)
            sys.exit(1)
        
    except Exception as e:
        print(f"Error generating dataset: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()